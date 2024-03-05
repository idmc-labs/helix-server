# Generated by Django 3.2 on 2024-03-26 08:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0097_fix_figure_created_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='entryreviewer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='figure',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='figuretag',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
    ]
