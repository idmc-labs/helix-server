import typing
from pathlib import Path
from typing import Optional

from django.contrib.postgres.aggregates.general import ArrayAgg, StringAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import Avg, Case, CharField, F, Func, Q, Value, When
from django.db.models.functions import Cast, Coalesce, Concat, ExtractYear, Lower
from django.shortcuts import redirect
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from openpyxl import Workbook
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.common.utils import (
    EXTERNAL_ARRAY_SEPARATOR,
    EXTERNAL_TUPLE_SEPARATOR,
    extract_event_code_data,
    extract_location_data,
)
from apps.entry.models import ExternalApiDump, Figure
from apps.entry.serializers import FigureReadOnlySerializer
from apps.gidd.views import client_id
from helix.storages import TemporaryStorageEnableAuthString, get_external_storage
from utils.common import track_gidd
from utils.db import Array

external_storage = get_external_storage()

CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "geojson": "application/geo+json",
}


def get_idu_data(filters=None):
    include_source = False
    if filters:
        include_source = filters.pop("include_source", False)

    base_query = (
        Figure.objects.annotate(
            displacement_date=Coalesce("end_date", "start_date"),
        )
        .filter(
            category__in=[
                Figure.FIGURE_CATEGORY_TYPES.RETURNEES.value,
                Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
                Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_RETURN.value,
                Figure.FIGURE_CATEGORY_TYPES.FAILED_RETURN_RETURNEE_DISPLACEMENT.value,
            ],
            excerpt_idu__isnull=False,
            include_idu=True,
            entry__is_confidential=False,
        )
        .filter(
            ~(Q(entry__document_url__isnull=True) | Q(entry__document_url=""))
            | ~(Q(entry__url__isnull=True) | Q(entry__url=""))
        )
        .annotate(
            country_name=F("country__idmc_short_name"),
            iso3=F("country__iso3"),
            figure_role=F("role"),
            centroid_lat=Avg("geo_locations__lat"),
            centroid_lon=Avg("geo_locations__lon"),
            centroid=Case(
                When(
                    centroid_lat__isnull=False,
                    then=Concat(
                        Value("["),
                        F("centroid_lat"),
                        Value(EXTERNAL_TUPLE_SEPARATOR),
                        F("centroid_lon"),
                        Value("]"),
                        output_field=CharField(),
                    ),
                ),
                default=Value(""),
            ),
            displacement_start_date=F("start_date"),
            displacement_end_date=F("end_date"),
            year=Coalesce(ExtractYear("start_date", "year"), ExtractYear("end_date", "year")),
            event_name=F("event__name"),
            event_codes=ArrayAgg(
                Array(
                    F("event__event_code__event_code"),
                    Cast(F("event__event_code__event_code_type"), CharField()),
                    output_field=ArrayField(CharField()),
                ),
                distinct=True,
                filter=Q(event__event_code__country__id=F("country__id")),
            ),
            event_start_date=F("event__start_date"),
            event_end_date=F("event__end_date"),
            disaster_category_name=F("disaster_category__name"),
            disaster_sub_category_name=F("disaster_sub_category__name"),
            disaster_type_name=F("disaster_sub_type__type__name"),
            disaster_sub_type_name=F("disaster_sub_type__name"),
            figure_term_label=Case(
                When(term=0, then=Lower(Value(Figure.FIGURE_TERMS.EVACUATED.label))),
                When(term=1, then=Lower(Value(Figure.FIGURE_TERMS.DISPLACED.label))),
                When(term=2, then=Lower(Value(Figure.FIGURE_TERMS.FORCED_TO_FLEE.label))),
                When(term=3, then=Lower(Value(Figure.FIGURE_TERMS.RELOCATED.label))),
                When(term=4, then=Lower(Value(Figure.FIGURE_TERMS.SHELTERED.label))),
                When(term=5, then=Lower(Value(Figure.FIGURE_TERMS.IN_RELIEF_CAMP.label))),
                When(term=6, then=Lower(Value(Figure.FIGURE_TERMS.DESTROYED_HOUSING.label))),
                When(term=8, then=Lower(Value(Figure.FIGURE_TERMS.PARTIALLY_DESTROYED_HOUSING.label))),
                When(term=9, then=Lower(Value(Figure.FIGURE_TERMS.UNINHABITABLE_HOUSING.label))),
                When(term=10, then=Lower(Value(Figure.FIGURE_TERMS.HOMELESS.label))),
                When(term=11, then=Lower(Value(Figure.FIGURE_TERMS.RETURNS.label))),
                When(term=12, then=Lower(Value(Figure.FIGURE_TERMS.MULTIPLE_OR_OTHER.label))),
                output_field=CharField(),
            ),
            quantifier_label=Case(
                When(quantifier=0, then=Lower(Value(Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.label))),
                When(quantifier=1, then=Lower(Value(Figure.QUANTIFIER.LESS_THAN_OR_EQUAL.label))),
                When(quantifier=2, then=Value("total")),
                When(quantifier=3, then=Lower(Value(Figure.QUANTIFIER.APPROXIMATELY.label))),
                output_field=CharField(),
            ),
            total_figures_text=Func(
                F("total_figures"), Value("999G999G999G990D"), function="to_char", output_field=CharField()
            ),
            sources_name=StringAgg("sources__name", EXTERNAL_ARRAY_SEPARATOR, distinct=True, output_field=CharField()),
            locations=ArrayAgg(
                Array(
                    F("geo_locations__display_name"),
                    Concat(
                        F("geo_locations__lat"),
                        Value(EXTERNAL_TUPLE_SEPARATOR),
                        F("geo_locations__lon"),
                        output_field=CharField(),
                    ),
                    Cast("geo_locations__accuracy", CharField()),
                    Cast("geo_locations__identifier", CharField()),
                    output_field=ArrayField(CharField()),
                ),
                distinct=True,
                filter=~Q(Q(geo_locations__display_name__isnull=True) | Q(geo_locations__display_name="")),
            ),
            displacement_occurred_transformed=Case(
                When(displacement_occurred=0, then=Value("Displacement reporting preventive evacuations")),
                When(
                    displacement_occurred__in=[1, 2, 3], then=Value("Displacement without preventive evacuations reported")
                ),
                output_field=CharField(),
            ),
            custom_figure_text=Case(
                When(
                    total_figures=1,
                    category=Figure.FIGURE_CATEGORY_TYPES.RETURN.value,
                    then=Concat(
                        F("country__idmc_short_name"),
                        Value(": "),
                        F("total_figures_text"),
                        Value(" return "),
                        Concat(Value("("), F("figure_term_label"), Value("),")),
                        Value(" "),
                        Func(F("start_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        Value(" - "),
                        Func(F("end_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        output_field=CharField(),
                    ),
                ),
                When(
                    (~Q(total_figures=1) & Q(category=Figure.FIGURE_CATEGORY_TYPES.RETURN.value)),
                    then=Concat(
                        F("country__idmc_short_name"),
                        Value(": "),
                        F("total_figures_text"),
                        Value(" returns "),
                        Concat(Value("("), F("figure_term_label"), Value("),")),
                        Value(" "),
                        Func(F("start_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        Value(" - "),
                        Func(F("end_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        output_field=CharField(),
                    ),
                ),
                When(
                    (Q(total_figures=1) & ~Q(term=Figure.FIGURE_TERMS.DISPLACED.value)),
                    then=Concat(
                        F("country__idmc_short_name"),
                        Value(": "),
                        F("total_figures_text"),
                        Value(" displacement "),
                        Concat(Value("("), F("figure_term_label"), Value("),")),
                        Value(" "),
                        Func(F("start_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        Value(" - "),
                        Func(F("end_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        output_field=CharField(),
                    ),
                ),
                When(
                    (
                        ~Q(total_figures=1)
                        & Q(
                            Q(term=Figure.FIGURE_TERMS.DISPLACED.value) | Q(term=Figure.FIGURE_TERMS.MULTIPLE_OR_OTHER.value)
                        )
                    ),
                    then=Concat(
                        F("country__idmc_short_name"),
                        Value(": "),
                        F("total_figures_text"),
                        Value(" displacements, "),
                        # THIS may be problematic
                        # Concat(Value('('), F('figure_term_label'), Value('),')),
                        # Value(' '),
                        Func(F("start_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        Value(" - "),
                        Func(F("end_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        output_field=CharField(),
                    ),
                ),
                When(
                    (~Q(total_figures=1) & ~Q(term=Figure.FIGURE_TERMS.DISPLACED.value)),
                    then=Concat(
                        F("country__idmc_short_name"),
                        Value(": "),
                        F("total_figures_text"),
                        Value(" displacements "),
                        Concat(Value("("), F("figure_term_label"), Value("),")),
                        Value(" "),
                        Func(F("start_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        Value(" - "),
                        Func(F("end_date"), Value("DD Month"), function="to_char", output_field=CharField()),
                        output_field=CharField(),
                    ),
                ),
            ),
            standard_info_text=Concat(
                Value("<b> "),
                F("custom_figure_text"),
                Value(" </b>"),
            ),
        )
        .order_by("-start_date", "-end_date")
    )

    if not include_source:
        base_query = base_query.annotate(
            entry_url_or_document_url=Value("", output_field=CharField()),
            custom_link_text=Concat(
                StringAgg("entry__publishers__name", " ", distinct=True),
                Value(" - "),
                Func(F("entry__publish_date"), Value("DD Month YYYY"), function="to_char", output_field=CharField()),
                output_field=CharField(),
            ),
            standard_popup_text=Concat(
                Value("<b> "),
                F("custom_figure_text"),
                Value(" </b> <br> "),
                F("excerpt_idu"),
                Value(" <br> "),
                F("custom_link_text"),
                output_field=CharField(),
            ),
        )
    else:
        base_query = base_query.annotate(
            entry_url_or_document_url=Case(
                When(entry__document__isnull=False, then=F("entry__document_url")),
                When(entry__document__isnull=True, then=F("entry__url")),
                output_field=CharField(),
            ),
            custom_link_text=Concat(
                Value('<a href="'),
                Case(
                    When(entry__url__isnull=False, then=F("entry__url")),
                    When(entry__document_url__isnull=False, then=F("entry__document_url")),
                ),
                Value('"'),
                Value('target="_blank">'),
                StringAgg("entry__publishers__name", " ", distinct=True),
                Value(" - "),
                Func(F("entry__publish_date"), Value("DD Month YYYY"), function="to_char", output_field=CharField()),
                Value("</a>"),
                output_field=CharField(),
            ),
            standard_popup_text=Concat(
                Value("<b> "),
                F("custom_figure_text"),
                Value(" </b> <br> "),
                F("excerpt_idu"),
                Value(" <br> "),
                F("custom_link_text"),
                output_field=CharField(),
            ),
        )

    # Apply filters if provided
    if filters:
        base_query = base_query.filter(**filters)

    for figure_data in base_query.values():
        locations_data = figure_data.pop("locations", [])
        location_parse = extract_location_data(locations_data)

        event_codes_data = figure_data.pop("event_codes", [])
        event_code_parse = extract_event_code_data(event_codes_data)

        yield {
            **figure_data,
            "locations_name": location_parse["display_name"],
            "locations_coordinates": location_parse["lat_lon"],
            "locations_accuracy": location_parse["accuracy"],
            "locations_type": location_parse["type_of_points"],
            "event_codes": event_code_parse["code"],
            "event_code_types": event_code_parse["code_type"],
        }


def get_idu_data_excel(filters=None):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("IDUS_Data")
    ws.append(
        [
            "Id",
            "Country",
            "Iso3",
            "Latitude",
            "Longitude",
            "Centroid",
            "Role",
            "DisplacementType",
            "Qualifier",
            "Figure",
            "DisplacementDate",
            "DisplacementStartDate",
            "DisplacementEndDate",
            "Year",
            "EventId",
            "EventName",
            "EventCodes",
            "EventCodeTypes",
            "EventStartDate",
            "EventEndDate",
            "Category",
            "Subcategory",
            "Type",
            "Subtype",
            "StandardPopupText",
            "StandardInfoText",
            "OldId",
            "Sources",
            "SourceUrl",
            "LocationsName",
            "LocationsCoordinates",
            "LocationsAccuracy",
            "LocationsType",
            "DisplacementOccurred",
            "CreatedAt",
        ]
    )

    if filters:
        idu_data = get_idu_data(filters)
    else:
        idu_data = get_idu_data()

    for obj in idu_data:
        serializer = FigureReadOnlySerializer(obj)
        item = dict(serializer.data)  # dict used here to solve pyright issue
        ws.append(
            [
                item["id"],
                item["country"],
                item["iso3"],
                item["latitude"],
                item["longitude"],
                item["centroid"],
                item["role"],
                item["displacement_type"],
                item["qualifier"],
                item["figure"],
                item["displacement_date"],
                item["displacement_start_date"],
                item["displacement_end_date"],
                item["year"],
                item["event_id"],
                item["event_name"],
                item["event_codes"],
                item["event_code_types"],
                item["event_start_date"],
                item["event_end_date"],
                item["category"],
                item["subcategory"],
                item["type"],
                item["subtype"],
                item["standard_popup_text"],
                item["standard_info_text"],
                item["old_id"],
                item["sources"],
                item["source_url"],
                item["locations_name"],
                item["locations_coordinates"],
                item["locations_accuracy"],
                item["locations_type"],
                item["displacement_occurred"],
                item["created_at"],
            ]
        )

    ws2 = wb.create_sheet("README")
    data_description = [
        ["ID: IDMC figure unique identifier."],
        ["Country / Territory: Short name of the country or territory."],
        ["ISO3: Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area."],
        ["Lalitude: Geographic coordinate in decimal degrees (latitude)."],
        ["Longitude: Geographic coordinate in decimal degrees (longitude)."],
        ["Centroid: Geographical center point of the data's location."],
        [
            "Role: The field of data shows the most reliable figure accessible as determined by the primary data source, "
            "the methodology used, the scope of coverage, and the timeliness of reported information. "
            "Recommended Figure: Figure with the highest confidence or robustness representing population flow. "
            "It is selected based on thorough evaluation and recommended for inclusion in official estimates for an event. "
            "Figures can be aggregated for detailed analysis. "
            "A figure's role can change over time. As new data arrives, a Recommended Figure may be reclassified as a "
            "Triangulation Figure. "
            "Triangulation Figure: Provisional estimates of displacement magnitude, used until more robust data is "
            "available."
        ],
        ["Displacement type: Identifies the trigger of displacement such as conflict or disasters."],
        ["Qualifier: Indicates the level of uncertainty or accuracy associated with the figure."],
        ["Figure: Total number of internal displacements (flows)."],
        ["Displacement date: Initial date when the displacement flow began."],
        ["Displacement start date: Approximate date when the displacement flow started."],
        ["Displacement end date: Approximate date when the displacement flow ended."],
        ["Year: Year in which the displacement occurred."],
        ["Event ID: Unique identifier for events as assigned by IDMC."],
        [
            "Event name: Event's coded name based on country, hazard type, location, and start date, "
            "and the common or official name when available."
        ],
        [
            "Event codes (Code:Type): Unique codes such as GLIDE number and other database-specific codes "
            "used to identify and track specific events across databases."
        ],
        [
            "Event codes types: Types of unique codes such as GLIDE number and other database-specific identifiers "
            "used to track events."
        ],
        ["Event start date: Event or hazard start date."],
        ["Event end date: Event or hazard end date."],
        ["Category: Hazard category based on the CRED EM-DAT classification."],
        ["Sub category: Hazard sub-category based on the CRED EM-DAT classification."],
        ["Type: Hazard type as categorized by CRED EM-DAT."],
        ["Sub-Type: Specific sub-type of the hazard based on CRED EM-DAT."],
        ["Standard popup text: Standard text from the IDMC website for the data entry."],
        ["Standard info text: Additional standard information provided by IDMC."],
        ["Old id: Legacy identifier for the data entry."],
        [
            "Sources: Names of the primary data providers or original sources for the internal displacement data reported "
            "by IDMC."
        ],
        ["Source url: URL of the reported source."],
        [
            "Locations name: Names of locations where displacement incidents were reported. Multiple names may be "
            "associated with a single figure, creating many-to-one relationships. Preprocessing is recommended."
        ],
        [
            "Locations coordinates: Geographic coordinates of reported locations. This field may contain multipoints, "
            "so multiple locations may correspond to a single figure, potentially duplicating GIS counts."
        ],
        [
            "Locations accuracy: Estimated precision of reported locations, indicating the likely administrative unit "
            "level used."
        ],
        [
            "Locations type: Specifies whether the location is origin, destination, or both. Multiple types may cause "
            "double-counting unless handled carefully."
        ],
        ["Displacement occurred: Indicates whether preventive evacuations were reported due to early warning systems."],
        ["Created at: Timestamp indicating when the data entry was created."],
    ]
    for item in data_description:
        ws2.append(item)

    return wb


def get_idu_data_geojson(filters=None):
    def format_coordinates(coordinates: typing.List[str]):
        if not coordinates:
            return []
        return coordinates.split(",")

    def remove_null_from_dict(data: dict) -> dict:
        return {key: value for key, value in data.items() if value is not None}

    if filters:
        idu_data = get_idu_data(filters)
    else:
        idu_data = get_idu_data()

    # TODO Add README
    readme_text = (
        "ID: IDMC figure unique identifier.\n"
        "\n"
        "Country / Territory: Short name of the country or territory.\n"
        "\n"
        "ISO3: Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area.\n"
        "\n"
        "Lalitude: Geographic coordinate in decimal degrees (latitude).\n"
        "\n"
        "Longitude: Geographic coordinate in decimal degrees (longitude).\n"
        "\n"
        "Centroid: Geographical center point of the data's location.\n"
        "\n"
        "Role: The field of data delineates the most reliable figure accessible as determined by the primary data source, "
        "the methodology employed in data collection, the scope of coverage, and the promptness of the reported "
        "information. This framework is essential in understanding two key types of figures: "
        "Recommended Figure: This is the figure that has been identified with the highest level of confidence or robustness "
        "to represent the population flow. It is selected based on thorough evaluation and is recommended for inclusion in "
        "official estimates for a specific event. Such figures can be aggregated to facilitate detailed analysis. "
        "The role of a figure can change over time. As new data becomes available, a figure that was once a Recommended "
        "Figure may become outdated and reclassified as a Triangulation Figure. "
        "Triangulation Figure: These entries often represent the first provisional estimates of displacement magnitude and "
        "are used until more robust data becomes available.\n"
        "\n"
        "Displacement type: Identifies the trigger of displacement such as conflict or disasters.\n"
        "\n"
        "Qualifier: Indicates the level of uncertainty or accuracy associated with the figure.\n"
        "\n"
        "Figure: Total number of internal displacements (flows).\n"
        "\n"
        "Displacement date: Initial date when the displacement flow began.\n"
        "\n"
        "Displacement start date: Approximate date when the displacement flow started.\n"
        "\n"
        "Displacement end date: Approximate date when the displacement flow ended.\n"
        "\n"
        "Year: Year in which the displacement occurred.\n"
        "\n"
        "Event ID: Unique identifier for events as assigned by IDMC.\n"
        "\n"
        "Event name: Includes the event's coded name based on the country, hazard type, location, and start date, "
        "as well as the common or official name of the event when available.\n"
        "\n"
        "Event codes (Code:Type): Unique codes such as the GLIDE number and other database-specific codes used to identify "
        "and track specific events across databases.\n"
        "\n"
        "Event codes types: Types of unique codes such as the GLIDE number and other database-specific identifiers used "
        "to track events.\n"
        "\n"
        "Event start date: Event or hazard start date.\n"
        "\n"
        "Event end date: Event or hazard end date.\n"
        "\n"
        "Category: Hazard category based on the CRED EM-DAT classification.\n"
        "\n"
        "Sub category: Hazard sub-category based on the CRED EM-DAT classification.\n"
        "\n"
        "Type: Hazard type as categorized by CRED EM-DAT.\n"
        "\n"
        "Sub-Type: Specific sub-type of the hazard based on CRED EM-DAT.\n"
        "\n"
        "Standard popup text: Standard text from the IDMC website for the data entry.\n"
        "\n"
        "Standard info text: Additional standard information provided by IDMC.\n"
        "\n"
        "Old id: Legacy identifier for the data entry.\n"
        "\n"
        "Sources: Names of the primary data providers or original sources for the internal displacement data reported "
        "by IDMC.\n"
        "\n"
        "Source url: URL of the reported source.\n"
        "\n"
        "Locations name: Names of locations where displacement incidents were reported. Multiple location names may be "
        "associated with a single figure, which can lead to double-counting in GIS analysis. Preprocessing such as dividing "
        "figures by number of locations or applying population-based weighting is recommended.\n"
        "\n"
        "Locations coordinates: Geographic coordinates representing reported locations. This field may contain multipoints, "
        "meaning multiple locations correspond to a single figure, which can lead to duplication in GIS analysis unless "
        "preprocessed appropriately.\n"
        "\n"
        "Locations accuracy: Estimated precision of the reported locations, indicating the likely administrative unit level "
        "used for reporting.\n"
        "\n"
        "Locations type: Specifies whether the location represents the origin, destination, or both for displacement. "
        "Multiple location types within a single figure can cause double-counting in GIS analysis unless handled "
        "carefully.\n"
        "\n"
        "Displacement occurred: Indicates whether preventive evacuations were reported as a result of early warning "
        "systems.\n"
        "\n"
        "Created at: Timestamp indicating when the data entry was created.\n"
    )
    feature_collection = {
        "type": "FeatureCollection",
        "readme": readme_text,
        "lastUpdated": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": [],
    }
    for obj in idu_data:
        serializer = FigureReadOnlySerializer(obj)
        item = dict(serializer.data)

        coordinates = format_coordinates(item["locations_coordinates"])
        if coordinates == []:
            continue

        geometry = {
            "type": "MultiPoint",
            "coordinates": coordinates,
        }

        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": remove_null_from_dict(
                {
                    "id": item["id"],
                    "country": item["country"],
                    "iso3": item["iso3"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "centroid": item["centroid"],
                    "role": item["role"],
                    "displacement_type": item["displacement_type"],
                    "qualifier": item["qualifier"],
                    "figure": item["figure"],
                    "displacement_date": item["displacement_date"],
                    "displacement_start_date": item["displacement_start_date"],
                    "displacement_end_date": item["displacement_end_date"],
                    "year": item["year"],
                    "event_id": item["event_id"],
                    "event_name": item["event_name"],
                    "event_codes": item["event_codes"],
                    "event_code_types": item["event_code_types"],
                    "event_start_date": item["event_start_date"],
                    "event_end_date": item["event_end_date"],
                    "category": item["category"],
                    "subcategory": item["subcategory"],
                    "type": item["type"],
                    "subtype": item["subtype"],
                    "standard_popup_text": item["standard_popup_text"],
                    "standard_info_text": item["standard_info_text"],
                    "old_id": item["old_id"],
                    "sources": item["sources"],
                    "source_url": item["source_url"],
                    "locations_name": item["locations_name"],
                    "locations_coordinates": item["locations_coordinates"],
                    "locations_accuracy": item["locations_accuracy"],
                    "locations_type": item["locations_type"],
                    "displacement_occurred": item["displacement_occurred"],
                    "created_at": item["created_at"],
                }
            ),
        }
        feature_collection["features"].append(feature)
    return feature_collection


class FigureViewSet(viewsets.ReadOnlyModelViewSet):
    # TODO Add url for this viewset
    serializer_class = FigureReadOnlySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_idu_data()


CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "geojson": "application/geo+json",
}


class ExternalEndpointBaseCachedViewMixin:
    ENDPOINT_TYPE = None

    def get_content_type(self, filename: str) -> Optional[str]:
        extension = Path(filename).suffix.lower().lstrip(".")
        return CONTENT_TYPES.get(extension)

    def build_download_params(self, filename: str) -> dict:
        params = {
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        }

        content_type = self.get_content_type(filename)
        if content_type:
            params["ResponseContentType"] = content_type

        return params

    def download_file(self, request, obj):
        filename = Path(obj.dump_file.name).name
        params = self.build_download_params(filename)
        with TemporaryStorageEnableAuthString(external_storage):
            url = external_storage.url(
                obj.dump_file.name,
                parameters=params,
            )

        return redirect(url)

    @client_id
    def get(self, request, data_format=ExternalApiDump.Format.JSON):
        # Check if request is comming from valid client
        client_id = request.GET.get("client_id", None)
        # Track client
        client = track_gidd(
            client_id,
            self.ENDPOINT_TYPE,
        )
        api_dump = ExternalApiDump.objects.filter(
            api_type=self.ENDPOINT_TYPE, include_sources=client.share_source, format=data_format
        ).first()
        # NOTE: Sending empty array so client don't break.
        _empty_response = []
        if not api_dump:
            return Response(_empty_response, status=status.HTTP_404_NOT_FOUND)

        if api_dump.status == ExternalApiDump.Status.COMPLETED:
            return self.download_file(request, api_dump)

        if api_dump.status == ExternalApiDump.Status.FAILED:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Finally, for pending. If we have a dump send it
        if api_dump.dump_file.name is not None:
            return self.download_file(request, api_dump)

        # Else send 202 response
        return Response(_empty_response, status=status.HTTP_202_ACCEPTED)


@extend_schema(
    description=Path("docs/idus/export-description.md").read_text(),
    responses=FigureReadOnlySerializer,
    tags=["IDU"],
)
class BaseIdusCachedView(ExternalEndpointBaseCachedViewMixin, ViewSet):
    @client_id
    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        return self._export(request, ExternalApiDump.Format.EXCEL)

    @client_id
    @action(detail=False, methods=["get"], url_path="export-json")
    def export_json(self, request):
        return self._export(request, ExternalApiDump.Format.JSON)

    @client_id
    @action(detail=False, methods=["get"], url_path="export-geojson")
    def export_geojson(self, request):
        return self._export(request, ExternalApiDump.Format.GEOJSON)

    def _export(self, request, fmt):
        return super().get(request, data_format=fmt)


class IdusFlatCachedView(BaseIdusCachedView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS


class IdusAllFlatCachedView(BaseIdusCachedView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS_ALL


class IdusAllDisasterCachedView(BaseIdusCachedView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS_ALL_DISASTER
