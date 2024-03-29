# Generated by Django 3.0.14 on 2022-12-29 05:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0028_auto_20221114_0519'),
        ('review', '0011_auto_20221107_0753'),
        ('entry', '0077_auto_20221114_0425'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notification', '0004_notification_entry'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='review_comment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='review.UnifiedReviewComment', verbose_name='Unified review comment'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='actor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='actor_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Actor'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='entry',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='entry.Entry', verbose_name='Entry'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='event',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='event.Event', verbose_name='Event'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='figure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notifications', to='entry.Figure', verbose_name='Figure'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='recipient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipient_notifications', to=settings.AUTH_USER_MODEL, verbose_name='For user'),
        ),
    ]
