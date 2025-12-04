from rest_framework import serializers
from esxi.models import ESXiServer, VirtualMachine, DatastoreInfo, EmailSettings
from backups.models import (
    BackupConfiguration, BackupJob, BackupSchedule,
    SnapshotSchedule, Snapshot, RemoteStorageConfig,
    OVFExportJob, VMBackupJob, StoragePath,
    VMReplication, FailoverEvent, BackupVerification, BackupVerificationSchedule
)

class ESXiServerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='hostname', read_only=True)
    host = serializers.CharField(source='hostname', read_only=True)

    class Meta:
        model = ESXiServer
        fields = '__all__'

class VirtualMachineSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source='server.hostname', read_only=True)
    server_host = serializers.CharField(source='server.hostname', read_only=True)

    class Meta:
        model = VirtualMachine
        fields = '__all__'

class DatastoreInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatastoreInfo
        fields = '__all__'

class BackupConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupConfiguration
        fields = '__all__'

class BackupJobSerializer(serializers.ModelSerializer):
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)
    base_backup_id = serializers.IntegerField(source='base_backup.id', read_only=True, allow_null=True)

    class Meta:
        model = BackupJob
        fields = ['id', 'virtual_machine', 'vm_name', 'job_type', 'backup_mode', 'backup_location', 'backup_full_path',
                  'status', 'progress_percentage', 'backup_size_mb', 'error_message', 'created_at', 'started_at',
                  'completed_at', 'duration_seconds', 'base_backup_id', 'change_id', 'is_cbt_enabled']


class BackupJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupJob
        fields = ['id', 'virtual_machine', 'job_type', 'backup_mode', 'backup_location', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

    def validate(self, data):
        """Valide que le mode de sauvegarde correspond au type"""
        job_type = data.get('job_type', 'full')
        backup_mode = data.get('backup_mode', 'ovf')

        # Validation: les modes supportés sont
        # - full + ovf (sauvegarde complète OVF)
        # - incremental + cbt (sauvegarde incrémentale CBT - non restaurable)
        # - incremental + ovf (sauvegarde incrémentale OVF - restaurable)

        # Si type full, le mode doit être OVF
        if job_type == 'full' and backup_mode == 'cbt':
            raise serializers.ValidationError({
                'backup_mode': 'Les sauvegardes complètes doivent utiliser le mode OVF'
            })

        return data

class BackupScheduleSerializer(serializers.ModelSerializer):
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)
    schedule_description = serializers.CharField(source='get_schedule_description', read_only=True)
    remote_storage_name = serializers.CharField(source='remote_storage.name', read_only=True, allow_null=True)

    class Meta:
        model = BackupSchedule
        fields = ['id', 'virtual_machine', 'vm_name', 'frequency', 'time_hour', 'time_minute',
                  'day_of_week', 'day_of_month', 'backup_mode', 'backup_strategy', 'remote_storage',
                  'remote_storage_name', 'is_active', 'last_run', 'next_run',
                  'schedule_description', 'created_at']
        read_only_fields = ['id', 'last_run', 'next_run', 'created_at']


class SnapshotScheduleSerializer(serializers.ModelSerializer):
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)
    schedule_description = serializers.CharField(source='get_schedule_description', read_only=True)

    class Meta:
        model = SnapshotSchedule
        fields = ['id', 'virtual_machine', 'vm_name', 'frequency', 'time_hour', 'time_minute',
                  'day_of_week', 'day_of_month', 'retention_count', 'include_memory',
                  'is_active', 'last_run', 'next_run', 'schedule_description', 'created_at']
        read_only_fields = ['id', 'last_run', 'next_run', 'created_at']


class SnapshotScheduleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SnapshotSchedule
        fields = ['virtual_machine', 'frequency', 'time_hour', 'time_minute', 'day_of_week',
                  'day_of_month', 'retention_count', 'include_memory', 'is_active']


