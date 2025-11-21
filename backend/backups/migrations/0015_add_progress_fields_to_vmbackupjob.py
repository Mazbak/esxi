# Generated manually on 2025-11-21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0014_add_download_progress_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='vmbackupjob',
            name='downloaded_bytes',
            field=models.BigIntegerField(default=0, help_text='Octets téléchargés en temps réel'),
        ),
        migrations.AddField(
            model_name='vmbackupjob',
            name='total_bytes',
            field=models.BigIntegerField(default=0, help_text='Taille totale à télécharger en octets'),
        ),
        migrations.AddField(
            model_name='vmbackupjob',
            name='download_speed_mbps',
            field=models.FloatField(default=0, help_text='Vitesse de téléchargement en MB/s'),
        ),
    ]
