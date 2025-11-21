# Generated migration for intelligent scheduling

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0010_add_remote_storage_config'),
    ]

    operations = [
        # Ajouter les nouveaux champs pour la planification intelligente
        migrations.AddField(
            model_name='backupschedule',
            name='backup_strategy',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('full_only', 'Full Backups Only'),
                    ('incremental_only', 'Incremental Only'),
                    ('full_weekly', 'Weekly Full + Daily Incremental'),
                    ('smart', 'Smart (Auto-decide)')
                ],
                default='full_weekly',
                help_text="Stratégie de backup: Full uniquement, Incremental uniquement, ou Full hebdomadaire + Incrémental quotidien"
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='full_backup_interval_days',
            field=models.IntegerField(
                default=7,
                help_text="Intervalle en jours pour les Full backups (pour stratégie full_weekly)"
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='backup_configuration',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='backups.backupconfiguration',
                related_name='schedules',
                help_text="Configuration de backup à utiliser"
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='remote_storage',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='backups.remotestorageconfig',
                related_name='schedules',
                help_text="Stockage distant pour les backups"
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='is_enabled',
            field=models.BooleanField(
                default=True,
                help_text="Si False, le schedule ne sera pas exécuté"
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='last_run_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Date et heure de la dernière exécution"
            ),
        ),
        migrations.AddField(
            model_name='backupschedule',
            name='interval_hours',
            field=models.IntegerField(
                null=True,
                blank=True,
                help_text="Intervalle personnalisé en heures (optionnel, remplace frequency)"
            ),
        ),
        migrations.AddField(
            model_name='backupjob',
            name='scheduled_by',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='backups.backupschedule',
                related_name='generated_jobs',
                help_text="Schedule qui a généré ce job (si automatique)"
            ),
        ),
    ]
