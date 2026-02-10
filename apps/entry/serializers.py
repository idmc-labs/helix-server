import typing
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import CharField

from apps.contrib.serializers import (
    IntegerIDField,
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
)
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.entry.models import (
    DisaggregatedAge,
    Entry,
    Figure,
    FigureLocation,
    FigureTag,
)
from apps.review.models import UnifiedReviewComment
from utils.common import round_half_up
from utils.validations import is_child_parent_dates_valid, is_child_parent_inclusion_valid

from .utils import (
    BulkUpdateFigureManager,
    get_event_notification_type,
    get_figure_notification_type,
    send_figure_notifications,
)


def xor(a: typing.Any, b: typing.Any):
    return bool(a) ^ bool(b)


class DisaggregatedAgeSerializer(serializers.ModelSerializer):
    # to allow updating
    id = IntegerIDField(required=False)

    class Meta:
        model = DisaggregatedAge
        fields = "__all__"
        extra_kwargs = {
            "uuid": {"validators": [], "required": True},
            "age_to": {"required": True, "allow_null": False},
            "age_from": {"required": True, "allow_null": False},
            "value": {"required": True, "allow_null": False},
        }


class DisaggregatedStratumSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(required=True)
    date = serializers.DateField(required=True)
    value = serializers.IntegerField(validators=[MinValueValidator(0, _("Minimum value is 1. "))], required=True)

    def validate(self, attrs: dict) -> dict:
        # in order to store into the JSONField
        attrs["uuid"] = str(attrs["uuid"])
        attrs["date"] = str(attrs["date"])
        return attrs


class FigureLocationSerializer(serializers.ModelSerializer):
    # to allow updating
    id = IntegerIDField(required=False)
    country = CharField(required=False, allow_blank=True, allow_null=True)
    geocoder_metadata = serializers.JSONField(required=False, allow_null=True)
    geocoder = serializers.ChoiceField(
        choices=FigureLocation.GEOCODER.choices(),
        required=True,
    )
    country_code = serializers.CharField(required=True)

    def validate_lat(self, lat):
        return -90 <= lat <= 90

    def validate_lng(self, lat):
        return -180 <= lat <= 180

    def validate(self, attrs: dict) -> dict:
        """
        NOTE: In some cases osmname api does not provides country,
        in this case get country from country code
        """
        if not self.instance and not attrs.get("country"):
            country_code = attrs.get("country_code").upper()
            country = Country.objects.filter(iso2__iexact=country_code).first()
            if not country:
                raise serializers.ValidationError("Country field is required.")
            attrs["country"] = country
        return attrs

    class Meta:
        model = FigureLocation
        fields = "__all__"
        extra_kwargs = {
            "uuid": {"validators": [], "required": True},
            "geocoder": {"required": True, "allow_null": False},
        }

    # NOTE: Preserving the geocoder_metadata
    def update(self, instance, validated_data):
        validated_data.pop("geocoder_metadata", None)
        return super().update(instance, validated_data)


