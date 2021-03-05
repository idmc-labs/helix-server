from django.test import RequestFactory

from apps.report.models import ReportGeneration
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
        self.report = ReportFactory.create()
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

    def test_generation_creation_is_invalid_because_unsigned_exists(self):
        self.request.user = self.it_head
        serializer = ReportGenerationSerializer(
            data=self.data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertFalse(serializer.is_valid())
        self.assertIn('report', serializer.errors)


class TestReportApprovalSerializer(HelixTestCase):
    def setUp(self):
        self.it_head = create_user_with_role(USER_ROLE.IT_HEAD.name)
        self.request = RequestFactory().post('/graphql')
        self.report = ReportFactory.create()
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
        assert self.report.is_approved is True
        # re approve
        serializer.save()
        # approval count should remain same
        assert self.report.is_approved is True
        self.report.last_generation.approvers.count() == 1

    def test_invalid_approval_report_signed_off(self):
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

    def test_valid_sign_off_flow(self):
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
