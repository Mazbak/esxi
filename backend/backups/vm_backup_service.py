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

        # Temps de démarrage de la phase de téléchargement (pour progression time-based)
        self.download_phase_start_time = None

    def check_cancelled(self):
        """Vérifie si le backup a été annulé par l'utilisateur"""
        self.backup_job.refresh_from_db(fields=['status'])
        if self.backup_job.status == 'cancelled':
            logger.info(f"[VM-BACKUP] Backup annulé par l'utilisateur")
            raise Exception("Backup annulé par l'utilisateur")

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

            # 1. Créer snapshot (1% -> 5%)
            self.check_cancelled()
            logger.info(f"[VM-BACKUP] Création snapshot...")
            self.create_snapshot()
            self.backup_job.progress_percentage = 5
            self.backup_job.save()

            # 2. Copier les VMDKs (5% -> 90%)
            self.check_cancelled()
            logger.info(f"[VM-BACKUP] Copie des VMDKs...")
            vmdk_files = self.copy_vmdks()
            self.backup_job.vmdk_files = vmdk_files
            self.backup_job.progress_percentage = 90
            self.backup_job.save()

            # 3. Télécharger fichiers config (.vmx, .nvram, .vmsd, .vmsn, .log) (90% -> 95%)
            self.check_cancelled()
            logger.info(f"[VM-BACKUP] Téléchargement fichiers configuration VM...")
            config_files = self.download_vm_files()
            self.backup_job.progress_percentage = 95
            self.backup_job.save()

            # 4. Sauvegarder métadonnées JSON (95% -> 98%)
            self.check_cancelled()
            logger.info(f"[VM-BACKUP] Sauvegarde métadonnées...")
            self.save_vm_configuration()
            self.backup_job.progress_percentage = 98
            self.backup_job.save()

            # 5. Supprimer le snapshot (98% -> 99%)
            self.check_cancelled()
            logger.info(f"[VM-BACKUP] Suppression snapshot...")
            self.remove_snapshot()
            self.backup_job.progress_percentage = 99
            self.backup_job.save()

            # Finaliser (99% -> 100%)
            self.backup_job.progress_percentage = 100
            self.backup_job.status = 'completed'
            self.backup_job.completed_at = timezone.now()
            self.backup_job.calculate_duration()

            # Calculer la taille
            self.calculate_backup_size()

            logger.info(f"[VM-BACKUP] Backup terminé avec succès")
            return True

        except Exception as e:
            # Vérifier si c'est une annulation utilisateur
            error_msg = str(e)
            is_cancelled = "annulé par l'utilisateur" in error_msg.lower() or "cancelled" in error_msg.lower()

            if is_cancelled:
                logger.info(f"[VM-BACKUP] Backup annulé: {error_msg}")
                # Garder le status 'cancelled' (déjà défini par l'API)
                self.backup_job.refresh_from_db(fields=['status'])
                if self.backup_job.status != 'cancelled':
                    self.backup_job.status = 'cancelled'
                self.backup_job.error_message = error_msg
                self.backup_job.completed_at = timezone.now()
                self.backup_job.calculate_duration()
                self.backup_job.save()

                # Supprimer le dossier de backup incomplet
                if self.backup_job.backup_full_path and os.path.exists(self.backup_job.backup_full_path):
                    try:
                        import shutil
                        shutil.rmtree(self.backup_job.backup_full_path)
                        logger.info(f"[VM-BACKUP] Dossier de backup incomplet supprimé: {self.backup_job.backup_full_path}")
                    except Exception as del_err:
                        logger.warning(f"[VM-BACKUP] Erreur suppression dossier backup: {del_err}")
            else:
                logger.error(f"[VM-BACKUP] Erreur backup: {e}", exc_info=True)
                self.backup_job.status = 'failed'
                self.backup_job.error_message = error_msg
                self.backup_job.completed_at = timezone.now()
                self.backup_job.calculate_duration()
                self.backup_job.save()

                # Note: On GARDE le dossier de backup en cas d'échec pour investigation/debug
                # L'utilisateur peut manuellement le supprimer s'il le souhaite
                logger.warning(f"[VM-BACKUP] Dossier de backup incomplet conservé pour investigation: {self.backup_job.backup_full_path}")

            # Nettoyer le snapshot en cas d'erreur ou d'annulation
            if self.snapshot:
                try:
                    logger.info(f"[VM-BACKUP] Nettoyage du snapshot...")
                    self.remove_snapshot()
                except Exception as cleanup_err:
                    logger.warning(f"[VM-BACKUP] Erreur nettoyage snapshot: {cleanup_err}")

            if not is_cancelled:
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

    def get_vmdk_chain_size(self, vmdk_filename, datastore, dc_name):
        """
        Calcule la taille réelle de toute la chaîne VMDK (tenant compte du thin provisioning)

        Args:
            vmdk_filename: Nom du fichier VMDK (ex: "SQL SERVER/SQL SERVER-000007.vmdk")
            datastore: Objet pyVmomi datastore
            dc_name: Nom du datacenter

        Returns:
            int: Taille totale en bytes de tous les fichiers de la chaîne
        """
        import re

        total_size = 0
        vmdk_dir = os.path.dirname(vmdk_filename)

        try:
            # Rechercher tous les fichiers dans le dossier de la VM
            search_spec = vim.host.DatastoreBrowser.SearchSpec()
            search_spec.matchPattern = ["*.vmdk", "*-delta.vmdk", "*-flat.vmdk"]
            search_spec.details = vim.host.DatastoreBrowser.FileInfo.Details()
            search_spec.details.fileSize = True
            search_spec.details.fileType = True
            search_spec.details.modification = False

            # Construire le chemin de recherche
            if vmdk_dir:
                search_path = f"[{datastore.name}] {vmdk_dir}"
            else:
                search_path = f"[{datastore.name}]"

            logger.info(f"[VM-BACKUP] Calcul taille réelle (thin provisioning): {search_path}")

            # Lancer la recherche
            task = datastore.browser.SearchDatastore_Task(datastorePath=search_path, searchSpec=search_spec)
            WaitForTask(task)

            if task.info.state == vim.TaskInfo.State.success:
                result = task.info.result
                if hasattr(result, 'file'):
                    for file_info in result.file:
                        # Additionner la taille de tous les fichiers VMDK
                        if hasattr(file_info, 'fileSize'):
                            total_size += file_info.fileSize
                            logger.info(f"[VM-BACKUP] Fichier: {file_info.path} ({file_info.fileSize / (1024*1024):.1f} MB)")

            logger.info(f"[VM-BACKUP] Taille totale réelle (thin): {total_size / (1024*1024):.1f} MB ({total_size / (1024*1024*1024):.2f} GB)")
            return total_size

        except Exception as e:
            logger.warning(f"[VM-BACKUP] Impossible de calculer la taille: {e}")
            # Retourner 0 si échec, la progression s'affichera sans pourcentage
            return 0

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

        # Vérifier si le backup a été annulé
        self.check_cancelled()

        # URL du descriptor
        vmdk_url = f"https://{self.esxi_host}/folder/{vmdk_filename}?dcPath={dc_name}&dsName={datastore_name}"
        dest_file = os.path.join(backup_path, os.path.basename(vmdk_filename))

        # Télécharger le descriptor
        logger.info(f"[VM-BACKUP] Téléchargement descriptor: {vmdk_filename}")
        self.download_vmdk_file(vmdk_url, dest_file)
        file_size = os.path.getsize(dest_file) if os.path.exists(dest_file) else 0
        total_size += file_size
        # Note: downloaded_bytes est déjà incrémenté dans download_vmdk_file() chunk par chunk

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
                # Note: downloaded_bytes est déjà incrémenté dans download_vmdk_file() chunk par chunk
                logger.info(f"[VM-BACKUP] Fichier données téléchargé: {data_dest_file} ({data_size / (1024*1024):.1f} MB)")
            except Exception as e:
                logger.error(f"[VM-BACKUP] Erreur téléchargement données: {e}")
                raise

        # Télécharger récursivement le parent
        if descriptor_info['parent']:
            parent_filename = descriptor_info['parent']
            # Le parent est toujours un nom relatif dans les descriptors VMware
            # Il faut TOUJOURS ajouter le dossier parent
            vmdk_dir = os.path.dirname(vmdk_filename)
            if vmdk_dir:
                parent_filename = f"{vmdk_dir}/{parent_filename}"

            logger.info(f"[VM-BACKUP] -> Téléchargement parent: {parent_filename}")
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

                        # INCRÉMENTER downloaded_bytes EN TEMPS RÉEL (chunk par chunk)
                        self.backup_job.downloaded_bytes += len(chunk)

                        # Mettre à jour tous les 1 MB téléchargés
                        downloaded_mb = downloaded / (1024 * 1024)
                        if downloaded_mb >= last_logged_mb + 1 or downloaded >= file_size:
                            # Vérifier si le backup a été annulé (refresh SEULEMENT le status pour ne pas écraser downloaded_bytes)
                            self.backup_job.refresh_from_db(fields=['status'])
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

                            # Calculer progression si total_bytes connu
                            if self.backup_job.total_bytes > 0:
                                download_percentage = (self.backup_job.downloaded_bytes / self.backup_job.total_bytes) * 100
                                # Progression: 1-5% (snapshot) + 5-90% (download VMDKs) + 90-95% (fichiers config) + 95-99% (finalization) + 100% (completed)
                                # Download VMDKs représente 5-90% de la progression totale (85%)
                                global_progress = 5 + int((download_percentage / 100) * 85)
                                global_progress = min(global_progress, 90)

                                self.backup_job.progress_percentage = global_progress
                                self.backup_job.save()

                                total_mb = self.backup_job.total_bytes / (1024 * 1024)
                                global_downloaded_mb = self.backup_job.downloaded_bytes / (1024 * 1024)
                                logger.info(f"[VM-BACKUP] Téléchargé: {global_downloaded_mb:.1f} MB / {total_mb:.1f} MB ({download_percentage:.1f}%) - Progression: {global_progress}%")
                            else:
                                # Si pas de total connu, estimer la progression basée sur les MB téléchargés
                                # Heuristique: 0-1GB=5-20%, 1-5GB=20-50%, 5-20GB=50-80%, 20+GB=80-90%
                                global_downloaded_mb = self.backup_job.downloaded_bytes / (1024 * 1024)
                                downloaded_gb = global_downloaded_mb / 1024

                                if downloaded_gb < 1:
                                    # 0-1 GB: progression de 5% à 20%
                                    global_progress = 5 + int(downloaded_gb * 15)
                                elif downloaded_gb < 5:
                                    # 1-5 GB: progression de 20% à 50%
                                    global_progress = 20 + int((downloaded_gb - 1) * 7.5)
                                elif downloaded_gb < 20:
                                    # 5-20 GB: progression de 50% à 80%
                                    global_progress = 50 + int((downloaded_gb - 5) * 2)
                                else:
                                    # 20+ GB: progression de 80% à 90%
                                    global_progress = 80 + min(10, int((downloaded_gb - 20) * 0.5))

                                global_progress = min(global_progress, 90)  # Toujours cap à 90%
                                self.backup_job.progress_percentage = global_progress
                                self.backup_job.save()

                                speed = self.backup_job.download_speed_mbps
                                logger.info(f"[VM-BACKUP] Téléchargé: {global_downloaded_mb:.1f} MB ({speed:.1f} MB/s) - Progression: {global_progress}%")

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

            # Note: Impossible de calculer précisément la taille totale à l'avance car:
            # - La chaîne de snapshots peut avoir des parents imprévisibles
            # - Les fichiers delta peuvent avoir des tailles variables
            # - Il faudrait parser tous les descriptors avant de commencer
            # On affichera donc la progression en MB téléchargés sans pourcentage total
            logger.info(f"[VM-BACKUP] Téléchargement des VMDKs (progression en temps réel)")

            # PHASE 2: Télécharger les VMDKs avec progression en temps réel
            logger.info(f"[VM-BACKUP] Phase 2: Téléchargement des VMDKs...")

            # Démarrer le timer pour la progression time-based
            import time
            self.download_phase_start_time = time.time()

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

    def download_vm_files(self):
        """
        Télécharge tous les fichiers de configuration de la VM (.vmx, .nvram, .vmsd, .vmsn, .log)
        Nécessaire pour une restauration complète et identique de la VM
        """
        try:
            backup_path = self.backup_job.backup_full_path

            # Obtenir le chemin du dossier de la VM
            # Format: [datastore] VM_Folder/VM.vmx
            vm_path = self.vm.config.files.vmPathName
            datastore_name = vm_path.split(']')[0].strip('[')
            vm_folder = os.path.dirname(vm_path.split(']')[1].strip().lstrip('/'))

            logger.info(f"[VM-BACKUP] Téléchargement fichiers de configuration depuis: [{datastore_name}] {vm_folder}")

            # Récupérer le datastore
            datastore = None
            for ds in self.vm.datastore:
                if ds.name == datastore_name:
                    datastore = ds
                    break

            if not datastore:
                logger.warning(f"[VM-BACKUP] Datastore non trouvé: {datastore_name}")
                return []

            # Obtenir le datacenter
            dc = self.vm.runtime.host.parent
            while not isinstance(dc, vim.Datacenter):
                dc = dc.parent

            # Lister tous les fichiers dans le dossier de la VM
            search_spec = vim.host.DatastoreBrowser.SearchSpec()
            # Chercher tous les fichiers de configuration
            search_spec.matchPattern = ["*.vmx", "*.nvram", "*.vmsd", "*.vmsn", "*.log"]
            search_spec.details = vim.host.DatastoreBrowser.FileInfo.Details()
            search_spec.details.fileSize = True
            search_spec.details.fileType = True

            search_path = f"[{datastore.name}] {vm_folder}"

            # Lancer la recherche
            task = datastore.browser.SearchDatastore_Task(datastorePath=search_path, searchSpec=search_spec)
            WaitForTask(task)

            downloaded_files = []

            if task.info.state == vim.TaskInfo.State.success:
                result = task.info.result
                if hasattr(result, 'file'):
                    for file_info in result.file:
                        filename = file_info.path
                        file_size_mb = file_info.fileSize / (1024 * 1024)

                        # Construire l'URL de téléchargement
                        if vm_folder:
                            remote_path = f"{vm_folder}/{filename}"
                        else:
                            remote_path = filename

                        file_url = f"https://{self.esxi_host}/folder/{remote_path}?dcPath={dc.name}&dsName={datastore_name}"
                        dest_file = os.path.join(backup_path, filename)

                        logger.info(f"[VM-BACKUP] Téléchargement config: {filename} ({file_size_mb:.2f} MB)")

                        try:
                            # Télécharger le fichier (sans progression car généralement petits)
                            session = requests.Session()
                            session.auth = (self.esxi_user, self.esxi_pass)
                            session.verify = False

                            response = session.get(file_url, timeout=60)
                            response.raise_for_status()

                            with open(dest_file, 'wb') as f:
                                f.write(response.content)

                            downloaded_files.append(filename)
                            logger.info(f"[VM-BACKUP]   -> OK: {filename}")

                        except Exception as e:
                            logger.warning(f"[VM-BACKUP]   -> ERREUR {filename}: {e}")
                            # Continuer même si un fichier échoue

            logger.info(f"[VM-BACKUP] Fichiers config téléchargés: {len(downloaded_files)}")

            return downloaded_files

        except Exception as e:
            logger.error(f"[VM-BACKUP] Erreur téléchargement fichiers config: {e}")
            # Ne pas lever d'exception, le backup des VMDKs est plus important
            return []

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
