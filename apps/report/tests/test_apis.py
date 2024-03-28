from django.utils import timezone
from apps.users.enums import USER_ROLE
from apps.report.models import ReportGeneration, Report
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from utils.factories import (
    CountryFactory,
    ReportFactory,
    ReportCommentFactory,
    EntryFactory,
    FigureFactory,
    MonitoringSubRegionFactory,
    EventFactory,
    CountryRegionFactory,
    CountrySubRegionFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


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
                    filterFigureCategories
                    filterFigureRoles
                    filterFigureCrisisTypes
                    isGiddReport
                    isPublic
                    id
                    isPfaVisibleInGidd
                    changeInDataAvailability
                    changeInMethodology
                    changeInSource
                    retroactiveChange
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
            "changeInSource": True,
            "changeInMethodology": True,
            "changeInDataAvailability": True,
            "retroactiveChange": True,
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
        self.assertEqual(content['data']['createReport']['result']['changeInSource'],
                         True)

    def test_invalid_report_creation_by_guest(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_is_gidd_report(self) -> None:

        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        self.input['filterFigureCategories'] = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.name
        self.input['filterFigureRoles'] = [Figure.ROLE.RECOMMENDED.name]
        self.input['filterFigureCrisisTypes'] = [Crisis.CRISIS_TYPE.DISASTER.name]
        self.input['isGiddReport'] = True
        self.input['isPublic'] = False
        self.input['giddReportYear'] = 2022

        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()
        data = content['data']['createReport']['result']

        self.assertEqual(data['filterFigureCategories'], [])
        self.assertEqual(data['filterFigureRoles'], [])
        self.assertEqual(data['filterFigureCrisisTypes'], [])
        self.assertEqual(data['filterFigureStartAfter'], '2022-01-01')
        self.assertEqual(data['filterFigureEndBefore'], '2022-12-31')
        self.assertEqual(data['isPublic'], True)
        self.assertEqual(data['isPfaVisibleInGidd'], False)


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
          query MyQuery($id: ID) {
            entryList(filters: {reportId: $id}) {
              results {
                id
                articleTitle
              }
              totalCount
            }
          }
        '''
        self.figures_report_query = '''
          query MyQuery($id: ID!) {
            report(id: $id) {
              figuresReport {
                results {
                  id
                  entry {
                    id
                  }
                  changeInSource
                  changeInMethodology
                  changeInDataAvailability
                  retroactiveChange
                }
                totalCount
              }
            }
          }
        '''
        self.report_list_query = '''
            query MyQuery(
                $changeInSource: Boolean,
                $changeInMethodology: Boolean
                $changeInDataAvailability: Boolean
            ){
              reportList(filters: {
                changeInSource: $changeInSource,
                changeInMethodology: $changeInMethodology
                changeInDataAvailability: $changeInDataAvailability
                }) {
                results {
                  id
                }
                totalCount
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
        self.category = Figure.FIGURE_CATEGORY_TYPES.IDPS
        self.force_login(self.editor)
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.OTHER.value,
        )

    def test_filter_report(self):
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(user)

        ReportFactory.create_batch(3, is_public=True, change_in_source=True)
        ReportFactory.create_batch(4, is_public=True, change_in_methodology=True)
        ReportFactory.create_batch(5, is_public=True, change_in_data_availability=True)

        for filter, exp_result in [
                ("changeInSource", 3),
                ("changeInMethodology", 4),
                ("changeInDataAvailability", 5),
        ]:
            response = self.query(
                self.report_list_query,
                variables={
                    filter: True
                }
            )
            content = response.json()
            self.assertEqual(content['data']['reportList']['totalCount'], exp_result)

    def test_report_should_list_entries_between_figure_start_date_and_figure_end_date(self):
        # Create entries such that report end date is between figure start
        # date and figure end date
        for _ in range(3):
            entry = EntryFactory.create()
            FigureFactory.create(
                entry=entry,
                start_date=timezone.now() + timezone.timedelta(days=-15),
                end_date=timezone.now() + timezone.timedelta(days=-10),
                category=self.category,
                event=self.event
            )
        # Create reports where  reference point is not in range
        # Should exclude these figures
        for _ in range(2):
            entry = EntryFactory.create()
            FigureFactory.create(
                entry=entry,
                start_date=timezone.now() + timezone.timedelta(days=50),
                end_date=timezone.now() + timezone.timedelta(days=50),
                category=self.category,
                event=self.event,
            )

        response = self.query(
            self.create_report,
            input_data=self.input,
        )
        report_id = response.json()["data"]["createReport"]["result"]["id"]

        # Test for entries
        response = self.query(
            self.entries_report_query,
            variables=dict(
                id=str(report_id),
            )
        )
        entries_count = response.json()["data"]["entryList"]["totalCount"]
        self.assertEqual(entries_count, 3)


class TestPrivatePublicReports(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''mutation MyMutation($input: ReportCreateInputType!) {
            createReport(data: $input) {
                result {
                    id
                    isPublic
                }
                ok
                errors
            }
        }'''

        self.report_query = '''
        query reportList($isPublic: Boolean){
          reportList(filters: {isPublic: $isPublic}) {
            results {
              isPublic
              id
              createdBy {
                id
              }
            }
            totalCount
          }
        }
        '''
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.user1 = create_user_with_role(USER_ROLE.ADMIN.name)

    def test_should_return_private_reports_if_filter_is_not_applied(self) -> None:
        self.force_login(self.user)
        # Create report a private report
        input = {
            "name": "test private report",
            "isPublic": False
        }
        create_response = self.query(
            self.mutation,
            input_data=input
        )
        content = create_response.json()
        self.assertResponseNoErrors(create_response)
        self.assertTrue(content['data']['createReport']['ok'], content)
        self.assertEqual(content['data']['createReport']['result']['isPublic'], False)

        # Test can list private reports
        variables = {}
        list_response = self.query(self.report_query, variables=variables)
        content = list_response.json()
        self.assertResponseNoErrors(list_response)
        self.assertEqual(content['data']['reportList']['totalCount'], 1)
        self.assertEqual(content['data']['reportList']['results'][0]['isPublic'], False)
        self.assertEqual(content['data']['reportList']['results'][0]['createdBy']["id"], str(self.user.id))

        # Test should not list other users private reports
        self.force_login(self.user1)
        variables = {}
        list_response = self.query(self.report_query, variables=variables)
        content = list_response.json()
        self.assertResponseNoErrors(list_response)
        self.assertEqual(content['data']['reportList']['results'], [])
        self.assertEqual(content['data']['reportList']['totalCount'], 0)

    def test_can_list_public_reports(self) -> None:
        self.force_login(self.user)
        # Create report a public report
        input = {
            "name": "test public report",
            "isPublic": True
        }
        create_response = self.query(
            self.mutation,
            input_data=input
        )
        content = create_response.json()
        self.assertResponseNoErrors(create_response)
        self.assertTrue(content['data']['createReport']['ok'], content)
        self.assertEqual(content['data']['createReport']['result']['isPublic'], True)

        # Test can list public reports
        variables = {"isPublic": True}
        list_response = self.query(self.report_query, variables=variables)
        content = list_response.json()
        self.assertResponseNoErrors(list_response)
        self.assertEqual(content['data']['reportList']['totalCount'], 1)
        self.assertEqual(content['data']['reportList']['results'][0]['isPublic'], True)
        self.assertEqual(content['data']['reportList']['results'][0]['createdBy']["id"], str(self.user.id))

        # Test can list other users public report
        self.force_login(self.user1)
        list_response = self.query(self.report_query, variables=variables)
        content = list_response.json()
        self.assertResponseNoErrors(list_response)
        self.assertEqual(content['data']['reportList']['totalCount'], 1)
        self.assertEqual(content['data']['reportList']['results'][0]['isPublic'], True)
        self.assertEqual(content['data']['reportList']['results'][0]['createdBy']["id"], str(self.user.id))


class TestIndividualReportExport(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.report = ReportFactory.create(
            created_by=self.admin,
            filter_figure_start_after='2020-01-01',
            filter_figure_end_before='2021-01-01',
            generated_from=Report.REPORT_TYPE.MASTERFACT,
        )
        self.export_mutation = '''
        mutation exportReport($id: ID!) {
          exportReport(id: $id) {
            errors
            ok
            result {
              id
              name
            }
          }
        }
        '''
        self.variables = {
            'id': str(self.report.id),
        }

    def test_user_can_export_individual_report(self):
        # Test admin user can export report
        user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(user)
        response = self.query(
            self.export_mutation,
            variables=self.variables
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['exportReport']['errors'], content)

        # Test non admin user can export report
        user = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(user)
        response = self.query(
            self.export_mutation,
            variables=self.variables
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['exportReport']['errors'], content)


class TestPaf(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.region = CountryRegionFactory.create()
        self.sub_region = CountrySubRegionFactory.create()
        self.monitoring_sub_region = MonitoringSubRegionFactory.create()

        self.country = CountryFactory.create(
            monitoring_sub_region=self.monitoring_sub_region,
            region=self.region,
            sub_region=self.sub_region,
        )
        self.regional_coordinator = create_user_with_role(
            USER_ROLE.REGIONAL_COORDINATOR.name,
            country=self.country.id,
            monitoring_sub_region=self.monitoring_sub_region.id,
        )
        self.monitoring_expert = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            country=self.country.id,
            monitoring_sub_region=self.monitoring_sub_region.id,
        )
        self.guest = create_user_with_role(
            USER_ROLE.GUEST.name,
        )
        self.admin = create_user_with_role(
            USER_ROLE.ADMIN.name,
        )
        self.report = ReportFactory.create(
            is_pfa_visible_in_gidd=False,
            filter_figure_start_after='2022-01-01',
            filter_figure_end_before='2022-12-31',
            is_public=True,
            filter_figure_categories=[Figure.FIGURE_CATEGORY_TYPES.IDPS.value],
            filter_figure_crisis_types=[Crisis.CRISIS_TYPE.CONFLICT.value]
        )
        self.report.filter_figure_countries.add(self.country)
        self.set_pfa_visible_in_gidd = '''
          mutation setPfaVisibleInGidd($reportId: ID!, $isPfaVisibleInGidd: Boolean!) {
              setPfaVisibleInGidd(reportId: $reportId, isPfaVisibleInGidd: $isPfaVisibleInGidd) {
                  ok
                  errors
                  result {
                      id
                      isPfaVisibleInGidd
                  }
              }
          }
        '''

        self.update_report = '''
          mutation MyMutation($input: ReportUpdateInputType!) {
            updateReport(data: $input) {
              ok
              result {
                isPfaVisibleInGidd
              }
            }
          }
        '''

    def test_only_admin_can_change_is_pfa_visible_in_gidd(self):
        # Valid case
        self.force_login(self.admin)
        response = self.query(
            self.set_pfa_visible_in_gidd,
            variables={'reportId': self.report.id, 'isPfaVisibleInGidd': True}
        )
        is_pfa_visible_in_gidd = response.json()['data']['setPfaVisibleInGidd']['result']['isPfaVisibleInGidd']
        self.assertEqual(is_pfa_visible_in_gidd, True)

        # Update report with invalid values for PFA
        update_response = self.query(
            self.update_report,
            input_data={'id': self.report.id, 'isPublic': False}
        )
        is_pfa_visible_in_gidd = update_response.json()['data']['updateReport']['result']['isPfaVisibleInGidd']
        self.assertEqual(is_pfa_visible_in_gidd, False)

        self.force_login(self.regional_coordinator)
        response = self.query(
            self.set_pfa_visible_in_gidd,
            variables={'reportId': self.report.id, 'isPfaVisibleInGidd': True}
        )
        is_pfa_visible_in_gidd = update_response.json()['data']['updateReport']['result']['isPfaVisibleInGidd']
        self.assertEqual(is_pfa_visible_in_gidd, False)

        self.force_login(self.monitoring_expert)
        response = self.query(
            self.set_pfa_visible_in_gidd,
            variables={'reportId': self.report.id, 'isPfaVisibleInGidd': True}
        )
        self.assertIn(PERMISSION_DENIED_MESSAGE, response.json()['errors'][0]['message'])

        self.force_login(self.guest)
        response = self.query(
            self.set_pfa_visible_in_gidd,
            variables={'reportId': self.report.id, 'isPfaVisibleInGidd': True}
        )
        self.assertIn(PERMISSION_DENIED_MESSAGE, response.json()['errors'][0]['message'])
