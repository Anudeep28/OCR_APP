# Generated by Django 5.0 on 2025-02-26 09:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ocr_app', '0014_alter_loandocument_driving_license'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loandocument',
            name='credit_score',
            field=models.CharField(blank=True, default='', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='loandocument',
            name='loan_amount',
            field=models.CharField(blank=True, default='', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='loandocument',
            name='loan_term_months',
            field=models.CharField(blank=True, default='', max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='loandocument',
            name='monthly_income',
            field=models.CharField(blank=True, default='', max_length=50, null=True),
        ),
    ]
