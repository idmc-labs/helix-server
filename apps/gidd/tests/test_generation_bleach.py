import re
from datetime import date

from django.test import TestCase

from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.gidd.models import GiddFigure, StatusLog
from apps.gidd.tasks import update_gidd_data
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    ReportFactory,
)
from utils.tests import create_user_with_role

GIDD_YEAR = 2018
YEAR_START = date(GIDD_YEAR, 1, 1)
YEAR_END = date(GIDD_YEAR, 12, 31)
FIGURE_TOTAL = 100

# Markup that would still execute in a browser. Deliberately narrow: it looks for the tags that
# carry script, the javascript: URI scheme, and any `on*=` event handler attribute.
ACTIVE_MARKUP = re.compile(r"<\s*(script|iframe|object|embed)|javascript:|on\w+\s*=", re.I)

# The three inputs below are chosen so that (b) below is a real safety assertion rather than a
# known-broken one. `utils.fields.BleachedTextField` stores `unescape(bleach.clean(value,
# strip=True))`: the unescape runs AFTER the clean, so any markup the clean merely ESCAPED comes
# back out live. Concretely, feeding the pre-escaped string "&lt;script&gt;alert(1)&lt;/script&gt;"
# leaves bleach's entity-aware serializer to pass the entities through untouched, and the trailing
# unescape then yields "<script>alert(1)</script>" -- so (b) would fail, on this branch and on its
# base alike. bleach output is therefore NOT a fixed point in general and "the stored value carries
# no active markup" is NOT an unconditional invariant of this codebase.
#
# What these inputs do exercise is the path that is safe: markup written as REAL tags. `script`,
# `img` and `iframe` are outside bleach's default allowlist and `strip=True` drops the tags (with
# their attributes, taking `onerror=` with them); `href` survives on `a` but a `javascript:` URI is
# not an allowed protocol, so the attribute is dropped. Nothing here is pre-escaped, so the final
# unescape has no markup left to resurrect.
RAW_SOURCE_EXCERPT = '<script>alert("x")</script>Flooding displaced <b>1200</b> people'
RAW_EXCERPT_IDU = "<img src=x onerror=alert(1)>Camps at 5 < 6 sites & rising"
RAW_CALCULATION_LOGIC = '<a href="javascript:alert(1)">source</a> minus <iframe src="//evil"></iframe> duplicates'


class GiddGenerationTextCopyTestCase(TestCase):
    """Generation copies the figure's free text into `GiddFigure` verbatim.

    `GiddFigure.source_excerpt` / `excerpt_idu` / `calculation_logic` are `UnbleachedTextField`,
    which opts them out of the global `TextField` bleach monkeypatch in `utils.fields`. The source
    `Figure` columns are plain `TextField`s and so are cleaned on write; the GIDD copy must
    reproduce what is stored there, byte for byte, and add no cleaning of its own.
    """

    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory.create(name="Nepal", iso3="NEP")
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.DISASTER,
            start_date=YEAR_START,
            end_date=YEAR_END,
        )
        self.figure = FigureFactory.create(
            entry=EntryFactory.create(publish_date=date(GIDD_YEAR + 1, 1, 1)),
            event=self.event,
            country=self.country,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=FIGURE_TOTAL,
            start_date=YEAR_START,
            end_date=YEAR_END,
            source_excerpt=RAW_SOURCE_EXCERPT,
            excerpt_idu=RAW_EXCERPT_IDU,
            calculation_logic=RAW_CALCULATION_LOGIC,
        )
        ReportFactory.create(
            is_gidd_report=True,
            gidd_report_year=GIDD_YEAR,
            filter_figure_start_after=YEAR_START,
            filter_figure_end_before=YEAR_END,
        )
        status_log = StatusLog.objects.create(
            triggered_by=self.user,
            triggered_at=YEAR_START,
            completed_at=YEAR_START,
            status=StatusLog.Status.PENDING,
        )
        update_gidd_data(status_log.id)
        status_log.refresh_from_db()
        # `_generate_gidd_data` swallows every exception and marks the log FAILED; without this
        # the assertions below could be reading an empty table.
        assert status_log.status == StatusLog.Status.SUCCESS

        # The in-memory instance still holds the raw input -- the bleach pass happens in
        # `get_db_prep_value`, so only the DB has the stored value.
        self.figure.refresh_from_db()
        self.gidd_figure = GiddFigure.objects.get(figure_id=self.figure.id, year=GIDD_YEAR)

    TEXT_FIELDS = ("source_excerpt", "excerpt_idu", "calculation_logic")

    def test_the_copy_is_verbatim(self):
        for field in self.TEXT_FIELDS:
            stored = getattr(self.figure, field)
            # Non-vacuity guard: an all-empty copy would satisfy equality trivially.
            assert stored, field
            assert getattr(self.gidd_figure, field) == stored, field

    def test_bleach_kept_the_harmless_markup(self):
        # Proves the cleaning step did not simply erase every tag, which would make the
        # active-markup assertion below vacuous.
        assert "<b>1200</b>" in self.figure.source_excerpt

    def test_the_published_text_carries_no_active_markup(self):
        # Scoped to the three inputs above -- see the module comment: this is an assertion about
        # what bleach does to REAL tags, not an unconditional invariant of the pipeline.
        for field in self.TEXT_FIELDS:
            published = getattr(self.gidd_figure, field)
            assert published
            assert ACTIVE_MARKUP.search(published) is None, (field, published)
