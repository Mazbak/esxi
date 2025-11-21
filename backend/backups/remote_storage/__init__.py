"""
Module de gestion du stockage distant pour backups ESXi
Support SMB/CIFS et NFS
"""

from .storage_manager import RemoteStorageManager

__all__ = ['RemoteStorageManager']
