# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupjob',
            name='progress_percentage',
            field=models.IntegerField(default=0),
        ),
    ]
