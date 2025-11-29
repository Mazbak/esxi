from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from esxi.models import VirtualMachine
from datetime import datetime, timedelta
import calendar
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class RemoteStorageConfig(models.Model):
    """
    Configuration pour stockage distant (SMB/CIFS, NFS)
    Gestion sécurisée des credentials avec chiffrement Fernet
    """
    PROTOCOL_CHOICES = [
        ('smb', 'SMB/CIFS (Windows Share/Samba)'),
        ('nfs', 'NFS (Network File System)'),
        ('local', 'Local Path (Development only)')
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nom descriptif de la configuration (ex: 'NAS Principal', 'Backup Server')"
    )

    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_CHOICES,
        default='smb',
        help_text="Protocole de connexion au stockage distant"
    )

    # Paramètres de connexion
    host = models.CharField(
        max_length=255,
        help_text="IP ou nom d'hôte (ex: 192.168.1.100, nas.local)"
    )

    port = models.IntegerField(
        default=445,
        help_text="Port de connexion (445 pour SMB, 2049 pour NFS)"
    )

    share_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom du partage SMB (ex: 'backups')"
    )

    base_path = models.CharField(
        max_length=512,
        default='',
        blank=True,
        help_text="Sous-dossier optionnel dans le partage (ex: 'esxi_backups')"
    )

    # Credentials chiffrés
    username = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom d'utilisateur pour authentification"
    )

    encrypted_password = models.BinaryField(
        blank=True,
        null=True,
        help_text="Mot de passe chiffré avec Fernet"
    )

    domain = models.CharField(
        max_length=255,
        blank=True,
        default='WORKGROUP',
        help_text="Domaine Windows (optionnel, défaut: WORKGROUP)"
    )

    # Status et tests
    is_active = models.BooleanField(
        default=True,
        help_text="Configuration active et utilisable"
    )

    is_default = models.BooleanField(
        default=False,
        help_text="Configuration par défaut pour les nouveaux backups"
    )

    last_test_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date du dernier test de connexion"
    )

    last_test_success = models.BooleanField(
        default=False,
        help_text="Résultat du dernier test"
    )

    last_test_message = models.TextField(
        blank=True,
        help_text="Message du dernier test (erreur ou succès)"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='storage_configs'
    )

    class Meta:
        verbose_name = "Remote Storage Configuration"
        verbose_name_plural = "Remote Storage Configurations"
        ordering = ['-is_default', '-is_active', 'name']

    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " [DEFAULT]" if self.is_default else ""
        return f"{status} {self.name} ({self.protocol.upper()}){default}"

    def set_password(self, raw_password):
        """
        Chiffre et stocke le mot de passe de manière sécurisée

        Args:
            raw_password (str): Mot de passe en clair
        """
        if not raw_password:
            self.encrypted_password = None
            return

        try:
            key = settings.ENCRYPTION_KEY
            fernet = Fernet(key)
            self.encrypted_password = fernet.encrypt(raw_password.encode('utf-8'))
            logger.info(f"[STORAGE] Mot de passe chiffré pour {self.name}")
        except Exception as e:
            logger.error(f"[STORAGE] Erreur chiffrement mot de passe: {e}")
            raise ValueError(f"Impossible de chiffrer le mot de passe: {e}")

    def get_password(self):
        """
        Déchiffre et retourne le mot de passe

        Returns:
            str: Mot de passe en clair
        """
        if not self.encrypted_password:
            return ''

        try:
            key = settings.ENCRYPTION_KEY
            fernet = Fernet(key)
            decrypted = fernet.decrypt(self.encrypted_password)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"[STORAGE] Erreur déchiffrement mot de passe: {e}")
            raise ValueError(f"Impossible de déchiffrer le mot de passe: {e}")

    def get_full_path(self):
        """
        Construit le chemin complet du stockage distant

        Returns:
            str: Chemin complet (ex: \\192.168.1.100\backups\esxi_backups)
        """
        if self.protocol == 'smb':
            # Format Windows UNC: \\host\share\path
            path = f"\\\\{self.host}\\{self.share_name}"
            if self.base_path:
                path = f"{path}\\{self.base_path.replace('/', '\\')}"
            return path
        elif self.protocol == 'nfs':
            # Format NFS: /mnt/nfs_mount/path
            # Note: NFS doit être monté localement au préalable
            path = f"/mnt/{self.host.replace('.', '_')}_{self.share_name}"
            if self.base_path:
                path = f"{path}/{self.base_path}"
            return path
        elif self.protocol == 'local':
            # Pour développement uniquement
            return self.base_path if self.base_path else '/tmp/backups'

        return ''

    def get_connection_string(self):
        """
        Retourne une chaîne de connexion lisible (sans mot de passe)

        Returns:
            str: Chaîne de connexion sanitisée
        """
        if self.protocol == 'smb':
            return f"smb://{self.username}@{self.host}/{self.share_name}"
        elif self.protocol == 'nfs':
            return f"nfs://{self.host}/{self.share_name}"
        return self.get_full_path()

    def save(self, *args, **kwargs):
        """
        Override save pour gérer le flag is_default unique
        """
        # Si cette config est marquée comme défaut, retirer le flag des autres
        if self.is_default:
            RemoteStorageConfig.objects.filter(
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)


