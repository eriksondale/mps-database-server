# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drugtrials', '0003'),
    ]

    operations = [
        migrations.AddField(
            model_name='openfdacompound',
            name='estimated_usage',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
