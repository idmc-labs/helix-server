# Generated by Django 3.0.14 on 2022-12-22 04:16

from django.db import migrations


class Migration(migrations.Migration):

    def update_parent_types(apps, schema_editor):
        from django.db.models import Subquery, OuterRef, Q

        # Import models
        Event = apps.get_model('event', 'Event')
        Figure = apps.get_model('entry', 'Figure')

        # Update event fields
        Event.objects.filter(
            (
                (
                    Q(disaster_category__isnull=True) |
                    Q(disaster_sub_category__isnull=True) |
                    Q(disaster_type__isnull=True)
                ) &
                Q(disaster_sub_type__isnull=False)
            ) |
            Q(violence__isnull=True, violence_sub_type__isnull=False)
        ).update(
            disaster_type=Subquery(Event.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type')[:1]),
            disaster_sub_category=Subquery(Event.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type__disaster_sub_category')[:1]),
            disaster_category=Subquery(Event.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type__disaster_sub_category__category')[:1]),
            violence=Subquery(Event.objects.filter(pk=OuterRef('pk')).values('violence_sub_type__violence')[:1]),
        )

        # Update figure fields
        Figure.objects.filter(
            (
                (
                    Q(disaster_category__isnull=True) |
                    Q(disaster_sub_category__isnull=True) |
                    Q(disaster_type__isnull=True)
                ) &
                Q(disaster_sub_type__isnull=False)
            ) |
            Q(violence__isnull=True, violence_sub_type__isnull=False)
        ).update(
            disaster_type=Subquery(Figure.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type')[:1]),
            disaster_sub_category=Subquery(Figure.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type__disaster_sub_category')[:1]),
            disaster_category=Subquery(Figure.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type__disaster_sub_category__category')[:1]),
            violence=Subquery(Figure.objects.filter(pk=OuterRef('pk')).values('violence_sub_type__violence')[:1]),
        )

    dependencies = [
        ('event', '0028_auto_20221114_0519'),
    ]

    operations = [
        migrations.RunPython(update_parent_types, reverse_code=migrations.RunPython.noop),
    ]
