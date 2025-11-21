"""
VM Restore Service - Restauration complète de machines virtuelles
Support restauration depuis Full ou chaîne incrémentale
"""

import os
import shutil
import logging
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class VMRestoreService:
    """
    Service de restauration complète de VM

    Fonctionnalités:
    - Restauration depuis backup Full
    - Restauration depuis point incrémental (reconstruction)
    - Restauration vers datastore ESXi ou export local
    - Validation et vérification avant restauration
    """

    def __init__(self, vmware_service, chain_manager):
        """
        Initialise le service de restauration

        Args:
            vmware_service: Instance de VMwareService
            chain_manager: Instance de BackupChainManager
        """
        self.vmware = vmware_service
        self.chain_manager = chain_manager
        self.vm_name = chain_manager.vm_name

        logger.info(f"[RESTORE_VM] Service initialisé pour {self.vm_name}")

    def restore_vm_complete(
        self,
        backup_id: str,
        target_datastore: str,
        target_vm_name: Optional[str] = None,
        restore_mode: str = 'new',
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Restaure une VM complète depuis une sauvegarde

        Args:
            backup_id: ID de la sauvegarde cible
            target_datastore: Datastore ESXi de destination
            target_vm_name: Nom de la VM restaurée (None = nom original)
            restore_mode: 'new' (nouvelle VM) | 'overwrite' (remplacer existante)
            progress_callback: Fonction callback(percentage: int)

        Returns:
            Dict: {
                'success': bool,
                'restored_vm_name': str,
                'restored_vm_id': str,
                'restored_from_chain': List[str],  # IDs des backups appliqués
                'duration_seconds': int,
                'errors': List[str]
            }
        """
        import time
        start_time = time.time()

        logger.info(f"[RESTORE_VM] === DÉBUT RESTAURATION VM ===")
        logger.info(f"[RESTORE_VM] Backup cible: {backup_id}")
        logger.info(f"[RESTORE_VM] Datastore: {target_datastore}")
        logger.info(f"[RESTORE_VM] Mode: {restore_mode}")

        result = {
            'success': False,
            'restored_vm_name': target_vm_name or self.vm_name,
            'restored_vm_id': None,
            'restored_from_chain': [],
            'duration_seconds': 0,
            'errors': []
        }

        try:
            # 1. Vérifier que le backup existe
            backup = self.chain_manager.get_backup(backup_id)
            if not backup:
                error = f"Backup {backup_id} introuvable dans la chaîne"
                logger.error(f"[RESTORE_VM] {error}")
                result['errors'].append(error)
                return result

            if progress_callback:
                progress_callback(5)

            # 2. Déterminer la chaîne de restauration
            restore_chain = self.chain_manager.get_restore_chain(backup_id)

            if not restore_chain:
                error = "Impossible de construire la chaîne de restauration"
                logger.error(f"[RESTORE_VM] {error}")
                result['errors'].append(error)
                return result

            logger.info(f"[RESTORE_VM] Chaîne de restauration: {len(restore_chain)} sauvegardes")
            for b in restore_chain:
                logger.info(f"[RESTORE_VM]   - {b['id']} ({b['type']})")
                result['restored_from_chain'].append(b['id'])

            if progress_callback:
                progress_callback(10)

            # 3. Préparer la restauration
            if len(restore_chain) == 1 and restore_chain[0]['type'] == 'full':
                # Restauration simple depuis Full
                logger.info("[RESTORE_VM] Restauration directe depuis Full backup")
                success = self._restore_from_full(
                    restore_chain[0],
                    target_datastore,
                    target_vm_name,
                    restore_mode,
                    progress_callback
                )

            else:
                # Restauration depuis chaîne incrémentale (reconstruction nécessaire)
                logger.info("[RESTORE_VM] Reconstruction depuis chaîne incrémentale")
                success = self._restore_from_incremental_chain(
                    restore_chain,
                    target_datastore,
                    target_vm_name,
                    restore_mode,
                    progress_callback
                )

            if success:
                result['success'] = True
                logger.info("[RESTORE_VM] ✓✓✓ RESTAURATION RÉUSSIE ✓✓✓")
            else:
                result['errors'].append("Échec de la restauration")
                logger.error("[RESTORE_VM] ✗✗✗ RESTAURATION ÉCHOUÉE ✗✗✗")

        except Exception as e:
            logger.exception(f"[RESTORE_VM] Erreur inattendue: {e}")
            result['errors'].append(str(e))

        finally:
            result['duration_seconds'] = int(time.time() - start_time)
            logger.info(f"[RESTORE_VM] Durée totale: {result['duration_seconds']}s")

        return result

    def _restore_from_full(
        self,
        backup: Dict[str, Any],
        target_datastore: str,
        target_vm_name: Optional[str],
        restore_mode: str,
        progress_callback
    ) -> bool:
        """
        Restaure directement depuis une sauvegarde complète

        Args:
            backup: Informations du backup Full
            target_datastore: Datastore de destination
            target_vm_name: Nom de la VM restaurée
            restore_mode: Mode de restauration
            progress_callback: Callback progression

        Returns:
            bool: True si succès
        """
        backup_folder = os.path.join(self.chain_manager.vm_folder, backup['id'])

        logger.info(f"[RESTORE_VM] Dossier source: {backup_folder}")

        # Vérifier que le dossier existe
        if not os.path.exists(backup_folder):
            logger.error(f"[RESTORE_VM] Dossier introuvable: {backup_folder}")
            return False

        # Trouver le fichier OVF
        ovf_files = [f for f in os.listdir(backup_folder) if f.endswith('.ovf')]

        if not ovf_files:
            logger.error("[RESTORE_VM] Aucun fichier OVF trouvé")
            return False

        ovf_file = os.path.join(backup_folder, ovf_files[0])
        logger.info(f"[RESTORE_VM] Fichier OVF: {ovf_file}")

        if progress_callback:
            progress_callback(20)

        try:
            # Importer l'OVF dans ESXi
            logger.info(f"[RESTORE_VM] Import OVF vers datastore '{target_datastore}'...")

            vm_name = target_vm_name or self.vm_name

            # Vérifier si la VM existe déjà
            if restore_mode == 'new':
                # S'assurer qu'aucune VM avec ce nom n'existe
                existing_vm = self.vmware._find_vm_by_name(vm_name)
                if existing_vm:
                    # Générer un nom unique
                    import datetime
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    vm_name = f"{vm_name}_restored_{timestamp}"
                    logger.info(f"[RESTORE_VM] VM existe, nouveau nom: {vm_name}")

            # Importer l'OVF
            success = self.vmware.import_ovf(
                ovf_file,
                target_datastore,
                vm_name=vm_name,
                progress_callback=lambda p: progress_callback(20 + int(p * 0.7)) if progress_callback else None
            )

            if success:
                logger.info(f"[RESTORE_VM] ✓ VM restaurée: {vm_name}")

                if progress_callback:
                    progress_callback(95)

                return True
            else:
                logger.error("[RESTORE_VM] ✗ Échec import OVF")
                return False

        except Exception as e:
            logger.exception(f"[RESTORE_VM] Erreur import OVF: {e}")
            return False

    def _restore_from_incremental_chain(
        self,
        restore_chain: list,
        target_datastore: str,
        target_vm_name: Optional[str],
        restore_mode: str,
        progress_callback
    ) -> bool:
        """
        Restaure depuis une chaîne incrémentale en reconstruisant

        Processus:
        1. Copier la Full backup dans un dossier temporaire
        2. Appliquer chaque incrémentale dans l'ordre
        3. Importer le résultat final

        Args:
            restore_chain: Liste ordonnée [full, incr1, incr2, ...]
            target_datastore: Datastore de destination
            target_vm_name: Nom de la VM restaurée
            restore_mode: Mode de restauration
            progress_callback: Callback progression

        Returns:
            bool: True si succès
        """
        logger.info("[RESTORE_VM] Début reconstruction depuis chaîne incrémentale")

        # Créer un dossier temporaire pour la reconstruction
        temp_dir = tempfile.mkdtemp(prefix='vm_restore_')
        logger.info(f"[RESTORE_VM] Dossier temporaire: {temp_dir}")

        try:
            # 1. Copier la Full backup
            base_backup = restore_chain[0]
            base_folder = os.path.join(self.chain_manager.vm_folder, base_backup['id'])

            logger.info(f"[RESTORE_VM] Copie base backup: {base_backup['id']}")

            if progress_callback:
                progress_callback(20)

            shutil.copytree(base_folder, os.path.join(temp_dir, 'vm_data'))

            if progress_callback:
                progress_callback(40)

            # 2. Appliquer les incrémentales
            if len(restore_chain) > 1:
                logger.info(f"[RESTORE_VM] Application de {len(restore_chain) - 1} incrémentales")

                for idx, incremental in enumerate(restore_chain[1:], start=1):
                    logger.info(f"[RESTORE_VM] Application incrémentale {idx}: {incremental['id']}")

                    success = self._apply_incremental(
                        os.path.join(temp_dir, 'vm_data'),
                        incremental
                    )

                    if not success:
                        logger.error(f"[RESTORE_VM] Échec application {incremental['id']}")
                        return False

                    if progress_callback:
                        progress = 40 + int((idx / (len(restore_chain) - 1)) * 40)
                        progress_callback(progress)

            # 3. Importer le résultat final
            logger.info("[RESTORE_VM] Import de la VM reconstruite")

            ovf_files = [f for f in os.listdir(os.path.join(temp_dir, 'vm_data')) if f.endswith('.ovf')]
            if not ovf_files:
                logger.error("[RESTORE_VM] Aucun fichier OVF dans la reconstruction")
                return False

            ovf_file = os.path.join(temp_dir, 'vm_data', ovf_files[0])
            vm_name = target_vm_name or self.vm_name

            success = self.vmware.import_ovf(
                ovf_file,
                target_datastore,
                vm_name=vm_name,
                progress_callback=lambda p: progress_callback(80 + int(p * 0.15)) if progress_callback else None
            )

            if success:
                logger.info(f"[RESTORE_VM] ✓ VM reconstruite et restaurée: {vm_name}")
                return True
            else:
                logger.error("[RESTORE_VM] ✗ Échec import VM reconstruite")
                return False

        except Exception as e:
            logger.exception(f"[RESTORE_VM] Erreur reconstruction: {e}")
            return False

        finally:
            # Nettoyer le dossier temporaire
            try:
                shutil.rmtree(temp_dir)
                logger.info("[RESTORE_VM] Dossier temporaire nettoyé")
            except Exception as e:
                logger.warning(f"[RESTORE_VM] Erreur nettoyage temp: {e}")

    def _apply_incremental(self, vm_data_folder: str, incremental: Dict[str, Any]) -> bool:
        """
        Applique une sauvegarde incrémentale sur une VM

        Pour OVF: Remplace les fichiers modifiés
        Pour CBT: Applique les blocs modifiés

        Args:
            vm_data_folder: Dossier contenant la VM
            incremental: Informations de l'incrémentale

        Returns:
            bool: True si succès
        """
        incr_folder = os.path.join(self.chain_manager.vm_folder, incremental['id'])

        logger.info(f"[RESTORE_VM] Application incrémentale depuis: {incr_folder}")

        if incremental['mode'] == 'ovf':
            # Pour OVF incrémental: copier les fichiers modifiés
            return self._apply_ovf_incremental(vm_data_folder, incr_folder)
        elif incremental['mode'] == 'cbt':
            # Pour CBT: appliquer les blocs modifiés
            return self._apply_cbt_incremental(vm_data_folder, incr_folder)
        else:
            logger.error(f"[RESTORE_VM] Mode incrémental non supporté: {incremental['mode']}")
            return False

    def _apply_ovf_incremental(self, vm_folder: str, incr_folder: str) -> bool:
        """Applique une incrémentale OVF (copie fichiers)"""
        try:
            # Pour OVF incrémental, les fichiers modifiés écrasent les anciens
            for file in os.listdir(incr_folder):
                if file == 'metadata.json':
                    continue

                src = os.path.join(incr_folder, file)
                dst = os.path.join(vm_folder, file)

                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    logger.debug(f"[RESTORE_VM]   Copié: {file}")

            return True

        except Exception as e:
            logger.error(f"[RESTORE_VM] Erreur application OVF incrémentale: {e}")
            return False

    def _apply_cbt_incremental(self, vm_folder: str, incr_folder: str) -> bool:
        """Applique une incrémentale CBT (blocs modifiés)"""
        try:
            # Charger la carte des blocs
            block_map_file = os.path.join(incr_folder, 'block_map.json')
            if not os.path.exists(block_map_file):
                logger.error("[RESTORE_VM] block_map.json introuvable")
                return False

            import json
            with open(block_map_file, 'r') as f:
                block_map = json.load(f)

            changed_blocks_file = os.path.join(incr_folder, 'changed_blocks.dat')
            if not os.path.exists(changed_blocks_file):
                logger.error("[RESTORE_VM] changed_blocks.dat introuvable")
                return False

            # Trouver le VMDK
            vmdk_files = [f for f in os.listdir(vm_folder) if f.endswith('.vmdk') and not f.endswith('-flat.vmdk')]
            if not vmdk_files:
                logger.error("[RESTORE_VM] Aucun VMDK trouvé")
                return False

            vmdk_file = os.path.join(vm_folder, vmdk_files[0])
            logger.info(f"[RESTORE_VM] Application CBT sur: {vmdk_file}")

            # Appliquer les blocs modifiés
            with open(changed_blocks_file, 'rb') as f_blocks:
                with open(vmdk_file, 'r+b') as f_vmdk:
                    for block in block_map.get('changed_blocks', []):
                        offset = block['offset']
                        length = block['length']

                        # Lire le bloc depuis changed_blocks.dat
                        f_blocks.seek(block['data_offset'])
                        block_data = f_blocks.read(length)

                        # Écrire dans le VMDK
                        f_vmdk.seek(offset)
                        f_vmdk.write(block_data)

                        logger.debug(f"[RESTORE_VM]   Bloc appliqué: offset={offset}, length={length}")

            logger.info(f"[RESTORE_VM] ✓ CBT appliqué: {len(block_map.get('changed_blocks', []))} blocs")
            return True

        except Exception as e:
            logger.exception(f"[RESTORE_VM] Erreur application CBT: {e}")
            return False

    def validate_before_restore(self, backup_id: str) -> Dict[str, Any]:
        """
        Valide qu'une restauration est possible avant de l'exécuter

        Args:
            backup_id: ID de la sauvegarde

        Returns:
            Dict: {
                'valid': bool,
                'warnings': List[str],
                'errors': List[str],
                'restore_chain': List[str],
                'total_size_gb': float
            }
        """
        logger.info(f"[RESTORE_VM] Validation pré-restauration: {backup_id}")

        validation = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'restore_chain': [],
            'total_size_gb': 0
        }

        # Vérifier que le backup existe
        backup = self.chain_manager.get_backup(backup_id)
        if not backup:
            validation['valid'] = False
            validation['errors'].append(f"Backup {backup_id} introuvable")
            return validation

        # Construire la chaîne de restauration
        restore_chain = self.chain_manager.get_restore_chain(backup_id)
        if not restore_chain:
            validation['valid'] = False
            validation['errors'].append("Impossible de construire la chaîne de restauration")
            return validation

        validation['restore_chain'] = [b['id'] for b in restore_chain]

        # Vérifier l'existence physique des backups
        for backup in restore_chain:
            backup_folder = os.path.join(self.chain_manager.vm_folder, backup['id'])

            if not os.path.exists(backup_folder):
                validation['valid'] = False
                validation['errors'].append(f"Dossier manquant: {backup['id']}")
            else:
                # Calculer la taille totale
                size_bytes = backup.get('size_bytes', 0)
                validation['total_size_gb'] += size_bytes / (1024 ** 3)

        # Avertissements
        if len(restore_chain) > 1:
            validation['warnings'].append(
                f"Restauration depuis chaîne incrémentale ({len(restore_chain)} sauvegardes). "
                "La reconstruction peut prendre du temps."
            )

        logger.info(f"[RESTORE_VM] Validation: {'✓ OK' if validation['valid'] else '✗ ERREURS'}")

        return validation
