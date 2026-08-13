from django.test import RequestFactory

from apps.report.filters import ReportFilter
from apps.report.models import (
    Report,
    ReportApproval,
    ReportGeneration,
)
from apps.users.roles import USER_ROLE
from utils.factories import ReportFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestReportFilter(HelixTestCase):
    def setUp(self) -> None:
        self.request = RequestFactory().post("/graphql")

    def test_filter_report_by_review_status(self):
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request.user = admin
        signed_off = Report.REPORT_REVIEW_FILTER.SIGNED_OFF.name
        approved = Report.REPORT_REVIEW_FILTER.APPROVED.name
        unapproved = Report.REPORT_REVIEW_FILTER.UNAPPROVED.name

        rep1 = ReportFactory.create(is_signed_off=True, is_signed_off_by=admin, is_public=True)
        rep2 = ReportFactory.create(is_public=True)
        data = dict(review_status=[signed_off], is_public=True)
        fqs = ReportFilter(data=data, request=self.request).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), rep1)

        # lets approve a report
        # create the report generation first
        gen2 = ReportGeneration.objects.create(
            report=rep2,
        )
        # and then add approvers
        ReportApproval.objects.create(generation=gen2, created_by=admin, is_approved=True)

        data = dict(review_status=[approved], is_public=True)
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), rep2)

        # lets create a third report
        rep3 = ReportFactory.create(is_public=True)

        data = dict(review_status=[approved, signed_off], is_public=True)
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 2)
        self.assertNotIn(rep3, fqs)

        data = dict(review_status=[approved, unapproved], is_public=True)
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 2)
        # signed off report should not be there
        self.assertNotIn(rep1, fqs)

        data = dict(review_status=[unapproved], is_public=True)
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), rep3)


class TestReportReviewStatusUsesTheLastGeneration(HelixTestCase):
    """The filter must read the same generation the client is shown.

    `Report.last_generation` and `ReportLastGenerationLoader` both take the newest generation by
    `created_at`. Ordering the filter's subquery by `created_by` picks the generation belonging to
    the highest user id instead, which is a different row whenever the newest generation was not
    made by the highest-numbered user -- 71 of the 92 multi-generation reports in the prod-like
    dump.
    """

    def setUp(self) -> None:
        self.request = RequestFactory().post("/graphql")
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request.user = self.admin
        # A second user, created after the admin so it holds the HIGHER id. The older generation
        # is approved and belongs to that user, so ordering by created_by picks it while ordering
        # by created_at picks the newer one.
        self.other = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.report = ReportFactory.create(is_public=True)

    def _generation(self, created_by, approved):
        generation = ReportGeneration.objects.create(report=self.report, created_by=created_by)
        if approved:
            ReportApproval.objects.create(generation=generation, created_by=created_by, is_approved=True)
        return generation

    def test_the_newest_generation_decides_the_status(self):
        older_approved = self._generation(created_by=self.other, approved=True)
        newer_unapproved = self._generation(created_by=self.admin, approved=False)
        # The newest generation is the unapproved one; the approved one has the higher created_by.
        self.assertGreater(newer_unapproved.created_at, older_approved.created_at)
        self.assertGreater(older_approved.created_by_id, newer_unapproved.created_by_id)

        self.assertEqual(self.report.last_generation, newer_unapproved)

        approved = ReportFilter(
            data=dict(review_status=[Report.REPORT_REVIEW_FILTER.APPROVED.name], is_public=True),
            request=self.request,
        ).qs
        unapproved = ReportFilter(
            data=dict(review_status=[Report.REPORT_REVIEW_FILTER.UNAPPROVED.name], is_public=True),
            request=self.request,
        ).qs
        self.assertNotIn(self.report, approved, "an older generation decided the status")
        self.assertIn(self.report, unapproved)
