"""Tests for backend IDU text generation.

The expected outputs are the documented cases from the frontend spec
(helix-client .../FigureInput/iduText.test.ts); inputs are expressed with
backend figure enums. Cause text comes from the DB (subtype ``idu_name``).
"""

from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure, FigureLocation
from apps.entry.utils import (
    format_date_range,
    format_source,
    generate_excerpt_idu_text,
    get_lowest_admin_level,
    get_quantifier_text,
    join_with_and,
    number_to_words_less_than_ten,
    to_ordinal,
)
from apps.event.models import OtherSubType
from apps.users.enums import USER_ROLE
from utils.factories import (
    DisasterSubTypeFactory,
    OrganizationFactory,
    OrganizationKindFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


# --- source / location shorthands (mirror the frontend test helpers) ---------
def geo(identifier, display_name):
    return {"identifier": FigureLocation.IDENTIFIER[identifier], "display_name": display_name}


gov = [{"name": "Ministry", "organization_kind": "Government"}]
gov2 = [
    {"name": "A", "organization_kind": "Government"},
    {"name": "B", "organization_kind": "Local Authority"},
]
media = [{"name": "El Capital", "organization_kind": "Media"}]
iom = [{"name": "International Organization for Migration (IOM)", "organization_kind": None}]
two_named = [
    {"name": "the Red Cross", "organization_kind": None},
    {"name": "UNHCR", "organization_kind": None},
]
three_named = [
    {"name": "the Red Cross", "organization_kind": None},
    {"name": "UNHCR", "organization_kind": None},
    {"name": "IOM", "organization_kind": None},
]

# The distinct idu_name values used across the frontend cases, keyed by the
# frontend numeric subtype id. Each is seeded once and the frontend id is mapped
# to the created row's real pk.
DISASTER_IDU_NAMES = {
    "1": "an earthquake",
    "7": "a drought",
    "13": "flooding",
    "15": "a landslide",
    "24": "a tropical cyclone",
}
CONFLICT_IDU_NAMES = {
    "2": "international armed conflict",
    "7": "non-international armed conflict",
    "12": "crime-related violence",
    "13": "communal violence",
}
OTHER_IDU_NAMES = {
    "1": "development",
    "2": "eviction",
}


class TestIDUCoreGenerator(TestCase):
    """The 39 documented cases + branch edges + array cardinality."""

    @classmethod
    def setUpTestData(cls):
        cls.disaster_ids = {
            key: DisasterSubTypeFactory.create(idu_name=idu_name).id for key, idu_name in DISASTER_IDU_NAMES.items()
        }
        cls.conflict_ids = {
            key: ViolenceSubTypeFactory.create(idu_name=idu_name).id for key, idu_name in CONFLICT_IDU_NAMES.items()
        }
        cls.other_ids = {
            key: OtherSubType.objects.create(name=idu_name, idu_name=idu_name).id
            for key, idu_name in OTHER_IDU_NAMES.items()
        }

    def disaster(self, frontend_id):
        return {"figure_cause": Crisis.CRISIS_TYPE.DISASTER, "disaster_sub_type": self.disaster_ids[frontend_id]}

    def conflict(self, frontend_id):
        return {"figure_cause": Crisis.CRISIS_TYPE.CONFLICT, "violence_sub_type": self.conflict_ids[frontend_id]}

    def other(self, frontend_id):
        return {"figure_cause": Crisis.CRISIS_TYPE.OTHER, "other_sub_type": self.other_ids[frontend_id]}

    def base(self):
        return {}

    def _cases(self):
        b = self.base()
        return [
            (
                1,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.EVACUATED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 8,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Komyshuvakha, Orikhiv Raion, Zaporizhia Oblast, Ukraine")],
                    **self.conflict("2"),
                    "sources": gov,
                    "start_date": "2026-06-12",
                },
                "According to national authorities, eight people were evacuated in Komyshuvakha due to "
                "international armed conflict on June 12, 2026.",
            ),
            (
                2,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 1156,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Mangochi, Southern Region, Malawi")],
                    **self.disaster("13"),
                    "sources": media,
                    "start_date": "2025-01-31",
                    "end_date": "2025-03-10",
                },
                "According to media sources, at least 1,156 households were displaced in Mangochi due to flooding "
                "between January 31 and March 10, 2025.",
            ),
            (
                3,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.FORCED_TO_FLEE,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 3,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Kharkiv, Ukraine"), geo("DESTINATION", "Poltava, Ukraine")],
                    **self.conflict("13"),
                    "sources": gov2,
                    "start_date": "2025-12-01",
                    "end_date": "2025-12-16",
                },
                "According to local authorities and national authorities, around three people were forced to flee "
                "from Kharkiv to Poltava due to communal violence between the 1st and 16th of December 2025.",
            ),
            (
                4,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.RELOCATED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 12450,
                    "quantifier": Figure.QUANTIFIER.LESS_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN_AND_DESTINATION", "Huambo, Angola")],
                    **self.disaster("15"),
                    "sources": iom,
                    "start_date": "2024-11-06",
                    "end_date": "2025-02-01",
                },
                "According to International Organization for Migration (IOM), up to 12,450 households were relocated "
                "in Huambo due to a landslide between November 6, 2024 and February 1, 2025.",
            ),
            (
                5,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.SHELTERED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Kathmandu, Bagmati, Nepal")],
                    **self.disaster("1"),
                    "sources": [],
                    "start_date": "2025-10-01",
                },
                "According to (Source), one person was sheltered in Kathmandu due to an earthquake on October 1, 2025.",
            ),
            (
                6,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.HOMELESS,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 27,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Poza Rica, Veracruz, Mexico")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-10-01",
                    "end_date": "2025-10-10",
                },
                "According to national authorities, at least 27 households were rendered homeless in Poza Rica due to "
                "flooding between the 1st and 10th of October 2025.",
            ),
            (
                7,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.AFFECTED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 5,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Gisuru, Burundi")],
                    **self.disaster("7"),
                    "sources": media,
                    "start_date": "2025-02-14",
                    "end_date": "2025-05-20",
                },
                "According to media sources, around five people were affected in Gisuru due to a drought between "
                "February 14 and May 20, 2025.",
            ),
            (
                8,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.IN_RELIEF_CAMP,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 2,
                    "quantifier": Figure.QUANTIFIER.LESS_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Cox Bazar, Bangladesh")],
                    **self.disaster("13"),
                    "sources": gov2,
                    "start_date": "2025-07-04",
                },
                "According to local authorities and national authorities, up to two households were in a relief camp "
                "in Cox Bazar due to flooding on July 4, 2025.",
            ),
            (
                9,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.RETURNS,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 340,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Kharkiv, Ukraine"), geo("DESTINATION", "Donetsk, Ukraine")],
                    **self.conflict("2"),
                    "sources": gov,
                    "start_date": "2025-03-01",
                    "end_date": "2025-09-15",
                },
                "According to national authorities, at least 340 households returned from Kharkiv to Donetsk following "
                "international armed conflict between March 1 and September 15, 2025.",
            ),
            (
                10,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.RETURNS,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Aleppo, Syria")],
                    **self.disaster("13"),
                    "sources": media,
                    "start_date": "2025-05-01",
                },
                "According to media sources, one person returned in Aleppo following flooding on May 1, 2025.",
            ),
            (
                11,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.MULTIPLE_OR_OTHER,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 60,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN_AND_DESTINATION", "Nairobi, Kenya")],
                    **self.other("1"),
                    "sources": iom,
                    "start_date": "2025-08-01",
                    "end_date": "2025-08-20",
                },
                "According to International Organization for Migration (IOM), around 60 people were displaced in Nairobi "
                "due to development between the 1st and 20th of August 2025.",
            ),
            (
                12,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DESTROYED_HOUSING,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 156,
                    "quantifier": Figure.QUANTIFIER.LESS_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Huambo, Huambo, Angola")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-11-06",
                    "end_date": "2025-12-31",
                },
                "According to national authorities, up to 156 houses were destroyed in Huambo due to flooding between "
                "November 6 and December 31, 2025.",
            ),
            (
                13,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DESTROYED_HOUSING,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 4,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Kathmandu, Nepal")],
                    **self.disaster("1"),
                    "sources": [],
                    "start_date": "2025-04-25",
                },
                "According to (Source), the housing of at least four people was destroyed in Kathmandu due to "
                "an earthquake on April 25, 2025.",
            ),
            (
                14,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.PARTIALLY_DESTROYED_HOUSING,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 9,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Beira, Mozambique")],
                    **self.disaster("13"),
                    "sources": gov2,
                    "start_date": "2025-03-01",
                    "end_date": "2025-03-14",
                },
                "According to local authorities and national authorities, nine houses were partially destroyed in Beira "
                "due to flooding between the 1st and 14th of March 2025.",
            ),
            (
                15,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.PARTIALLY_DESTROYED_HOUSING,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 210,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Freetown, Sierra Leone")],
                    **self.disaster("15"),
                    "sources": media,
                    "start_date": "2024-08-14",
                    "end_date": "2025-01-10",
                },
                "According to media sources, the housing of around 210 people was partially destroyed in Freetown due to "
                "a landslide between August 14, 2024 and January 10, 2025.",
            ),
            (
                16,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.UNINHABITABLE_HOUSING,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.LESS_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Tacloban, Philippines")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-09-09",
                },
                "According to national authorities, one house was rendered uninhabitable in Tacloban due to flooding "
                "on September 9, 2025.",
            ),
            (
                17,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.UNINHABITABLE_HOUSING,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 33,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN_AND_DESTINATION", "Manila, Philippines")],
                    **self.other("2"),
                    "sources": iom,
                    "start_date": "2025-06-01",
                    "end_date": "2025-06-30",
                },
                "According to International Organization for Migration (IOM), the housing of at least 33 people was "
                "rendered uninhabitable in Manila due to eviction between the 1st and 30th of June 2025.",
            ),
            (
                18,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 40,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Goma, North Kivu, DRC")],
                    **self.conflict("13"),
                    "sources": two_named,
                    "start_date": "2025-05-02",
                },
                "According to the Red Cross and UNHCR, 40 people were displaced in Goma due to communal violence "
                "on May 2, 2025.",
            ),
            (
                19,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.EVACUATED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 12,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Tarawa, Kiribati")],
                    **self.disaster("24"),
                    "sources": three_named,
                    "start_date": "2025-02-11",
                    "end_date": "2025-02-13",
                },
                "According to the Red Cross, UNHCR, and IOM, around 12 households were evacuated in Tarawa due to "
                "a tropical cyclone between the 11th and 13th of February 2025.",
            ),
            (
                20,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.SHELTERED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Lviv, Ukraine")],
                    **self.conflict("2"),
                    "sources": gov,
                    "start_date": "2026-01-15",
                },
                "According to national authorities, at least one person was sheltered in Lviv due to "
                "international armed conflict on January 15, 2026.",
            ),
            (
                21,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.RETURNS,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 500,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Mosul, Iraq"), geo("DESTINATION", "Baghdad, Iraq")],
                    **self.conflict("2"),
                    "sources": gov,
                    "start_date": "2025-04-01",
                    "end_date": "2025-11-30",
                },
                "According to national authorities, at least 500 people returned from Mosul to Baghdad following "
                "international armed conflict between April 1 and November 30, 2025.",
            ),
            (
                22,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 3,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Beira, Mozambique")],
                    **self.disaster("13"),
                    "sources": media,
                    "start_date": "2025-03-02",
                    "end_date": "2025-03-03",
                },
                "According to media sources, three households were displaced in Beira due to flooding between "
                "the 2nd and 3rd of March 2025.",
            ),
            (
                23,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.AFFECTED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 7,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Chennai, Tamil Nadu, India")],
                    **self.disaster("7"),
                    "sources": gov2,
                    "start_date": "2025-11-11",
                    "end_date": "2025-11-13",
                },
                "According to local authorities and national authorities, around seven people were affected in Chennai "
                "due to a drought between the 11th and 13th of November 2025.",
            ),
            # incomplete-form behavior
            (
                24,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DESTROYED_HOUSING,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Tacloban, Philippines")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-09-09",
                },
                "According to national authorities, one (People or Household) was destroyed in Tacloban due to flooding "
                "on September 9, 2025.",
            ),
            (
                25,
                {},
                "According to (Source), (Quantifier) (Figure) (People or Household) were (Term) (Location) due to "
                "(Main trigger) (Date of Event DD/MM/YYY).",
            ),
            # edge-case / regression checks
            (
                26,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [
                        geo("ORIGIN_AND_DESTINATION", "Kyiv, Ukraine"),
                        geo("ORIGIN_AND_DESTINATION", "Lviv, Ukraine"),
                    ],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-07-04",
                },
                "According to national authorities, at least 100 households were displaced in Kyiv and Lviv due to "
                "flooding on July 4, 2025.",
            ),
            (
                27,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Springfield, Illinois"), geo("ORIGIN", "Springfield, Ohio")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-07-04",
                },
                "According to national authorities, at least 100 households were displaced in Springfield due to "
                "flooding on July 4, 2025.",
            ),
            (
                28,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Kharkiv, Ukraine"), geo("ORIGIN", "Poltava, Ukraine")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-07-04",
                },
                "According to national authorities, at least 100 households were displaced in Kharkiv and Poltava due to "
                "flooding on July 4, 2025.",
            ),
            (
                29,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Kharkiv, Ukraine")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-10-01",
                    "end_date": "2025-10-08",
                },
                "According to national authorities, at least 100 households were displaced in Kharkiv due to flooding "
                "between the 1st and 8th of October 2025.",
            ),
            (
                30,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [
                        geo("ORIGIN", "Kharkiv, Ukraine"),
                        geo("ORIGIN", "Sumy, Ukraine"),
                        geo("DESTINATION", "Poltava, Ukraine"),
                        geo("DESTINATION", "Lviv, Ukraine"),
                    ],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-07-04",
                },
                "According to national authorities, at least 100 households were displaced from Kharkiv and Sumy to "
                "Poltava and Lviv due to flooding on July 4, 2025.",
            ),
            (
                31,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Beira, Mozambique")],
                    **self.disaster("13"),
                    "sources": [
                        {"name": "Ministry", "organization_kind": "Government"},
                        {"name": "El Capital", "organization_kind": "Media"},
                    ],
                    "start_date": "2025-07-04",
                },
                "According to national authorities and media sources, at least 100 households were displaced in Beira "
                "due to flooding on July 4, 2025.",
            ),
            # grammar-locking edge intersections
            (
                32,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.HOMELESS,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 5,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Poza Rica, Veracruz, Mexico")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-10-01",
                },
                "According to national authorities, around five people were rendered homeless in Poza Rica due to "
                "flooding on October 1, 2025.",
            ),
            (
                33,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DESTROYED_HOUSING,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Kathmandu, Nepal")],
                    **self.disaster("1"),
                    "sources": gov,
                    "start_date": "2025-04-25",
                },
                "According to national authorities, the housing of one person was destroyed in Kathmandu due to "
                "an earthquake on April 25, 2025.",
            ),
            (
                34,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.UNINHABITABLE_HOUSING,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Manila, Philippines")],
                    **self.other("2"),
                    "sources": gov,
                    "start_date": "2025-06-01",
                },
                "According to national authorities, the housing of at least one person was rendered uninhabitable "
                "in Manila due to eviction on June 1, 2025.",
            ),
            (
                35,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.MULTIPLE_OR_OTHER,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 60,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN_AND_DESTINATION", "Nairobi, Kenya")],
                    **self.other("1"),
                    "sources": iom,
                    "start_date": "2025-08-01",
                    "end_date": "2025-08-20",
                },
                "According to International Organization for Migration (IOM), around 60 households were displaced "
                "in Nairobi due to development between the 1st and 20th of August 2025.",
            ),
            (
                36,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.IN_RELIEF_CAMP,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.EXACT,
                    "geo_locations": [geo("ORIGIN", "Cox Bazar, Bangladesh")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-07-04",
                },
                "According to national authorities, one person was in a relief camp in Cox Bazar due to flooding "
                "on July 4, 2025.",
            ),
            (
                37,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 1,
                    "quantifier": Figure.QUANTIFIER.APPROXIMATELY,
                    "geo_locations": [geo("ORIGIN", "Goma, North Kivu, DRC")],
                    **self.conflict("13"),
                    "sources": gov,
                    "start_date": "2025-05-02",
                },
                "According to national authorities, one person was displaced in Goma due to communal violence "
                "on May 2, 2025.",
            ),
            (
                38,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.PERSON,
                    "reported": 200,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("ORIGIN", "Tijuana, Mexico")],
                    **self.conflict("12"),
                    "sources": gov,
                    "start_date": "2025-05-02",
                },
                "According to national authorities, at least 200 people were displaced in Tijuana due to "
                "crime-related violence on May 2, 2025.",
            ),
            (
                39,
                {
                    **b,
                    "term": Figure.FIGURE_TERMS.DISPLACED,
                    "unit": Figure.UNIT.HOUSEHOLD,
                    "reported": 100,
                    "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
                    "geo_locations": [geo("DESTINATION", "Lviv, Ukraine")],
                    **self.disaster("13"),
                    "sources": gov,
                    "start_date": "2025-07-04",
                },
                "According to national authorities, at least 100 households were displaced in Lviv due to flooding "
                "on July 4, 2025.",
            ),
        ]

    def test_all_documented_cases(self):
        for n, input_data, expected in self._cases():
            with self.subTest(case=n):
                self.assertEqual(generate_excerpt_idu_text(input_data), expected)

    # --- branch edges --------------------------------------------------------
    def test_disaster_cause_missing_subtype(self):
        result = generate_excerpt_idu_text(
            {
                "figure_cause": Crisis.CRISIS_TYPE.DISASTER,
                "reported": 5,
                "unit": Figure.UNIT.PERSON,
                "term": Figure.FIGURE_TERMS.DISPLACED,
            }
        )
        self.assertIn("due to (Main trigger)", result)

    def test_conflict_cause_branch(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                **self.conflict("7"),
                "reported": 5,
                "unit": Figure.UNIT.PERSON,
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "sources": gov,
            }
        )
        self.assertIn("due to non-international armed conflict", result)

    def test_unmapped_disaster_subtype(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "figure_cause": Crisis.CRISIS_TYPE.DISASTER,
                "disaster_sub_type": "999",
                "reported": 5,
                "unit": Figure.UNIT.PERSON,
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "sources": gov,
            }
        )
        self.assertIn("due to (Main trigger)", result)

    def test_unmapped_conflict_subtype(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "figure_cause": Crisis.CRISIS_TYPE.CONFLICT,
                "violence_sub_type": "999",
                "reported": 5,
                "unit": Figure.UNIT.PERSON,
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "sources": gov,
            }
        )
        self.assertIn("due to (Main trigger)", result)

    def test_unmapped_other_subtype(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "figure_cause": Crisis.CRISIS_TYPE.OTHER,
                "other_sub_type": "999",
                "reported": 5,
                "unit": Figure.UNIT.PERSON,
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "sources": gov,
            }
        )
        self.assertIn("due to (Main trigger)", result)

    def test_null_idu_name_degrades_to_placeholder(self):
        sub_type = DisasterSubTypeFactory.create(idu_name=None)
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "figure_cause": Crisis.CRISIS_TYPE.DISASTER,
                "disaster_sub_type": sub_type.id,
                "reported": 5,
                "unit": Figure.UNIT.PERSON,
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "sources": gov,
            }
        )
        self.assertIn("due to (Main trigger)", result)

    def test_housing_term_unit_unset(self):
        result = generate_excerpt_idu_text(
            {"term": Figure.FIGURE_TERMS.DESTROYED_HOUSING, "reported": 2, **self.disaster("13"), "sources": gov}
        )
        self.assertEqual(
            result,
            "According to national authorities, (Quantifier) two (People or Household) were destroyed (Location) "
            "due to flooding (Date of Event DD/MM/YYY).",
        )

    def test_singular_household_non_housing_term(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "unit": Figure.UNIT.HOUSEHOLD,
                "reported": 1,
                "quantifier": Figure.QUANTIFIER.EXACT,
                "geo_locations": [geo("ORIGIN", "Beira, Mozambique")],
                **self.disaster("13"),
                "sources": gov,
                "start_date": "2025-07-04",
            }
        )
        self.assertEqual(
            result,
            "According to national authorities, one household was displaced in Beira due to flooding on July 4, 2025.",
        )

    def test_lone_local_authority(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "term": Figure.FIGURE_TERMS.DISPLACED,
                "unit": Figure.UNIT.HOUSEHOLD,
                "reported": 50,
                "quantifier": Figure.QUANTIFIER.EXACT,
                "geo_locations": [geo("ORIGIN", "Beira, Mozambique")],
                **self.disaster("13"),
                "sources": [{"name": "City of Beira", "organization_kind": "Local Authority"}],
                "start_date": "2025-07-04",
            }
        )
        self.assertEqual(
            result,
            "According to local authorities, 50 households were displaced in Beira due to flooding on July 4, 2025.",
        )

    def test_returns_destination_only(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "term": Figure.FIGURE_TERMS.RETURNS,
                "unit": Figure.UNIT.PERSON,
                "reported": 5,
                "quantifier": Figure.QUANTIFIER.EXACT,
                "geo_locations": [geo("DESTINATION", "Aleppo, Syria")],
                **self.disaster("13"),
                "sources": gov,
                "start_date": "2025-05-01",
            }
        )
        self.assertEqual(
            result,
            "According to national authorities, five people returned to Aleppo following flooding on May 1, 2025.",
        )

    def test_returns_origin_only(self):
        result = generate_excerpt_idu_text(
            {
                **self.base(),
                "term": Figure.FIGURE_TERMS.RETURNS,
                "unit": Figure.UNIT.PERSON,
                "reported": 5,
                "quantifier": Figure.QUANTIFIER.EXACT,
                "geo_locations": [geo("ORIGIN", "Aleppo, Syria")],
                **self.disaster("13"),
                "sources": gov,
                "start_date": "2025-05-01",
            }
        )
        self.assertEqual(
            result,
            "According to national authorities, five people returned in Aleppo following flooding on May 1, 2025.",
        )

    # --- array cardinality ---------------------------------------------------
    def _frame(self):
        return {
            **self.base(),
            "term": Figure.FIGURE_TERMS.DISPLACED,
            "unit": Figure.UNIT.HOUSEHOLD,
            "reported": 100,
            "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL,
            **self.disaster("13"),
            "sources": gov,
            "start_date": "2025-07-04",
        }

    def _line(self, loc):
        return (
            f"According to national authorities, at least 100 households were displaced {loc} "
            "due to flooding on July 4, 2025."
        )

    def test_cardinality(self):
        cases = [
            ([geo("ORIGIN", "Kharkiv, Ukraine")], self._line("in Kharkiv")),
            (
                [geo("ORIGIN", "Kharkiv, Ukraine"), geo("ORIGIN", "Poltava, Ukraine"), geo("ORIGIN", "Sumy, Ukraine")],
                self._line("in Kharkiv, Poltava, and Sumy"),
            ),
            ([geo("ORIGIN", "Kharkiv, Ukraine"), geo("DESTINATION", "Lviv, Ukraine")], self._line("from Kharkiv to Lviv")),
            ([geo("ORIGIN", "Kathmandu, Nepal"), geo("DESTINATION", "Kathmandu, Nepal")], self._line("in Kathmandu")),
            (
                [
                    geo("ORIGIN", "Kharkiv, Ukraine"),
                    geo("ORIGIN", "Lviv, Ukraine"),
                    geo("DESTINATION", "Lviv, Ukraine"),
                    geo("DESTINATION", "Kharkiv, Ukraine"),
                ],
                self._line("in Kharkiv and Lviv"),
            ),
            (
                [
                    geo("ORIGIN", "Kharkiv, Ukraine"),
                    geo("ORIGIN", "Poltava, Ukraine"),
                    geo("ORIGIN", "Sumy, Ukraine"),
                    geo("DESTINATION", "Lviv, Ukraine"),
                    geo("DESTINATION", "Odesa, Ukraine"),
                    geo("DESTINATION", "Kyiv, Ukraine"),
                ],
                self._line("from Kharkiv, Poltava, and Sumy to Lviv, Odesa, and Kyiv"),
            ),
            ([geo("ORIGIN_AND_DESTINATION", "Kyiv, Ukraine")], self._line("in Kyiv")),
            (
                [
                    geo("ORIGIN_AND_DESTINATION", "Kyiv, Ukraine"),
                    geo("ORIGIN_AND_DESTINATION", "Lviv, Ukraine"),
                    geo("ORIGIN_AND_DESTINATION", "Odesa, Ukraine"),
                ],
                self._line("in Kyiv, Lviv, and Odesa"),
            ),
        ]
        for locs, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(generate_excerpt_idu_text({**self._frame(), "geo_locations": locs}), expected)

    def test_cardinality_sources(self):
        self.assertEqual(
            generate_excerpt_idu_text(
                {**self._frame(), "geo_locations": [geo("ORIGIN", "Beira, Mozambique")], "sources": gov}
            ),
            self._line("in Beira"),
        )
        self.assertEqual(
            generate_excerpt_idu_text(
                {**self._frame(), "geo_locations": [geo("ORIGIN", "Beira, Mozambique")], "sources": three_named}
            ),
            "According to the Red Cross, UNHCR, and IOM, at least 100 households were displaced in Beira due to "
            "flooding on July 4, 2025.",
        )


