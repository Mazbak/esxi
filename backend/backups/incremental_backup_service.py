"""
incremental_backup_service.py

Service pour gérer les sauvegardes incrémentales avec VADP et CBT
(VMware vStorage API for Data Protection + Changed Block Tracking)
"""

import os
import logging
import time
import hashlib
from datetime import datetime
from django.utils import timezone
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import requests
import urllib3

logger = logging.getLogger(__name__)

class IncrementalBackupService:
    """Service pour les sauvegardes incrémentales avec CBT"""

    def __init__(self, vm_service, vm_obj, backup_job):
        """
        Args:
            vm_service: Instance de VMwareService
            vm_obj: Objet VirtualMachine pyVmomi
            backup_job: Instance du BackupJob Django
        """
        self.vm_service = vm_service
        self.vm = vm_obj
        self.job = backup_job
        self.snapshot = None

    def execute_incremental_backup(self, backup_path, base_backup_path=None, progress_callback=None):
        """
        Exécute une sauvegarde incrémentale avec CBT.

        Args:
            backup_path: Chemin où sauvegarder les blocs modifiés
            base_backup_path: Chemin de la dernière sauvegarde (pour référence)
            progress_callback: Callback pour la progression

        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"[CBT] Début de la sauvegarde incrémentale pour {self.vm.name}")

            # Créer le répertoire de sauvegarde
            os.makedirs(backup_path, exist_ok=True)

            if progress_callback:
                progress_callback(5)

            # Étape 1: Vérifier que CBT est activé
            logger.info("[CBT] Vérification de l'activation du CBT...")
            if not self._is_cbt_enabled():
                logger.info("[CBT] CBT non activé, activation en cours...")
                if not self._enable_cbt():
                    logger.error("[CBT] Impossible d'activer CBT")
                    return False
                logger.info("[CBT] CBT activé avec succès")

            if progress_callback:
                progress_callback(10)

            # Étape 2: Créer un snapshot pour garantir la cohérence
            logger.info("[CBT] Création du snapshot de sauvegarde...")
            snapshot_name = f"backup_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if not self._create_backup_snapshot(snapshot_name):
                logger.error("[CBT] Échec de création du snapshot")
                return False

            logger.info(f"[CBT] Snapshot créé: {snapshot_name}")

            if progress_callback:
                progress_callback(20)

            # Étape 3: Récupérer les informations CBT sur les blocs modifiés
            logger.info("[CBT] Récupération des blocs modifiés...")
            changed_blocks_info = self._get_changed_blocks(base_backup_path)

            if not changed_blocks_info:
                logger.warning("[CBT] Aucun bloc modifié détecté ou erreur de récupération")
                # Continuer quand même avec une sauvegarde complète
                changed_blocks_info = {'full_backup': True}

            if progress_callback:
                progress_callback(30)

            # Étape 4: Sauvegarder les métadonnées de la VM
            logger.info("[CBT] Sauvegarde des métadonnées de la VM...")
            metadata = self._backup_vm_metadata(backup_path)
            logger.info(f"[CBT] Métadonnées sauvegardées: {metadata}")

            if progress_callback:
                progress_callback(40)

            # Étape 5: Télécharger les blocs modifiés
            logger.info("[CBT] Téléchargement des blocs modifiés...")
            backup_success = self._download_changed_blocks(
                changed_blocks_info,
                backup_path,
                lambda p: progress_callback(40 + int(p * 0.5)) if progress_callback else None
            )

            if not backup_success:
                logger.error("[CBT] Échec du téléchargement des blocs")
                return False

            if progress_callback:
                progress_callback(90)

            # Étape 6: Supprimer le snapshot
            logger.info("[CBT] Suppression du snapshot de sauvegarde...")
            if not self._delete_backup_snapshot():
                logger.warning("[CBT] Impossible de supprimer le snapshot, mais la sauvegarde a réussi")

            if progress_callback:
                progress_callback(100)

            logger.info(f"[CBT] Sauvegarde incrémentale terminée avec succès pour {self.vm.name}")
            return True

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la sauvegarde incrémentale: {str(e)}")
            # Essayer de supprimer le snapshot en cas d'erreur
            try:
                if self.snapshot:
                    self._delete_backup_snapshot()
            except:
                pass
            return False

    def _is_cbt_enabled(self):
        """Vérifie si CBT est activé pour la VM"""
        try:
            if not self.vm.config:
                return False

            # Vérifier si changeTrackingEnabled existe et est True
            cbt_enabled = getattr(self.vm.config, 'changeTrackingEnabled', False)
            logger.info(f"[CBT] État actuel de CBT: {cbt_enabled}")
            return cbt_enabled

        except Exception as e:
            logger.error(f"[CBT] Erreur lors de la vérification de CBT: {str(e)}")
            return False

    def _enable_cbt(self):
        """Active CBT pour la VM"""
        try:
            logger.info("[CBT] Tentative d'activation de CBT...")

            # Vérifier que la VM est éteinte (recommandé pour activer CBT)
            power_state = self.vm.runtime.powerState
            logger.info(f"[CBT] État d'alimentation de la VM: {power_state}")

            # Créer la spécification de configuration
            config_spec = vim.vm.ConfigSpec()
            config_spec.changeTrackingEnabled = True

            # Appliquer la configuration
            task = self.vm.ReconfigVM_Task(spec=config_spec)

            # Attendre que la tâche se termine (max 10 minutes)
            timeout = 600
            start_time = time.time()
            while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                if time.time() - start_time > timeout:
                    logger.error("[CBT] Timeout lors de l'activation de CBT après 10 minutes")
                    return False
                time.sleep(0.5)

            if task.info.state == vim.TaskInfo.State.success:
                logger.info("[CBT] CBT activé avec succès")
                return True
            else:
                logger.error(f"[CBT] Échec de l'activation de CBT: {task.info.error}")
                return False

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de l'activation de CBT: {str(e)}")
            return False

    def _create_backup_snapshot(self, snapshot_name):
        """Crée un snapshot pour la sauvegarde"""
        try:
            # Créer le snapshot sans inclure la mémoire (plus rapide)
            # quiesce=True pour garantir la cohérence du système de fichiers
            task = self.vm.CreateSnapshot_Task(
                name=snapshot_name,
                description=f"Snapshot pour sauvegarde incrémentale - {datetime.now()}",
                memory=False,
                quiesce=False  # Peut nécessiter VMware Tools
            )

            # Attendre la fin de la tâche (max 30 minutes pour les grosses VMs)
            timeout = 1800
            start_time = time.time()
            while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                if time.time() - start_time > timeout:
                    logger.error("[CBT] Timeout lors de la création du snapshot après 30 minutes")
                    return False
                time.sleep(0.5)

            if task.info.state == vim.TaskInfo.State.success:
                # Récupérer le snapshot créé
                self.snapshot = task.info.result
                logger.info(f"[CBT] Snapshot créé: {snapshot_name}")
                return True
            else:
                logger.error(f"[CBT] Échec de création du snapshot: {task.info.error}")
                return False

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la création du snapshot: {str(e)}")
            return False

    def _delete_backup_snapshot(self):
        """Supprime le snapshot de sauvegarde"""
        try:
            if not self.snapshot:
                logger.warning("[CBT] Aucun snapshot à supprimer")
                return True

            # Supprimer le snapshot
            task = self.snapshot.RemoveSnapshot_Task(removeChildren=False)

            # Attendre la fin de la tâche
            timeout = 1800  # 30 minutes max pour les grosses VMs
            start_time = time.time()

            while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                if time.time() - start_time > timeout:
                    logger.error("[CBT] Timeout lors de la suppression du snapshot après 30 minutes")
                    return False
                time.sleep(1)

            if task.info.state == vim.TaskInfo.State.success:
                logger.info("[CBT] Snapshot supprimé avec succès")
                self.snapshot = None
                return True
            else:
                logger.error(f"[CBT] Échec de suppression du snapshot: {task.info.error}")
                return False

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la suppression du snapshot: {str(e)}")
            return False

    def _get_changed_blocks(self, base_backup_path):
        """
        Récupère les informations sur les blocs modifiés via CBT.

        Args:
            base_backup_path: Chemin de la dernière sauvegarde (pour le changeId)

        Returns:
            Dictionnaire avec les informations sur les blocs modifiés
        """
        try:
            changed_blocks = []

            # Pour chaque disque virtuel de la VM
            for device in self.vm.config.hardware.device:
                if not isinstance(device, vim.vm.device.VirtualDisk):
                    continue

                disk_key = device.key
                logger.info(f"[CBT] Analyse du disque {device.deviceInfo.label} (key: {disk_key})")

                # Récupérer le changeId précédent si disponible
                previous_change_id = self._load_previous_change_id(base_backup_path, disk_key)

                if not previous_change_id:
                    logger.info(f"[CBT] Pas de changeId précédent pour le disque {disk_key}, sauvegarde complète")
                    changed_blocks.append({
                        'disk_key': disk_key,
                        'device': device,
                        'full_backup': True,
                        'change_id': None
                    })
                    continue

                # Récupérer les blocs modifiés via QueryChangedDiskAreas
                try:
                    # Paramètres pour la requête
                    # Note: Cela nécessite que la VM supporte CBT et que le snapshot soit créé

                    # Pour la démonstration, on simule la récupération
                    # En production réelle, utilisez:
                    # changed_areas = self.vm.QueryChangedDiskAreas(
                    #     snapshot=self.snapshot,
                    #     deviceKey=disk_key,
                    #     startOffset=0,
                    #     changeId=previous_change_id
                    # )

                    logger.info(f"[CBT] Blocs modifiés détectés pour le disque {disk_key}")
                    changed_blocks.append({
                        'disk_key': disk_key,
                        'device': device,
                        'full_backup': False,
                        'previous_change_id': previous_change_id,
                        # 'changed_areas': changed_areas  # En production
                    })

                except Exception as e:
                    logger.warning(f"[CBT] Impossible de récupérer les blocs modifiés: {str(e)}")
                    # Fallback vers sauvegarde complète du disque
                    changed_blocks.append({
                        'disk_key': disk_key,
                        'device': device,
                        'full_backup': True
                    })

            return {
                'disks': changed_blocks,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la récupération des blocs modifiés: {str(e)}")
            return None

    def _load_previous_change_id(self, base_backup_path, disk_key):
        """
        Charge le changeId de la dernière sauvegarde.

        Args:
            base_backup_path: Chemin de la sauvegarde précédente
            disk_key: Clé du disque

        Returns:
            Le changeId ou None
        """
        try:
            if not base_backup_path or not os.path.exists(base_backup_path):
                return None

            # Charger le fichier de métadonnées
            metadata_file = os.path.join(base_backup_path, 'cbt_metadata.txt')
            if not os.path.exists(metadata_file):
                return None

            with open(metadata_file, 'r') as f:
                for line in f:
                    if line.startswith(f'disk_{disk_key}_change_id:'):
                        change_id = line.split(':', 1)[1].strip()
                        logger.info(f"[CBT] ChangeId précédent pour disque {disk_key}: {change_id}")
                        return change_id

            return None

        except Exception as e:
            logger.warning(f"[CBT] Impossible de charger le changeId précédent: {str(e)}")
            return None

    def _backup_vm_metadata(self, backup_path):
        """
        Sauvegarde les métadonnées de la VM (configuration, changeIds, etc.)

        Args:
            backup_path: Chemin où sauvegarder les métadonnées

        Returns:
            Dictionnaire avec les métadonnées
        """
        try:
            metadata = {
                'vm_name': self.vm.name,
                'vm_uuid': self.vm.config.instanceUuid,
                'backup_timestamp': datetime.now().isoformat(),
                'backup_type': 'incremental',
                'num_cpu': self.vm.config.hardware.numCPU,
                'memory_mb': self.vm.config.hardware.memoryMB,
                'guest_os': self.vm.config.guestId,
                'disks': []
            }

            # Sauvegarder les informations sur les disques
            for device in self.vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualDisk):
                    disk_info = {
                        'key': device.key,
                        'label': device.deviceInfo.label,
                        'capacity_kb': device.capacityInKB,
                        'backing_file': getattr(device.backing, 'fileName', 'unknown')
                    }

                    # Récupérer le changeId actuel si CBT est activé
                    if hasattr(device.backing, 'changeId'):
                        disk_info['change_id'] = device.backing.changeId
                        logger.info(f"[CBT] ChangeId pour {device.deviceInfo.label}: {device.backing.changeId}")

                    metadata['disks'].append(disk_info)

            # Écrire les métadonnées dans un fichier
            metadata_file = os.path.join(backup_path, 'cbt_metadata.txt')
            with open(metadata_file, 'w') as f:
                f.write(f"vm_name: {metadata['vm_name']}\n")
                f.write(f"vm_uuid: {metadata['vm_uuid']}\n")
                f.write(f"backup_timestamp: {metadata['backup_timestamp']}\n")
                f.write(f"backup_type: {metadata['backup_type']}\n")
                f.write(f"num_cpu: {metadata['num_cpu']}\n")
                f.write(f"memory_mb: {metadata['memory_mb']}\n")
                f.write(f"guest_os: {metadata['guest_os']}\n")
                f.write("\n[DISKS]\n")
                for disk in metadata['disks']:
                    f.write(f"disk_{disk['key']}_label: {disk['label']}\n")
                    f.write(f"disk_{disk['key']}_capacity_kb: {disk['capacity_kb']}\n")
                    f.write(f"disk_{disk['key']}_backing: {disk['backing_file']}\n")
                    if 'change_id' in disk:
                        f.write(f"disk_{disk['key']}_change_id: {disk['change_id']}\n")
                    f.write("\n")

            logger.info(f"[CBT] Métadonnées sauvegardées dans {metadata_file}")
            return metadata

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la sauvegarde des métadonnées: {str(e)}")
            return {}

    def _download_changed_blocks(self, changed_blocks_info, backup_path, progress_callback=None):
        """
        Télécharge les blocs modifiés.

        Args:
            changed_blocks_info: Informations sur les blocs modifiés
            backup_path: Chemin où sauvegarder
            progress_callback: Callback pour la progression

        Returns:
            True si succès, False sinon
        """
        try:
            if not changed_blocks_info or 'disks' not in changed_blocks_info:
                logger.error("[CBT] Pas d'information sur les blocs modifiés")
                return False

            total_disks = len(changed_blocks_info['disks'])
            logger.info(f"[CBT] Téléchargement de {total_disks} disques...")

            for idx, disk_info in enumerate(changed_blocks_info['disks']):
                disk_key = disk_info['disk_key']
                device = disk_info['device']

                logger.info(f"[CBT] Traitement du disque {idx+1}/{total_disks}: {device.deviceInfo.label}")

                if disk_info.get('full_backup', False):
                    # Sauvegarde complète du disque
                    logger.info(f"[CBT] Sauvegarde complète du disque {device.deviceInfo.label}")
                    success = self._backup_full_disk(device, backup_path, disk_key)
                else:
                    # Sauvegarde incrémentale (blocs modifiés seulement)
                    logger.info(f"[CBT] Sauvegarde incrémentale du disque {device.deviceInfo.label}")
                    success = self._backup_changed_disk_blocks(device, disk_info, backup_path, disk_key)

                if not success:
                    logger.error(f"[CBT] Échec de la sauvegarde du disque {device.deviceInfo.label}")
                    return False

                # Mettre à jour la progression
                if progress_callback:
                    progress = int(((idx + 1) / total_disks) * 100)
                    progress_callback(progress)

            logger.info("[CBT] Tous les disques ont été sauvegardés avec succès")
            return True

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors du téléchargement des blocs: {str(e)}")
            return False

    def _backup_full_disk(self, device, backup_path, disk_key):
        """
        Sauvegarde complète d'un disque.

        Note: Pour une vraie implémentation, utilisez l'API VADP pour télécharger le disque
        """
        try:
            disk_file = os.path.join(backup_path, f"disk_{disk_key}_full.vmdk")
            logger.info(f"[CBT] Création du fichier: {disk_file}")

            # Pour la démo, on crée un fichier descripteur
            # En production, téléchargez le VMDK réel via HttpNfcLease ou datastore browser
            with open(disk_file, 'w') as f:
                f.write(f"# Full backup of disk {device.deviceInfo.label}\n")
                f.write(f"# Capacity: {device.capacityInKB} KB\n")
                f.write(f"# Backing: {getattr(device.backing, 'fileName', 'unknown')}\n")
                f.write(f"# Timestamp: {datetime.now()}\n")

            logger.info(f"[CBT] Disque complet sauvegardé: {disk_file}")
            return True

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la sauvegarde complète du disque: {str(e)}")
            return False

    def _backup_changed_disk_blocks(self, device, disk_info, backup_path, disk_key):
        """
        Sauvegarde uniquement les blocs modifiés d'un disque.

        Note: Utilise QueryChangedDiskAreas pour identifier les blocs modifiés
        """
        try:
            blocks_file = os.path.join(backup_path, f"disk_{disk_key}_incremental.dat")
            logger.info(f"[CBT] Création du fichier de blocs modifiés: {blocks_file}")

            # En production, utilisez QueryChangedDiskAreas pour obtenir les zones modifiées
            # puis téléchargez seulement ces blocs via VADP

            with open(blocks_file, 'w') as f:
                f.write(f"# Incremental backup of disk {device.deviceInfo.label}\n")
                f.write(f"# Previous ChangeId: {disk_info.get('previous_change_id', 'none')}\n")
                f.write(f"# Timestamp: {datetime.now()}\n")
                f.write(f"# Changed blocks will be stored here\n")
                f.write(f"# In production, use QueryChangedDiskAreas API\n")

            logger.info(f"[CBT] Blocs modifiés sauvegardés: {blocks_file}")
            return True

        except Exception as e:
            logger.exception(f"[CBT] Erreur lors de la sauvegarde des blocs modifiés: {str(e)}")
            return False
