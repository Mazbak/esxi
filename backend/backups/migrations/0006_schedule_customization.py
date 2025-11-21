# Generated manually for schedule customization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0005_snapshot_snapshotschedule_ovf_only'),
    ]

    operations = [
        # BackupSchedule customization fields
        migrations.AddField(
            model_name='backupschedule',
            name='time_hour',
            field=models.IntegerField(default=2, help_text="Heure d'exécution (0-23)"),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='time_minute',
            field=models.IntegerField(default=0, help_text="Minute d'exécution (0-59)"),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='day_of_week',
            field=models.IntegerField(
                blank=True,
                choices=[(0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')],
                help_text="Jour de la semaine (pour frequency='weekly')",
                null=True
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='day_of_month',
            field=models.IntegerField(
                blank=True,
                help_text="Jour du mois (1-31, pour frequency='monthly')",
                null=True
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='last_run',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='next_run',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # SnapshotSchedule customization fields
        migrations.AddField(
            model_name='snapshotschedule',
            name='time_hour',
            field=models.IntegerField(default=2, help_text="Heure d'exécution (0-23)"),
        ),
        migrations.AddField(
            model_name='snapshotschedule',
            name='time_minute',
            field=models.IntegerField(default=0, help_text="Minute d'exécution (0-59)"),
        ),
        migrations.AddField(
            model_name='snapshotschedule',
            name='day_of_week',
            field=models.IntegerField(
                blank=True,
                choices=[(0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')],
                help_text="Jour de la semaine (pour frequency='weekly')",
                null=True
            ),
        ),
        migrations.AddField(
            model_name='snapshotschedule',
            name='day_of_month',
            field=models.IntegerField(
                blank=True,
                help_text="Jour du mois (1-31, pour frequency='monthly')",
                null=True
            ),
        ),
    ]
