# Generated by Django 3.0.5 on 2022-11-17 09:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('event', '0028_auto_20221114_0519'),
        ('entry', '0077_auto_20221114_0425'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.IntegerField(choices=[(0, 'Figure approved'), (2, 'Figure re-requested review'), (3, 'Figure un-approved'), (4, 'Event assigned'), (5, 'Event assignee cleared'), (6, 'Event signed off')], verbose_name='Notification Type')),
                ('is_read', models.BooleanField(default=False, help_text='Whether notification has been marked as read', verbose_name='Is read?')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When notification was created', verbose_name='Created at')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='events', to='event.Event', verbose_name='Event')),
                ('figure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='figures', to='entry.Figure', verbose_name='Figure')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='For user')),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
            },
        ),
    ]