class SnapshotSerializer(serializers.ModelSerializer):
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)

    class Meta:
        model = Snapshot
        fields = ['id', 'virtual_machine', 'vm_name', 'schedule', 'snapshot_name',
                  'snapshot_id', 'description', 'status', 'include_memory', 'size_mb', 'created_at']
        read_only_fields = ['id', 'snapshot_id', 'size_mb', 'created_at']


class DashboardStatsSerializer(serializers.Serializer):
    total_servers = serializers.IntegerField()
    total_vms = serializers.IntegerField()
    total_backups = serializers.IntegerField()
    successful_backups = serializers.IntegerField()
    failed_backups = serializers.IntegerField()
    running_backups = serializers.IntegerField()
    total_backup_size_gb = serializers.FloatField()
    active_schedules = serializers.IntegerField()


class RemoteStorageConfigSerializer(serializers.ModelSerializer):
    """Serializer pour lecture des configurations de stockage distant"""
    connection_string = serializers.CharField(source='get_connection_string', read_only=True)
    full_path = serializers.CharField(source='get_full_path', read_only=True)

    class Meta:
        model = RemoteStorageConfig
        fields = [
            'id', 'name', 'protocol', 'host', 'port', 'share_name', 'base_path',
            'username', 'domain', 'is_active', 'is_default',
            'last_test_at', 'last_test_success', 'last_test_message',
            'connection_string', 'full_path', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_test_at', 'last_test_success', 'last_test_message',
            'created_at', 'updated_at'
        ]


class RemoteStorageConfigCreateSerializer(serializers.ModelSerializer):
    """Serializer pour création/modification avec gestion du mot de passe"""
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
        help_text="Mot de passe pour authentification (sera chiffré)"
    )

    class Meta:
        model = RemoteStorageConfig
        fields = [
            'id', 'name', 'protocol', 'host', 'port', 'share_name', 'base_path',
            'username', 'password', 'domain', 'is_active', 'is_default'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        """Crée une configuration en chiffrant le mot de passe"""
        password = validated_data.pop('password', None)

        storage_config = RemoteStorageConfig.objects.create(**validated_data)

        if password:
            storage_config.set_password(password)
            storage_config.save()

        return storage_config

    def update(self, instance, validated_data):
        """Met à jour une configuration, chiffre le mot de passe si fourni"""
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class RemoteStorageTestSerializer(serializers.Serializer):
    """Serializer pour tester une configuration de stockage"""
    # Mêmes champs que création mais tout optionnel pour test avant sauvegarde
    name = serializers.CharField(required=False)
    protocol = serializers.ChoiceField(
        choices=['smb', 'nfs', 'local'],
        required=True
    )
    host = serializers.CharField(required=True)
    port = serializers.IntegerField(required=False, default=445)
    share_name = serializers.CharField(required=False, allow_blank=True)
    base_path = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, style={'input_type': 'password'})
    domain = serializers.CharField(required=False, allow_blank=True, default='WORKGROUP')


# ============================================================================
# RESTORATION SERIALIZERS
# ============================================================================

class RestoreVMSerializer(serializers.Serializer):
    """Serializer pour restaurer une VM complète"""
    backup_id = serializers.CharField(required=True, help_text="ID de la sauvegarde à restaurer")
    target_datastore = serializers.CharField(required=True, help_text="Datastore ESXi de destination")
    target_vm_name = serializers.CharField(required=False, allow_blank=True, help_text="Nom de la VM restaurée (optionnel)")
    restore_mode = serializers.ChoiceField(
        choices=['new', 'replace', 'test'],
        default='new',
        help_text="Mode de restauration: new (nouvelle VM), replace (remplacer existante), test (VM de test)"
    )
    power_on = serializers.BooleanField(default=False, help_text="Démarrer la VM après restauration")


class RestoreVMDKSerializer(serializers.Serializer):
    """Serializer pour restaurer un VMDK individuel"""
    backup_id = serializers.CharField(required=True, help_text="ID de la sauvegarde source")
    vmdk_filename = serializers.CharField(required=True, help_text="Nom du fichier VMDK à restaurer")
    target_datastore = serializers.CharField(required=True, help_text="Datastore de destination")
    target_name = serializers.CharField(required=False, allow_blank=True, help_text="Nom du VMDK restauré (optionnel)")
    attach_to_vm = serializers.CharField(required=False, allow_blank=True, help_text="Nom de la VM à laquelle attacher le VMDK (optionnel)")