class CommonFigureValidationMixin:
    def _validate_is_disaggregated(self, instance, attrs):
        errors = OrderedDict()

        is_disaggregated = attrs.get(
            "is_disaggregated",
            getattr(instance, "is_disaggregated", False),
        )
        if not is_disaggregated:
            attrs["disaggregation_displacement_rural"] = None
            attrs["disaggregation_displacement_urban"] = None
            attrs["disaggregation_location_camp"] = None
            attrs["disaggregation_location_non_camp"] = None
            attrs["disaggregation_disability"] = None
            attrs["disaggregation_indigenous_people"] = None
            # NOTE: hidden in ui
            attrs["disaggregation_conflict"] = None
            attrs["disaggregation_conflict_communal"] = None
            attrs["disaggregation_conflict_criminal"] = None
            attrs["disaggregation_conflict_other"] = None
            attrs["disaggregation_conflict_political"] = None
            attrs["disaggregation_sex_female"] = None
            attrs["disaggregation_sex_male"] = None
            attrs["disaggregation_lgbtiq"] = None
        else:
            errors.update(
                self._validate_disaggregated_sum_against_total_figures(
                    instance,
                    attrs,
                    ["disaggregation_location_camp", "disaggregation_location_non_camp"],
                    "camp and non-camp",
                )
            )
            errors.update(
                self._validate_disaggregated_sum_against_total_figures(
                    instance,
                    attrs,
                    ["disaggregation_displacement_urban", "disaggregation_displacement_rural"],
                    "urban and rural",
                )
            )
            errors.update(
                self._validate_disaggregated_sum_against_total_figures(
                    instance,
                    attrs,
                    ["disaggregation_disability"],
                    "disability",
                )
            )
            errors.update(
                self._validate_disaggregated_sum_against_total_figures(
                    instance,
                    attrs,
                    ["disaggregation_indigenous_people"],
                    "indigenous people",
                )
            )
            errors.update(
                self._validate_disaggregated_age_sum_against_total_figures(
                    instance,
                    attrs,
                )
            )
            errors.update(self._validate_disaggregation_age(instance, attrs))

        return errors

    def _validate_disaggregation_age(self, instance, attrs):
        errors = OrderedDict()
        age_groups = attrs.get("disaggregation_age", getattr(instance, "disaggregation_age", []))
        if not isinstance(age_groups, list):
            return errors

        values = []
        for each in age_groups:
            values.append((each.get("age_from"), each.get("age_to"), each.get("sex")))
        if len(values) != len(set(values)):
            errors.update({"disaggregation_age": "Age range and sex must be unique."})

        return errors

    def _validate_unit(self, instance, attrs):
        errors = OrderedDict()

        unit = attrs.get("unit", getattr(instance, "unit", Figure.UNIT.PERSON))
        household_size = attrs.get("household_size", getattr(instance, "household_size", 0))
        reported = attrs.get("reported", getattr(instance, "reported", 0))

        if unit == Figure.UNIT.PERSON:
            attrs["household_size"] = None
            attrs["total_figures"] = reported
        elif unit == Figure.UNIT.HOUSEHOLD:
            if not household_size:
                attrs["total_figures"] = 0
                errors.update({"household_size": "This field is required"})
            else:
                attrs["total_figures"] = round_half_up(reported * Decimal(str(household_size)))
        else:
            typing.assert_never(unit)

        return errors

    def _validate_geo_locations(self, instance, attrs):
        errors = OrderedDict()

        country = attrs.get("country", getattr(instance, "country", None))
        geo_locations = attrs.get("geo_locations", None)

        # Skip on update if geo_locations is not sent
        if instance and "geo_locations" not in attrs:
            return errors

        # Check if there are invalid location ids in attrs
        if instance and "geo_locations" in attrs:
            geo_location_ids = {geo_location["id"] for geo_location in geo_locations if "id" in geo_location}
            geo_location_ids_on_db = (
                list(instance.geo_locations.values_list("id", flat=True)) if instance.geo_locations else []
            )
            if geo_location_ids.difference(geo_location_ids_on_db):
                errors["geo_locations"] = "Some locations not found."

        # NOTE: geolocations mandatory check is already defined in kwargs
        # We can skip futher validation if geo_locations is not defined
        if not geo_locations:
            return errors

        # NOTE: A location should be inside the figure's country unless:
        # - it's moved
        # - figure's country does not have iso2
        # - figure's country is not supported by geocoder
        country_code = country.iso2
        if not country_code:
            return errors
        if country_code not in Figure.SUPPORTED_COUNTRY_CODES:
            return errors

        for location in geo_locations:
            # If location is moved manually allow to save location of other coutries
            # These locations are considered as problematic border issues
            location_moved = location.get("moved", False)
            location_country_code = location.get("country_code", "")
            if not location_moved and location_country_code.lower() != country_code.lower():
                errors.update({"geo_locations": "Location should be inside the selected figure's country"})
        return errors

    def _validate_disaggregated_sum_against_total_figures(self, instance, attrs, fields, verbose_names):
        def _format_message(fields, verbose_names):
            if len(fields) > 1:
                return f"Sum of {verbose_names} figures is greater than total figures."
            return f"{verbose_names} figures is greater than total figures."

        errors = OrderedDict()

        total_figures = attrs.get("total_figures", getattr(instance, "total_figures", 0))

        disaggregated_sum = 0
        for field in fields:
            disaggregated_sum += attrs.get(field, getattr(instance, field, 0)) or 0

        if disaggregated_sum > total_figures:
            errors.update({field: _format_message(fields, verbose_names) for field in fields})
        return errors

    def _validate_disaggregated_age_sum_against_total_figures(self, instance, attrs):
        errors = OrderedDict()

        total_figures = attrs.get("total_figures")

        age_groups = attrs.get("disaggregation_age") or getattr(instance, "disaggregation_age", [])
        if not isinstance(age_groups, list):
            return errors

        total = sum([age_group["value"] for age_group in age_groups])

        if total > total_figures:
            errors.update({"disaggregation_age": "Sum of age figures is greater than total figures."})
        return errors

    def _validate_event_country(self, instance, attrs):
        errors = OrderedDict()

        event = attrs.get("event", getattr(instance, "event", None))

        if event:
            errors.update(
                is_child_parent_inclusion_valid(
                    attrs,
                    instance,
                    "country",
                    "event.countries",
                )
            )
        return errors

    def _validate_event_dates(self, instance, attrs):
        errors = OrderedDict()
        event = attrs.get("event", getattr(instance, "event", None))

        if event:
            errors.update(
                is_child_parent_dates_valid(
                    attrs.get("start_date", getattr(instance, "start_date", None)),
                    attrs.get("end_date", getattr(instance, "end_date", None)),
                    event.start_date,
                    "event",
                )
            )
        return errors

    def _validate_idu(self, instance, attrs):
        errors = OrderedDict()

        include_idu = attrs.get("include_idu", getattr(instance, "include_idu", None))

        if include_idu:
            excerpt_idu = attrs.get("excerpt_idu", getattr(instance, "excerpt_idu", None))
            if excerpt_idu is None or not excerpt_idu.strip():
                errors["excerpt_idu"] = gettext("This field is required.")
        else:
            attrs["excerpt_idu"] = None

        return errors

    def _validate_figure_cause(self, instance, attrs):
        errors = OrderedDict()

        # Skip on update if not provided
        if instance and "figure_cause" not in attrs:
            return errors

        event = attrs.get("event", getattr(instance, "event", None))
        figure_cause = attrs.get("figure_cause", getattr(instance, "figure_cause", None))

        if figure_cause == Crisis.CRISIS_TYPE.CONFLICT:
            # clear disaster fields
            attrs["disaster_category"] = None
            attrs["disaster_type"] = None
            attrs["disaster_sub_category"] = None
            attrs["disaster_sub_type"] = None
            # clear other fields
            attrs["other_sub_type"] = None

            # TODO: clear osv_sub_type when it's not applicable

            violence_sub_type = attrs.get("violence_sub_type", getattr(instance, "violence_sub_type", None))
            if not violence_sub_type:
                errors.update({"violence_sub_type": "This field is required"})
            else:
                attrs["violence"] = violence_sub_type.violence
        elif figure_cause == Crisis.CRISIS_TYPE.DISASTER:
            # clear conflict fields
            attrs["violence"] = None
            attrs["violence_sub_type"] = None
            attrs["context_of_violence"] = []
            attrs["osv_sub_type"] = None
            # clear other fields
            attrs["other_sub_type"] = None

            disaster_sub_type = attrs.get("disaster_sub_type", getattr(instance, "disaster_sub_type", None))
            if not disaster_sub_type:
                errors.update({"disaster_sub_type": "This field is required"})
            else:
                disaster_type = disaster_sub_type.type
                attrs["disaster_type"] = disaster_type
                if disaster_type:
                    disaster_sub_category = disaster_type.disaster_sub_category
                    attrs["disaster_sub_category"] = disaster_sub_category
                    if disaster_sub_category:
                        attrs["disaster_category"] = disaster_sub_category.category
        elif figure_cause == Crisis.CRISIS_TYPE.OTHER:
            # clear disaster fields
            attrs["disaster_category"] = None
            attrs["disaster_type"] = None
            attrs["disaster_sub_category"] = None
            attrs["disaster_sub_type"] = None
            # clear conflict fields
            attrs["violence"] = None
            attrs["violence_sub_type"] = None
            attrs["context_of_violence"] = []
            attrs["osv_sub_type"] = None

        if figure_cause and event and event.event_type.value != figure_cause:
            errors.update({"figure_cause": f"Cause should be {event.event_type.label}"})
        return errors

    def _validate_term(self, instance, attrs):
        term = attrs.get("term", getattr(instance, "term", None))

        if term not in Figure.housing_list():
            attrs["is_housing_destruction"] = None

        if term not in Figure.displacement_occur_list():
            attrs["displacement_occurred"] = None

        return OrderedDict()

    def _validate_category(self, instance, attrs):
        errors = OrderedDict()

        category = attrs.get("category", getattr(instance, "category", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))

        if category in Figure.flow_list():
            if end_date > datetime.today().date():
                errors.update({"end_date": "This must be a past date"})
        elif category in Figure.stock_list():
            attrs["end_date_accuracy"] = None

        return errors

    def validate(self, attrs: dict) -> dict:
        # FIXME: Add a note why self.instance is not used
        instance = None
        if attrs.get("id"):
            instance = Figure.objects.get(id=attrs["id"])

        attrs = super().validate(attrs)

        errors = OrderedDict()

        # NOTE: order is important
        errors.update(self._validate_idu(instance, attrs))
        errors.update(self._validate_term(instance, attrs))
        errors.update(self._validate_unit(instance, attrs))
        errors.update(self._validate_category(instance, attrs))
        errors.update(self._validate_figure_cause(instance, attrs))
        errors.update(self._validate_is_disaggregated(instance, attrs))

        errors.update(self._validate_event_dates(instance, attrs))
        errors.update(self._validate_event_country(instance, attrs))
        errors.update(self._validate_geo_locations(instance, attrs))

        if errors:
            raise ValidationError(errors)

        return attrs


class FigureTagSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = FigureTag
        fields = "__all__"


class FigureSerializer(
    MetaInformationSerializerMixin,
    CommonFigureValidationMixin,
    serializers.ModelSerializer,
):
    id = IntegerIDField(required=False)
    disaggregation_age = DisaggregatedAgeSerializer(many=True, required=False, allow_null=False)
    geo_locations = FigureLocationSerializer(many=True, required=False, allow_empty=False, allow_null=False)

    class Meta:
        model = Figure
        fields = [
            "id",
            "entry",
            "quantifier",
            "reported",
            "unit",
            "household_size",
            "category",
            "term",
            "displacement_occurred",
            "role",
            "start_date",
            "start_date_accuracy",
            "end_date",
            "end_date_accuracy",
            "include_idu",
            "excerpt_idu",
            "country",
            "is_disaggregated",
            "is_housing_destruction",
            "calculation_logic",
            "tags",
            "source_excerpt",
            "event",
            "context_of_violence",
            "figure_cause",
            "violence_sub_type",
            "disaster_sub_category",
            "disaster_sub_type",
            "other_sub_type",
            "osv_sub_type",
            "sources",
            # UUID abstract fields
            "uuid",
            # Figure disaggregation abstract fields
            "disaggregation_displacement_urban",
            "disaggregation_displacement_rural",
            "disaggregation_location_camp",
            "disaggregation_location_non_camp",
            "disaggregation_lgbtiq",
            "disaggregation_disability",
            "disaggregation_indigenous_people",
            "disaggregation_sex_male",
            "disaggregation_sex_female",
            "disaggregation_age",
            "disaggregation_conflict",
            "disaggregation_conflict_political",
            "disaggregation_conflict_criminal",
            "disaggregation_conflict_communal",
            "disaggregation_conflict_other",
            "geo_locations",
        ]
        extra_kwargs = {
            "uuid": {"validators": [], "required": True},
            "entry": {"validators": [], "required": True},
            "calculation_logic": {"required": True, "allow_blank": False, "allow_null": False},
            # FIXME: Add a validation that start_date should not be in the future
            "start_date": {"required": True, "allow_null": False},
            # FIXME: Add a validation that end_date should not be in the figure (for flow)
            "end_date": {"required": True, "allow_null": False},
            "sources": {"required": True, "allow_empty": False, "allow_null": False},
            "country": {"required": True, "allow_null": False},
            "term": {"required": True, "allow_null": False},
            "category": {"required": True, "allow_null": False},
            "role": {"required": True, "allow_null": False},
            "unit": {"required": True, "allow_null": False},
        }

    def create(self, validated_data: dict) -> Figure:
        validated_data["created_by"] = self.context["request"].user
        geo_locations = validated_data.pop("geo_locations", [])
        tags = validated_data.pop("tags", [])
        context_of_violence = validated_data.pop("context_of_violence", [])
        disaggregation_ages = validated_data.pop("disaggregation_age", [])
        sources = validated_data.pop("sources", [])
        if geo_locations:
            geo_locations = FigureLocation.objects.bulk_create([FigureLocation(**each) for each in geo_locations])

        if disaggregation_ages:
            disaggregation_ages = DisaggregatedAge.objects.bulk_create(
                [DisaggregatedAge(**age_dict) for age_dict in disaggregation_ages]
            )
        instance = Figure.objects.create(**validated_data)
        instance.geo_locations.set(geo_locations)
        instance.tags.set(tags)
        instance.context_of_violence.set(context_of_violence)
        instance.disaggregation_age.set(disaggregation_ages)
        instance.sources.set(sources)

        # Notification create
        if notification_type := get_figure_notification_type(instance.event, is_new=True):
            send_figure_notifications(instance, self.context["request"].user, notification_type)
        bulk_manager: BulkUpdateFigureManager = self.context["bulk_manager"]
        bulk_manager.add_event(instance.event_id)
        return instance

    def _update_locations(self, instance, attr: str, data: list):
        figure_locations = []
        if data:
            getattr(instance, attr).exclude(id__in=[each["id"] for each in data if "id" in each]).delete()
            for each in data:
                if not each.get("id"):
                    figure_location_serializer = FigureLocationSerializer()
                    figure_location_serializer._validated_data = {**each}
                else:
                    figure_location_serializer = FigureLocationSerializer(
                        instance=getattr(instance, attr).get(id=each["id"]), partial=True
                    )
                    figure_location_serializer._validated_data = {**each}
                figure_location_serializer._errors = {}
                figure_locations.append(figure_location_serializer.save())
        getattr(instance, attr).set(figure_locations)

    def _update_disaggregation_age(self, instance, attr: str, data: list):
        disaggregation_age = []
        if data:
            getattr(instance, attr).exclude(id__in=[each["id"] for each in data if "id" in each]).delete()
            for each in data:
                if not each.get("id"):
                    age_serializer = DisaggregatedAgeSerializer()
                    age_serializer._validated_data = {**each}
                else:
                    age_serializer = DisaggregatedAgeSerializer(
                        instance=getattr(instance, attr).get(id=each["id"]), partial=True
                    )
                    age_serializer._validated_data = {**each}
                age_serializer._errors = {}
                disaggregation_age.append(age_serializer.save())
        getattr(instance, attr).set(disaggregation_age)

    def _send_event_change_notification(self, figure, existing_event, new_event):
        # Send notifications
        # -- Delete notification
        if notification_type := get_event_notification_type(existing_event, is_figure_deleted=True):
            send_figure_notifications(
                figure,
                self.context["request"].user,
                notification_type,
                event=existing_event,
            )
        # -- Create notification
        if notification_type := get_event_notification_type(new_event, is_figure_new=True):
            send_figure_notifications(
                figure,
                self.context["request"].user,
                notification_type,
                event=new_event,
            )

    def update(self, instance: Figure, validated_data):
        validated_data["last_modified_by"] = self.context["request"].user
        # Event change tracking
        existing_event = instance.event

        with transaction.atomic():
            if "geo_locations" in validated_data:
                geo_locations = validated_data.pop("geo_locations")
                self._update_locations(instance=instance, attr="geo_locations", data=geo_locations)
            if "disaggregation_age" in validated_data:
                disaggregation_age = validated_data.pop("disaggregation_age")
                self._update_disaggregation_age(instance=instance, attr="disaggregation_age", data=disaggregation_age)
            if "tags" in validated_data:
                tags = validated_data.pop("tags")
                instance.tags.set(tags)
            if "context_of_violence" in validated_data:
                context_of_violence = validated_data.pop("context_of_violence")
                instance.context_of_violence.set(context_of_violence)
            if "sources" in validated_data:
                sources = validated_data.pop("sources")
                instance.sources.set(sources)
            instance = super().update(instance, validated_data)

        Figure.update_figure_status(instance)

        bulk_manager: BulkUpdateFigureManager = self.context["bulk_manager"]
        if existing_event != instance.event:
            # NOTE: Updating UnifiedReviewComment while changing event for the figure
            UnifiedReviewComment.objects.filter(figure=instance.id, event=existing_event).update(event_id=instance.event)
            bulk_manager.add_event(existing_event.pk)
            self._send_event_change_notification(instance, existing_event, instance.event)
        else:
            # NOTE: We do not send notification when figure is updated if
            # the figure's event has been updated
            if notification_type := get_figure_notification_type(instance.event):
                send_figure_notifications(instance, self.context["request"].user, notification_type)
        bulk_manager.add_event(instance.event_id)
        return instance