class TestIDUHelpers(TestCase):
    """Direct unit tests of the helper functions (no DB needed)."""

    def test_format_source(self):
        # No recognized source -> empty; the "(Source)" placeholder is applied at assembly time.
        self.assertEqual(format_source([]), "")
        self.assertEqual(format_source(gov), "national authorities")
        self.assertEqual(format_source([{"name": "City Hall", "organization_kind": "Local Authority"}]), "local authorities")
        self.assertEqual(format_source(gov2), "local authorities and national authorities")
        self.assertEqual(format_source(media), "media sources")
        self.assertEqual(format_source(iom), "International Organization for Migration (IOM)")
        self.assertEqual(format_source(two_named), "the Red Cross and UNHCR")
        self.assertEqual(format_source(three_named), "the Red Cross, UNHCR, and IOM")
        self.assertEqual(format_source([{"organization_kind": "Academia"}]), "")

    def test_format_date_range(self):
        self.assertIsNone(format_date_range(None, None))
        self.assertEqual(format_date_range("2025-06-12"), "on June 12, 2025")
        self.assertEqual(format_date_range("2025-06-12", "2025-06-12"), "on June 12, 2025")
        self.assertEqual(format_date_range("2025-12-01", "2025-12-16"), "between the 1st and 16th of December 2025")
        self.assertEqual(format_date_range("2025-01-31", "2025-03-10"), "between January 31 and March 10, 2025")
        self.assertEqual(format_date_range("2024-11-06", "2025-02-01"), "between November 6, 2024 and February 1, 2025")
        self.assertEqual(format_date_range("2024-08-14", "2025-01-10"), "between August 14, 2024 and January 10, 2025")
        self.assertEqual(format_date_range("2025-10-01", "2025-10-08"), "between the 1st and 8th of October 2025")
        self.assertEqual(format_date_range("2025-11-11", "2025-11-13"), "between the 11th and 13th of November 2025")

    def test_get_quantifier_text(self):
        self.assertEqual(get_quantifier_text(None), "(Quantifier)")
        self.assertIsNone(get_quantifier_text("EXACT"))
        self.assertEqual(get_quantifier_text("APPROXIMATELY"), "around")
        self.assertEqual(get_quantifier_text("MORE_THAN_OR_EQUAL"), "at least")
        self.assertEqual(get_quantifier_text("LESS_THAN_OR_EQUAL"), "up to")

    def test_number_to_words_less_than_ten(self):
        self.assertIsNone(number_to_words_less_than_ten(None))
        self.assertEqual(number_to_words_less_than_ten(5), "five")
        self.assertEqual(number_to_words_less_than_ten(10), "10")
        self.assertEqual(number_to_words_less_than_ten(1500), "1,500")

    def test_get_lowest_admin_level(self):
        self.assertIsNone(get_lowest_admin_level(None))
        self.assertIsNone(get_lowest_admin_level(""))
        self.assertEqual(get_lowest_admin_level("Ukraine"), "Ukraine")
        self.assertEqual(get_lowest_admin_level(" Kyiv , Ukraine "), "Kyiv")

    def test_to_ordinal(self):
        self.assertEqual(to_ordinal(1), "1st")
        self.assertEqual(to_ordinal(2), "2nd")
        self.assertEqual(to_ordinal(3), "3rd")
        self.assertEqual(to_ordinal(4), "4th")
        self.assertEqual(to_ordinal(11), "11th")
        self.assertEqual(to_ordinal(12), "12th")
        self.assertEqual(to_ordinal(13), "13th")
        self.assertEqual(to_ordinal(21), "21st")

    def test_join_with_and(self):
        self.assertEqual(join_with_and([]), "")
        self.assertEqual(join_with_and(["a"]), "a")
        self.assertEqual(join_with_and(["a", "b"]), "a and b")
        self.assertEqual(join_with_and(["a", "b", "c"]), "a, b, and c")

    def test_placeholders_for_empty_input(self):
        self.assertEqual(
            generate_excerpt_idu_text({}),
            "According to (Source), (Quantifier) (Figure) (People or Household) were (Term) (Location) due to "
            "(Main trigger) (Date of Event DD/MM/YYY).",
        )

    def test_singular_verb_for_one(self):
        self.assertIn(
            "one household was displaced",
            generate_excerpt_idu_text({"reported": 1, "unit": Figure.UNIT.HOUSEHOLD, "term": Figure.FIGURE_TERMS.DISPLACED}),
        )

    def test_returns_omits_auxiliary_verb(self):
        self.assertIn(
            "three people returned in X",
            generate_excerpt_idu_text(
                {
                    "reported": 3,
                    "unit": Figure.UNIT.PERSON,
                    "term": Figure.FIGURE_TERMS.RETURNS,
                    "geo_locations": [geo("ORIGIN", "X")],
                }
            ),
        )