class FileRecoverySerializer(serializers.Serializer):
    """Serializer pour récupérer des fichiers depuis un backup"""
    backup_id = serializers.CharField(required=True, help_text="ID de la sauvegarde")
    vmdk_filename = serializers.CharField(required=True, help_text="Nom du VMDK contenant les fichiers")
    file_paths = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text="Liste des chemins de fichiers à récupérer"
    )
    destination_folder = serializers.CharField(required=True, help_text="Dossier de destination local")


class ListFilesSerializer(serializers.Serializer):
    """Serializer pour lister les fichiers dans un backup"""
    backup_id = serializers.CharField(required=True, help_text="ID de la sauvegarde")
    vmdk_filename = serializers.CharField(required=True, help_text="Nom du VMDK")
    directory_path = serializers.CharField(default='/', help_text="Chemin du répertoire à lister")


class SearchFilesSerializer(serializers.Serializer):
    """Serializer pour rechercher des fichiers dans un backup"""
    backup_id = serializers.CharField(required=True, help_text="ID de la sauvegarde")
    vmdk_filename = serializers.CharField(required=True, help_text="Nom du VMDK")
    search_pattern = serializers.CharField(required=True, help_text="Pattern de recherche (ex: '*.conf', 'nginx*')")


class ValidateRestoreSerializer(serializers.Serializer):
    """Serializer pour valider une restauration"""
    backup_id = serializers.CharField(required=True, help_text="ID de la sauvegarde")
    vmdk_filename = serializers.CharField(required=False, allow_blank=True, help_text="Nom du VMDK (pour validation VMDK)")


# ============================================================================
# Notification Serializers (Phase 6)
# ============================================================================

class NotificationConfigSerializer(serializers.ModelSerializer):
    """Serializer pour les configurations de notification"""
    filter_vm_names = serializers.SerializerMethodField()
    filter_schedule_names = serializers.SerializerMethodField()

    class Meta:
        from backups.models import NotificationConfig
        model = NotificationConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def get_filter_vm_names(self, obj):
        """Retourne les noms des VMs filtrées"""
        return [vm.name for vm in obj.filter_vms.all()]

    def get_filter_schedule_names(self, obj):
        """Retourne les noms des schedules filtrés"""
        return [f"Schedule #{s.id}" for s in obj.filter_schedules.all()]


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des notifications"""
    config_name = serializers.CharField(source='config.name', read_only=True)
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True, allow_null=True)
    job_type = serializers.CharField(source='backup_job.job_type', read_only=True, allow_null=True)

    class Meta:
        from backups.models import NotificationLog
        model = NotificationLog
        fields = '__all__'
        read_only_fields = ('sent_at',)


class TestNotificationSerializer(serializers.Serializer):
    """Serializer pour tester une configuration de notification"""
    config_id = serializers.IntegerField(required=True, help_text="ID de la configuration à tester")
    test_message = serializers.CharField(
        default="Ceci est un test de notification depuis ESXi Backup Manager",
        help_text="Message de test personnalisé"
    )


# ============================================================
# NOUVEAUX SERIALIZERS: OVF Export et VM Backup
# ============================================================

class OVFExportJobSerializer(serializers.ModelSerializer):
    """Serializer pour les exports OVF/OVA"""
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)
    remote_storage_name = serializers.CharField(source='remote_storage.name', read_only=True, allow_null=True)

    class Meta:
        model = OVFExportJob
        fields = [
            'id', 'virtual_machine', 'vm_name', 'remote_storage', 'remote_storage_name',
            'export_format', 'export_location', 'export_full_path', 'export_size_mb',
            'downloaded_bytes', 'total_bytes', 'download_speed_mbps',
            'status', 'progress_percentage', 'error_message',
            'created_by', 'created_at', 'started_at', 'completed_at', 'duration_seconds'
        ]
        read_only_fields = ['id', 'status', 'progress_percentage', 'export_full_path',
                            'export_size_mb', 'downloaded_bytes', 'total_bytes', 'download_speed_mbps',
                            'created_at', 'started_at', 'completed_at', 'duration_seconds']


class OVFExportJobCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un export OVF/OVA"""
    class Meta:
        model = OVFExportJob
        fields = ['virtual_machine', 'remote_storage', 'export_location', 'export_format']

    def validate(self, data):
        """Valide les données d'export"""
        if not data.get('export_location'):
            raise serializers.ValidationError("Le chemin d'export est requis")

        # Valider export_format
        export_format = data.get('export_format', 'ova')
        if export_format not in ['ovf', 'ova']:
            raise serializers.ValidationError("Format d'export invalide. Utilisez 'ovf' ou 'ova'.")

        return data


