from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestEntryFiguresPaginated(HelixGraphQLTestCase):
    """EntryType.figures is a paginated field (DjangoPaginatedListObjectField over
    FigureListType), served via the OneToManyLoader paginated path. These tests assert the
    nested `entryList { results { figures { results { ... } } } }` path resolves correctly
    (per-entry grouping, no under-fetch) and that pageSize bounds the per-entry breadth."""

    def setUp(self) -> None:
        self.guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(self.guest)

        self.country = CountryFactory.create()
        self.event = EventFactory.create()
        self.entry = EntryFactory.create(created_by=self.guest)

        # three figures on the entry, distinct total_figures (non-zero → detect under-fetch)
        self.figures = [
            FigureFactory.create(
                entry=self.entry,
                event=self.event,
                country=self.country,
                category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                role=Figure.ROLE.RECOMMENDED,
                total_figures=100 + i,
            )
            for i in range(3)
        ]

    def test_nested_figures_resolve_per_entry_without_underfetch(self):
        query = """
            query EntryListFigures {
              entryList {
                results {
                  id
                  figures {
                    results {
                      id
                      totalFigures
                    }
                  }
                }
              }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)
        results = response.json()["data"]["entryList"]["results"]
        entry_row = next(r for r in results if r["id"] == str(self.entry.id))
        figures = entry_row["figures"]["results"]

        self.assertEqual({f["id"] for f in figures}, {str(f.id) for f in self.figures})
        # totalFigures comes back for every figure (no selection-set under-fetch)
        self.assertEqual(
            {f["id"]: f["totalFigures"] for f in figures},
            {str(f.id): f.total_figures for f in self.figures},
        )

    def test_page_size_bounds_per_entry_breadth(self):
        query = """
            query EntryListFigures {
              entryList {
                results {
                  id
                  figures(pageSize: 2) {
                    results { id }
                  }
                }
              }
            }
        """
        response = self.query(query)
        self.assertResponseNoErrors(response)
        results = response.json()["data"]["entryList"]["results"]
        entry_row = next(r for r in results if r["id"] == str(self.entry.id))
        self.assertEqual(len(entry_row["figures"]["results"]), 2)
