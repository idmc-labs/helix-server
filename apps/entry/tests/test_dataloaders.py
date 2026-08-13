from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.entry.dataloaders import FigureLastReviewCommentStatusLoader
from apps.review.models import UnifiedReviewComment
from utils.factories import EntryFactory, EventFactory, FigureFactory, UnifiedReviewCommentFactory
from utils.tests import HelixTestCase


class TestFigureLastReviewCommentStatusLoader(HelixTestCase):
    def setUp(self) -> None:
        self.entry = EntryFactory.create()
        self.event = EventFactory.create()
        self.figure = FigureFactory.create(entry=self.entry, event=self.event)
        self.other_figure = FigureFactory.create(entry=self.entry, event=self.event)

        self.comment = UnifiedReviewCommentFactory.create(
            figure=self.figure,
            event=self.event,
            comment_type=UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN,
            field=UnifiedReviewComment.REVIEW_FIELD_TYPE.FIGURE_ROLE,
        )
        # Comments on a figure outside the batch, plus a comment type the loader ignores.
        UnifiedReviewCommentFactory.create_batch(
            2,
            figure=self.other_figure,
            event=self.event,
            comment_type=UnifiedReviewComment.REVIEW_COMMENT_TYPE.RED,
            field=UnifiedReviewComment.REVIEW_FIELD_TYPE.FIGURE_TERM,
        )
        UnifiedReviewCommentFactory.create(
            figure=self.figure,
            event=self.event,
            comment_type=UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREY,
            field=UnifiedReviewComment.REVIEW_FIELD_TYPE.FIGURE_UNIT,
        )

    def test_batch_reads_only_the_requested_figures_comments(self) -> None:
        with CaptureQueriesContext(connection) as ctx:
            values = FigureLastReviewCommentStatusLoader().batch_load_fn([self.figure.id]).get()

        # Only the batched figure's GREEN/RED comment, keyed positionally.
        self.assertEqual([[item["id"] for item in group] for group in values], [[self.comment.id]])

        # The batch's own query must return the batch's rows and nothing else: the figure
        # restriction has to reach SQL, or the loader reads the whole comment table.
        self.assertEqual(len(ctx.captured_queries), 1)
        with connection.cursor() as cursor:
            cursor.execute(ctx.captured_queries[0]["sql"])
            self.assertEqual(len(cursor.fetchall()), 1)


class TestFigureLastReviewCommentStatusLoaderPicksTheNewestComment(HelixTestCase):
    """The last comment on a `(figure, field)` is the highest pk, and only the pk can decide it.

    Reviewers comment on the same field repeatedly and the figure's review status is the latest
    verdict, so a `DISTINCT ON (figure_id, field)` has to keep the newest row. `created_at` cannot
    decide it: two comments saved in the same tick share it (forced below, since `auto_now_add`
    stamps each insert), and the loader does not read it at all. Without a pk in the sort key the
    kept row is whatever the plan emits first, which is the OLDEST verdict whenever the scan
    follows insertion order -- the figure then shows a status the reviewer has already replaced.
    """

    def setUp(self) -> None:
        self.entry = EntryFactory.create()
        self.event = EventFactory.create()
        self.figure = FigureFactory.create(entry=self.entry, event=self.event)
        self.field = UnifiedReviewComment.REVIEW_FIELD_TYPE.FIGURE_ROLE

        # Same figure, same field, opposite verdicts: the superseded RED first, then the GREEN
        # that replaces it. Only the pk separates them.
        self.superseded = UnifiedReviewCommentFactory.create(
            figure=self.figure,
            event=self.event,
            field=self.field,
            comment_type=UnifiedReviewComment.REVIEW_COMMENT_TYPE.RED,
        )
        self.latest = UnifiedReviewCommentFactory.create(
            figure=self.figure,
            event=self.event,
            field=self.field,
            comment_type=UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN,
        )
        UnifiedReviewComment.objects.filter(figure=self.figure).update(created_at=timezone.now())
        self.superseded.refresh_from_db()
        self.latest.refresh_from_db()

    def test_the_fixture_really_ties(self) -> None:
        self.assertEqual(self.superseded.created_at, self.latest.created_at)
        self.assertGreater(self.latest.id, self.superseded.id)

    def test_the_newest_comment_on_a_field_is_the_one_returned(self) -> None:
        values = FigureLastReviewCommentStatusLoader().batch_load_fn([self.figure.id]).get()
        self.assertEqual(
            values,
            [
                [
                    {
                        "id": self.latest.id,
                        "field": self.field,
                        "comment_type": UnifiedReviewComment.REVIEW_COMMENT_TYPE.GREEN,
                    }
                ]
            ],
        )
