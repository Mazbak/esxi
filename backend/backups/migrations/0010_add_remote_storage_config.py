# Generated migration for Remote Storage Config

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('backups', '0009_add_backup_full_path'),
    ]

    operations = [
        # Créer le modèle RemoteStorageConfig
        migrations.CreateModel(
            name='RemoteStorageConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Nom descriptif de la configuration (ex: 'NAS Principal', 'Backup Server')", max_length=100, unique=True)),
                ('protocol', models.CharField(choices=[('smb', 'SMB/CIFS (Windows Share/Samba)'), ('nfs', 'NFS (Network File System)'), ('local', 'Local Path (Development only)')], default='smb', help_text='Protocole de connexion au stockage distant', max_length=10)),
                ('host', models.CharField(help_text='IP ou nom d\'hôte (ex: 192.168.1.100, nas.local)', max_length=255)),
                ('port', models.IntegerField(default=445, help_text='Port de connexion (445 pour SMB, 2049 pour NFS)')),
                ('share_name', models.CharField(blank=True, help_text="Nom du partage SMB (ex: 'backups')", max_length=255)),
                ('base_path', models.CharField(blank=True, default='', help_text="Sous-dossier optionnel dans le partage (ex: 'esxi_backups')", max_length=512)),
                ('username', models.CharField(blank=True, help_text='Nom d\'utilisateur pour authentification', max_length=255)),
                ('encrypted_password', models.BinaryField(blank=True, help_text='Mot de passe chiffré avec Fernet', null=True)),
                ('domain', models.CharField(blank=True, default='WORKGROUP', help_text='Domaine Windows (optionnel, défaut: WORKGROUP)', max_length=255)),
                ('is_active', models.BooleanField(default=True, help_text='Configuration active et utilisable')),
                ('is_default', models.BooleanField(default=False, help_text='Configuration par défaut pour les nouveaux backups')),
                ('last_test_at', models.DateTimeField(blank=True, help_text='Date du dernier test de connexion', null=True)),
                ('last_test_success', models.BooleanField(default=False, help_text='Résultat du dernier test')),
                ('last_test_message', models.TextField(blank=True, help_text='Message du dernier test (erreur ou succès)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='storage_configs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Remote Storage Configuration',
                'verbose_name_plural': 'Remote Storage Configurations',
                'ordering': ['-is_default', '-is_active', 'name'],
            },
        ),

        # Ajouter le champ remote_storage à BackupJob
        migrations.AddField(
            model_name='backupjob',
            name='remote_storage',
            field=models.ForeignKey(
                blank=True,
                help_text='Configuration du stockage distant à utiliser',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='backup_jobs',
                to='backups.remotestorageconfig'
            ),
        ),

        # Mettre à jour l'aide des champs backup_location
        migrations.AlterField(
            model_name='backupjob',
            name='backup_location',
            field=models.CharField(blank=True, help_text='Chemin de base de la sauvegarde (legacy)', max_length=255),
        ),
    ]