class BackupConfiguration(models.Model):
    name = models.CharField(max_length=255)
    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='backup_configs')
    backup_location = models.CharField(max_length=255)
    retention_days = models.PositiveIntegerField(default=30)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='backup_configs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.virtual_machine.name})"

class BackupLog(models.Model):
    job = models.ForeignKey('BackupJob', on_delete=models.CASCADE)
    level = models.CharField(max_length=50, default='info')
    message = models.TextField(default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job} - {self.level}: {self.message[:50]} at {self.timestamp}"


class BackupJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]

    JOB_TYPE_CHOICES = [
        ('full', 'Full'),
        ('incremental', 'Incremental')
    ]

    BACKUP_MODE_CHOICES = [
        ('ovf', 'OVF Export (Standard format - Restorable)'),
        ('cbt', 'CBT Incremental (Changed Block Tracking)')
    ]

    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='backup_jobs')

    # Configuration stockage distant (nouvelle approche professionnelle)
    remote_storage = models.ForeignKey(
        RemoteStorageConfig,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='backup_jobs',
        help_text="Configuration du stockage distant à utiliser"
    )

    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES, default='full')
    backup_mode = models.CharField(max_length=50, choices=BACKUP_MODE_CHOICES, default='ovf')
    backup_size_mb = models.FloatField(default=0)

    # Chemins de sauvegarde (ancienne approche, conservée pour compatibilité)
    backup_location = models.CharField(max_length=255, blank=True, help_text="Chemin de base de la sauvegarde (legacy)")
    backup_full_path = models.CharField(max_length=512, blank=True, help_text="Chemin complet du dossier de sauvegarde créé")

    # Champs spécifiques aux sauvegardes incrémentales
    base_backup = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='incremental_backups',
                                     help_text="Référence à la sauvegarde de base (pour les sauvegardes incrémentales)")
    change_id = models.CharField(max_length=255, blank=True,
                                  help_text="CBT Change ID pour suivre les modifications")
    is_cbt_enabled = models.BooleanField(default=False,
                                          help_text="Indique si CBT était activé lors de cette sauvegarde")

    # Lien vers le schedule qui a généré ce job (si automatique)
    scheduled_by = models.ForeignKey(
        'BackupSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_jobs',
        help_text="Schedule qui a généré ce job (si automatique)"
    )

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True, help_text="Message d'erreur si le backup a échoué")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='backup_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    def calculate_duration(self):
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
        else:
            self.duration_seconds = 0
        self.save()

    def __str__(self):
        return f"BackupJob {self.id} - {self.virtual_machine.name}"


# ============================================================
# NOUVEAU: Systèmes séparés Export OVF et Backup
# ============================================================