class EntryCreateSerializer(
    MetaInformationSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = Entry
        exclude = (
            "review_status",
            "old_id",
            "version_id",
        )
        extra_kwargs = {
            "publishers": {"required": True, "allow_empty": False},
        }

    def _validate_url_and_document(self, values: dict) -> OrderedDict:
        errors = OrderedDict()

        url = values.get("url", getattr(self.instance, "url", None))
        document = values.get("document", getattr(self.instance, "document", None))

        # NOTE: we do not allow updates to type of entry sources
        if self.instance and (xor(self.instance.url, url) or xor(self.instance.document, document)):
            errors["url"] = gettext("Cannot change type of the entry.")
            errors["document"] = gettext("Cannot change type of the entry.")
            return errors

        if not url and not document:
            # url and document not defined
            errors["url"] = gettext("URL or document is required.")
            errors["document"] = gettext("URL or document is required.")
        elif url and document:
            # url and document both defined
            errors["url"] = gettext("Both URL and document cannot be set.")
            errors["document"] = gettext("Both URL and document cannot be set.")
        elif not document:
            # url defined, document not defined
            values["document_url"] = None
        elif not document.is_file_uploaded:
            # url not defined, document defined
            errors["document"] = gettext("Document must be uploaded before linking to entry.")

        return errors

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        errors = OrderedDict()
        errors.update(self._validate_url_and_document(attrs))
        if errors:
            raise ValidationError(errors)
        return attrs


class EntryUpdateSerializer(UpdateSerializerMixin, EntryCreateSerializer):
    """Created for update mutation input type"""

    id = IntegerIDField(required=True)


class FigureTagCreateSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = FigureTag
        fields = "__all__"


class FigureTagUpdateSerializer(UpdateSerializerMixin, FigureTagCreateSerializer):
    id = IntegerIDField(required=True)


class FigureReadOnlySerializer(serializers.ModelSerializer):
    country = serializers.CharField(source="country_name", help_text="Short name of the country or territory.")
    iso3 = serializers.CharField(
        help_text="Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area."
    )
    latitude = serializers.FloatField(
        source="centroid_lat", help_text="Geographic coordinate in decimal degrees (latitude)."
    )
    longitude = serializers.FloatField(
        source="centroid_lon", help_text="Geographic coordinate in decimal degrees (longitude)."
    )
    centroid = serializers.CharField(help_text="Geographical center point of the data's location.")
    displacement_type = serializers.CharField(
        source="figure_cause", help_text="Identifies the trigger of displacement such as conflict or disasters."
    )
    qualifier = serializers.CharField(
        source="quantifier_label", help_text="Indicates the level of uncertainty or accuracy associated with the figure."
    )
    figure = serializers.IntegerField(source="total_figures", help_text="Total number of internal displacements (flows).")
    displacement_start_date = serializers.CharField(help_text="Approximate date when the displacement flow started.")
    displacement_end_date = serializers.CharField(help_text="Approximate date when the displacement flow ended.")
    displacement_date = serializers.CharField(help_text="Initial date when the displacement flow began.")
    event_id = serializers.IntegerField(help_text="Unique identifier for events as assigned by IDMC.")
    event_name = serializers.CharField(
        help_text="This field includes the event's coded name which is based on the country,\n"
        "type of hazard, location, and start date. "
        "It also incorporates the common or official name of the event when available."
    )
    event_codes = serializers.CharField(
        help_text="(Field description not provided in the context; consider documenting separately if needed.)"
    )
    event_code_types = serializers.CharField(
        help_text="(Field description not provided in the context; consider documenting separately if needed.)"
    )
    event_start_date = serializers.CharField(help_text="Date when the event or hazard began.")
    event_end_date = serializers.CharField(help_text="Date when the event or hazard concluded.")
    category = serializers.CharField(
        source="disaster_category_name",
        help_text="Natural Hazard category that triggered displacement based on the "
        "IRDR Peril Classification and Hazard Glossary.",
    )
    subcategory = serializers.CharField(
        source="disaster_sub_category_name", help_text="Hazard category based on the CRED EM-DAT classification."
    )
    type = serializers.CharField(source="disaster_type_name", help_text="Hazard type as categorized by CRED EM-DAT.")
    subtype = serializers.CharField(
        source="disaster_sub_type_name", help_text="Specific sub-type of the hazard based on the CRED EM-DAT."
    )
    year = serializers.IntegerField(help_text="Year in which the displacement occurred.")
    standard_popup_text = serializers.CharField(help_text="Standard text from the IDMC website for the data entry.")
    standard_info_text = serializers.CharField(help_text="Additional standard information provided by IDMC.")
    role = serializers.CharField(
        help_text="The field of data delineates the most reliable figure accessible"
        "as determined by the primary data source, "
        "the methodology employed in data collection, the scope of coverage, "
        "and the promptness of the reported information. "
        "This framework is essential in understanding two key types of figures: \n\n"
        "**Recommended Figure:** This is the figure that has been identified with "
        "the highest level of confidence or robustness to represent the population "
        "flow. It is selected based on thorough evaluation and "
        "is recommended for inclusion in our official estimates for a specific event. "
        "Such figures are crucial "
        "as they can be aggregated to facilitate detailed analysis. The role of a "
        "figure can change over time. "
        "As new data becomes available, a figure that was once a “Recommended Figure” may become outdated and "
        "be reclassified as a “Triangulation Figure”.\n\n"
        "**Triangulation Figure:** For the purposes of the IDU dataset, these entries represent often the first "
        "estimates of the magnitude of a displacement situation. These are provisional estimates reflect various "
        "updates regarding displacement situations. They are utilized until a more solid or robust estimate becomes "
        "available, especially as more data is gathered by local primary data sources."
    )
    locations_name = serializers.CharField(
        help_text="This field indicates the names of locations where displacement incidents have been reported.\n\n"
        "It is important to note that this field may exhibit a many-to-one relationship "
        "signifying that multiple location names could be associated with a single "
        "reported figure preventing disaggregation by individual location. "
        "This becomes particularly relevant in geospatial analysis, where Geographic Information System (GIS) "
        "software may interpret these multi-point entities as single data points, "
        "potentially leading to the inadvertent double-counting of figures. "
        "To mitigate this issue, it's advisable to preprocess the dataset by "
        "either dividing the total figure by the number of locations "
        "or distributing the 'Total figures' values based on a weighting factor such as population density. "
        "This ensures a more accurate representation of the displacement data across "
        "individual locations and prevents duplication of figures during analysis."
    )
    locations_coordinates = serializers.CharField(
        help_text="This field contains geographic coordinates representing the reported locations. "
        "Please note that this field contains multipoints, meaning that multiple locations may represent one figures. "
        "It's important to note that this field may exhibit a many-to-one relationship signifying that multiple location "
        "names could be associated with a single reported figure preventing disaggregation by individual location. "
        "This becomes particularly relevant in geospatial analysis, where Geographic Information System (GIS) software "
        "may interpret these multi-point entities as single data points, potentially leading "
        "to the inadvertent double-counting of figures. To mitigate this issue, it's "
        "advisable to preprocess the dataset by either dividing the total figure by the number of locations "
        "or distributing the 'Total figures' values based on a weighting factor "
        "such as population density. This ensures a more accurate representation of the displacement "
        "data across individual locations and prevents duplication of figures during analysis."
    )
    locations_accuracy = serializers.CharField(
        help_text="This field indicates the estimated precision of the reported "
        "locations. It serves as a clue to the likely administrative unit level (e.g. "
        "country, state, district) used for reporting."
    )
    locations_type = serializers.CharField(
        help_text="This field specifies the type of displacement location within a reported event. It can indicate:\n\n"
        "**Origin:** The place where people were displaced from \n\n"
        "**Destination:** The location where displaced people arrived.\n\n"
        "**Both:** In some cases both origin and destination information might be included. \n\n"
        "It's crucial to note that different locations reported for a single figure may "
        "pertain to both the origin and destination of displacement incidents. This "
        "distinction is particularly salient in geospatial analysis where Geographic "
        "Information System (GIS) software may interpret these multi-point entities as "
        "singular data points potentially resulting in inadvertent double-counting of "
        "figures. To mitigate this issue, it is recommended to preprocess the dataset "
        "prior to GIS analysis to ensure accurate representation and avoid duplication "
        "of figures."
    )
    displacement_occurred = serializers.CharField(
        source="displacement_occurred_transformed",
        help_text="This field contains values that represent if preventive evacuations were reported."
        "These evacuations are the result of existing early warning systems.",
    )
    old_id = serializers.CharField(help_text="Legacy identifier for the data entry.")
    sources = serializers.CharField(
        source="sources_name",
        help_text="This field lists the names of the primary data providers "
        "or the original sources for the internal displacement data reported by IDMC.",
    )
    source_url = serializers.CharField(source="entry_url_or_document_url", help_text="URL of the source reported.")
    created_at = serializers.DateTimeField(help_text="Date when the data entry was created.")

    class Meta:
        model = Figure
        fields = (
            "id",
            "country",
            "iso3",
            "latitude",
            "longitude",
            "centroid",
            "role",
            "displacement_type",
            "qualifier",
            "figure",
            "displacement_date",
            "displacement_start_date",
            "displacement_end_date",
            "year",
            "event_id",
            "event_name",
            "event_codes",
            "event_code_types",
            "event_start_date",
            "event_end_date",
            "category",
            "subcategory",
            "type",
            "subtype",
            "standard_popup_text",
            "standard_info_text",
            "old_id",
            "sources",
            "source_url",
            "locations_name",
            "locations_coordinates",
            "locations_accuracy",
            "locations_type",
            "displacement_occurred",
            "created_at",
        )
