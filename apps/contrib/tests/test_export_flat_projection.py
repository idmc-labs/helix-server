"""Guards for the two export fast paths that replace framework machinery.

`make_flat_to_representation` reimplements DRF's per-row serialisation and `get_enum_label` caches
a translation DRF resolves on every access. Both are equivalence-critical and neither is reachable
from an existing test, so a regression in either publishes wrong numbers on a public endpoint at
full speed. DRF itself is the oracle here: it serialises a Mapping, so the same row dict can go
through both paths and be compared.
"""

from django.test import SimpleTestCase
from rest_framework import serializers

from apps.common.utils import get_enum_label
from apps.entry.models import FigureLocation
from apps.entry.serializers import FigureReadOnlySerializer
from utils.serializers import make_flat_to_representation


def _row_for(serializer, **overrides):
    """A `.values()`-shaped row carrying every source `serializer` reads."""
    row = {}
    for index, field in enumerate(serializer.fields.values()):
        if isinstance(field, serializers.IntegerField):
            row[field.source] = index
        elif isinstance(field, serializers.FloatField):
            row[field.source] = index + 0.5
        elif isinstance(field, serializers.BooleanField):
            row[field.source] = bool(index % 2)
        elif isinstance(field, serializers.ListField):
            row[field.source] = []
        else:
            row[field.source] = f"value-{index}"
    row.update(overrides)
    return row


class TestFlatProjectionMatchesDrf(SimpleTestCase):
    """The fast path must agree with DRF field for field, not merely in shape."""

    def setUp(self):
        self.serializer = FigureReadOnlySerializer()
        self.flat = make_flat_to_representation(self.serializer)

    def test_every_field_matches_drf_on_a_populated_row(self):
        row = _row_for(self.serializer)
        self.assertEqual(self.flat(row), dict(FigureReadOnlySerializer(row).data))

    def test_every_field_matches_drf_when_every_value_is_null(self):
        # The fast path short-circuits None instead of calling `to_representation`. That is only
        # equivalent while no field coerces None into something else.
        row = {field.source: None for field in self.serializer.fields.values()}
        self.assertEqual(self.flat(row), dict(FigureReadOnlySerializer(row).data))

    def test_renamed_sources_are_read_from_the_source_not_the_field_name(self):
        # `country` reads `country_name`, `latitude` reads `centroid_lat`: a fast path keyed on the
        # field name would silently emit nulls for all three.
        row = _row_for(self.serializer, country_name="Nepal", centroid_lat=1.5, centroid_lon=2.5)
        flat = self.flat(row)
        self.assertEqual(flat["country"], "Nepal")
        self.assertEqual(flat["latitude"], 1.5)
        self.assertEqual(flat["longitude"], 2.5)
        self.assertEqual(flat, dict(FigureReadOnlySerializer(row).data))

    def test_field_and_source_names_are_both_covered_by_the_serializer_contract(self):
        # The fast path indexes rows by source and emits field names. Both sets are asserted so a
        # renamed field cannot pass by matching itself.
        sources = {field.source for field in self.serializer.fields.values()}
        names = set(self.serializer.fields)
        self.assertEqual(set(self.flat(_row_for(self.serializer))), names)
        self.assertTrue(sources)


class TestFlatProjectionRefusesWhatItCannotDo(SimpleTestCase):
    """The divergences from DRF are pinned, so widening the serializer fails here first.

    `make_flat_to_representation` is equivalent to DRF only because
    `FigureReadOnlySerializer` declares plain, non-dotted, always-present sources. Each test below
    is a shape that would make it silently or loudly wrong, and the assertion records which.
    """

    def test_dotted_source_is_refused_when_the_projection_is_built(self):
        class Dotted(serializers.Serializer):
            name = serializers.CharField(source="country.name")

        with self.assertRaises(ValueError) as caught:
            make_flat_to_representation(Dotted())
        self.assertIn("country.name", str(caught.exception))

    def test_star_source_raises_instead_of_being_handed_the_whole_row(self):
        # DRF passes the entire object to a `source="*"` field. The fast path looks up the literal
        # key "*", so such a field must not be added without teaching it this case.
        class Star(serializers.Serializer):
            everything = serializers.DictField(source="*")

        flat = make_flat_to_representation(Star())
        with self.assertRaises(KeyError):
            flat({"anything": 1})

    def test_absent_source_raises_on_both_paths(self):
        # Both raise KeyError: `SkipField` governs writes, so on read DRF surfaces the missing key
        # too, only with a friendlier message. A queryset that stops selecting a column therefore
        # fails the same way on either path, which is one fewer divergence than it appears.
        serializer = FigureReadOnlySerializer()
        row = _row_for(serializer)
        row.pop("iso3")
        with self.assertRaises(KeyError):
            dict(FigureReadOnlySerializer(row).data)
        with self.assertRaises(KeyError):
            make_flat_to_representation(serializer)(row)


class TestEnumLabelCacheKeying(SimpleTestCase):
    """A member-only cache key returns another enum's label for the same integer.

    `django_enumfield` members compare and hash as their integer value, so `ACCURACY(0)` and
    `IDENTIFIER(0)` are interchangeable as dict keys. The export looks a label up per row, so a
    collision mislabels every affected row at full speed and no timing measurement can see it.
    """

    def test_same_integer_in_two_enums_keeps_its_own_label(self):
        accuracy = FigureLocation.ACCURACY(0)
        identifier = FigureLocation.IDENTIFIER(0)
        self.assertEqual(int(accuracy), int(identifier))
        self.assertEqual(get_enum_label(accuracy), str(accuracy.label))
        self.assertEqual(get_enum_label(identifier), str(identifier.label))
        self.assertNotEqual(get_enum_label(accuracy), get_enum_label(identifier))

    def test_lookup_order_does_not_decide_the_label(self):
        # Whichever enum is seen first must not populate the cache for the other.
        identifier_first = get_enum_label(FigureLocation.IDENTIFIER(1))
        accuracy_second = get_enum_label(FigureLocation.ACCURACY(1))
        self.assertEqual(identifier_first, str(FigureLocation.IDENTIFIER(1).label))
        self.assertEqual(accuracy_second, str(FigureLocation.ACCURACY(1).label))
        self.assertNotEqual(identifier_first, accuracy_second)

    def test_none_is_passed_through(self):
        self.assertIsNone(get_enum_label(None))

    def test_repeated_lookups_agree_with_the_uncached_label(self):
        member = FigureLocation.ACCURACY(2)
        self.assertEqual(get_enum_label(member), str(member.label))
        self.assertEqual(get_enum_label(member), str(member.label))
