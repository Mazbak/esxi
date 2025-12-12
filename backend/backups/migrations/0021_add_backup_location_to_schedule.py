# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0020_make_source_server_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupschedule',
            name='backup_location',
            field=models.CharField(
                max_length=512,
                blank=True,
                default='',
                help_text="Répertoire de sauvegarde (ex: /mnt/backups, /var/backups/vms)"
            ),
        ),
    ]
