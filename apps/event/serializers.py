import typing
from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db.models import Max, Min, Q
from django.utils.translation import gettext
from rest_framework import serializers
from typing_extensions import assert_never

from apps.contrib.serializers import (
    IntegerIDField,
    MetaInformationSerializerMixin,
    UpdateSerializerMixin,
)
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.event.models import Actor, ContextOfViolence, Event, EventCode
from apps.notification.models import Notification
from utils.validations import (
    is_child_parent_dates_valid,
    is_child_parent_inclusion_valid,
    is_date_within_future_bound,
)


class ActorSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = "__all__"


class ActorUpdateSerializer(UpdateSerializerMixin, ActorSerializer):
    """Just to create input type"""

    id = IntegerIDField(required=True)


class EventCodeSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EventCode
        fields = ["country", "uuid", "event_code", "event_code_type"]
        extra_kwargs = {
            "uuid": {"validators": [], "required": True},
        }


class EventCodeUpdateSerializer(serializers.ModelSerializer):
    id = IntegerIDField(required=False)

    class Meta:
        model = EventCode
        exclude = ["event"]
        extra_kwargs = {
            "uuid": {"validators": [], "required": True},
        }


class EventSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    event_codes = EventCodeSerializer(many=True, required=False)

    class Meta:
        model = Event
        exclude = (
            "assigner",
            "assigned_at",
            "review_status",
            "glide_numbers",
            "assignee",
            "disaster_category",
            "disaster_type",
            "ignore_qa",
            "old_id",
            "version_id",
            "violence",
        )
        extra_kwargs = {
            "countries": {"required": True, "allow_empty": False},
            "event_narrative": {"required": True, "allow_blank": False, "allow_null": False},
        }

    def _validate_event_codes(self, attrs):
        errors = OrderedDict()
        if "event_codes" in attrs:
            event_codes = attrs.get("event_codes")
            if event_codes and len(event_codes) > 50:
                errors["event_codes"] = gettext("More than 50 event codes are not allowed")
        return errors

    def _validate_violence(self, attrs):
        # clear disaster fields
        attrs["disaster_category"] = None
        attrs["disaster_type"] = None
        attrs["disaster_sub_category"] = None
        attrs["disaster_sub_type"] = None
        # clear other fields
        attrs["other_sub_type"] = None

        # TODO: clear osv_sub_type when it's not applicable

        errors = OrderedDict()
        violence_sub_type = attrs.get("violence_sub_type", self.instance and self.instance.violence_sub_type)
        if not violence_sub_type:
            errors["violence_sub_type"] = gettext("This field is required.")
        else:
            attrs["violence"] = violence_sub_type.violence
        return errors

    def _validate_other(self, attrs):
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
        attrs["actor"] = None
        return OrderedDict()

    def _validate_crisis(self, attrs):
        errors = OrderedDict()

        crisis = attrs.get("crisis", getattr(self.instance, "crisis", None))
        event_type = attrs.get("event_type", getattr(self.instance, "event_type", None))

        if not crisis:
            return errors

        errors.update(
            is_child_parent_dates_valid(
                attrs.get("start_date", getattr(self.instance, "start_date", None)),
                attrs.get("end_date", getattr(self.instance, "end_date", None)),
                crisis.start_date,
                "crisis",
            )
        )
        errors.update(
            is_child_parent_inclusion_valid(
                attrs,
                self.instance,
                field="countries",
                parent_field="crisis.countries",
            )
        )
        if crisis.crisis_type != event_type:
            errors["event_type"] = gettext("Cause should be {} to match cause of the crisis.").format(
                gettext(crisis.crisis_type.label.lower())
            )
        return errors

    def _validate_event_date_order(self, attrs):
        # NOTE: _validate_crisis also handles this validation but requires crisis and crisis.start_date
        errors = OrderedDict()
        if "start_date" not in attrs and "end_date" not in attrs:
            return errors

        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            msg = gettext("The start date must be earlier than end date.")
            if "start_date" in attrs:
                errors["start_date"] = msg
            if "end_date" in attrs:
                errors["end_date"] = msg
        return errors

    def _validate_event_future_dates(self, attrs):
        # reject event start/end dates more than N years in the future.
        errors = OrderedDict()
        if "start_date" in attrs:
            errors.update(is_date_within_future_bound(attrs["start_date"], "start_date"))
        if "end_date" in attrs:
            errors.update(is_date_within_future_bound(attrs["end_date"], "end_date"))
        return errors

    def _validate_disaster(self, attrs):
        # clear conflict fields
        attrs["violence"] = None
        attrs["violence_sub_type"] = None
        attrs["context_of_violence"] = []
        attrs["osv_sub_type"] = None
        attrs["actor"] = None
        # clear other fields
        attrs["other_sub_type"] = None

        errors = OrderedDict()
        disaster_sub_type = attrs.get("disaster_sub_type", self.instance and self.instance.disaster_sub_type)
        if not disaster_sub_type:
            errors["disaster_sub_type"] = gettext("This field is required.")
        else:
            disaster_type = disaster_sub_type.type
            attrs["disaster_type"] = disaster_type
            if disaster_type:
                disaster_sub_category = disaster_type.disaster_sub_category
                attrs["disaster_sub_category"] = disaster_sub_category
                if disaster_sub_category:
                    attrs["disaster_category"] = disaster_sub_category.category
        return errors

    def _validate_figures_countries(self, attrs):
        """
        downward validation by considering children during event update
        """
        errors = OrderedDict()
        if not self.instance:
            return errors

        countries = [each.id for each in attrs.get("countries", [])]
        if not countries:
            return errors

        figures_countries = Figure.objects.filter(country__isnull=False, event=self.instance).values_list(
            "country", flat=True
        )
        if diffs := set(figures_countries).difference(countries):
            errors["countries"] = gettext("The following countries in the figures are outside of the event: %s") % ", ".join(
                [item for item in Country.objects.filter(id__in=diffs).values_list("idmc_short_name", flat=True)]
            )

        return errors

    def _validate_figures_dates(self, attrs):
        errors = OrderedDict()
        if not self.instance:
            return errors

        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))

        _ = Figure.objects.filter(
            event=self.instance,
        ).aggregate(
            min_date=Min(
                "start_date",
                filter=Q(
                    start_date__isnull=False,
                ),
            ),
            max_date=Max("end_date", filter=Q(end_date__isnull=False, category__in=Figure.flow_list())),
        )
        min_start_date = _["min_date"]
        if start_date and (min_start_date and min_start_date < start_date):
            errors["start_date"] = gettext("The earliest start date of one of the figures is %s.") % min_start_date
        return errors

    def _update_event_codes(self, event: Event, event_codes: typing.List[typing.Dict]):
        instance_event_codes_qs = EventCode.objects.filter(event=event)

        # For empty - Delete all
        if not event_codes:
            instance_event_codes_qs.delete()
            return

        # Delete missing event_codes
        event_code_to_delete_qs = instance_event_codes_qs.exclude(
            id__in=[each["id"] for each in event_codes if each.get("id")]
        )
        event_code_to_delete_qs.delete()

        # Update provided event_codes
        for code in event_codes:
            if not code.get("id"):
                # Create new
                event_code_ser = EventCodeSerializer(context=self.context)
            else:
                # Update existing
                event_code_ser = EventCodeUpdateSerializer(
                    instance=instance_event_codes_qs.get(id=code["id"]),
                    partial=True,
                    context=self.context,
                )
            event_code_ser._validated_data = {**code, "event": event}
            event_code_ser._errors = {}
            event_code_ser.save()

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)

        errors = OrderedDict()

        event_type = attrs.get("event_type", getattr(self.instance, "event_type", None))
        if event_type == Crisis.CRISIS_TYPE.DISASTER:
            errors.update(self._validate_disaster(attrs))
        elif event_type == Crisis.CRISIS_TYPE.CONFLICT:
            errors.update(self._validate_violence(attrs))
        elif event_type == Crisis.CRISIS_TYPE.OTHER:
            errors.update(self._validate_other(attrs))
        else:
            assert_never(event_type)

        errors.update(self._validate_crisis(attrs))
        errors.update(self._validate_event_date_order(attrs))
        errors.update(self._validate_event_future_dates(attrs))

        # TODO: Validate that more than 50 event_codes cannot be assigned
        errors.update(self._validate_event_codes(attrs))

        # NOTE: we don't need to check with figures if we are just creating an event
        if self.instance:
            errors.update(self._validate_figures_countries(attrs))
            errors.update(self._validate_figures_dates(attrs))

        if errors:
            raise ValidationError(errors)

        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        countries = validated_data.pop("countries", None)
        context_of_violence = validated_data.pop("context_of_violence", None)
        event_codes = validated_data.pop("event_codes", None)
        event = Event.objects.create(**validated_data)
        if countries:
            event.countries.set(countries)
        if context_of_violence:
            event.context_of_violence.set(context_of_violence)

        if event_codes:
            for event_code in event_codes:
                EventCode.objects.create(
                    event=event,
                    country=event_code.get("country"),
                    event_code=event_code.get("event_code"),
                    event_code_type=event_code.get("event_code_type"),
                )
        context_of_violence = validated_data.pop("context_of_violence", None)
        return event

    def update(self, instance, validated_data):
        # Update event status if include_triangulation_in_qa is changed
        validated_data["last_modified_by"] = self.context["request"].user

        is_include_triangulation_in_qa_changed = False
        if "include_triangulation_in_qa" in validated_data:
            new_include_triangulation_in_qa = validated_data.get("include_triangulation_in_qa")
            is_include_triangulation_in_qa_changed = new_include_triangulation_in_qa != instance.include_triangulation_in_qa

        # Update Event Codes
        if "event_codes" in validated_data:
            self._update_event_codes(
                instance,
                validated_data.pop("event_codes"),
            )

        instance = super().update(instance, validated_data)

        if is_include_triangulation_in_qa_changed:
            recipients = [
                user["id"]
                for user in Event.regional_coordinators(
                    instance,
                    actor=self.context["request"].user,
                )
            ]
            if instance.created_by_id:
                recipients.append(instance.created_by_id)
            if instance.assignee_id:
                recipients.append(instance.assignee_id)

            Notification.send_safe_multiple_notifications(
                recipients=recipients,
                type=Notification.Type.EVENT_INCLUDE_TRIANGULATION_CHANGED,
                actor=self.context["request"].user,
                event=instance,
            )

            Figure.update_event_status_and_send_notifications(instance.id)
            instance.refresh_from_db()

        return instance


class EventUpdateSerializer(UpdateSerializerMixin, EventSerializer):
    id = IntegerIDField(required=True)
    event_codes = EventCodeUpdateSerializer(many=True, required=True)


class CloneEventSerializer(serializers.Serializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())

    def save(self, *args, **kwargs):
        event: Event = self.validated_data["event"]

        return event.clone_and_save_event(
            user=self.context["request"].user,
        )


class ContextOfViolenceSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ContextOfViolence
        fields = "__all__"


class ContextOfViolenceUpdateSerializer(UpdateSerializerMixin, ContextOfViolenceSerializer):
    """Just to create input type"""

    id = IntegerIDField(required=True)
