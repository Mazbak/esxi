# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0008_add_cbt_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupjob',
            name='backup_full_path',
            field=models.CharField(blank=True, help_text='Chemin complet du dossier de sauvegarde créé', max_length=512),
        ),
        migrations.AlterField(
            model_name='backupjob',
            name='backup_location',
            field=models.CharField(blank=True, help_text='Chemin de base de la sauvegarde', max_length=255),
        ),
    ]
