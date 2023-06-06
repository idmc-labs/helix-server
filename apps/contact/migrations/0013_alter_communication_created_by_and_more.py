# Generated by Django 4.0 on 2023-06-05 08:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_user_first_name'),
        ('contact', '0012_contact_full_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='communication',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_%(class)s', to='users.user', verbose_name='Created By'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_%(class)s', to='users.user', verbose_name='Created By'),
        ),
    ]
