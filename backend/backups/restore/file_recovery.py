"""
File Recovery Service - Récupération de fichiers individuels depuis backups
Permet d'extraire des fichiers spécifiques depuis des VMDK sauvegardés
"""

import os
import shutil
import tempfile
import logging
import platform
import subprocess
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class FileRecoveryService:
    """
    Service de récupération de fichiers depuis des backups

    Fonctionnalités:
    - Lister le contenu d'un VMDK sauvegardé
    - Extraire des fichiers/dossiers spécifiques
    - Support des chaînes incrémentales (reconstruction automatique)
    - Support multi-OS (Windows NTFS, Linux ext4, etc.)
    - Recherche de fichiers dans les backups
    """

    def __init__(self, chain_manager, integrity_checker, vmdk_restore_service):
        """
        Initialise le service de récupération de fichiers

        Args:
            chain_manager: Instance de BackupChainManager
            integrity_checker: Instance de IntegrityChecker
            vmdk_restore_service: Instance de VMDKRestoreService
        """
        self.chain_manager = chain_manager
        self.integrity_checker = integrity_checker
        self.vmdk_restore = vmdk_restore_service
        self.vm_name = chain_manager.vm_name

        # Vérifier les outils disponibles
        self._check_available_tools()

        logger.info(f"[FILE-RECOVERY] Service initialisé pour {self.vm_name}")

    def _check_available_tools(self):
        """Vérifie les outils disponibles pour le montage de VMDK"""
        self.has_guestfs = False
        self.has_7zip = False
        self.os_type = platform.system()

        # Vérifier libguestfs (Linux)
        if self.os_type == 'Linux':
            try:
                result = subprocess.run(
                    ['guestmount', '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.has_guestfs = True
                    logger.info("[FILE-RECOVERY] libguestfs disponible")
            except Exception:
                logger.warning("[FILE-RECOVERY] libguestfs non disponible")

        # Vérifier 7-Zip (Windows/Linux)
        try:
            cmd = '7z' if self.os_type == 'Windows' else '7za'
            result = subprocess.run(
                [cmd, '--help'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self.has_7zip = True
                logger.info("[FILE-RECOVERY] 7-Zip disponible")
        except Exception:
            logger.warning("[FILE-RECOVERY] 7-Zip non disponible")

    def recover_files(
        self,
        backup_id: str,
        vmdk_filename: str,
        file_paths: List[str],
        destination_folder: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Récupère des fichiers spécifiques depuis un VMDK sauvegardé

        Args:
            backup_id: ID de la sauvegarde
            vmdk_filename: Nom du VMDK contenant les fichiers
            file_paths: Liste des chemins de fichiers à récupérer (ex: ['/etc/nginx/nginx.conf', 'C:\\Users\\Admin\\Documents\\file.txt'])
            destination_folder: Dossier de destination local
            progress_callback: Fonction de callback pour progression

        Returns:
            Dict avec résultats de la récupération
        """
        logger.info(f"[FILE-RECOVERY] === DÉBUT RÉCUPÉRATION FICHIERS ===")
        logger.info(f"[FILE-RECOVERY] Backup: {backup_id}")
        logger.info(f"[FILE-RECOVERY] VMDK: {vmdk_filename}")
        logger.info(f"[FILE-RECOVERY] Fichiers: {len(file_paths)}")

        results = {
            'success': False,
            'recovered_files': [],
            'failed_files': [],
            'destination': destination_folder,
            'errors': []
        }

        temp_vmdk = None
        mount_point = None

        try:
            # 1. Validation
            if progress_callback:
                progress_callback(5, "Validation...")

            if not file_paths:
                results['errors'].append("Aucun fichier spécifié")
                return results

            # Créer le dossier de destination
            os.makedirs(destination_folder, exist_ok=True)

            # 2. Reconstruire le VMDK si nécessaire
            if progress_callback:
                progress_callback(10, "Reconstruction du VMDK...")

            temp_vmdk = self._prepare_vmdk_for_recovery(
                backup_id,
                vmdk_filename,
                progress_callback
            )

            if not temp_vmdk:
                results['errors'].append("Échec reconstruction VMDK")
                return results

            # 3. Monter le VMDK
            if progress_callback:
                progress_callback(40, "Montage du VMDK...")

            mount_point = self._mount_vmdk(temp_vmdk)

            if not mount_point:
                results['errors'].append("Échec montage VMDK")
                return results

            logger.info(f"[FILE-RECOVERY] VMDK monté: {mount_point}")

            # 4. Extraire chaque fichier
            total_files = len(file_paths)

            for idx, file_path in enumerate(file_paths, 1):
                progress = 50 + (idx / total_files * 40)
                if progress_callback:
                    progress_callback(
                        int(progress),
                        f"Extraction {idx}/{total_files}: {os.path.basename(file_path)}..."
                    )

                success = self._extract_file(
                    mount_point,
                    file_path,
                    destination_folder,
                    results
                )

                if success:
                    results['recovered_files'].append(file_path)
                else:
                    results['failed_files'].append(file_path)

            # 5. Résumé
            results['success'] = len(results['recovered_files']) > 0

            if progress_callback:
                progress_callback(100, "Récupération terminée")

            logger.info(f"[FILE-RECOVERY] ✓ Récupérés: {len(results['recovered_files'])}")
            logger.info(f"[FILE-RECOVERY] ✗ Échecs: {len(results['failed_files'])}")

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur: {e}", exc_info=True)
            results['errors'].append(str(e))

        finally:
            # Démonter et nettoyer
            if mount_point:
                self._unmount_vmdk(mount_point)

            if temp_vmdk and os.path.exists(temp_vmdk):
                try:
                    os.remove(temp_vmdk)
                    logger.info("[FILE-RECOVERY] VMDK temporaire supprimé")
                except Exception as e:
                    logger.warning(f"[FILE-RECOVERY] Erreur suppression temp VMDK: {e}")

        return results

    def _prepare_vmdk_for_recovery(
        self,
        backup_id: str,
        vmdk_filename: str,
        progress_callback: Optional[Callable]
    ) -> Optional[str]:
        """
        Prépare un VMDK pour la récupération (reconstruction si nécessaire)

        Args:
            backup_id: ID de la sauvegarde
            vmdk_filename: Nom du VMDK
            progress_callback: Callback de progression

        Returns:
            Chemin du VMDK temporaire ou None
        """
        restore_chain = self.chain_manager.get_restore_chain(backup_id)

        if not restore_chain:
            logger.error("[FILE-RECOVERY] Chaîne de restauration vide")
            return None

        # Si c'est une full backup simple, utiliser directement
        if len(restore_chain) == 1 and restore_chain[0]['type'] == 'full':
            base_folder = os.path.join(
                self.chain_manager.vm_folder,
                restore_chain[0]['id']
            )
            source_vmdk = os.path.join(base_folder, vmdk_filename)

            if not os.path.exists(source_vmdk):
                logger.error(f"[FILE-RECOVERY] VMDK introuvable: {source_vmdk}")
                return None

            # Copier vers temp
            temp_dir = tempfile.gettempdir()
            temp_vmdk = os.path.join(temp_dir, f"recovery_{vmdk_filename}")

            shutil.copy2(source_vmdk, temp_vmdk)
            logger.info(f"[FILE-RECOVERY] VMDK copié: {temp_vmdk}")

            return temp_vmdk

        # Sinon, reconstruire depuis la chaîne
        logger.info(f"[FILE-RECOVERY] Reconstruction depuis chaîne de {len(restore_chain)} backups")

        temp_dir = tempfile.mkdtemp(prefix='file_recovery_')
        temp_vmdk = os.path.join(temp_dir, vmdk_filename)

        try:
            # Copier la base
            base_folder = os.path.join(
                self.chain_manager.vm_folder,
                restore_chain[0]['id']
            )
            source_vmdk = os.path.join(base_folder, vmdk_filename)

            shutil.copy2(source_vmdk, temp_vmdk)

            # Appliquer les incrémentales
            total_incrementals = len(restore_chain) - 1

            for idx, incremental in enumerate(restore_chain[1:], 1):
                progress = 15 + (idx / total_incrementals * 25)
                if progress_callback:
                    progress_callback(
                        int(progress),
                        f"Application incrémentale {idx}/{total_incrementals}..."
                    )

                success = self.vmdk_restore._apply_incremental_to_vmdk(
                    temp_vmdk,
                    incremental,
                    vmdk_filename
                )

                if not success:
                    logger.error(f"[FILE-RECOVERY] Échec application incrémentale {incremental['id']}")
                    return None

            logger.info(f"[FILE-RECOVERY] ✓ VMDK reconstruit: {temp_vmdk}")
            return temp_vmdk

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur reconstruction: {e}")
            return None

    def _mount_vmdk(self, vmdk_path: str) -> Optional[str]:
        """
        Monte un VMDK et retourne le point de montage

        Args:
            vmdk_path: Chemin du VMDK

        Returns:
            Point de montage ou None
        """
        if self.os_type == 'Linux' and self.has_guestfs:
            return self._mount_vmdk_linux(vmdk_path)
        elif self.has_7zip:
            return self._mount_vmdk_7zip(vmdk_path)
        else:
            logger.error("[FILE-RECOVERY] Aucun outil de montage disponible")
            logger.error("[FILE-RECOVERY] Installez libguestfs (Linux) ou 7-Zip")
            return None

    def _mount_vmdk_linux(self, vmdk_path: str) -> Optional[str]:
        """Monte un VMDK avec guestmount (Linux)"""
        mount_point = tempfile.mkdtemp(prefix='vmdk_mount_')

        try:
            logger.info(f"[FILE-RECOVERY] Montage avec guestmount: {mount_point}")

            cmd = [
                'guestmount',
                '-a', vmdk_path,
                '-i',  # Auto-detect partitions
                '--ro',  # Read-only
                mount_point
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logger.error(f"[FILE-RECOVERY] Erreur guestmount: {result.stderr}")
                os.rmdir(mount_point)
                return None

            logger.info(f"[FILE-RECOVERY] ✓ VMDK monté: {mount_point}")
            return mount_point

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur montage Linux: {e}")
            if os.path.exists(mount_point):
                os.rmdir(mount_point)
            return None

    def _mount_vmdk_7zip(self, vmdk_path: str) -> Optional[str]:
        """Extrait le contenu d'un VMDK avec 7-Zip"""
        extract_dir = tempfile.mkdtemp(prefix='vmdk_extract_')

        try:
            logger.info(f"[FILE-RECOVERY] Extraction avec 7-Zip: {extract_dir}")

            cmd = '7z' if self.os_type == 'Windows' else '7za'

            result = subprocess.run(
                [cmd, 'x', vmdk_path, f'-o{extract_dir}', '-y'],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                logger.error(f"[FILE-RECOVERY] Erreur 7-Zip: {result.stderr}")
                shutil.rmtree(extract_dir)
                return None

            logger.info(f"[FILE-RECOVERY] ✓ VMDK extrait: {extract_dir}")
            return extract_dir

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur extraction 7-Zip: {e}")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            return None

    def _unmount_vmdk(self, mount_point: str):
        """Démonte un VMDK"""
        try:
            if self.os_type == 'Linux' and self.has_guestfs:
                subprocess.run(
                    ['guestunmount', mount_point],
                    capture_output=True,
                    timeout=30
                )
                os.rmdir(mount_point)
                logger.info(f"[FILE-RECOVERY] VMDK démonté: {mount_point}")
            else:
                # 7-Zip: juste supprimer le répertoire d'extraction
                shutil.rmtree(mount_point)
                logger.info(f"[FILE-RECOVERY] Répertoire extrait supprimé: {mount_point}")

        except Exception as e:
            logger.warning(f"[FILE-RECOVERY] Erreur démontage: {e}")

    def _extract_file(
        self,
        mount_point: str,
        file_path: str,
        destination_folder: str,
        results: Dict
    ) -> bool:
        """
        Extrait un fichier depuis le VMDK monté

        Args:
            mount_point: Point de montage du VMDK
            file_path: Chemin du fichier dans le VMDK
            destination_folder: Dossier de destination
            results: Dict de résultats

        Returns:
            bool: True si succès
        """
        try:
            # Normaliser le chemin (supprimer les / ou \ de début)
            normalized_path = file_path.lstrip('/\\')

            # Convertir les backslash en forward slash
            normalized_path = normalized_path.replace('\\', '/')

            # Construire le chemin complet dans le montage
            source_path = os.path.join(mount_point, normalized_path)

            logger.info(f"[FILE-RECOVERY] Extraction: {file_path}")
            logger.info(f"[FILE-RECOVERY] Source: {source_path}")

            if not os.path.exists(source_path):
                logger.warning(f"[FILE-RECOVERY] Fichier introuvable: {source_path}")
                results['errors'].append(f"Fichier introuvable: {file_path}")
                return False

            # Créer la structure de répertoires dans la destination
            relative_dir = os.path.dirname(normalized_path)
            dest_dir = os.path.join(destination_folder, relative_dir)
            os.makedirs(dest_dir, exist_ok=True)

            # Copier le fichier
            dest_path = os.path.join(destination_folder, normalized_path)

            if os.path.isdir(source_path):
                # Copier un répertoire
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                logger.info(f"[FILE-RECOVERY] ✓ Répertoire copié: {dest_path}")
            else:
                # Copier un fichier
                shutil.copy2(source_path, dest_path)
                logger.info(f"[FILE-RECOVERY] ✓ Fichier copié: {dest_path}")

            return True

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur extraction {file_path}: {e}")
            results['errors'].append(f"Erreur extraction {file_path}: {e}")
            return False

    def list_files_in_backup(
        self,
        backup_id: str,
        vmdk_filename: str,
        directory_path: str = '/',
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Liste les fichiers disponibles dans un VMDK sauvegardé

        Args:
            backup_id: ID de la sauvegarde
            vmdk_filename: Nom du VMDK
            directory_path: Chemin du répertoire à lister
            progress_callback: Callback de progression

        Returns:
            Dict avec la liste des fichiers
        """
        logger.info(f"[FILE-RECOVERY] Listage: {vmdk_filename}:{directory_path}")

        results = {
            'success': False,
            'files': [],
            'directories': [],
            'current_path': directory_path,
            'errors': []
        }

        temp_vmdk = None
        mount_point = None

        try:
            # Préparer le VMDK
            if progress_callback:
                progress_callback(20, "Préparation du VMDK...")

            temp_vmdk = self._prepare_vmdk_for_recovery(
                backup_id,
                vmdk_filename,
                progress_callback
            )

            if not temp_vmdk:
                results['errors'].append("Échec préparation VMDK")
                return results

            # Monter le VMDK
            if progress_callback:
                progress_callback(60, "Montage du VMDK...")

            mount_point = self._mount_vmdk(temp_vmdk)

            if not mount_point:
                results['errors'].append("Échec montage VMDK")
                return results

            # Lister le contenu
            if progress_callback:
                progress_callback(80, "Listage des fichiers...")

            normalized_path = directory_path.lstrip('/\\').replace('\\', '/')
            full_path = os.path.join(mount_point, normalized_path)

            if not os.path.exists(full_path):
                results['errors'].append(f"Répertoire introuvable: {directory_path}")
                return results

            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                entry_relative = os.path.join(directory_path, entry).replace('\\', '/')

                if os.path.isdir(entry_path):
                    results['directories'].append({
                        'name': entry,
                        'path': entry_relative
                    })
                else:
                    size = os.path.getsize(entry_path)
                    results['files'].append({
                        'name': entry,
                        'path': entry_relative,
                        'size_bytes': size,
                        'size_mb': round(size / (1024 * 1024), 2)
                    })

            results['success'] = True

            if progress_callback:
                progress_callback(100, "Listage terminé")

            logger.info(f"[FILE-RECOVERY] ✓ {len(results['files'])} fichiers, {len(results['directories'])} répertoires")

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur listage: {e}", exc_info=True)
            results['errors'].append(str(e))

        finally:
            if mount_point:
                self._unmount_vmdk(mount_point)

            if temp_vmdk and os.path.exists(temp_vmdk):
                try:
                    os.remove(temp_vmdk)
                except Exception as e:
                    logger.warning(f"[FILE-RECOVERY] Erreur suppression temp: {e}")

        return results

    def search_files_in_backup(
        self,
        backup_id: str,
        vmdk_filename: str,
        search_pattern: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Recherche des fichiers dans un backup par pattern

        Args:
            backup_id: ID de la sauvegarde
            vmdk_filename: Nom du VMDK
            search_pattern: Pattern de recherche (ex: '*.conf', 'nginx*')
            progress_callback: Callback de progression

        Returns:
            Dict avec résultats de la recherche
        """
        logger.info(f"[FILE-RECOVERY] Recherche: {search_pattern} dans {vmdk_filename}")

        results = {
            'success': False,
            'matches': [],
            'search_pattern': search_pattern,
            'errors': []
        }

        temp_vmdk = None
        mount_point = None

        try:
            # Préparer et monter
            if progress_callback:
                progress_callback(20, "Préparation du VMDK...")

            temp_vmdk = self._prepare_vmdk_for_recovery(backup_id, vmdk_filename, progress_callback)
            if not temp_vmdk:
                results['errors'].append("Échec préparation VMDK")
                return results

            if progress_callback:
                progress_callback(50, "Montage du VMDK...")

            mount_point = self._mount_vmdk(temp_vmdk)
            if not mount_point:
                results['errors'].append("Échec montage VMDK")
                return results

            # Recherche récursive
            if progress_callback:
                progress_callback(70, f"Recherche de {search_pattern}...")

            from fnmatch import fnmatch

            for root, dirs, files in os.walk(mount_point):
                for filename in files:
                    if fnmatch(filename, search_pattern):
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(full_path, mount_point)
                        size = os.path.getsize(full_path)

                        results['matches'].append({
                            'filename': filename,
                            'path': '/' + relative_path.replace('\\', '/'),
                            'size_bytes': size,
                            'size_kb': round(size / 1024, 2)
                        })

            results['success'] = True

            if progress_callback:
                progress_callback(100, f"Recherche terminée: {len(results['matches'])} résultats")

            logger.info(f"[FILE-RECOVERY] ✓ {len(results['matches'])} fichiers trouvés")

        except Exception as e:
            logger.error(f"[FILE-RECOVERY] Erreur recherche: {e}", exc_info=True)
            results['errors'].append(str(e))

        finally:
            if mount_point:
                self._unmount_vmdk(mount_point)

            if temp_vmdk and os.path.exists(temp_vmdk):
                try:
                    os.remove(temp_vmdk)
                except Exception:
                    pass

        return results