class TestIDUGenerateMutation(HelixGraphQLTestCase):
    """End-to-end smoke tests of the permissive generateIdu mutation."""

    def setUp(self):
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(self.editor)
        self.org_kind_gov = OrganizationKindFactory.create(name="Government")
        self.org_gov = OrganizationFactory.create(name="Ministry", organization_kind=self.org_kind_gov)
        self.disaster_sub_type = DisasterSubTypeFactory.create(idu_name="flooding")
        self.mutation = """
            mutation MyMutation($data: IDUGenerateInputType!) {
                generateIdu(data: $data) {
                    ok
                    errors
                    result
                }
            }
        """

    def test_full_input(self):
        variables = {
            "data": {
                "mainTrigger": Crisis.CRISIS_TYPE.DISASTER.name,
                "disasterSubType": str(self.disaster_sub_type.id),
                "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
                "figure": 100,
                "sources": [self.org_gov.id],
                "displacementTerm": Figure.FIGURE_TERMS.DISPLACED.name,
                "unit": Figure.UNIT.HOUSEHOLD.name,
                "locations": [{"identifier": "ORIGIN", "displayName": "Beira, Mozambique"}],
                "startDate": "2025-07-04",
            }
        }
        response = self.query(self.mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()
        self.assertTrue(content["data"]["generateIdu"]["ok"])
        self.assertEqual(
            content["data"]["generateIdu"]["result"],
            "According to national authorities, at least 100 households were displaced in Beira due to flooding "
            "on July 4, 2025.",
        )

    def test_empty_input_emits_placeholders(self):
        response = self.query(self.mutation, variables={"data": {}})
        self.assertResponseNoErrors(response)
        content = response.json()
        self.assertTrue(content["data"]["generateIdu"]["ok"])
        self.assertEqual(
            content["data"]["generateIdu"]["result"],
            "According to (Source), (Quantifier) (Figure) (People or Household) were (Term) (Location) due to "
            "(Main trigger) (Date of Event DD/MM/YYY).",
        )

    def test_end_before_start_does_not_fail(self):
        # A preview must not hard-fail on an inverted date range.
        variables = {
            "data": {
                "mainTrigger": Crisis.CRISIS_TYPE.DISASTER.name,
                "disasterSubType": str(self.disaster_sub_type.id),
                "figure": 5,
                "unit": Figure.UNIT.PERSON.name,
                "displacementTerm": Figure.FIGURE_TERMS.DISPLACED.name,
                "sources": [self.org_gov.id],
                "startDate": "2025-07-10",
                "endDate": "2025-07-01",
            }
        }
        response = self.query(self.mutation, variables=variables)
        self.assertResponseNoErrors(response)
        content = response.json()
        self.assertTrue(content["data"]["generateIdu"]["ok"])
        self.assertIsNotNone(content["data"]["generateIdu"]["result"])
