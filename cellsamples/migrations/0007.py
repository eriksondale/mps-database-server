# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cellsamples', '0006'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cellsample',
            name='restricted',
        ),
        migrations.AlterField(
            model_name='cellsample',
            name='group',
            field=models.ForeignKey(help_text=b'Bind to a group', to='auth.Group'),
        ),
    ]
