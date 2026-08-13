from django.test import TestCase

from apps.organization.models import Organization
from utils.factories import OrganizationFactory


class TestSoftDeleteQueryset(TestCase):
    """`delete()` is a queryset method, and must not be reachable through the manager.

    `SoftDeleteQueryset.delete()` archives every row it is given. Django marks its own
    `QuerySet.delete` as queryset-only precisely so `Model.objects.delete()` cannot exist; an
    override that drops the marker is copied onto the manager by `Manager.from_queryset`, and
    `Organization.objects.delete()` then archives the whole table.
    """

    def test_manager_does_not_expose_delete(self):
        self.assertFalse(hasattr(Organization.objects, "delete"))

    def test_manager_delete_cannot_archive_the_table(self):
        OrganizationFactory.create(name="kept-org")

        with self.assertRaises(AttributeError):
            Organization.objects.delete()

        # Nothing was archived, because the call never happened.
        self.assertEqual(Organization.objects.filter(deleted_on__isnull=False).count(), 0)

    def test_queryset_delete_archives_instead_of_removing(self):
        archived = OrganizationFactory.create(name="archived-org")
        kept = OrganizationFactory.create(name="kept-org")

        Organization.objects.filter(pk=archived.pk).delete()

        archived.refresh_from_db()
        kept.refresh_from_db()
        self.assertIsNotNone(archived.deleted_on)
        self.assertIsNone(kept.deleted_on)
