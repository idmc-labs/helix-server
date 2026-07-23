from datetime import timedelta
from unittest import mock

from django.test import RequestFactory
from django.utils import timezone

from apps.report.models import Report, ReportGeneration
from apps.report.serializers import (
    ReportApproveSerializer,
    ReportGenerationSerializer,
    ReportSerializer,
    ReportSignoffSerializer,
)
from apps.users.enums import USER_ROLE
from utils.factories import ReportFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestGenerationSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.it_head = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request = RequestFactory().post("/graphql")
        self.report = ReportFactory.create(
            # only grid based report or null can be generated
            filter_figure_start_after="2019-01-01",
            filter_figure_end_before="2019-12-31",
        )
        self.data = dict(report=self.report.id)
        self.context = dict(request=self.request)

    def test_generation_creation(self):
        self.request.user = self.it_head
        serializer = ReportGenerationSerializer(data=self.data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        assert self.report.is_signed_off is False
        assert self.report.generations.count() == 0
        serializer.save()
        assert self.report.generations.count() == 1
        assert self.report.is_signed_off is False

    def test_user_can_generation_non_grid_report(self):
        self.request.user = self.it_head
        report = ReportFactory.create(
            # we are now generating a masterfact report
            generated_from=Report.REPORT_TYPE.MASTERFACT
        )
        data = dict(report=report.id)
        serializer = ReportGenerationSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid())

    def test_generation_creation_is_invalid_because_unsigned_exists(self):
        self.request.user = self.it_head
        serializer = ReportGenerationSerializer(data=self.data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        serializer = ReportGenerationSerializer(data=self.data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("report", serializer.errors)

    # TODO: report generation is valid for MYU as well


class TestReportApprovalSerializer(HelixTestCase):
    def setUp(self):
        self.it_head = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request = RequestFactory().post("/graphql")
        self.report = ReportFactory.create()
        self.report_id = self.report.id
        self.data = dict(report=self.report.id)

    def test_valid_approval(self):
        # check report approved flag
        assert self.report.is_approved is None
        ReportGeneration.objects.create(report=self.report)

        # approve
        self.request.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        context = dict(request=self.request)
        serializer = ReportApproveSerializer(data=self.data, context=context)
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

    @mock.patch("apps.report.tasks.trigger_report_generation.delay")
    def test_invalid_approval_report_signed_off(self, trigger_delay):
        # report not yet started generation
        assert self.report.generations.count() == 0
        # try approving fails
        self.request.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        context = dict(request=self.request)
        serializer = ReportApproveSerializer(data=self.data, context=context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("report", serializer.errors)
        # begin generation
        ReportGeneration.objects.create(report=self.report)

        # try approving passes
        # NOTE we cannot reuse the old serializer reference, cache is problematic
        serializer = ReportApproveSerializer(data=self.data, context=context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        # generation is signed off
        self.report.sign_off(self.it_head)
        trigger_delay.assert_called()
        self.report.last_generation.status = ReportGeneration.REPORT_GENERATION_STATUS.COMPLETED
        self.report.last_generation.save()
        # report is signed off check
        self.report.refresh_from_db()
        assert self.report.is_signed_off is True
        # try approving again fails
        serializer = ReportApproveSerializer(data=self.data, context=context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("report", serializer.errors)


class TestReportSignOffSerializer(HelixTestCase):
    def setUp(self):
        self.it_head = create_user_with_role(USER_ROLE.ADMIN.name)
        self.request = RequestFactory().post("/graphql")
        self.request.user = self.it_head
        self.context = dict(request=self.request)
        self.report = ReportFactory.create()
        self.data = dict(report=self.report.id)

    @mock.patch("apps.report.tasks.trigger_report_generation.delay")
    def test_valid_sign_off_flow(self, trigger_delay):
        # check report approved flag
        assert self.report.is_signed_off is False
        serializer = ReportSignoffSerializer(data=self.data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("report", serializer.errors)

        ReportGeneration.objects.create(report=self.report)
        self.report.refresh_from_db()
        assert self.report.is_signed_off is False

        # sign off
        serializer = ReportSignoffSerializer(data=self.data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        trigger_delay.assert_called()
        self.report.last_generation.status = ReportGeneration.REPORT_GENERATION_STATUS.COMPLETED
        self.report.last_generation.save()
        # check report sign flag should be true
        self.report.refresh_from_db()
        assert self.report.is_signed_off is True
        assert self.report.is_signed_off_by == self.it_head

        # re signoff should fail
        serializer = ReportSignoffSerializer(data=self.data, context=self.context)
        self.assertFalse(serializer.is_valid())


class TestReportSerializer(HelixTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/graphql")
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=self.request)

    def test_report_date_range(self):
        ref = timezone.now()
        start = ref.strftime("%Y-%m-%d")
        end = (ref + timedelta(days=1)).strftime("%Y-%m-%d")

        report = Report.objects.create(name="hello")
        data = dict(filter_figure_start_after=start, filter_figure_end_before=end)
        serializer = ReportSerializer(instance=report, data=data, partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        end = (ref - timedelta(days=1)).strftime("%Y-%m-%d")
        data = dict(filter_figure_start_after=start, filter_figure_end_before=end)
        serializer = ReportSerializer(instance=report, data=data, partial=True, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("filter_figure_start_after", serializer.errors)

    def test_summary_rejects_blank_and_null_but_allows_omission(self):
        ref = timezone.now()
        report = Report.objects.create(
            name="hello",
            filter_figure_start_after=ref.date(),
            filter_figure_end_before=(ref + timedelta(days=1)).date(),
        )

        # omitting summary is allowed on a patch update
        serializer = ReportSerializer(instance=report, data=dict(name="renamed"), partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # blank summary is rejected
        serializer = ReportSerializer(instance=report, data=dict(summary=""), partial=True, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("summary", serializer.errors)

        # null summary is rejected
        serializer = ReportSerializer(instance=report, data=dict(summary=None), partial=True, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("summary", serializer.errors)

        # a real summary is accepted
        serializer = ReportSerializer(instance=report, data=dict(summary="real summary"), partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestReportValidationSerializer(HelixTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/graphql")
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=self.request)

    def test_non_gidd_report_requires_date_range(self):
        data = dict(name="no dates", is_gidd_report=False)
        serializer = ReportSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("filter_figure_start_after", serializer.errors)
        self.assertIn("filter_figure_end_before", serializer.errors)

        data = dict(
            name="with dates",
            is_gidd_report=False,
            filter_figure_start_after="2020-01-01",
            filter_figure_end_before="2020-12-31",
        )
        serializer = ReportSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_figure_crisis_type_clears_only_opposite_subtypes(self):
        from apps.crisis.models import Crisis
        from utils.factories import DisasterSubTypeFactory, ViolenceSubTypeFactory

        violence_sub_type = ViolenceSubTypeFactory.create()
        disaster_sub_type = DisasterSubTypeFactory.create()
        subtypes = dict(
            filter_figure_violence_sub_types=[violence_sub_type.id],
            filter_figure_disaster_sub_types=[disaster_sub_type.id],
        )

        def _report(crisis_types):
            return Report.objects.create(
                name="crisis type report",
                filter_figure_crisis_types=crisis_types,
                filter_figure_start_after="2020-01-01",
                filter_figure_end_before="2020-12-31",
            )

        # DISASTER present -> keep disaster subtypes, clear violence
        report = _report([Crisis.CRISIS_TYPE.DISASTER.value])
        serializer = ReportSerializer(instance=report, data=subtypes, partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["filter_figure_violence_sub_types"], [])
        self.assertEqual(serializer.validated_data["filter_figure_disaster_sub_types"], [disaster_sub_type])

        # CONFLICT present -> keep violence subtypes, clear disaster
        report = _report([Crisis.CRISIS_TYPE.CONFLICT.value])
        serializer = ReportSerializer(instance=report, data=subtypes, partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["filter_figure_violence_sub_types"], [violence_sub_type])
        self.assertEqual(serializer.validated_data["filter_figure_disaster_sub_types"], [])

        # neither -> clear both
        report = _report([Crisis.CRISIS_TYPE.OTHER.value])
        serializer = ReportSerializer(instance=report, data=subtypes, partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["filter_figure_violence_sub_types"], [])
        self.assertEqual(serializer.validated_data["filter_figure_disaster_sub_types"], [])
