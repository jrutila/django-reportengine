# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-10-25 04:58
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion
import reportengine.jsonfield


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ReportRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_made', models.DateTimeField(db_index=True, default=datetime.datetime.now)),
                ('completion_timestamp', models.DateTimeField(blank=True, null=True)),
                ('token', models.CharField(db_index=True, max_length=255)),
                ('task', models.CharField(blank=True, max_length=128)),
                ('namespace', models.CharField(max_length=255)),
                ('slug', models.CharField(max_length=255)),
                ('params', reportengine.jsonfield.JSONField(blank=True)),
                ('viewed_on', models.DateTimeField(blank=True, null=True)),
                ('aggregates', reportengine.jsonfield.JSONField(blank=True)),
            ],
            options={
                'permissions': (('run_report', 'Can run reports'),),
            },
        ),
        migrations.CreateModel(
            name='ReportRequestExport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_made', models.DateTimeField(db_index=True, default=datetime.datetime.now)),
                ('completion_timestamp', models.DateTimeField(blank=True, null=True)),
                ('token', models.CharField(db_index=True, max_length=255)),
                ('task', models.CharField(blank=True, max_length=128)),
                ('format', models.CharField(max_length=10)),
                ('payload', models.FileField(upload_to=b'reportengine/exports/%Y/%m/%d')),
                ('report_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exports', to='reportengine.ReportRequest')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ReportRequestRow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row_number', models.PositiveIntegerField()),
                ('data', reportengine.jsonfield.JSONField(blank=True)),
                ('report_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='reportengine.ReportRequest')),
            ],
        ),
    ]