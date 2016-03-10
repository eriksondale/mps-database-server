# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assays', '0015'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assaychipreadout',
            name='chip_setup',
            field=models.ForeignKey(default=15, to='assays.AssayChipSetup'),
            preserve_default=False,
        ),
    ]
