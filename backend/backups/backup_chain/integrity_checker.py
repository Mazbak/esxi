"""
Integrity Checker - Vérification de l'intégrité des sauvegardes
Calcul et vérification de checksums (MD5, SHA256)
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class IntegrityChecker:
    """
    Vérificateur d'intégrité pour sauvegardes

    Fonctionnalités:
    - Calcul checksums MD5/SHA256
    - Vérification intégrité fichiers
    - Validation structure OVF
    - Génération rapports d'intégrité
    """

    def __init__(self, chain_manager):
        """
        Initialise le vérificateur

        Args:
            chain_manager: Instance de BackupChainManager
        """
        self.chain_manager = chain_manager
        self.vm_name = chain_manager.vm_name

        logger.info(f"[INTEGRITY] Vérificateur initialisé pour {self.vm_name}")

    def calculate_checksums(self, backup_folder: str, algorithm: str = 'sha256') -> Dict[str, Dict[str, Any]]:
        """
        Calcule les checksums de tous les fichiers d'une sauvegarde

        Args:
            backup_folder: Chemin du dossier de sauvegarde
            algorithm: 'md5' ou 'sha256'

        Returns:
            Dict: {
                'filename': {
                    'size': int,
                    'checksum': str,
                    'algorithm': str,
                    'modified': str
                }
            }
        """
        if not os.path.exists(backup_folder):
            raise FileNotFoundError(f"Dossier introuvable: {backup_folder}")

        checksums = {}

        logger.info(f"[INTEGRITY] Calcul checksums ({algorithm}) pour: {backup_folder}")

        for root, _, files in os.walk(backup_folder):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, backup_folder)

                try:
                    checksum, file_size = self._calculate_file_checksum(file_path, algorithm)

                    checksums[relative_path] = {
                        'size': file_size,
                        'checksum': checksum,
                        'algorithm': algorithm,
                        'modified': os.path.getmtime(file_path)
                    }

                    logger.debug(f"[INTEGRITY]   {relative_path}: {checksum[:16]}...")

                except Exception as e:
                    logger.error(f"[INTEGRITY] Erreur calcul {relative_path}: {e}")
                    checksums[relative_path] = {
                        'error': str(e)
                    }

        logger.info(f"[INTEGRITY] ✓ Checksums calculés: {len(checksums)} fichiers")

        return checksums

    def verify_backup_integrity(self, backup_id: str) -> Dict[str, Any]:
        """
        Vérifie l'intégrité complète d'une sauvegarde

        Args:
            backup_id: ID de la sauvegarde

        Returns:
            Dict: {
                'valid': bool,
                'total_files': int,
                'verified_files': int,
                'corrupted_files': List[str],
                'missing_files': List[str],
                'errors': List[str]
            }
        """
        backup_folder = os.path.join(self.chain_manager.vm_folder, backup_id)
        metadata_file = os.path.join(backup_folder, 'metadata.json')

        logger.info(f"[INTEGRITY] Vérification intégrité: {backup_id}")

        results = {
            'valid': True,
            'total_files': 0,
            'verified_files': 0,
            'corrupted_files': [],
            'missing_files': [],
            'errors': []
        }

        # Vérifier que le dossier existe
        if not os.path.exists(backup_folder):
            results['valid'] = False
            results['errors'].append(f"Dossier de sauvegarde introuvable: {backup_folder}")
            logger.error(f"[INTEGRITY] ✗ {results['errors'][-1]}")
            return results

        # Charger les métadonnées si elles existent
        if not os.path.exists(metadata_file):
            logger.warning(f"[INTEGRITY] Pas de metadata.json, vérification limitée")
            # Vérification basique sans métadonnées
            return self._basic_verification(backup_folder, results)

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            stored_checksums = metadata.get('checksums', {})
            results['total_files'] = len(stored_checksums)

            # Vérifier chaque fichier
            for filename, stored_info in stored_checksums.items():
                file_path = os.path.join(backup_folder, filename)

                # Vérifier existence
                if not os.path.exists(file_path):
                    results['valid'] = False
                    results['missing_files'].append(filename)
                    logger.error(f"[INTEGRITY] ✗ Fichier manquant: {filename}")
                    continue

                # Vérifier taille
                actual_size = os.path.getsize(file_path)
                expected_size = stored_info.get('size', 0)

                if actual_size != expected_size:
                    results['valid'] = False
                    results['corrupted_files'].append(filename)
                    logger.error(f"[INTEGRITY] ✗ Taille incorrecte {filename}: {actual_size} != {expected_size}")
                    continue

                # Vérifier checksum
                expected_checksum = stored_info.get('checksum')
                algorithm = stored_info.get('algorithm', 'sha256')

                actual_checksum, _ = self._calculate_file_checksum(file_path, algorithm)

                if actual_checksum != expected_checksum:
                    results['valid'] = False
                    results['corrupted_files'].append(filename)
                    logger.error(f"[INTEGRITY] ✗ Checksum invalide {filename}")
                    logger.error(f"[INTEGRITY]   Attendu: {expected_checksum}")
                    logger.error(f"[INTEGRITY]   Actuel:  {actual_checksum}")
                    continue

                # Fichier valide
                results['verified_files'] += 1
                logger.debug(f"[INTEGRITY] ✓ {filename}")

            # Résumé
            if results['valid']:
                logger.info(f"[INTEGRITY] ✓✓✓ Intégrité validée: {results['verified_files']}/{results['total_files']} fichiers")
            else:
                logger.error(f"[INTEGRITY] ✗✗✗ Intégrité compromise:")
                logger.error(f"[INTEGRITY]   Fichiers manquants: {len(results['missing_files'])}")
                logger.error(f"[INTEGRITY]   Fichiers corrompus: {len(results['corrupted_files'])}")

        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Erreur vérification: {e}")
            logger.exception(f"[INTEGRITY] Erreur vérification: {e}")

        return results

    def create_manifest(self, backup_folder: str, backup_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un fichier metadata.json avec checksums

        Args:
            backup_folder: Dossier de la sauvegarde
            backup_info: Informations supplémentaires du backup

        Returns:
            Dict: Métadonnées créées
        """
        logger.info(f"[INTEGRITY] Création manifest pour: {backup_folder}")

        # Calculer checksums
        checksums = self.calculate_checksums(backup_folder, algorithm='sha256')

        # Créer métadonnées complètes
        metadata = {
            'backup_id': backup_info.get('backup_id'),
            'vm_name': self.vm_name,
            'vm_uuid': backup_info.get('vm_uuid'),
            'backup_type': backup_info.get('type'),
            'backup_mode': backup_info.get('mode'),
            'timestamp': backup_info.get('timestamp'),
            'total_size_bytes': sum(f['size'] for f in checksums.values() if 'size' in f),
            'file_count': len(checksums),
            'checksums': checksums,
            'created_at': backup_info.get('timestamp'),
            'storage_location': backup_folder
        }

        # Sauvegarder
        metadata_file = os.path.join(backup_folder, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"[INTEGRITY] ✓ Manifest créé: {metadata_file}")

        return metadata

    def verify_all_backups(self) -> Dict[str, Any]:
        """
        Vérifie l'intégrité de toutes les sauvegardes de la chaîne

        Returns:
            Dict: Résultats globaux
        """
        chain = self.chain_manager.load_chain()

        logger.info(f"[INTEGRITY] Vérification globale: {len(chain['backups'])} sauvegardes")

        global_results = {
            'total_backups': len(chain['backups']),
            'valid_backups': 0,
            'invalid_backups': 0,
            'backup_results': {}
        }

        for backup in chain['backups']:
            backup_id = backup['id']
            logger.info(f"[INTEGRITY] Vérification {backup_id}...")

            result = self.verify_backup_integrity(backup_id)
            global_results['backup_results'][backup_id] = result

            if result['valid']:
                global_results['valid_backups'] += 1
            else:
                global_results['invalid_backups'] += 1

        # Résumé
        logger.info(f"[INTEGRITY] === RÉSUMÉ GLOBAL ===")
        logger.info(f"[INTEGRITY] Total: {global_results['total_backups']}")
        logger.info(f"[INTEGRITY] Valides: {global_results['valid_backups']}")
        logger.info(f"[INTEGRITY] Invalides: {global_results['invalid_backups']}")

        return global_results

    def _calculate_file_checksum(self, file_path: str, algorithm: str = 'sha256') -> tuple:
        """
        Calcule le checksum d'un fichier

        Args:
            file_path: Chemin du fichier
            algorithm: 'md5' ou 'sha256'

        Returns:
            (checksum: str, size: int)
        """
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Algorithme non supporté: {algorithm}")

        file_size = 0

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)  # 8KB chunks
                if not chunk:
                    break
                hasher.update(chunk)
                file_size += len(chunk)

        return hasher.hexdigest(), file_size

    def _basic_verification(self, backup_folder: str, results: Dict) -> Dict:
        """
        Vérification basique sans métadonnées

        Vérifie seulement l'existence des fichiers essentiels

        Args:
            backup_folder: Dossier de sauvegarde
            results: Dict de résultats à compléter

        Returns:
            Dict de résultats mis à jour
        """
        # Fichiers essentiels pour un backup OVF
        essential_files = ['.ovf', '.vmdk']

        found_essential = []

        for root, _, files in os.walk(backup_folder):
            for file in files:
                for ext in essential_files:
                    if file.endswith(ext):
                        found_essential.append(ext)
                        break

        if not found_essential:
            results['valid'] = False
            results['errors'].append("Aucun fichier essentiel (.ovf, .vmdk) trouvé")
            logger.error(f"[INTEGRITY] ✗ Pas de fichiers essentiels")
        else:
            logger.info(f"[INTEGRITY] ✓ Fichiers essentiels trouvés: {found_essential}")

        return results
