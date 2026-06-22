from django.test import SimpleTestCase

from apps.entry.models import Figure


class FigureCategoryListsTest(SimpleTestCase):
    """Guards the figureList listing semantics: every figure category must be classified as
    exactly stock OR flow.

    ``Figure.category`` is NOT NULL (required), and the unfiltered figureList relies on a
    non-null category necessarily being *listable* (stock or flow). That holds only while
    ``flow_list() ∪ stock_list()`` stays exhaustive over the enum — so a newly added category
    can't silently be neither (and slip into / be excluded from the list). These tests pin that.
    """

    def test_flow_and_stock_are_exhaustive_over_the_enum(self):
        flow = set(Figure.flow_list())
        stock = set(Figure.stock_list())
        all_values = {member.value for member in Figure.FIGURE_CATEGORY_TYPES}
        self.assertEqual(
            flow | stock,
            all_values,
            "flow_list() ∪ stock_list() must cover every FIGURE_CATEGORY_TYPES value. When "
            "adding a category, classify it as stock or flow so a non-null category is always listable.",
        )

    def test_no_category_is_both_flow_and_stock(self):
        self.assertEqual(
            set(Figure.flow_list()) & set(Figure.stock_list()),
            set(),
            "a category must be either stock or flow, not both",
        )
