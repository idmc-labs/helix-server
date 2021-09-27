from django.utils import timezone
from django.core.cache import cache
from apps.users.enums import USER_ROLE
from apps.report.models import ReportGeneration, Report
from apps.entry.models import FigureCategory
from utils.factories import (
    CountryFactory,
    ReportFactory,
    ReportCommentFactory,
    EntryFactory,
    FigureFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from apps.entry.constants import STOCK


class TestCreateReport(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = '''mutation MyMutation($input: ReportCreateInputType!) {
            createReport(data: $input) {
                result {
                    name
                    filterFigureStartAfter
                    filterFigureEndBefore
                    filterFigureCountries {
                        id
                    }
                }
                ok
                errors
            }
        }'''
        self.input = {
            "name": "disss",
            "filterFigureStartAfter": "2020-01-01",
            "filterFigureEndBefore": "2020-07-01",
            "filterFigureCountries": [str(each.id) for each in countries],
        }

    def test_valid_report_creation(self) -> None:
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createReport']['ok'], content)
        self.assertEqual(content['data']['createReport']['result']['name'], self.input['name'])
        self.assertEqual(len(content['data']['createReport']['result']['filterFigureCountries']),
                         len(self.input['filterFigureCountries']))

    def test_invalid_report_creation_by_guest(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestReportSignOff(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.report = ReportFactory.create(
            created_by=self.admin,
            generated_from=Report.REPORT_TYPE.GROUP,
            filter_figure_start_after='2019-01-01',
            filter_figure_end_before='2019-12-31',
        )
        self.mutation = '''
        mutation SignOffReport($id: ID!, $includeHistory: Boolean) {
          signOffReport(id: $id, includeHistory: $includeHistory) {
            errors
            ok
            result {
              isSignedOff
              id
              generations {
                results {
                  isSignedOff
                  isSignedOffBy { email }
                  createdBy {
                    email
                  }
                  snapshot
                  fullReport
                }
              }
            }
          }
        }
        '''
        self.variables = {
            'id': str(self.report.id),
            'includeHistory': False,
        }

        self.generate_mutation = '''
        mutation GenerateReport($id: ID!) {
          startReportGeneration(id: $id) {
            errors
            ok
            result {
              isSignedOff
              lastGeneration {
                isApproved
              }
              id
              generations {
                results {
                  createdBy {
                    email
                  }
                  snapshot
                  fullReport
                }
              }
            }
          }
        }
        '''

    def test_valid_report_generation_for_sign_off(self):
        assert self.report.is_approved is None
        assert self.report.is_signed_off is False
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(user)
        response = self.query(
            self.generate_mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['startReportGeneration']['errors'], content)
        self.assertEqual(content['data']['startReportGeneration']['result']['isSignedOff'], False)
        self.assertEqual(content['data']['startReportGeneration']['result']['lastGeneration']['isApproved'], False)
        self.assertEqual(len(content['data']['startReportGeneration']['result']['generations']['results']), 1)

        # retry generate should fail
        response = self.query(
            self.generate_mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertIn('report', [item['field'] for item in content['data']['startReportGeneration']['errors']])

    def test_valid_report_sign_off_and_retrieval(self):
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(user)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        # we need to generate first
        self.assertIn(
            'report',
            [i['field'] for i in content['data']['signOffReport']['errors']]
        )

        gen = ReportGeneration.objects.create(report=self.report)
        assert gen.is_signed_off is False

        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['signOffReport']['errors'], content)
        self.report.refresh_from_db()
        assert self.report.is_signed_off is True
        self.assertEqual(content['data']['signOffReport']['result']['isSignedOff'], True, content)
        self.assertEqual(content['data']['signOffReport']['result']['id'], str(self.report.id))
        self.assertEqual(len(content['data']['signOffReport']['result']['generations']['results']), 1)

    def test_invalid_report_signoff(self):
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestReportApprove(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.report = ReportFactory.create(
            created_by=self.admin
        )
        self.generation = ReportGeneration.objects.create(
            report=self.report
        )
        self.mutation = '''
        mutation ApproveReport($id: ID!, $approve: Boolean!) {
          approveReport(id: $id, approve: $approve) {
            ok
            errors
            result {
              lastGeneration {
                isApproved
                approvals {
                  results {
                    createdBy {
                      email
                      id
                    }
                  }
                }
              }
            }
          }
        }
        '''
        self.variables = {
            'id': str(self.report.id),
            'approve': True,
        }

    def test_valid_report_approval(self):
        user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.report.approvals.count() == 0
        self.force_login(user)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['approveReport']['errors'], content)
        assert self.report.approvals.count() == self.report.last_generation.approvers.count()
        self.assertEqual(
            content['data']['approveReport']['result']['lastGeneration']['approvals']['results'][0]['createdBy']['email'],
            user.email, content
        )

    def test_invalid_report_approval_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestReportComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''
        mutation MyMutation($input: ReportCommentCreateInputType!) {
          createReportComment(data: $input) {
            ok
            result {
              id
              createdBy { email }
            }
          }
        }
        '''
        self.update_mutation = '''
        mutation MyMutation($input: ReportCommentUpdateInputType!) {
          updateReportComment(data: $input) {
            ok
            result {
              id
              createdBy { email }
            }
          }
        }
        '''

        self.report = ReportFactory.create()
        self.input = dict(
            report=str(self.report.id),
            body='lol'
        )

    def test_valid_commenting(self):
        user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(user)
        response = self.query(
            self.mutation,
            input_data=self.input,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createReportComment']['ok'], content)
        self.assertTrue(content['data']['createReportComment']['result']['createdBy']['email'],
                        user.email)

    def test_valid_comment_update(self):
        user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        comment = ReportCommentFactory.create(
            created_by=user
        )
        input_data = dict(
            body='blaaa',
            id=str(comment.id),
        )
        self.force_login(user)
        response = self.query(
            self.update_mutation,
            input_data=input_data,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateReportComment']['ok'], content)
        self.assertTrue(content['data']['updateReportComment']['result']['createdBy']['email'],
                        user.email)

        # different user
        user2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(user2)
        response = self.query(
            self.update_mutation,
            input_data=input_data,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateReportComment']['ok'], content)


class TestReportFilter(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.create_report = '''mutation MyMutation($input: ReportCreateInputType!) {
            createReport(data: $input) {
                result {
                    id
                }
                ok
                errors
            }
        }'''
        self.entries_report_query = '''
        query MyQuery($id: ID!) {
          report(id: $id) {
            entriesReport {
              results {
                id
                articleTitle
              }
              totalCount
            }
          }
        }
        '''
        self.figures_report_query = '''
        query MyQuery($id: ID!) {
          report(id: $id) {
            figuresReport {
              results {
                id
              }
              totalCount
            }
          }
        }
        '''
        # Create 10 days grid report
        report_start_date = timezone.now() + timezone.timedelta(days=-20)
        report_end_date = timezone.now() + timezone.timedelta(days=-10)
        self.input = {
            "name": "disss",
            "filterFigureStartAfter": str(report_start_date.date()),
            "filterFigureEndBefore": str(report_end_date.date()),
        }
        self.editor = create_user_with_role(USER_ROLE.ADMIN.name)
        self.category = FigureCategory.objects.get(name__iexact="idps", type=STOCK)
        self.force_login(self.editor)

    def tearDown(self):
        cache.clear()

    def test_report_should_list_entries_between_figure_start_date_and_figure_end_date(self):
        # Create entries such that report end date is between figure start
        # date and figure end date
        for i in range(3):
            entry = EntryFactory.create()
            FigureFactory.create(
                entry=entry,
                start_date=timezone.now() + timezone.timedelta(days=-15),
                end_date=timezone.now() + timezone.timedelta(days=20),
                category=self.category
            )

        # Creat reports where  reference point is not in renge
        # Should exclude these figures
        for i in range(2):
            entry = EntryFactory.create()
            FigureFactory.create(
                entry=entry,
                start_date=timezone.now() + timezone.timedelta(days=50),
                end_date=timezone.now() + timezone.timedelta(days=50),
                category=self.category
            )

        # Test for entries
        response = self.query(
            self.create_report,
            input_data=self.input,
        )
        report = response.json()
        repot_id = report["data"]["createReport"]["result"]["id"]
        response = self.query(
            self.entries_report_query,
            variables=dict(
                id=str(repot_id),
            )
        )
        entries = response.json()
        entries_count = entries["data"]["report"]["entriesReport"]["totalCount"]
        self.assertEqual(entries_count, 3)

        # Test for figures
        response = self.query(
            self.figures_report_query,
            variables=dict(
                id=str(repot_id),
            )
        )
        entries = response.json()
        entries_count = entries["data"]["report"]["figuresReport"]["totalCount"]
        self.assertEqual(entries_count, 3)

    def test_report_should_include_figures_without_end_date_in_range(self):
        for i in range(3):
            entry = EntryFactory.create()
            FigureFactory.create(
                entry=entry,
                start_date=timezone.now() + timezone.timedelta(days=-15),
                category=self.category
            )

        # Creat reports where  reference point is not in renge
        # Should exclude these figures
        for i in range(2):
            entry = EntryFactory.create()
            FigureFactory.create(
                entry=entry,
                start_date=timezone.now() + timezone.timedelta(days=50),
                end_date=timezone.now() + timezone.timedelta(days=50),
                category=self.category
            )
        response = self.query(
            self.create_report,
            input_data=self.input,
        )
        report = response.json()
        repot_id = report["data"]["createReport"]["result"]["id"]

        # Test for entries
        response = self.query(
            self.entries_report_query,
            variables=dict(
                id=str(repot_id),
            )
        )
        entries = response.json()
        entries_count = entries["data"]["report"]["entriesReport"]["totalCount"]
        self.assertEqual(entries_count, 3)

        # Test for figures
        response = self.query(
            self.figures_report_query,
            variables=dict(
                id=str(repot_id),
            )
        )
        entries = response.json()
        entries_count = entries["data"]["report"]["figuresReport"]["totalCount"]
        self.assertEqual(entries_count, 3)
