from django.db import models

# Create your models here.
# esxi/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ESXiServer(models.Model):
    hostname = models.CharField(max_length=255)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    port = models.PositiveIntegerField(default=443)
    connection_status = models.CharField(max_length=50, default='disconnected')
    last_connection = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='servers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.hostname


class VirtualMachine(models.Model):
    server = models.ForeignKey(ESXiServer, on_delete=models.CASCADE, related_name='vms')
    vm_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    power_state = models.CharField(max_length=50)
    num_cpu = models.IntegerField()
    memory_mb = models.IntegerField()
    disk_gb = models.FloatField()
    guest_os = models.CharField(max_length=255)
    guest_os_full = models.CharField(max_length=255)
    tools_status = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.server.hostname})"


class DatastoreInfo(models.Model):
    server = models.ForeignKey(ESXiServer, on_delete=models.CASCADE, related_name='datastores')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    capacity_gb = models.FloatField()
    free_space_gb = models.FloatField()
    accessible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.server.hostname})"


class EmailSettings(models.Model):
    """
    Singleton model for email notification settings.
    Only one instance should exist.
    """
    # SMTP Configuration
    smtp_host = models.CharField(max_length=255, default='smtp.gmail.com', help_text='Serveur SMTP')
    smtp_port = models.PositiveIntegerField(default=587, help_text='Port SMTP (587 pour TLS, 465 pour SSL)')
    smtp_username = models.CharField(max_length=255, blank=True, help_text='Nom d\'utilisateur SMTP')
    smtp_password = models.CharField(max_length=255, blank=True, help_text='Mot de passe SMTP')
    smtp_use_tls = models.BooleanField(default=True, help_text='Utiliser TLS')
    smtp_use_ssl = models.BooleanField(default=False, help_text='Utiliser SSL')
    from_email = models.EmailField(max_length=255, blank=True, help_text='Adresse email d\'expédition')

    # Administrator Email
    admin_email = models.EmailField(max_length=255, blank=True, help_text='Email administrateur pour les notifications')

    # Notification Settings
    notify_backup_success = models.BooleanField(default=False, help_text='Notifier les sauvegardes réussies')
    notify_backup_failure = models.BooleanField(default=True, help_text='Notifier les échecs de sauvegarde')
    notify_surebackup_success = models.BooleanField(default=True, help_text='Notifier les vérifications SureBackup réussies')
    notify_surebackup_failure = models.BooleanField(default=True, help_text='Notifier les échecs de vérification SureBackup')
    notify_replication_failure = models.BooleanField(default=True, help_text='Notifier les échecs de réplication')

    # Email enabled
    email_notifications_enabled = models.BooleanField(default=False, help_text='Activer les notifications par email')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email Settings'
        verbose_name_plural = 'Email Settings'

    def __str__(self):
        return f"Email Settings (Admin: {self.admin_email or 'Non configuré'})"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)"""
        if not self.pk and EmailSettings.objects.exists():
            # If trying to create a new instance when one already exists, update the existing one
            existing = EmailSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
