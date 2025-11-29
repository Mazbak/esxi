# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0016_add_backup_mode_to_schedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='ovfexportjob',
            name='export_format',
            field=models.CharField(
                choices=[
                    ('ovf', 'OVF (Multi-fichiers)'),
                    ('ova', 'OVA (Archive unique - Recommandé)')
                ],
                default='ova',
                help_text='OVA (recommandé): archive unique. OVF: multi-fichiers.',
                max_length=10
            ),
        ),
    ]
