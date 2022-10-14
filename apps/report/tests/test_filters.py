from django.test import RequestFactory
from apps.report.models import (
    Report,
    ReportGeneration,
    ReportApproval,
)
from apps.report.filters import ReportFilter
from apps.users.roles import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import (
    ReportFactory
)


class TestReportFilter(HelixTestCase):

    def setUp(self) -> None:
        self.request = RequestFactory().post('/graphql')

    def test_filter_report_by_review_status(self):
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request.user = admin
        signed_off = Report.REPORT_REVIEW_FILTER.SIGNED_OFF.name
        approved = Report.REPORT_REVIEW_FILTER.APPROVED.name
        unapproved = Report.REPORT_REVIEW_FILTER.UNAPPROVED.name

        rep1 = ReportFactory.create(
            is_signed_off=True,
            is_signed_off_by=admin,
            is_public=True
        )
        rep2 = ReportFactory.create(is_public=True)
        data = dict(
            review_status=[signed_off],
            is_public=True
        )
        fqs = ReportFilter(
            data=data,
            request=self.request
        ).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), rep1)

        # lets approve a report
        # create the report generation first
        gen2 = ReportGeneration.objects.create(
            report=rep2,
        )
        # and then add approvers
        ReportApproval.objects.create(
            generation=gen2,
            created_by=admin,
            is_approved=True
        )

        data = dict(
            review_status=[approved],
            is_public=True
        )
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), rep2)

        # lets create a third report
        rep3 = ReportFactory.create(is_public=True)

        data = dict(
            review_status=[approved, signed_off],
            is_public=True
        )
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 2)
        self.assertNotIn(rep3, fqs)

        data = dict(
            review_status=[approved, unapproved],
            is_public=True
        )
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 2)
        # signed off report should not be there
        self.assertNotIn(rep1, fqs)

        data = dict(
            review_status=[unapproved],
            is_public=True
        )
        fqs = ReportFilter(
            data=data,
            request=self.request,
        ).qs
        self.assertEqual(fqs.count(), 1)
        self.assertEqual(fqs.first(), rep3)
