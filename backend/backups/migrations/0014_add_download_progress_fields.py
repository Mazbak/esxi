# Generated manually on 2025-11-21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0013_add_ovfexport_vmbackup_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='ovfexportjob',
            name='downloaded_bytes',
            field=models.BigIntegerField(default=0, help_text='Octets téléchargés en temps réel'),
        ),
        migrations.AddField(
            model_name='ovfexportjob',
            name='total_bytes',
            field=models.BigIntegerField(default=0, help_text='Taille totale à télécharger en octets'),
        ),
        migrations.AddField(
            model_name='ovfexportjob',
            name='download_speed_mbps',
            field=models.FloatField(default=0, help_text='Vitesse de téléchargement en MB/s'),
        ),
    ]
