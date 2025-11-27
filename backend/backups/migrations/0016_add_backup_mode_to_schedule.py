# Generated manually for adding backup_mode to BackupSchedule

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0015_add_progress_fields_to_vmbackupjob'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupschedule',
            name='backup_mode',
            field=models.CharField(
                choices=[
                    ('ovf', 'OVF Export (Optimisé thin-provisioning - Recommandé)'),
                    ('vmdk', 'VMDK Direct (Copie disque complet)')
                ],
                default='ovf',
                help_text="OVF Export (recommandé): télécharge uniquement données réelles (~34.6%). VMDK: télécharge disque complet.",
                max_length=50
            ),
        ),
    ]