class OVFExportJob(models.Model):
    """
    Export OVF/OVA - Pour migration/archivage de VMs
    Exporte la VM au format OVF (multi-fichiers) ou OVA (archive unique)
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]

    EXPORT_FORMAT_CHOICES = [
        ('ovf', 'OVF (Multi-fichiers)'),
        ('ova', 'OVA (Archive unique - Recommandé)')
    ]

    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='ovf_exports')

    # Format d'export (OVF ou OVA)
    export_format = models.CharField(
        max_length=10,
        choices=EXPORT_FORMAT_CHOICES,
        default='ova',
        help_text="OVA (recommandé): archive unique. OVF: multi-fichiers."
    )

    # Stockage distant
    remote_storage = models.ForeignKey(
        RemoteStorageConfig,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ovf_exports'
    )

    export_location = models.CharField(max_length=255, help_text="Chemin de base de l'export")
    export_full_path = models.CharField(max_length=512, blank=True, help_text="Chemin complet de l'export")
    export_size_mb = models.FloatField(default=0)

    # Suivi de progression en temps réel (poids téléchargé)
    downloaded_bytes = models.BigIntegerField(default=0, help_text="Octets téléchargés en temps réel")
    total_bytes = models.BigIntegerField(default=0, help_text="Taille totale à télécharger en octets")
    download_speed_mbps = models.FloatField(default=0, help_text="Vitesse de téléchargement en MB/s")

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ovf_exports')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"OVFExport {self.id} - {self.virtual_machine.name}"

    def delete(self, *args, **kwargs):
        """
        Override delete to also remove export files from disk
        """
        import shutil
        import logging
        logger = logging.getLogger(__name__)

        # Delete export directory if it exists
        if self.export_full_path:
            try:
                import os
                if os.path.exists(self.export_full_path):
                    logger.info(f"[OVF-EXPORT] Suppression du répertoire d'export: {self.export_full_path}")
                    shutil.rmtree(self.export_full_path)
                    logger.info(f"[OVF-EXPORT] Répertoire d'export supprimé avec succès")
                else:
                    logger.warning(f"[OVF-EXPORT] Répertoire d'export introuvable: {self.export_full_path}")
            except Exception as e:
                logger.error(f"[OVF-EXPORT] Erreur lors de la suppression du répertoire: {e}")
                # Continue with database deletion even if file deletion fails

        # Call parent delete to remove from database
        super().delete(*args, **kwargs)


class VMBackupJob(models.Model):
    """
    VM Backup - Véritable sauvegarde avec snapshot + copie VMDK
    Permet restauration VM/VMDK/Fichiers
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]

    BACKUP_TYPE_CHOICES = [
        ('full', 'Full Backup'),
        ('incremental', 'Incremental Backup')
    ]

    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='vm_backups')

    # Type de backup
    backup_type = models.CharField(max_length=50, choices=BACKUP_TYPE_CHOICES, default='full')

    # Stockage distant
    remote_storage = models.ForeignKey(
        RemoteStorageConfig,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='vm_backups'
    )

    # Chemins de sauvegarde
    backup_location = models.CharField(max_length=255, help_text="Chemin de base de la sauvegarde")
    backup_full_path = models.CharField(max_length=512, blank=True, help_text="Chemin complet de la sauvegarde")
    backup_size_mb = models.FloatField(default=0)

    # Snapshot info
    snapshot_name = models.CharField(max_length=255, blank=True, help_text="Nom du snapshot créé")
    snapshot_id = models.CharField(max_length=255, blank=True, help_text="ID du snapshot VMware")

    # Pour backups incrémentaux
    base_backup = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incremental_backups',
        help_text="Référence à la sauvegarde de base"
    )

    # Métadonnées pour restauration
    vm_config_file = models.CharField(max_length=512, blank=True, help_text="Fichier .vmx de configuration")
    vmdk_files = models.JSONField(default=list, help_text="Liste des fichiers VMDK sauvegardés")

    # Lien vers schedule
    scheduled_by = models.ForeignKey(
        'BackupSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vm_backup_jobs'
    )

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)

    # Suivi de progression en temps réel (poids téléchargé)
    downloaded_bytes = models.BigIntegerField(default=0, help_text="Octets téléchargés en temps réel")
    total_bytes = models.BigIntegerField(default=0, help_text="Taille totale à télécharger en octets")
    download_speed_mbps = models.FloatField(default=0, help_text="Vitesse de téléchargement en MB/s")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vm_backups')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    def calculate_duration(self):
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
        else:
            self.duration_seconds = 0
        self.save()

    def __str__(self):
        return f"VMBackup {self.id} - {self.virtual_machine.name} ({self.backup_type})"

    def delete(self, *args, **kwargs):
        """
        Override delete to also remove backup files from disk
        """
        import shutil
        import logging
        logger = logging.getLogger(__name__)

        # Delete backup directory if it exists
        if self.backup_full_path:
            try:
                import os
                if os.path.exists(self.backup_full_path):
                    logger.info(f"[VM-BACKUP] Suppression du répertoire de backup: {self.backup_full_path}")
                    shutil.rmtree(self.backup_full_path)
                    logger.info(f"[VM-BACKUP] Répertoire de backup supprimé avec succès")
                else:
                    logger.warning(f"[VM-BACKUP] Répertoire de backup introuvable: {self.backup_full_path}")
            except Exception as e:
                logger.error(f"[VM-BACKUP] Erreur lors de la suppression du répertoire: {e}")
                # Continue with database deletion even if file deletion fails

        # Call parent delete to remove from database
        super().delete(*args, **kwargs)


class BackupSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]

    DAY_OF_WEEK_CHOICES = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche')
    ]

    STRATEGY_CHOICES = [
        ('full_only', 'Full Backups Only'),
        ('incremental_only', 'Incremental Only'),
        ('full_weekly', 'Weekly Full + Daily Incremental'),
        ('smart', 'Smart (Auto-decide)')
    ]

    BACKUP_MODE_CHOICES = [
        ('ovf', 'OVF Export (Optimisé thin-provisioning - Recommandé)'),
        ('vmdk', 'VMDK Direct (Copie disque complet)'),
    ]

    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='backup_schedules')
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='daily')

    # Mode de backup (OVF recommandé pour thin provisioning)
    backup_mode = models.CharField(
        max_length=50,
        choices=BACKUP_MODE_CHOICES,
        default='ovf',
        help_text="OVF Export (recommandé): télécharge uniquement données réelles (~34.6%). VMDK: télécharge disque complet."
    )

    # Personnalisation de la planification
    time_hour = models.IntegerField(default=2, help_text="Heure d'exécution (0-23)")
    time_minute = models.IntegerField(default=0, help_text="Minute d'exécution (0-59)")
    day_of_week = models.IntegerField(
        null=True,
        blank=True,
        choices=DAY_OF_WEEK_CHOICES,
        help_text="Jour de la semaine (pour frequency='weekly')"
    )
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        help_text="Jour du mois (1-31, pour frequency='monthly')"
    )

    # Configuration de backup intelligent (Phase 5)
    backup_strategy = models.CharField(
        max_length=50,
        choices=STRATEGY_CHOICES,
        default='full_weekly',
        help_text="Stratégie de backup: Full uniquement, Incremental uniquement, ou Full hebdomadaire + Incrémental quotidien"
    )
    full_backup_interval_days = models.IntegerField(
        default=7,
        help_text="Intervalle en jours pour les Full backups (pour stratégie full_weekly)"
    )
    backup_configuration = models.ForeignKey(
        BackupConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedules',
        help_text="Configuration de backup à utiliser"
    )
    remote_storage = models.ForeignKey(
        RemoteStorageConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedules',
        help_text="Stockage distant pour les backups"
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Si False, le schedule ne sera pas exécuté"
    )
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure de la dernière exécution"
    )
    interval_hours = models.IntegerField(
        null=True,
        blank=True,
        help_text="Intervalle personnalisé en heures (optionnel, remplace frequency)"
    )

    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='backup_schedules')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Schedule {self.id} - {self.virtual_machine.name} ({self.get_schedule_description()})"

    def get_schedule_description(self):
        """Retourne une description lisible de la planification"""
        time_str = f"{self.time_hour:02d}:{self.time_minute:02d}"

        if self.frequency == 'daily':
            return f"Tous les jours à {time_str}"
        elif self.frequency == 'weekly':
            day_name = dict(self.DAY_OF_WEEK_CHOICES).get(self.day_of_week, 'Lundi')
            return f"Chaque {day_name} à {time_str}"
        elif self.frequency == 'monthly':
            day = self.day_of_month or 1
            return f"Le {day} de chaque mois à {time_str}"
        return f"{self.frequency} à {time_str}"

    def calculate_next_run(self, from_time=None):
        """Calcule la prochaine exécution planifiée"""
        if from_time is None:
            from_time = timezone.now()

        # Créer la prochaine date d'exécution
        next_run = from_time.replace(hour=self.time_hour, minute=self.time_minute, second=0, microsecond=0)

        if self.frequency == 'daily':
            # Si l'heure est déjà passée aujourd'hui, passer à demain
            if next_run <= from_time:
                next_run += timedelta(days=1)

        elif self.frequency == 'weekly':
            # Trouver le prochain jour de la semaine
            target_weekday = self.day_of_week if self.day_of_week is not None else 0
            current_weekday = next_run.weekday()

            days_ahead = target_weekday - current_weekday
            if days_ahead < 0 or (days_ahead == 0 and next_run <= from_time):
                days_ahead += 7

            next_run += timedelta(days=days_ahead)

        elif self.frequency == 'monthly':
            # Trouver le prochain jour du mois
            target_day = self.day_of_month if self.day_of_month is not None else 1

            # Essayer le mois actuel
            try:
                next_run = next_run.replace(day=target_day)
            except ValueError:
                # Le jour n'existe pas ce mois-ci (ex: 31 février)
                # Passer au mois suivant
                next_run = next_run.replace(day=1)
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)

                # Essayer à nouveau avec le jour cible
                try:
                    next_run = next_run.replace(day=target_day)
                except ValueError:
                    # Utiliser le dernier jour du mois
                    last_day = calendar.monthrange(next_run.year, next_run.month)[1]
                    next_run = next_run.replace(day=last_day)

            # Si la date est déjà passée, passer au mois suivant
            if next_run <= from_time:
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)

                # Gérer le cas où le jour n'existe pas dans le nouveau mois
                try:
                    next_run = next_run.replace(day=target_day)
                except ValueError:
                    last_day = calendar.monthrange(next_run.year, next_run.month)[1]
                    next_run = next_run.replace(day=last_day)

        return next_run

    def save(self, *args, **kwargs):
        """Override save pour calculer automatiquement next_run"""
        if self.is_active and not self.next_run:
            self.next_run = self.calculate_next_run()
        super().save(*args, **kwargs)


