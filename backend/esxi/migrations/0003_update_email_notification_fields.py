# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esxi', '0002_emailsettings'),
    ]

    operations = [
        # Remove old SureBackup fields
        migrations.RemoveField(
            model_name='emailsettings',
            name='notify_surebackup_success',
        ),
        migrations.RemoveField(
            model_name='emailsettings',
            name='notify_surebackup_failure',
        ),
        # Add new Restore notification fields
        migrations.AddField(
            model_name='emailsettings',
            name='notify_restore_success',
            field=models.BooleanField(default=False, help_text='Notifier les restaurations réussies'),
        ),
        migrations.AddField(
            model_name='emailsettings',
            name='notify_restore_failure',
            field=models.BooleanField(default=True, help_text='Notifier les échecs de restauration'),
        ),
        # Add new Replication success field
        migrations.AddField(
            model_name='emailsettings',
            name='notify_replication_success',
            field=models.BooleanField(default=False, help_text='Notifier les réplications réussies'),
        ),
    ]