class VMBackupJobSerializer(serializers.ModelSerializer):
    """Serializer pour les backups de VMs"""
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)
    remote_storage_name = serializers.CharField(source='remote_storage.name', read_only=True, allow_null=True)
    base_backup_id = serializers.IntegerField(source='base_backup.id', read_only=True, allow_null=True)

    class Meta:
        model = VMBackupJob
        fields = [
            'id', 'virtual_machine', 'vm_name', 'backup_type', 'remote_storage', 'remote_storage_name',
            'backup_location', 'backup_full_path', 'backup_size_mb',
            'snapshot_name', 'snapshot_id', 'base_backup', 'base_backup_id',
            'vm_config_file', 'vmdk_files', 'scheduled_by',
            'status', 'progress_percentage', 'error_message',
            'downloaded_bytes', 'total_bytes', 'download_speed_mbps',
            'created_by', 'created_at', 'started_at', 'completed_at', 'duration_seconds'
        ]
        read_only_fields = ['id', 'status', 'progress_percentage', 'backup_full_path',
                            'backup_size_mb', 'snapshot_name', 'snapshot_id', 'vm_config_file',
                            'vmdk_files', 'downloaded_bytes', 'total_bytes', 'download_speed_mbps',
                            'created_at', 'started_at', 'completed_at', 'duration_seconds']


class VMBackupJobCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un backup de VM"""
    class Meta:
        model = VMBackupJob
        fields = ['virtual_machine', 'backup_type', 'remote_storage', 'backup_location', 'base_backup']

    def validate(self, data):
        """Valide les données de backup"""
        backup_type = data.get('backup_type', 'full')
        base_backup = data.get('base_backup')

        # Si backup incrémental, vérifier qu'un base_backup est fourni
        if backup_type == 'incremental' and not base_backup:
            raise serializers.ValidationError(
                "Un backup de base est requis pour un backup incrémental"
            )

        # Si backup full, base_backup doit être None
        if backup_type == 'full' and base_backup:
            raise serializers.ValidationError(
                "Un backup full ne peut pas avoir de backup de base"
            )

        if not data.get('backup_location'):
            raise serializers.ValidationError("Le chemin de backup est requis")

        return data


# ==========================================================
# 🔹 STORAGE PATHS - Chemins de sauvegarde
# ==========================================================
class StoragePathSerializer(serializers.ModelSerializer):
    """Serializer pour les chemins de sauvegarde prédéfinis"""
    
    storage_type_display = serializers.CharField(source='get_storage_type_display', read_only=True)
    
    class Meta:
        model = StoragePath
        fields = [
            'id', 'name', 'path', 'storage_type', 'storage_type_display',
            'description', 'is_active', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_name(self, value):
        """Valide l'unicité du nom"""
        instance = self.instance
        if StoragePath.objects.exclude(pk=instance.pk if instance else None).filter(name=value).exists():
            raise serializers.ValidationError("Un chemin avec ce nom existe déjà")
        return value
    
    def validate_path(self, value):
        """Valide le format du chemin"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("Le chemin ne peut pas être vide")
        return value.strip()


# ==========================================================
# 🔹 VM REPLICATION - Réplication de VMs
# ==========================================================
class VMReplicationSerializer(serializers.ModelSerializer):
    """Serializer pour la réplication de VMs"""
    
    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True)
    source_server_name = serializers.CharField(source='source_server.name', read_only=True)
    destination_server_name = serializers.CharField(source='destination_server.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    failover_mode_display = serializers.CharField(source='get_failover_mode_display', read_only=True)
    
    class Meta:
        model = VMReplication
        fields = [
            'id', 'name', 'virtual_machine', 'vm_name',
            'source_server', 'source_server_name',
            'destination_server', 'destination_server_name',
            'destination_datastore', 'replication_interval_minutes',
            'status', 'status_display', 'failover_mode', 'failover_mode_display',
            'auto_failover_threshold_minutes', 'last_replication_at',
            'last_replication_duration_seconds', 'total_replicated_size_mb',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_replication_at', 
                            'last_replication_duration_seconds', 'total_replicated_size_mb']


class FailoverEventSerializer(serializers.ModelSerializer):
    """Serializer pour les événements de failover"""
    
    vm_name = serializers.CharField(source='replication.virtual_machine.name', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True)
    failover_type_display = serializers.CharField(source='get_failover_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = FailoverEvent
        fields = [
            'id', 'replication', 'vm_name', 'failover_type', 'failover_type_display',
            'status', 'status_display', 'triggered_by', 'triggered_by_username',
            'reason', 'source_vm_powered_off', 'destination_vm_powered_on',
            'error_message', 'started_at', 'completed_at'
        ]
        read_only_fields = ['started_at', 'completed_at']


# ==========================================================
# 🔹 SUREBACKUP - Vérification de sauvegardes
# ==========================================================
class BackupVerificationSerializer(serializers.ModelSerializer):
    """Serializer pour les vérifications de sauvegardes (SureBackup)"""
    
    backup_name = serializers.SerializerMethodField()
    test_type_display = serializers.CharField(source='get_test_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    server_name = serializers.CharField(source='esxi_server.name', read_only=True)
    
    class Meta:
        model = BackupVerification
        fields = [
            'id', 'ovf_export', 'vm_backup', 'backup_name',
            'esxi_server', 'server_name', 'test_type', 'test_type_display',
            'status', 'status_display', 'vm_restored', 'vm_booted',
            'boot_time_seconds', 'ping_successful', 'services_checked',
            'test_network', 'test_datastore', 'vm_cleanup_done',
            'detailed_log', 'error_message', 'total_duration_seconds',
            'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['created_at', 'started_at', 'completed_at', 
                            'vm_restored', 'vm_booted', 'ping_successful', 'vm_cleanup_done']
    
    def get_backup_name(self, obj):
        """Nom du backup vérifié"""
        if obj.ovf_export:
            return obj.ovf_export.vm_name
        elif obj.vm_backup:
            return obj.vm_backup.virtual_machine.name
        return "Unknown"


class BackupVerificationScheduleSerializer(serializers.ModelSerializer):
    """Serializer pour les planifications de vérifications"""

    vm_name = serializers.CharField(source='virtual_machine.name', read_only=True, allow_null=True)
    server_name = serializers.CharField(source='esxi_server.name', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    test_type_display = serializers.CharField(source='get_test_type_display', read_only=True)

    class Meta:
        model = BackupVerificationSchedule
        fields = [
            'id', 'name', 'virtual_machine', 'vm_name',
            'frequency', 'frequency_display', 'test_type', 'test_type_display',
            'esxi_server', 'server_name', 'is_active',
            'last_run_at', 'next_run_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_run_at', 'next_run_at']


class EmailSettingsSerializer(serializers.ModelSerializer):
    """Serializer pour les paramètres d'email"""

    class Meta:
        model = EmailSettings
        fields = [
            'id', 'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_use_tls', 'smtp_use_ssl', 'from_email', 'admin_email',
            'notify_backup_success', 'notify_backup_failure',
            'notify_surebackup_success', 'notify_surebackup_failure',
            'notify_replication_failure', 'email_notifications_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'smtp_password': {'write_only': True}  # Don't expose password in responses
        }
