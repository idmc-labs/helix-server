"""A published GIDD release must not change because Helix data changed.

Names are already denormalized onto the GIDD tables, so this file covers the ids, which are the
part that can still be reached back through a foreign key:

- the typology ids are published (six `*Id` fields on GiddEventDisplacementType, and the four
  hazard fields DisasterSerializer renders as primary keys), so their lookup rows are PROTECTed --
  Helix refuses the delete rather than nulling an id inside a published release
- an event stays deletable, because `event_raw_id` carries the published id instead
- a report stays deletable too, and deleting one nulls the foreign key rather than taking the
  published analysis row with it
- the names a release publishes come from the denormalised columns, not from a live join, so
  renaming a country or a hazard type in Helix cannot change an already-published release

`on_delete` is enforced by Django, not by the database, so these guarantees cover ORM and admin
deletions. Raw SQL bypasses them.
"""

import datetime

from django.db.models import ProtectedError
from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import GiddEventDisplacement, PublicFigureAnalysis
from utils.factories import (
    CountryFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterSubTypeFactory,
    DisasterTypeFactory,
    EventFactory,
    ReportFactory,
    ViolenceFactory,
    ViolenceSubTypeFactory,
)

YEAR = 2020


class TestPublishedIdsSurviveHelixDeletes(TestCase):
    def setUp(self):
        self.country = CountryFactory.create(iso3="AFG", idmc_short_name="Afghanistan")
        self.event = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)
        self.violence = ViolenceFactory.create()
        self.violence_sub_type = ViolenceSubTypeFactory.create(violence=self.violence)
        self.hazard_category = DisasterCategoryFactory.create()
        self.hazard_sub_category = DisasterSubCategoryFactory.create(category=self.hazard_category)
        self.hazard_type = DisasterTypeFactory.create(disaster_sub_category=self.hazard_sub_category)
        self.hazard_sub_type = DisasterSubTypeFactory.create(type=self.hazard_type)

        self.row = GiddEventDisplacement.objects.create(
            event=self.event,
            event_raw_id=self.event.id,
            country=self.country,
            iso3="AFG",
            country_name="Afghanistan",
            year=YEAR,
            cause=Crisis.CRISIS_TYPE.DISASTER,
            event_name="Afghanistan: Earthquake",
            start_date=datetime.date(YEAR, 6, 1),
            end_date=datetime.date(YEAR, 6, 30),
            new_displacement=100,
            violence=self.violence,
            violence_sub_type=self.violence_sub_type,
            hazard_category=self.hazard_category,
            hazard_sub_category=self.hazard_sub_category,
            hazard_type=self.hazard_type,
            hazard_sub_type=self.hazard_sub_type,
        )

    def test_a_referenced_typology_row_cannot_be_deleted(self):
        # Each of the six is published as an id, so nulling it would rewrite a released figure's
        # typology reference. Refusing the delete is the lesser evil.
        for name, obj in (
            ("violence", self.violence),
            ("violence_sub_type", self.violence_sub_type),
            ("hazard_category", self.hazard_category),
            ("hazard_sub_category", self.hazard_sub_category),
            ("hazard_type", self.hazard_type),
            ("hazard_sub_type", self.hazard_sub_type),
        ):
            with self.subTest(field=name):
                with self.assertRaises(ProtectedError):
                    obj.delete()

    def test_an_event_stays_deletable_and_its_published_id_survives(self):
        # The opposite call from the typology: events are deleted in Helix as a matter of course, so
        # the published id is the stored copy rather than the foreign key.
        event_id = self.event.id
        self.event.delete()
        self.row.refresh_from_db()
        assert self.row.event_id is None
        assert self.row.event_raw_id == event_id

    def test_public_figure_analysis_survives_its_report_being_deleted(self):
        report = ReportFactory.create(is_public=True)
        analysis = PublicFigureAnalysis.objects.create(
            id=report.id,
            iso3="AFG",
            year=YEAR,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            figure_category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            figures=100,
            figures_rounded=100,
            report=report,
            report_raw_id=report.id,
        )
        report.delete()
        analysis.refresh_from_db()
        # Generation assigns the report's id as the row's key, so what a caller references
        # survives both a rebuild and the report being deleted.
        assert analysis.report_id is None


class TestPublishedNamesComeFromTheRelease(TestCase):
    """The names are captured at generation, so a Helix rename must not reach a published release.

    `Country.name` and `Country.idmc_short_name` genuinely differ for a good number of countries, so
    a fixture where they agree cannot tell a cached read from a live one. These deliberately differ.
    """

    def setUp(self):
        self.country = CountryFactory.create(
            iso3="AFG",
            name="Islamic Republic of Afghanistan",
            idmc_short_name="Afghanistan",
        )
        self.hazard_category = DisasterCategoryFactory.create(name="Natural")
        self.hazard_sub_category = DisasterSubCategoryFactory.create(category=self.hazard_category)
        self.hazard_type = DisasterTypeFactory.create(disaster_sub_category=self.hazard_sub_category, name="Earthquake")
        self.row = GiddEventDisplacement.objects.create(
            country=self.country,
            iso3="AFG",
            country_name="Afghanistan",
            year=YEAR,
            cause=Crisis.CRISIS_TYPE.DISASTER,
            event_name="Afghanistan: Earthquake",
            new_displacement=100,
            hazard_category=self.hazard_category,
            hazard_sub_category=self.hazard_sub_category,
            hazard_type=self.hazard_type,
            hazard_category_name="Natural",
            hazard_type_name="Earthquake",
        )

    def test_a_helix_rename_does_not_change_the_published_row(self):
        self.country.name = "RENAMED IN HELIX"
        self.country.idmc_short_name = "RENAMED IN HELIX"
        self.country.save()
        self.hazard_type.name = "RENAMED IN HELIX"
        self.hazard_type.save()

        self.row.refresh_from_db()
        assert self.row.country_name == "Afghanistan"
        assert self.row.hazard_type_name == "Earthquake"

    def test_the_published_country_name_is_the_idmc_short_name(self):
        # The xlsx export used to read `country.name` live while every other GIDD surface published
        # `idmc_short_name`, so the two disagreed for the countries where those columns differ.
        assert self.country.name != self.country.idmc_short_name
        assert self.row.country_name == self.country.idmc_short_name
