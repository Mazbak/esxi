# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0003_backuplog_level_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupjob',
            name='backup_mode',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('metadata_only', 'Metadata Only (VMX, NVRAM only - Fast)'),
                    ('thin', 'Thin (Config + VMDK descriptors - Faster)'),
                    ('full', 'Full (All files including data - Slow)')
                ],
                default='thin'
            ),
        ),
    ]
