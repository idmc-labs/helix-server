import json

from apps.parking_lot.models import ParkedItem
from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, ParkingLotFactory
from utils.tests import HelixAPITestCase, HelixGraphQLTestCase, create_user_with_role


class TestCreateParkedItem(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_id = str(CountryFactory.create().id)
        self.mutation = """
        mutation CreateParkedItem($input: ParkedItemCreateInputType!) {
            createParkedItem(data: $input) {
                ok
                errors
                result {
                    id
                    title
                }
            }
        }
        """

        self.assigned_to = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.input = dict(
            assignedTo=str(self.assigned_to.id),
            status="TO_BE_REVIEWED",
            title="title",
            url="http://google.com",
            country=str(self.country_id),
        )

    def test_valid_parking_lot_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(self.mutation, input_data=self.input)

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createParkedItem"]["ok"], content)
        self.assertEqual(content["data"]["createParkedItem"]["result"]["title"], self.input["title"])


class TestUpdateParkedItem(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.parking_lot = ParkingLotFactory.create(created_by=self.reviewer)
        self.mutation = """
        mutation UpdateParkedItem($input: ParkedItemUpdateInputType!) {
            updateParkedItem(data: $input) {
                ok
                errors
                result {
                    id
                    title
                }
            }
        }
        """
        self.input = {
            "id": self.parking_lot.id,
            "title": "updated title",
        }

    def test_valid_parking_lot_update(self) -> None:
        self.force_login(self.reviewer)
        response = self.query(self.mutation, input_data=self.input)

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["updateParkedItem"]["ok"], content)
        self.assertEqual(content["data"]["updateParkedItem"]["result"]["title"], self.input["title"])


class ParkedItemAPITestCase(HelixAPITestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = "/api/parking-lot/"

    def test_get_parked_item(self):
        self.parking_lot = ParkingLotFactory.create()
        self.authenticate()
        response = self.client.get(self.url)
        assert response.status_code == 200
        data = response.data
        self.assertEqual(data[0]["id"], self.parking_lot.id)

    def test_post_parked_item(self):
        self.country = CountryFactory.create(iso3="NPL")
        self.assigned_to = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        data = {
            "title": "test_parking",
            "url": "http://google.com",
            "country_iso3": self.country.iso3,
            "country": self.country.id,
            "assigned_to": self.assigned_to.id,
        }
        self.authenticate()
        response = self.client.post(self.url, data)
        assert response.status_code == 201

    def test_post_multiple_parked_item(self):
        old_count = ParkedItem.objects.count()
        self.country1 = CountryFactory.create(iso3="NPL")
        self.country2 = CountryFactory.create(iso3="USA")
        self.assigned_to1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.assigned_to2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        data = [
            {
                "title": "test_parking",
                "url": "http://google.com",
                "country_iso3": self.country1.iso3,
                "country": self.country1.id,
                "assigned_to": self.assigned_to1.id,
            },
            {
                "title": "test_parking1",
                "url": "http://hello.com",
                "country_iso3": self.country2.iso3,
                "country": self.country2.id,
                "assigned_to": self.assigned_to2.id,
            },
        ]
        self.authenticate()
        response = self.client.post(self.url, json.dumps(data), content_type="application/json")
        assert response.status_code == 201
        self.assertEqual(ParkedItem.objects.count(), old_count + 2)

    def test_validate_iso3_for_country(self):
        self.country1 = CountryFactory.create(iso3="npl")
        self.country2 = CountryFactory.create(iso3="ind")
        self.assigned_to1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        data = {
            "title": "test_parking",
            "url": "http://google.com",
            "country_iso3": "abc",
            "country": self.country1.id,
            "assigned_to": self.assigned_to1.id,
        }
        self.authenticate()
        response = self.client.post(self.url, data)
        assert response.status_code == 400

        # try to post with the iso3 that country has
        data["country_iso3"] = "npl"
        self.authenticate()
        response = self.client.post(self.url, data)
        assert response.status_code == 201
        self.assertEqual(response.data["country"], self.country1.id)  # should set the country of iso3 posted

        # try to post without iso3
        del data["country_iso3"]
        self.authenticate()
        response = self.client.post(self.url, data)
        assert response.status_code == 201

        # try to post without iso3
        data["country_iso3"] = []
        self.authenticate()
        response = self.client.post(self.url, data)
        assert response.status_code == 201

    def test_multiword_diacritics_search(self):
        list_query = """
            query MyQuery($search: String!) {
                parkedItemList(filters: {search: $search}) {
                    totalCount
                    results {
                        comments
                        url
                        title
                    }
                }
            }
        """

        title1 = "ženg_prøtest"
        url1 = "http://youba.com"
        self.country1 = CountryFactory.create(iso3="NPL")
        self.assigned_to1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

        self.country2 = CountryFactory.create(iso3="USA")
        self.assigned_to2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        title2 = "Bangladesh flood"
        url2 = "http://bangali.com"
        data = [
            {
                "title": title1,
                "url": url1,
                "country_iso3": self.country1.iso3,
                "country": self.country1.id,
                "assigned_to": self.assigned_to1.id,
            },
            {
                "title": title2,
                "url": url2,
                "country_iso3": self.country2.iso3,
                "country": self.country2.id,
                "assigned_to": self.assigned_to2.id,
                "comments": "Many people participated in the protest here.",
            },
        ]

        self.authenticate()

        response = self.client.post(self.url, json.dumps(data), content_type="application/json")

        assert response.status_code == 201

        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": list_query,
                    "variables": {
                        "search": "protest",
                    },
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200

        content = json.loads(response.content)

        results = content["data"]["parkedItemList"]["results"]
        self.assertEqual(len(results), 1)

        returned_titles = [item["title"] for item in results]
        self.assertIn(title1, returned_titles)

        response = self.client.post(
            "/graphql/",
            data=json.dumps(
                {
                    "query": list_query,
                    "variables": {"search": "nonexistent content"},
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200

        content = json.loads(response.content)

        results = content["data"]["parkedItemList"]["results"]
        self.assertEqual(len(results), 0)
