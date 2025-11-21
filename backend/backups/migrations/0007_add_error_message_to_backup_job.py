# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0006_schedule_customization'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupjob',
            name='error_message',
            field=models.TextField(blank=True, null=True, help_text="Message d'erreur si le backup a échoué"),
        ),
    ]
