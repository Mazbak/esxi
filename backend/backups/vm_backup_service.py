"""
Service de backup réel pour VMs ESXi
Utilise snapshot + copie directe des VMDKs
Permet restauration VM/VMDK/Fichiers
"""
import os
import shutil
import logging
import json
import requests
import urllib3
from datetime import datetime
from django.utils import timezone
from pyVim.task import WaitForTask
from pyVmomi import vim

# Désactiver les avertissements SSL pour ESXi
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class VMBackupService:
    """
    Service de backup de VMs avec snapshot + copie VMDK
    """

    def __init__(self, vm_obj, backup_job):
        """
        Args:
            vm_obj: Objet pyVmomi VM
            backup_job: Instance de VMBackupJob model
        """
        self.vm = vm_obj
        self.backup_job = backup_job
        self.snapshot = None
        self.snapshot_name = f"backup_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Récupérer les credentials ESXi pour le téléchargement HTTP
        esxi_server = self.backup_job.virtual_machine.server
        self.esxi_host = esxi_server.hostname
        self.esxi_user = esxi_server.username
        self.esxi_pass = esxi_server.password

    def execute_backup(self):
        """
        Exécute le backup complet
        1. Créer snapshot
        2. Copier VMDKs
        3. Sauvegarder configuration
        4. Supprimer snapshot
        """
        try:
            logger.info(f"[VM-BACKUP] Début backup de {self.vm.name}")
            self.backup_job.status = 'running'
            self.backup_job.save()

            # 1. Créer snapshot
            logger.info(f"[VM-BACKUP] Création snapshot...")
            self.create_snapshot()
            self.backup_job.progress_percentage = 20
            self.backup_job.save()

            # 2. Copier les VMDKs
            logger.info(f"[VM-BACKUP] Copie des VMDKs...")
            vmdk_files = self.copy_vmdks()
            self.backup_job.vmdk_files = vmdk_files
            self.backup_job.progress_percentage = 70
            self.backup_job.save()

            # 3. Sauvegarder la configuration
            logger.info(f"[VM-BACKUP] Sauvegarde configuration...")
            self.save_vm_configuration()
            self.backup_job.progress_percentage = 90
            self.backup_job.save()

            # 4. Supprimer le snapshot
            logger.info(f"[VM-BACKUP] Suppression snapshot...")
            self.remove_snapshot()
            self.backup_job.progress_percentage = 100
            self.backup_job.save()

            # Finaliser
            self.backup_job.status = 'completed'
            self.backup_job.completed_at = timezone.now()
            self.backup_job.calculate_duration()

            # Calculer la taille
            self.calculate_backup_size()

            logger.info(f"[VM-BACKUP] Backup terminé avec succès")
            return True

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur backup: {e}", exc_info=True)
            self.backup_job.status = 'failed'
            self.backup_job.error_message = str(e)
            self.backup_job.save()

            # Nettoyer le snapshot en cas d'erreur
            if self.snapshot:
                try:
                    self.remove_snapshot()
                except:
                    pass

            raise

    def create_snapshot(self):
        """Crée un snapshot de la VM"""
        try:
            logger.info(f"[VM-BACKUP] Création snapshot '{self.snapshot_name}'...")

            task = self.vm.CreateSnapshot_Task(
                name=self.snapshot_name,
                description=f"Backup snapshot for job {self.backup_job.id}",
                memory=False,  # Pas de mémoire pour les backups
                quiesce=True   # Quiesce pour cohérence du filesystem
            )

            WaitForTask(task)

            # Récupérer le snapshot créé
            self.snapshot = self.vm.snapshot.currentSnapshot

            # Sauvegarder les infos du snapshot
            self.backup_job.snapshot_name = self.snapshot_name
            self.backup_job.snapshot_id = str(self.snapshot)
            self.backup_job.save()

            logger.info(f"[VM-BACKUP] Snapshot créé: {self.snapshot_name}")

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur création snapshot: {e}")
            raise Exception(f"Échec création snapshot: {str(e)}")

    def download_vmdk_file(self, vmdk_url, dest_path, chunk_size=8192*1024):
        """
        Télécharge un fichier VMDK depuis ESXi via HTTP

        Args:
            vmdk_url: URL du fichier VMDK sur ESXi
            dest_path: Chemin de destination local
            chunk_size: Taille des chunks pour le téléchargement (8MB par défaut)

        Returns:
            bool: True si succès
        """
        try:
            logger.info(f"[VM-BACKUP] Téléchargement: {vmdk_url}")

            # Créer une session avec authentification
            session = requests.Session()
            session.auth = (self.esxi_user, self.esxi_pass)
            session.verify = False  # ESXi utilise souvent des certificats auto-signés

            # Faire la requête avec streaming pour les gros fichiers
            response = session.get(vmdk_url, stream=True, timeout=(30, 600))  # (connect timeout, read timeout between chunks)
            response.raise_for_status()

            # Obtenir la taille totale si disponible
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            last_logged_progress = 0

            # Télécharger par chunks
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Update progress every 5%
                        if total_size > 0:
                            download_progress = (downloaded / total_size) * 100
                            if download_progress >= last_logged_progress + 5 or downloaded >= total_size:
                                # Calculate global progress: 20% (snapshot) + download progress (20-70%)
                                # Download represents 50% of total progress (from 20% to 70%)
                                global_progress = 20 + int((download_progress / 100) * 50)

                                # Update database with real-time progress
                                self.backup_job.progress_percentage = global_progress
                                self.backup_job.save()

                                logger.info(f"[VM-BACKUP] Download: {download_progress:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB) - Global: {global_progress}%")
                                last_logged_progress = int(download_progress / 5) * 5

            logger.info(f"[VM-BACKUP] VMDK téléchargé: {dest_path} ({downloaded / (1024*1024):.1f} MB)")
            return True

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur téléchargement VMDK: {e}")
            # Nettoyer le fichier partiel en cas d'erreur
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise Exception(f"Échec téléchargement VMDK: {str(e)}")

    def copy_vmdks(self):
        """
        Copie les fichiers VMDK

        Returns:
            list: Liste des fichiers VMDKs copiés
        """
        vmdk_files = []

        try:
            # Créer le dossier de backup
            backup_path = self.backup_job.backup_full_path
            os.makedirs(backup_path, exist_ok=True)

            logger.info(f"[VM-BACKUP] Destination: {backup_path}")

            # Récupérer les disques de la VM
            for device in self.vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualDisk):
                    if hasattr(device.backing, 'fileName'):
                        vmdk_file = device.backing.fileName
                        logger.info(f"[VM-BACKUP] VMDK trouvé: {vmdk_file}")

                        # Extraire le nom du fichier VMDK
                        vmdk_filename = vmdk_file.split(']')[1].strip().lstrip('/')

                        # Chemin source (sur datastore ESXi)
                        datastore_name = vmdk_file.split(']')[0].strip('[')

                        # Récupérer le chemin datastore
                        datastore = None
                        for ds in self.vm.datastore:
                            if ds.name == datastore_name:
                                datastore = ds
                                break

                        if datastore:
                            # URL du fichier VMDK
                            dc = self.vm.runtime.host.parent
                            while not isinstance(dc, vim.Datacenter):
                                dc = dc.parent

                            # Construction de l'URL pour téléchargement via HTTP
                            # Format: https://esxi/folder/path?dcPath=datacenter&dsName=datastore
                            vmdk_url = f"https://{self.esxi_host}/folder/{vmdk_filename}?dcPath={dc.name}&dsName={datastore_name}"

                            # Chemin de destination local
                            dest_file = os.path.join(backup_path, os.path.basename(vmdk_filename))

                            # Télécharger le fichier VMDK via HTTP
                            self.download_vmdk_file(vmdk_url, dest_file)

                            # Enregistrer les métadonnées
                            vmdk_info = {
                                'filename': vmdk_filename,
                                'size_gb': device.capacityInKB / (1024 * 1024),
                                'dest_path': dest_file,
                                'datastore': datastore_name,
                                'size_mb': os.path.getsize(dest_file) / (1024 * 1024) if os.path.exists(dest_file) else 0
                            }
                            vmdk_files.append(vmdk_info)

                            logger.info(f"[VM-BACKUP] VMDK copié: {vmdk_filename} -> {dest_file}")

            return vmdk_files

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur copie VMDKs: {e}")
            raise Exception(f"Échec copie VMDKs: {str(e)}")

    def save_vm_configuration(self):
        """Sauvegarde la configuration de la VM (fichier .vmx simulé)"""
        try:
            backup_path = self.backup_job.backup_full_path
            config_file = os.path.join(backup_path, "vm_config.json")

            # Collecter la configuration
            config = {
                'name': self.vm.name,
                'num_cpus': self.vm.config.hardware.numCPU,
                'memory_mb': self.vm.config.hardware.memoryMB,
                'guest_os': self.vm.config.guestId,
                'version': self.vm.config.version,
                'uuid': self.vm.config.uuid,
                'instance_uuid': self.vm.config.instanceUuid,
                'network_adapters': [],
                'disks': []
            }

            # Réseaux
            for device in self.vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualEthernetCard):
                    config['network_adapters'].append({
                        'type': type(device).__name__,
                        'mac_address': device.macAddress if hasattr(device, 'macAddress') else None
                    })
                elif isinstance(device, vim.vm.device.VirtualDisk):
                    config['disks'].append({
                        'capacity_kb': device.capacityInKB,
                        'file': device.backing.fileName if hasattr(device.backing, 'fileName') else None
                    })

            # Sauvegarder en JSON
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            self.backup_job.vm_config_file = config_file
            self.backup_job.save()

            logger.info(f"[VM-BACKUP] Configuration sauvegardée: {config_file}")

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur sauvegarde config: {e}")
            raise Exception(f"Échec sauvegarde configuration: {str(e)}")

    def remove_snapshot(self):
        """Supprime le snapshot créé"""
        if not self.snapshot:
            return

        try:
            logger.info(f"[VM-BACKUP] Suppression snapshot '{self.snapshot_name}'...")

            task = self.snapshot.RemoveSnapshot_Task(removeChildren=False)
            WaitForTask(task)

            logger.info(f"[VM-BACKUP] Snapshot supprimé")
            self.snapshot = None

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur suppression snapshot: {e}")
            # On ne lève pas d'exception car le backup peut être réussi
            # Le snapshot sera nettoyé manuellement si nécessaire

    def calculate_backup_size(self):
        """Calcule la taille totale du backup"""
        try:
            backup_path = self.backup_job.backup_full_path
            total_size = 0

            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

            # Convertir en MB
            size_mb = total_size / (1024 * 1024)
            self.backup_job.backup_size_mb = size_mb
            self.backup_job.save()

            logger.info(f"[VM-BACKUP] Taille backup: {size_mb:.2f} MB")

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur calcul taille: {e}")


def execute_vm_backup(vm_obj, backup_job):
    """
    Fonction helper pour exécuter un backup

    Args:
        vm_obj: Objet pyVmomi VM
        backup_job: Instance de VMBackupJob

    Returns:
        bool: True si succès
    """
    service = VMBackupService(vm_obj, backup_job)
    return service.execute_backup()
