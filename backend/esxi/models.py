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
