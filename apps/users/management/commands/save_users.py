from django.core.management.base import BaseCommand


class Command(BaseCommand):
    # TODO: REMOVE ME
    help = "Update users and contacts for full names"

    def handle(self, *args, **options):
        from apps.contact.models import Contact
        from apps.users.models import User

        for u in User.objects.all():
            u.save()
        for u in Contact.objects.all():
            u.save()