class SnapshotSchedule(models.Model):
    """Planification automatique de snapshots pour les VMs"""
    FREQUENCY_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ]

    DAY_OF_WEEK_CHOICES = [
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche')
    ]

    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='snapshot_schedules')
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='daily')
    retention_count = models.PositiveIntegerField(default=7, help_text="Nombre de snapshots à conserver")
    include_memory = models.BooleanField(default=False, help_text="Inclure la mémoire RAM dans le snapshot")

    # Personnalisation de la planification
    time_hour = models.IntegerField(default=2, help_text="Heure d'exécution (0-23)")
    time_minute = models.IntegerField(default=0, help_text="Minute d'exécution (0-59)")
    day_of_week = models.IntegerField(
        null=True,
        blank=True,
        choices=DAY_OF_WEEK_CHOICES,
        help_text="Jour de la semaine (pour frequency='weekly')"
    )
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        help_text="Jour du mois (1-31, pour frequency='monthly')"
    )

    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='snapshot_schedules')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Snapshot Schedule - {self.virtual_machine.name} ({self.get_schedule_description()})"

    def get_schedule_description(self):
        """Retourne une description lisible de la planification"""
        time_str = f"{self.time_hour:02d}:{self.time_minute:02d}"

        if self.frequency == 'hourly':
            return f"Toutes les heures à la minute {self.time_minute}"
        elif self.frequency == 'daily':
            return f"Tous les jours à {time_str}"
        elif self.frequency == 'weekly':
            day_name = dict(self.DAY_OF_WEEK_CHOICES).get(self.day_of_week, 'Lundi')
            return f"Chaque {day_name} à {time_str}"
        elif self.frequency == 'monthly':
            day = self.day_of_month or 1
            return f"Le {day} de chaque mois à {time_str}"
        return f"{self.frequency} à {time_str}"

    def calculate_next_run(self, from_time=None):
        """Calcule la prochaine exécution planifiée"""
        if from_time is None:
            from_time = timezone.now()

        # Créer la prochaine date d'exécution
        next_run = from_time.replace(minute=self.time_minute, second=0, microsecond=0)

        if self.frequency == 'hourly':
            # Si la minute est déjà passée cette heure, passer à l'heure suivante
            if next_run <= from_time:
                next_run += timedelta(hours=1)

        else:
            # Pour daily, weekly, monthly - utiliser l'heure spécifiée
            next_run = from_time.replace(hour=self.time_hour, minute=self.time_minute, second=0, microsecond=0)

            if self.frequency == 'daily':
                # Si l'heure est déjà passée aujourd'hui, passer à demain
                if next_run <= from_time:
                    next_run += timedelta(days=1)

            elif self.frequency == 'weekly':
                # Trouver le prochain jour de la semaine
                target_weekday = self.day_of_week if self.day_of_week is not None else 0
                current_weekday = next_run.weekday()

                days_ahead = target_weekday - current_weekday
                if days_ahead < 0 or (days_ahead == 0 and next_run <= from_time):
                    days_ahead += 7

                next_run += timedelta(days=days_ahead)

            elif self.frequency == 'monthly':
                # Trouver le prochain jour du mois
                target_day = self.day_of_month if self.day_of_month is not None else 1

                # Essayer le mois actuel
                try:
                    next_run = next_run.replace(day=target_day)
                except ValueError:
                    # Le jour n'existe pas ce mois-ci (ex: 31 février)
                    # Passer au mois suivant
                    next_run = next_run.replace(day=1)
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)

                    # Essayer à nouveau avec le jour cible
                    try:
                        next_run = next_run.replace(day=target_day)
                    except ValueError:
                        # Utiliser le dernier jour du mois
                        last_day = calendar.monthrange(next_run.year, next_run.month)[1]
                        next_run = next_run.replace(day=last_day)

                # Si la date est déjà passée, passer au mois suivant
                if next_run <= from_time:
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)

                    # Gérer le cas où le jour n'existe pas dans le nouveau mois
                    try:
                        next_run = next_run.replace(day=target_day)
                    except ValueError:
                        last_day = calendar.monthrange(next_run.year, next_run.month)[1]
                        next_run = next_run.replace(day=last_day)

        return next_run

    def save(self, *args, **kwargs):
        """Override save pour calculer automatiquement next_run"""
        if self.is_active and not self.next_run:
            self.next_run = self.calculate_next_run()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Snapshot Schedule"
        verbose_name_plural = "Snapshot Schedules"


