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
            self.backup_job.progress_percentage = 1
            self.backup_job.downloaded_bytes = 0
            self.backup_job.total_bytes = 0
            self.backup_job.download_speed_mbps = 0
            self.backup_job.save()

            # 1. Créer snapshot
            logger.info(f"[VM-BACKUP] Création snapshot...")
            self.create_snapshot()
            self.backup_job.progress_percentage = 10
            self.backup_job.save()

            # 2. Copier les VMDKs
            logger.info(f"[VM-BACKUP] Copie des VMDKs...")
            vmdk_files = self.copy_vmdks()
            self.backup_job.vmdk_files = vmdk_files
            self.backup_job.progress_percentage = 90
            self.backup_job.save()

            # 3. Sauvegarder la configuration
            logger.info(f"[VM-BACKUP] Sauvegarde configuration...")
            self.save_vm_configuration()
            self.backup_job.progress_percentage = 95
            self.backup_job.save()

            # 4. Supprimer le snapshot
            logger.info(f"[VM-BACKUP] Suppression snapshot...")
            self.remove_snapshot()
            self.backup_job.progress_percentage = 98
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

    def parse_vmdk_descriptor(self, descriptor_path):
        """
        Parse un fichier descriptor VMDK pour extraire les informations importantes

        Args:
            descriptor_path: Chemin vers le fichier descriptor VMDK

        Returns:
            dict: Informations extraites (parent, extent, etc.)
        """
        info = {
            'parent': None,
            'extent_file': None
        }

        try:
            with open(descriptor_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

                # Chercher le parent (snapshot chain)
                for line in content.split('\n'):
                    line = line.strip()

                    # Parent file hint (snapshots)
                    if line.startswith('parentFileNameHint'):
                        # Format: parentFileNameHint="SQL SERVER-000006.vmdk"
                        # Extraire le contenu entre guillemets
                        import re
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            parent = match.group(1)
                            info['parent'] = parent
                            logger.info(f"[VM-BACKUP] Parent VMDK trouvé: {parent}")

                    # Extent file (fichier de données)
                    elif line.startswith('RW') or line.startswith('RDONLY'):
                        # Format: RW 16777216 VMFSSPARSE "SQL SERVER-000007-delta.vmdk"
                        # Trouver le texte entre guillemets
                        import re
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            extent = match.group(1)
                            info['extent_file'] = extent
                            logger.info(f"[VM-BACKUP] Extent file trouvé: {extent}")

        except Exception as e:
            logger.warning(f"[VM-BACKUP] Erreur parsing descriptor: {e}")

        return info

    def download_vmdk_chain(self, vmdk_filename, datastore_name, dc_name, backup_path, downloaded_files_set):
        """
        Télécharge récursivement toute la chaîne VMDK (parent + deltas)

        Args:
            vmdk_filename: Nom du fichier VMDK (descriptor)
            datastore_name: Nom du datastore
            dc_name: Nom du datacenter
            backup_path: Chemin de destination
            downloaded_files_set: Set des fichiers déjà téléchargés (pour éviter doublons)

        Returns:
            int: Taille totale téléchargée en bytes
        """
        import re

        # Éviter les doublons
        if vmdk_filename in downloaded_files_set:
            logger.info(f"[VM-BACKUP] Fichier déjà téléchargé: {vmdk_filename}")
            return 0

        downloaded_files_set.add(vmdk_filename)
        total_size = 0

        # URL du descriptor
        vmdk_url = f"https://{self.esxi_host}/folder/{vmdk_filename}?dcPath={dc_name}&dsName={datastore_name}"
        dest_file = os.path.join(backup_path, os.path.basename(vmdk_filename))

        # Télécharger le descriptor
        logger.info(f"[VM-BACKUP] Téléchargement descriptor: {vmdk_filename}")
        self.download_vmdk_file(vmdk_url, dest_file)
        file_size = os.path.getsize(dest_file) if os.path.exists(dest_file) else 0
        total_size += file_size
        # Mettre à jour les bytes téléchargés
        self.backup_job.downloaded_bytes += file_size
        self.backup_job.save()

        # Parser le descriptor pour trouver le parent et l'extent
        descriptor_info = self.parse_vmdk_descriptor(dest_file)

        # Télécharger le fichier de données (flat ou delta)
        is_snapshot = re.search(r'-\d{6}\.vmdk$', vmdk_filename)

        if is_snapshot:
            # Snapshot: chercher le fichier -delta.vmdk
            data_filename = vmdk_filename.replace('.vmdk', '-delta.vmdk')
        else:
            # VMDK normal: chercher le fichier -flat.vmdk
            data_filename = vmdk_filename.replace('.vmdk', '-flat.vmdk')

        # Utiliser l'extent du descriptor si disponible
        if descriptor_info['extent_file']:
            # L'extent file peut contenir le chemin complet, extraire juste le nom
            extent_basename = os.path.basename(descriptor_info['extent_file'])
            # Reconstruire le chemin avec le même dossier que le descriptor
            vmdk_dir = os.path.dirname(vmdk_filename)
            if vmdk_dir:
                data_filename = f"{vmdk_dir}/{extent_basename}"
            else:
                data_filename = extent_basename

        if data_filename not in downloaded_files_set:
            downloaded_files_set.add(data_filename)
            data_url = f"https://{self.esxi_host}/folder/{data_filename}?dcPath={dc_name}&dsName={datastore_name}"
            data_dest_file = os.path.join(backup_path, os.path.basename(data_filename))

            logger.info(f"[VM-BACKUP] Téléchargement données: {data_filename}")
            try:
                self.download_vmdk_file(data_url, data_dest_file)
                data_size = os.path.getsize(data_dest_file) if os.path.exists(data_dest_file) else 0
                total_size += data_size
                # Mettre à jour les bytes téléchargés
                self.backup_job.downloaded_bytes += data_size
                self.backup_job.save()
                logger.info(f"[VM-BACKUP] Fichier données téléchargé: {data_dest_file}")
            except Exception as e:
                logger.error(f"[VM-BACKUP] Erreur téléchargement données: {e}")
                raise

        # Télécharger récursivement le parent
        if descriptor_info['parent']:
            parent_filename = descriptor_info['parent']
            # Le parent peut être relatif, construire le chemin complet
            vmdk_dir = os.path.dirname(vmdk_filename)
            if vmdk_dir and not parent_filename.startswith(vmdk_dir):
                parent_filename = f"{vmdk_dir}/{parent_filename}"

            logger.info(f"[VM-BACKUP] ↳ Téléchargement parent: {parent_filename}")
            parent_size = self.download_vmdk_chain(
                parent_filename,
                datastore_name,
                dc_name,
                backup_path,
                downloaded_files_set
            )
            total_size += parent_size

        return total_size

    def download_vmdk_file(self, vmdk_url, dest_path, chunk_size=8192*1024):
        """
        Télécharge un fichier VMDK depuis ESXi via HTTP avec progression en temps réel

        Args:
            vmdk_url: URL du fichier VMDK sur ESXi
            dest_path: Chemin de destination local
            chunk_size: Taille des chunks pour le téléchargement (8MB par défaut)

        Returns:
            bool: True si succès
        """
        import time

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
            file_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            last_logged_mb = 0
            start_time = time.time()
            last_speed_update = start_time

            # Télécharger par chunks
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Mettre à jour tous les 1 MB téléchargés
                        downloaded_mb = downloaded / (1024 * 1024)
                        if downloaded_mb >= last_logged_mb + 1 or downloaded >= file_size:
                            # Vérifier si le backup a été annulé
                            self.backup_job.refresh_from_db()
                            if self.backup_job.status == 'cancelled':
                                logger.info(f"[VM-BACKUP] Backup annulé pendant le téléchargement")
                                raise Exception("Backup annulé par l'utilisateur")

                            # Calculer la vitesse de téléchargement (tous les 2 secondes)
                            current_time = time.time()
                            if current_time - last_speed_update >= 2.0:
                                elapsed_time = current_time - start_time
                                if elapsed_time > 0:
                                    speed_mbps = (self.backup_job.downloaded_bytes / (1024 * 1024)) / elapsed_time
                                    self.backup_job.download_speed_mbps = round(speed_mbps, 2)
                                last_speed_update = current_time

                            # Mettre à jour les bytes téléchargés (cumulatif)
                            # Note: downloaded_bytes est mis à jour par download_vmdk_chain

                            # Calculer progression si total_bytes connu
                            if self.backup_job.total_bytes > 0:
                                download_percentage = (self.backup_job.downloaded_bytes / self.backup_job.total_bytes) * 100
                                # Progression: 10% (snapshot) + 80% (download) + 10% (finalization)
                                # Download représente 10-90% de la progression totale (80%)
                                global_progress = 10 + int((download_percentage / 100) * 80)
                                global_progress = min(global_progress, 90)

                                self.backup_job.progress_percentage = global_progress
                                self.backup_job.save()

                                total_mb = self.backup_job.total_bytes / (1024 * 1024)
                                global_downloaded_mb = self.backup_job.downloaded_bytes / (1024 * 1024)
                                logger.info(f"[VM-BACKUP] Téléchargé: {global_downloaded_mb:.1f} MB / {total_mb:.1f} MB ({download_percentage:.1f}%) - Progression: {global_progress}%")

                            last_logged_mb = int(downloaded_mb)

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

            # Estimer la taille totale à télécharger
            estimated_total_bytes = 0
            for device in self.vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualDisk):
                    # Utiliser la capacité du disque comme estimation
                    # Note: peut être plus que la taille réelle (thin provisioning)
                    estimated_total_bytes += device.capacityInKB * 1024

            if estimated_total_bytes > 0:
                self.backup_job.total_bytes = estimated_total_bytes
                self.backup_job.save()
                logger.info(f"[VM-BACKUP] Taille estimée: {estimated_total_bytes / (1024**3):.2f} GB")

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

                            # Télécharger toute la chaîne VMDK (récursif: snapshot + tous les parents)
                            # Cela permet d'avoir un backup complet et restaurable
                            logger.info(f"[VM-BACKUP] Téléchargement chaîne VMDK complète pour: {vmdk_filename}")
                            downloaded_files_set = set()

                            total_size_bytes = self.download_vmdk_chain(
                                vmdk_filename,
                                datastore_name,
                                dc.name,
                                backup_path,
                                downloaded_files_set
                            )

                            total_size_mb = total_size_bytes / (1024 * 1024)

                            # Enregistrer les métadonnées
                            vmdk_info = {
                                'filename': vmdk_filename,
                                'size_gb': device.capacityInKB / (1024 * 1024),
                                'dest_path': os.path.join(backup_path, os.path.basename(vmdk_filename)),
                                'datastore': datastore_name,
                                'size_mb': total_size_mb,
                                'chain_files': list(downloaded_files_set)  # Liste tous les fichiers de la chaîne
                            }
                            vmdk_files.append(vmdk_info)

                            logger.info(f"[VM-BACKUP] Chaîne VMDK complète téléchargée: {vmdk_filename}")
                            logger.info(f"[VM-BACKUP]   Fichiers dans la chaîne: {len(downloaded_files_set)}")
                            logger.info(f"[VM-BACKUP]   Taille totale: {total_size_mb:.2f} MB")

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
