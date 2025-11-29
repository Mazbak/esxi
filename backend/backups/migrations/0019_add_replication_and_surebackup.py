# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('esxi', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('backups', '0018_add_storagepath'),
    ]

    operations = [
        # VM Replication
        migrations.CreateModel(
            name='VMReplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nom descriptif de la réplication', max_length=200)),
                ('destination_datastore', models.CharField(help_text='Datastore de destination sur le serveur cible', max_length=200)),
                ('replication_interval_minutes', models.IntegerField(default=15, help_text='Intervalle de réplication en minutes (minimum 5)')),
                ('status', models.CharField(choices=[('active', 'Active'), ('paused', 'En pause'), ('error', 'Erreur'), ('syncing', 'Synchronisation en cours')], default='active', max_length=20)),
                ('failover_mode', models.CharField(choices=[('manual', 'Manuel uniquement'), ('automatic', 'Automatique'), ('test', 'Mode test (pas de failover réel)')], default='manual', help_text='Mode de basculement en cas de panne', max_length=20)),
                ('auto_failover_threshold_minutes', models.IntegerField(default=5, help_text='Délai avant failover automatique (en minutes)')),
                ('last_replication_at', models.DateTimeField(blank=True, help_text='Dernière réplication réussie', null=True)),
                ('last_replication_duration_seconds', models.IntegerField(blank=True, help_text='Durée de la dernière réplication en secondes', null=True)),
                ('total_replicated_size_mb', models.FloatField(default=0, help_text='Taille totale répliquée en MB')),
                ('is_active', models.BooleanField(default=True, help_text='Réplication active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('destination_server', models.ForeignKey(help_text='Serveur ESXi de réplication', on_delete=django.db.models.deletion.CASCADE, related_name='replication_destinations', to='esxi.esxiserver')),
                ('source_server', models.ForeignKey(help_text='Serveur ESXi source', on_delete=django.db.models.deletion.CASCADE, related_name='replication_sources', to='esxi.esxiserver')),
                ('virtual_machine', models.ForeignKey(help_text='VM source à répliquer', on_delete=django.db.models.deletion.CASCADE, related_name='replications', to='esxi.virtualmachine')),
            ],
            options={
                'verbose_name': 'Réplication VM',
                'verbose_name_plural': 'Réplications VM',
                'ordering': ['-created_at'],
                'unique_together': {('virtual_machine', 'destination_server')},
            },
        ),

        # Failover Event
        migrations.CreateModel(
            name='FailoverEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('failover_type', models.CharField(choices=[('manual', 'Manuel'), ('automatic', 'Automatique'), ('test', 'Test')], max_length=20)),
                ('status', models.CharField(choices=[('initiated', 'Initié'), ('in_progress', 'En cours'), ('completed', 'Terminé'), ('failed', 'Échoué'), ('rolled_back', 'Annulé (rollback)')], default='initiated', max_length=20)),
                ('reason', models.TextField(blank=True, help_text='Raison du failover')),
                ('source_vm_powered_off', models.BooleanField(default=False, help_text='VM source arrêtée pendant le failover')),
                ('destination_vm_powered_on', models.BooleanField(default=False, help_text='VM répliquée démarrée')),
                ('error_message', models.TextField(blank=True, help_text="Message d'erreur si échec")),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('replication', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='failover_events', to='backups.vmreplication')),
                ('triggered_by', models.ForeignKey(blank=True, help_text='Utilisateur ayant déclenché le failover (si manuel)', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Événement Failover',
                'verbose_name_plural': 'Événements Failover',
                'ordering': ['-started_at'],
            },
        ),

        # Backup Verification (SureBackup)
        migrations.CreateModel(
            name='BackupVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_type', models.CharField(choices=[('boot', 'Test démarrage uniquement'), ('boot_ping', 'Démarrage + Ping'), ('boot_ping_services', 'Démarrage + Ping + Services'), ('full', 'Test complet personnalisé')], default='boot_ping', max_length=30)),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('running', 'En cours'), ('passed', 'Réussie'), ('failed', 'Échouée'), ('warning', 'Avertissement')], default='pending', max_length=20)),
                ('vm_restored', models.BooleanField(default=False, help_text='VM restaurée avec succès')),
                ('vm_booted', models.BooleanField(default=False, help_text='VM a démarré')),
                ('boot_time_seconds', models.IntegerField(blank=True, help_text='Temps de démarrage en secondes', null=True)),
                ('ping_successful', models.BooleanField(default=False, help_text='Ping réseau réussi')),
                ('services_checked', models.JSONField(blank=True, default=dict, help_text='Services vérifiés et leur état')),
                ('test_network', models.CharField(default='VM Network Isolated', help_text='Réseau isolé pour les tests', max_length=100)),
                ('test_datastore', models.CharField(help_text='Datastore utilisé pour le test', max_length=200)),
                ('vm_cleanup_done', models.BooleanField(default=False, help_text='VM de test supprimée après vérification')),
                ('detailed_log', models.TextField(blank=True, help_text='Log détaillé de la vérification')),
                ('error_message', models.TextField(blank=True, help_text="Message d'erreur si échec")),
                ('total_duration_seconds', models.IntegerField(blank=True, help_text='Durée totale de la vérification', null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('esxi_server', models.ForeignKey(help_text='Serveur ESXi pour effectuer le test', on_delete=django.db.models.deletion.CASCADE, to='esxi.esxiserver')),
                ('ovf_export', models.ForeignKey(blank=True, help_text='Export OVF à vérifier', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verifications', to='backups.ovfexportjob')),
                ('vm_backup', models.ForeignKey(blank=True, help_text='Backup VMDK à vérifier', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verifications', to='backups.vmbackupjob')),
            ],
            options={
                'verbose_name': 'Vérification Backup (SureBackup)',
                'verbose_name_plural': 'Vérifications Backup (SureBackup)',
                'ordering': ['-created_at'],
            },
        ),

        # Backup Verification Schedule
        migrations.CreateModel(
            name='BackupVerificationSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nom de la planification', max_length=200)),
                ('frequency', models.CharField(choices=[('daily', 'Quotidienne'), ('weekly', 'Hebdomadaire'), ('monthly', 'Mensuelle'), ('after_backup', 'Après chaque sauvegarde')], default='weekly', max_length=20)),
                ('test_type', models.CharField(choices=[('boot', 'Test démarrage uniquement'), ('boot_ping', 'Démarrage + Ping'), ('boot_ping_services', 'Démarrage + Ping + Services'), ('full', 'Test complet personnalisé')], default='boot_ping', max_length=30)),
                ('is_active', models.BooleanField(default=True, help_text='Planification active')),
                ('last_run_at', models.DateTimeField(blank=True, null=True)),
                ('next_run_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('esxi_server', models.ForeignKey(help_text='Serveur pour effectuer les tests', on_delete=django.db.models.deletion.CASCADE, to='esxi.esxiserver')),
                ('virtual_machine', models.ForeignKey(blank=True, help_text='VM spécifique à vérifier (null = toutes les VMs)', null=True, on_delete=django.db.models.deletion.CASCADE, to='esxi.virtualmachine')),
            ],
            options={
                'verbose_name': 'Planification Vérification',
                'verbose_name_plural': 'Planifications Vérification',
                'ordering': ['name'],
            },
        ),
    ]
