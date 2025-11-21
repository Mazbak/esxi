"""
VMDK Restore Service - Restauration de disques virtuels individuels
Permet de restaurer un VMDK depuis une sauvegarde complète ou incrémentale
"""

import os
import shutil
import tempfile
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class VMDKRestoreService:
    """
    Service de restauration de disques VMDK individuels

    Fonctionnalités:
    - Restaurer un disque depuis une sauvegarde full ou incremental
    - Reconstruire le VMDK depuis une chaîne incrémentale
    - Attacher le VMDK à une VM existante
    - Créer un nouveau disque indépendant
    - Support des modes OVF et CBT
    """

    def __init__(self, chain_manager, integrity_checker, vmware_service):
        """
        Initialise le service de restauration VMDK

        Args:
            chain_manager: Instance de BackupChainManager
            integrity_checker: Instance de IntegrityChecker
            vmware_service: Instance du service VMware
        """
        self.chain_manager = chain_manager
        self.integrity_checker = integrity_checker
        self.vmware = vmware_service
        self.vm_name = chain_manager.vm_name

        logger.info(f"[VMDK-RESTORE] Service initialisé pour {self.vm_name}")

    def restore_vmdk(
        self,
        backup_id: str,
        vmdk_filename: str,
        target_datastore: str,
        target_name: Optional[str] = None,
        attach_to_vm: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Restaure un disque VMDK individuel depuis une sauvegarde

        Args:
            backup_id: ID de la sauvegarde source
            vmdk_filename: Nom du fichier VMDK à restaurer (ex: 'VM_WebServer.vmdk')
            target_datastore: Datastore ESXi de destination
            target_name: Nom du fichier VMDK restauré (optionnel)
            attach_to_vm: Nom de la VM à laquelle attacher (optionnel, sinon crée un disque orphelin)
            progress_callback: Fonction de callback pour progression

        Returns:
            Dict avec résultats de la restauration
        """
        logger.info(f"[VMDK-RESTORE] === DÉBUT RESTAURATION VMDK ===")
        logger.info(f"[VMDK-RESTORE] Backup: {backup_id}")
        logger.info(f"[VMDK-RESTORE] VMDK: {vmdk_filename}")
        logger.info(f"[VMDK-RESTORE] Datastore: {target_datastore}")

        results = {
            'success': False,
            'vmdk_path': None,
            'vmdk_name': None,
            'attached_to_vm': None,
            'size_bytes': 0,
            'restored_from_chain': False,
            'errors': []
        }

        try:
            # 1. Validation
            if progress_callback:
                progress_callback(5, "Validation de la restauration...")

            validation = self.validate_vmdk_restore(backup_id, vmdk_filename)
            if not validation['valid']:
                results['errors'] = validation['errors']
                logger.error(f"[VMDK-RESTORE] Validation échouée: {validation['errors']}")
                return results

            # 2. Déterminer le mode de restauration
            backup = self.chain_manager.get_backup(backup_id)
            restore_chain = self.chain_manager.get_restore_chain(backup_id)

            if len(restore_chain) == 1 and restore_chain[0]['type'] == 'full':
                # Restauration directe depuis full
                if progress_callback:
                    progress_callback(10, "Restauration directe depuis full backup...")

                success = self._restore_vmdk_from_full(
                    backup,
                    vmdk_filename,
                    target_datastore,
                    target_name,
                    attach_to_vm,
                    results,
                    progress_callback
                )
            else:
                # Reconstruction depuis chaîne incrémentale
                if progress_callback:
                    progress_callback(10, f"Reconstruction depuis chaîne de {len(restore_chain)} backups...")

                success = self._restore_vmdk_from_chain(
                    restore_chain,
                    vmdk_filename,
                    target_datastore,
                    target_name,
                    attach_to_vm,
                    results,
                    progress_callback
                )
                results['restored_from_chain'] = True

            results['success'] = success

            if success:
                logger.info(f"[VMDK-RESTORE] ✓ Restauration réussie: {results['vmdk_path']}")
                if attach_to_vm:
                    logger.info(f"[VMDK-RESTORE] ✓ Attaché à la VM: {attach_to_vm}")
            else:
                logger.error(f"[VMDK-RESTORE] ✗ Restauration échouée")

        except Exception as e:
            logger.error(f"[VMDK-RESTORE] Erreur: {e}", exc_info=True)
            results['errors'].append(str(e))
            results['success'] = False

        return results

    def _restore_vmdk_from_full(
        self,
        backup: Dict,
        vmdk_filename: str,
        target_datastore: str,
        target_name: Optional[str],
        attach_to_vm: Optional[str],
        results: Dict,
        progress_callback: Optional[Callable]
    ) -> bool:
        """
        Restaure un VMDK directement depuis une full backup

        Args:
            backup: Informations de la sauvegarde
            vmdk_filename: Nom du fichier VMDK
            target_datastore: Datastore de destination
            target_name: Nom du VMDK restauré
            attach_to_vm: VM à laquelle attacher
            results: Dict de résultats à remplir
            progress_callback: Callback de progression

        Returns:
            bool: True si succès
        """
        backup_folder = os.path.join(self.chain_manager.vm_folder, backup['id'])
        source_vmdk = os.path.join(backup_folder, vmdk_filename)

        if not os.path.exists(source_vmdk):
            logger.error(f"[VMDK-RESTORE] VMDK introuvable: {source_vmdk}")
            results['errors'].append(f"VMDK {vmdk_filename} introuvable dans le backup")
            return False

        # Déterminer le nom du VMDK restauré
        vmdk_name = target_name or f"restored_{vmdk_filename}"

        logger.info(f"[VMDK-RESTORE] Source: {source_vmdk}")
        logger.info(f"[VMDK-RESTORE] Destination: {target_datastore}/{vmdk_name}")

        try:
            # Upload du VMDK vers le datastore
            if progress_callback:
                progress_callback(30, f"Upload du VMDK vers {target_datastore}...")

            vmdk_path = self.vmware.upload_vmdk_to_datastore(
                source_vmdk,
                target_datastore,
                vmdk_name
            )

            results['vmdk_path'] = vmdk_path
            results['vmdk_name'] = vmdk_name
            results['size_bytes'] = os.path.getsize(source_vmdk)

            if progress_callback:
                progress_callback(80, "Upload terminé")

            # Attacher à une VM si demandé
            if attach_to_vm:
                if progress_callback:
                    progress_callback(85, f"Attachement à la VM {attach_to_vm}...")

                success = self._attach_vmdk_to_vm(
                    attach_to_vm,
                    vmdk_path,
                    results
                )

                if not success:
                    logger.warning(f"[VMDK-RESTORE] Échec attachement à {attach_to_vm}")
                    results['errors'].append(f"Échec attachement à la VM {attach_to_vm}")

            if progress_callback:
                progress_callback(100, "Restauration VMDK terminée")

            return True

        except Exception as e:
            logger.error(f"[VMDK-RESTORE] Erreur upload VMDK: {e}")
            results['errors'].append(f"Erreur upload: {e}")
            return False

    def _restore_vmdk_from_chain(
        self,
        restore_chain: List[Dict],
        vmdk_filename: str,
        target_datastore: str,
        target_name: Optional[str],
        attach_to_vm: Optional[str],
        results: Dict,
        progress_callback: Optional[Callable]
    ) -> bool:
        """
        Restaure un VMDK en reconstruisant depuis une chaîne incrémentale

        Args:
            restore_chain: Chaîne de restauration [full, incr1, incr2, ...]
            vmdk_filename: Nom du fichier VMDK
            target_datastore: Datastore de destination
            target_name: Nom du VMDK restauré
            attach_to_vm: VM à laquelle attacher
            results: Dict de résultats
            progress_callback: Callback de progression

        Returns:
            bool: True si succès
        """
        temp_dir = None

        try:
            # Créer un répertoire temporaire pour la reconstruction
            temp_dir = tempfile.mkdtemp(prefix='vmdk_restore_')
            logger.info(f"[VMDK-RESTORE] Répertoire temporaire: {temp_dir}")

            # 1. Copier le VMDK de base
            base_backup = restore_chain[0]
            base_folder = os.path.join(self.chain_manager.vm_folder, base_backup['id'])
            source_vmdk = os.path.join(base_folder, vmdk_filename)

            if not os.path.exists(source_vmdk):
                results['errors'].append(f"VMDK {vmdk_filename} introuvable dans la base")
                return False

            if progress_callback:
                progress_callback(20, "Copie du VMDK de base...")

            temp_vmdk = os.path.join(temp_dir, vmdk_filename)
            shutil.copy2(source_vmdk, temp_vmdk)

            logger.info(f"[VMDK-RESTORE] VMDK de base copié: {temp_vmdk}")

            # 2. Appliquer chaque incrémentale dans l'ordre
            total_incrementals = len(restore_chain) - 1

            for idx, incremental in enumerate(restore_chain[1:], 1):
                progress = 20 + (idx / total_incrementals * 50)
                if progress_callback:
                    progress_callback(
                        int(progress),
                        f"Application incrémentale {idx}/{total_incrementals}..."
                    )

                logger.info(f"[VMDK-RESTORE] Application incrémentale {idx}/{total_incrementals}: {incremental['id']}")

                success = self._apply_incremental_to_vmdk(
                    temp_vmdk,
                    incremental,
                    vmdk_filename
                )

                if not success:
                    results['errors'].append(f"Échec application incrémentale {incremental['id']}")
                    return False

            # 3. Upload du VMDK reconstruit
            vmdk_name = target_name or f"restored_{vmdk_filename}"

            if progress_callback:
                progress_callback(75, f"Upload du VMDK reconstruit vers {target_datastore}...")

            vmdk_path = self.vmware.upload_vmdk_to_datastore(
                temp_vmdk,
                target_datastore,
                vmdk_name
            )

            results['vmdk_path'] = vmdk_path
            results['vmdk_name'] = vmdk_name
            results['size_bytes'] = os.path.getsize(temp_vmdk)

            # 4. Attacher à une VM si demandé
            if attach_to_vm:
                if progress_callback:
                    progress_callback(90, f"Attachement à la VM {attach_to_vm}...")

                success = self._attach_vmdk_to_vm(attach_to_vm, vmdk_path, results)

                if not success:
                    logger.warning(f"[VMDK-RESTORE] Échec attachement à {attach_to_vm}")
                    results['errors'].append(f"Échec attachement à la VM {attach_to_vm}")

            if progress_callback:
                progress_callback(100, "Reconstruction et restauration terminées")

            return True

        except Exception as e:
            logger.error(f"[VMDK-RESTORE] Erreur reconstruction: {e}", exc_info=True)
            results['errors'].append(f"Erreur reconstruction: {e}")
            return False

        finally:
            # Nettoyer le répertoire temporaire
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"[VMDK-RESTORE] Répertoire temporaire supprimé")
                except Exception as e:
                    logger.warning(f"[VMDK-RESTORE] Erreur suppression temp: {e}")

    def _apply_incremental_to_vmdk(
        self,
        vmdk_path: str,
        incremental: Dict,
        vmdk_filename: str
    ) -> bool:
        """
        Applique les modifications d'une incrémentale à un VMDK

        Args:
            vmdk_path: Chemin du VMDK à modifier
            incremental: Informations de l'incrémentale
            vmdk_filename: Nom du fichier VMDK

        Returns:
            bool: True si succès
        """
        incr_folder = os.path.join(self.chain_manager.vm_folder, incremental['id'])

        if incremental['mode'] == 'ovf':
            # Mode OVF: remplacer le VMDK s'il existe dans l'incrémentale
            incr_vmdk = os.path.join(incr_folder, vmdk_filename)

            if os.path.exists(incr_vmdk):
                logger.info(f"[VMDK-RESTORE] Remplacement du VMDK depuis OVF incremental")
                shutil.copy2(incr_vmdk, vmdk_path)
                return True
            else:
                # Pas de modification de ce VMDK dans cette incrémentale
                logger.debug(f"[VMDK-RESTORE] Pas de modification de {vmdk_filename} dans {incremental['id']}")
                return True

        elif incremental['mode'] == 'cbt':
            # Mode CBT: appliquer les blocs modifiés
            return self._apply_cbt_blocks_to_vmdk(vmdk_path, incr_folder, vmdk_filename)

        else:
            logger.error(f"[VMDK-RESTORE] Mode inconnu: {incremental['mode']}")
            return False

    def _apply_cbt_blocks_to_vmdk(
        self,
        vmdk_path: str,
        incr_folder: str,
        vmdk_filename: str
    ) -> bool:
        """
        Applique les blocs CBT à un VMDK

        Args:
            vmdk_path: Chemin du VMDK
            incr_folder: Dossier de l'incrémentale
            vmdk_filename: Nom du VMDK

        Returns:
            bool: True si succès
        """
        # Chercher le fichier de block map pour ce VMDK
        vmdk_base = os.path.splitext(vmdk_filename)[0]
        block_map_file = os.path.join(incr_folder, f"{vmdk_base}_block_map.json")
        changed_blocks_file = os.path.join(incr_folder, f"{vmdk_base}_changed_blocks.dat")

        if not os.path.exists(block_map_file):
            # Pas de modifications CBT pour ce VMDK
            logger.debug(f"[VMDK-RESTORE] Pas de block_map pour {vmdk_filename}")
            return True

        if not os.path.exists(changed_blocks_file):
            logger.error(f"[VMDK-RESTORE] changed_blocks.dat manquant pour {vmdk_filename}")
            return False

        try:
            import json

            # Charger la block map
            with open(block_map_file, 'r') as f:
                block_map = json.load(f)

            logger.info(f"[VMDK-RESTORE] Application de {len(block_map.get('changed_blocks', []))} blocs CBT")

            # Appliquer les blocs modifiés
            with open(changed_blocks_file, 'rb') as f_blocks:
                with open(vmdk_path, 'r+b') as f_vmdk:
                    for block in block_map['changed_blocks']:
                        # Lire les données du bloc
                        block_data = f_blocks.read(block['length'])

                        # Écrire au bon offset dans le VMDK
                        f_vmdk.seek(block['offset'])
                        f_vmdk.write(block_data)

            logger.info(f"[VMDK-RESTORE] ✓ Blocs CBT appliqués avec succès")
            return True

        except Exception as e:
            logger.error(f"[VMDK-RESTORE] Erreur application CBT: {e}")
            return False

    def _attach_vmdk_to_vm(
        self,
        vm_name: str,
        vmdk_path: str,
        results: Dict
    ) -> bool:
        """
        Attache un VMDK à une VM existante

        Args:
            vm_name: Nom de la VM
            vmdk_path: Chemin du VMDK sur le datastore
            results: Dict de résultats

        Returns:
            bool: True si succès
        """
        try:
            logger.info(f"[VMDK-RESTORE] Attachement de {vmdk_path} à {vm_name}")

            # Trouver le prochain contrôleur et unité disponibles
            vm = self.vmware.get_vm(vm_name)
            if not vm:
                logger.error(f"[VMDK-RESTORE] VM {vm_name} introuvable")
                return False

            # Attacher le disque
            self.vmware.attach_disk_to_vm(vm, vmdk_path)

            results['attached_to_vm'] = vm_name
            logger.info(f"[VMDK-RESTORE] ✓ VMDK attaché à {vm_name}")

            return True

        except Exception as e:
            logger.error(f"[VMDK-RESTORE] Erreur attachement: {e}")
            return False

    def validate_vmdk_restore(
        self,
        backup_id: str,
        vmdk_filename: str
    ) -> Dict[str, Any]:
        """
        Valide qu'une restauration VMDK est possible

        Args:
            backup_id: ID de la sauvegarde
            vmdk_filename: Nom du fichier VMDK

        Returns:
            Dict avec résultats de validation
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # 1. Vérifier que le backup existe
        backup = self.chain_manager.get_backup(backup_id)
        if not backup:
            results['valid'] = False
            results['errors'].append(f"Backup {backup_id} introuvable")
            return results

        # 2. Vérifier la chaîne de restauration
        restore_chain = self.chain_manager.get_restore_chain(backup_id)
        if not restore_chain:
            results['valid'] = False
            results['errors'].append(f"Impossible de construire la chaîne de restauration")
            return results

        # 3. Vérifier que le VMDK existe dans au moins un backup de la chaîne
        vmdk_found = False

        for backup_in_chain in restore_chain:
            backup_folder = os.path.join(
                self.chain_manager.vm_folder,
                backup_in_chain['id']
            )
            vmdk_path = os.path.join(backup_folder, vmdk_filename)

            if os.path.exists(vmdk_path):
                vmdk_found = True
                break

        if not vmdk_found:
            results['valid'] = False
            results['errors'].append(f"VMDK {vmdk_filename} introuvable dans la chaîne de backup")
            return results

        # 4. Vérifier l'intégrité des backups dans la chaîne
        for backup_in_chain in restore_chain:
            integrity = self.integrity_checker.verify_backup_integrity(backup_in_chain['id'])

            if not integrity['valid']:
                results['warnings'].append(
                    f"Intégrité compromise pour {backup_in_chain['id']}: {len(integrity['corrupted_files'])} fichiers corrompus"
                )

        logger.info(f"[VMDK-RESTORE] Validation: {'✓ OK' if results['valid'] else '✗ ERREURS'}")

        return results

    def list_vmdks_in_backup(self, backup_id: str) -> List[Dict[str, Any]]:
        """
        Liste tous les VMDK disponibles dans une sauvegarde

        Args:
            backup_id: ID de la sauvegarde

        Returns:
            Liste de dict avec infos sur chaque VMDK
        """
        backup = self.chain_manager.get_backup(backup_id)
        if not backup:
            return []

        backup_folder = os.path.join(self.chain_manager.vm_folder, backup['id'])
        vmdks = []

        try:
            for filename in os.listdir(backup_folder):
                if filename.endswith('.vmdk') and not filename.endswith('-flat.vmdk'):
                    vmdk_path = os.path.join(backup_folder, filename)
                    size = os.path.getsize(vmdk_path)

                    vmdks.append({
                        'filename': filename,
                        'size_bytes': size,
                        'size_gb': round(size / (1024 ** 3), 2),
                        'backup_id': backup_id
                    })

            logger.info(f"[VMDK-RESTORE] {len(vmdks)} VMDK(s) trouvé(s) dans {backup_id}")

        except Exception as e:
            logger.error(f"[VMDK-RESTORE] Erreur listage VMDK: {e}")

        return vmdks
