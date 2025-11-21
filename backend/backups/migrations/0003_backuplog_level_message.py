# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0002_backupjob_progress_percentage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='backuplog',
            name='status',
        ),
        migrations.AddField(
            model_name='backuplog',
            name='level',
            field=models.CharField(default='info', max_length=50),
        ),
        migrations.AddField(
            model_name='backuplog',
            name='message',
            field=models.TextField(default=''),
        ),
    ]
