from django.test import RequestFactory
import mock

from apps.report.models import ReportGeneration, Report
from apps.report.serializers import (
    ReportSignoffSerializer,
    ReportGenerationSerializer,
    ReportApproveSerializer,
)
from apps.users.enums import USER_ROLE
from utils.factories import ReportFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestGenerationSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.it_head = create_user_with_role(USER_ROLE.IT_HEAD.name)
        self.request = RequestFactory().post('/graphql')
        self.report = ReportFactory.create(
            # only grid based report or null can be generated
            filter_figure_start_after='2019-01-01',
            filter_figure_end_before='2019-12-31',
        )
        self.data = dict(report=self.report.id)
        self.context = dict(
            request=self.request
        )

    def test_generation_creation(self):
        self.request.user = self.it_head
        serializer = ReportGenerationSerializer(
            data=self.data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        assert self.report.is_signed_off is False
        assert self.report.generations.count() == 0
        serializer.save()
        assert self.report.generations.count() == 1
        assert self.report.is_signed_off is False

    def test_generation_creation_fails_for_non_grid_report(self):
        self.request.user = self.it_head
        report = ReportFactory.create(
            # we are now generating a masterfact report
            generated_from=Report.REPORT_TYPE.MASTERFACT
        )
        data = dict(report=report.id)
        serializer = ReportGenerationSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('report', serializer.errors)

    def test_generation_creation_is_invalid_because_unsigned_exists(self):
        self.request.user = self.it_head
        serializer = ReportGenerationSerializer(
            data=self.data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        serializer = ReportGenerationSerializer(
            data=self.data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('report', serializer.errors)

    # TODO: report generation is valid for MYU as well


class TestReportApprovalSerializer(HelixTestCase):
    def setUp(self):
        self.it_head = create_user_with_role(USER_ROLE.IT_HEAD.name)
        self.request = RequestFactory().post('/graphql')
        self.report = ReportFactory.create()
        self.report_id = self.report.id
        self.data = dict(report=self.report.id)

    def test_valid_approval(self):
        # check report approved flag
        assert self.report.is_approved is None
        ReportGeneration.objects.create(report=self.report)

        # approve
        self.request.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        context = dict(
            request=self.request
        )
        serializer = ReportApproveSerializer(
            data=self.data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        # check report approved flag should be true
        report = Report.objects.get(id=self.report_id)
        assert report.is_approved is True
        # re approve
        serializer.save()
        # approval count should remain same
        report = Report.objects.get(id=self.report_id)
        assert report.is_approved is True
        report.last_generation.approvers.count() == 1

    @mock.patch('apps.report.tasks.trigger_report_generation.send')
    def test_invalid_approval_report_signed_off(self, trigger_send):
        # report not yet started generation
        assert self.report.generations.count() == 0
        # try approving fails
        self.request.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        context = dict(
            request=self.request
        )
        serializer = ReportApproveSerializer(
            data=self.data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('report', serializer.errors)
        # begin generation
        ReportGeneration.objects.create(report=self.report)

        # try approving passes
        # NOTE we cannot reuse the old serializer reference, cache is problematic
        serializer = ReportApproveSerializer(
            data=self.data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        # generation is signed off
        self.report.sign_off(self.it_head)
        trigger_send.assert_called()
        self.report.last_generation.status = ReportGeneration.REPORT_GENERATION_STATUS.COMPLETED
        self.report.last_generation.save()
        # report is signed off check
        self.report.refresh_from_db()
        assert self.report.is_signed_off is True
        # try approving again fails
        serializer = ReportApproveSerializer(
            data=self.data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('report', serializer.errors)


class TestReportSignOffSerializer(HelixTestCase):
    def setUp(self):
        self.it_head = create_user_with_role(USER_ROLE.IT_HEAD.name)
        self.request = RequestFactory().post('/graphql')
        self.request.user = self.it_head
        self.context = dict(
            request=self.request
        )
        self.report = ReportFactory.create()
        self.data = dict(report=self.report.id)

    @mock.patch('apps.report.tasks.trigger_report_generation.send')
    def test_valid_sign_off_flow(self, trigger_send):
        # check report approved flag
        assert self.report.is_signed_off is False
        serializer = ReportSignoffSerializer(
            data=self.data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('report', serializer.errors)

        ReportGeneration.objects.create(report=self.report)
        self.report.refresh_from_db()
        assert self.report.is_signed_off is False

        # sign off
        serializer = ReportSignoffSerializer(
            data=self.data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        trigger_send.assert_called()
        self.report.last_generation.status = ReportGeneration.REPORT_GENERATION_STATUS.COMPLETED
        self.report.last_generation.save()
        # check report sign flag should be true
        self.report.refresh_from_db()
        assert self.report.is_signed_off is True
        assert self.report.is_signed_off_by == self.it_head

        # re signoff should fail
        serializer = ReportSignoffSerializer(
            data=self.data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