class Snapshot(models.Model):
    """Historique des snapshots créés"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('creating', 'Creating'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    virtual_machine = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name='snapshots')
    schedule = models.ForeignKey(SnapshotSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='snapshots')
    snapshot_name = models.CharField(max_length=255)
    snapshot_id = models.CharField(max_length=255, blank=True)  # ID du snapshot dans ESXi
    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    include_memory = models.BooleanField(default=False)
    size_mb = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='snapshots')

    def __str__(self):
        return f"Snapshot - {self.snapshot_name} ({self.created_at})"

    class Meta:
        verbose_name = "Snapshot"
        verbose_name_plural = "Snapshots"
        ordering = ['-created_at']


class NotificationConfig(models.Model):
    """
    Configuration des notifications Email et Webhook
    Permet de configurer des alertes pour les événements de backup
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email'),
        ('webhook', 'Webhook'),
        ('slack', 'Slack'),
        ('teams', 'Microsoft Teams')
    ]

    EVENT_TYPE_CHOICES = [
        ('backup_success', 'Backup Success'),
        ('backup_failure', 'Backup Failure'),
        ('backup_warning', 'Backup Warning'),
        ('schedule_missed', 'Schedule Missed'),
        ('storage_full', 'Storage Full'),
        ('chain_broken', 'Backup Chain Broken'),
        ('retention_applied', 'Retention Policy Applied')
    ]

    name = models.CharField(
        max_length=255,
        help_text="Nom descriptif de la notification (ex: 'Email Admin - Erreurs')"
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default='email',
        help_text="Type de notification"
    )

    event_types = models.JSONField(
        default=list,
        help_text="Liste des événements à surveiller (ex: ['backup_failure', 'storage_full'])"
    )

    is_enabled = models.BooleanField(
        default=True,
        help_text="Activer/désactiver cette notification"
    )

    # Configuration Email
    email_recipients = models.TextField(
        blank=True,
        help_text="Adresses email séparées par des virgules"
    )

    email_subject_template = models.CharField(
        max_length=255,
        blank=True,
        default="[ESXi Backup] {event_type} - {vm_name}",
        help_text="Template du sujet de l'email (variables: {event_type}, {vm_name}, {status})"
    )

    # Configuration Webhook
    webhook_url = models.URLField(
        blank=True,
        help_text="URL du webhook (ex: https://hooks.slack.com/services/...)"
    )

    webhook_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Headers HTTP personnalisés pour le webhook (JSON)"
    )

    webhook_method = models.CharField(
        max_length=10,
        default='POST',
        choices=[('POST', 'POST'), ('GET', 'GET'), ('PUT', 'PUT')],
        help_text="Méthode HTTP"
    )

    # Filtres
    filter_vms = models.ManyToManyField(
        VirtualMachine,
        blank=True,
        related_name='notification_configs',
        help_text="Filtrer par VMs spécifiques (vide = toutes les VMs)"
    )

    filter_schedules = models.ManyToManyField(
        'BackupSchedule',
        blank=True,
        related_name='notification_configs',
        help_text="Filtrer par schedules spécifiques"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_configs'
    )

    class Meta:
        verbose_name = "Notification Configuration"
        verbose_name_plural = "Notification Configurations"
        ordering = ['-created_at']

    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.name} ({self.notification_type})"


class NotificationLog(models.Model):
    """
    Historique des notifications envoyées
    Permet de tracer toutes les notifications et déboguer les problèmes
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped')
    ]

    config = models.ForeignKey(
        NotificationConfig,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Configuration utilisée pour envoyer la notification"
    )

    event_type = models.CharField(
        max_length=50,
        help_text="Type d'événement qui a déclenché la notification"
    )

    backup_job = models.ForeignKey(
        BackupJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Job de backup associé"
    )

    virtual_machine = models.ForeignKey(
        VirtualMachine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending'
    )

    subject = models.CharField(
        max_length=500,
        blank=True,
        help_text="Sujet de la notification (email)"
    )

    message = models.TextField(
        help_text="Contenu de la notification"
    )

    recipient = models.CharField(
        max_length=500,
        help_text="Destinataire (email ou URL webhook)"
    )

    response = models.TextField(
        blank=True,
        help_text="Réponse du serveur (pour webhooks) ou erreur"
    )

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.event_type} - {self.status} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
