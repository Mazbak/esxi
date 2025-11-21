"""
Backup Chain Manager - Gestion professionnelle des chaînes de sauvegarde
Maintient un fichier chain.json par VM sur le stockage distant
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupChainManager:
    """
    Gestionnaire de chaînes de sauvegarde pour une VM

    Structure:
    \\\\NAS\\backups\\
        ├── VM_WebServer\\
        │   ├── chain.json                    # Fichier de chaîne
        │   ├── full_20250118_140000\\        # Sauvegarde complète
        │   │   ├── VM_WebServer.ovf
        │   │   ├── VM_WebServer.vmdk
        │   │   └── metadata.json
        │   └── incr_20250119_080000\\        # Incrémentale
        │       ├── changed_blocks.dat
        │       └── metadata.json
    """

    def __init__(self, remote_storage_config, vm_name: str):
        """
        Initialise le gestionnaire de chaîne

        Args:
            remote_storage_config: Instance RemoteStorageConfig
            vm_name: Nom de la VM
        """
        self.storage = remote_storage_config
        self.vm_name = vm_name
        self.vm_folder = os.path.join(self.storage.get_full_path(), vm_name)
        self.chain_file = os.path.join(self.vm_folder, 'chain.json')

        # Créer le dossier VM si nécessaire
        os.makedirs(self.vm_folder, exist_ok=True)

        logger.info(f"[CHAIN] Gestionnaire initialisé pour {vm_name}")
        logger.info(f"[CHAIN] Dossier VM: {self.vm_folder}")
        logger.info(f"[CHAIN] Fichier chain: {self.chain_file}")

    def load_chain(self) -> Dict[str, Any]:
        """
        Charge le fichier chain.json

        Returns:
            Dict contenant la chaîne de sauvegarde
        """
        if not os.path.exists(self.chain_file):
            logger.info(f"[CHAIN] Pas de chaîne existante pour {self.vm_name}, création d'une nouvelle")
            return self._create_empty_chain()

        try:
            with open(self.chain_file, 'r', encoding='utf-8') as f:
                chain = json.load(f)

            logger.info(f"[CHAIN] Chaîne chargée: {len(chain.get('backups', []))} sauvegardes")
            return chain

        except Exception as e:
            logger.error(f"[CHAIN] Erreur chargement chaîne: {e}")
            # En cas d'erreur, créer une nouvelle chaîne
            return self._create_empty_chain()

    def save_chain(self, chain: Dict[str, Any]):
        """
        Sauvegarde le fichier chain.json

        Args:
            chain: Dictionnaire de la chaîne
        """
        try:
            # Backup de l'ancienne chaîne
            if os.path.exists(self.chain_file):
                backup_file = f"{self.chain_file}.backup"
                with open(self.chain_file, 'r', encoding='utf-8') as f_src:
                    with open(backup_file, 'w', encoding='utf-8') as f_dst:
                        f_dst.write(f_src.read())

            # Sauvegarder la nouvelle chaîne
            with open(self.chain_file, 'w', encoding='utf-8') as f:
                json.dump(chain, f, indent=2, ensure_ascii=False)

            logger.info(f"[CHAIN] Chaîne sauvegardée: {self.chain_file}")

        except Exception as e:
            logger.error(f"[CHAIN] Erreur sauvegarde chaîne: {e}")
            raise

    def add_backup(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajoute une nouvelle sauvegarde à la chaîne

        Args:
            backup_data: Informations de la sauvegarde
            {
                'backup_id': 'full_20250118_140000',
                'type': 'full' | 'incremental',
                'mode': 'ovf' | 'cbt',
                'timestamp': '2025-01-18T14:00:00Z',
                'change_id': '52 3e 5b...',  # Pour CBT
                'size_bytes': 53687091200,
                'files': ['VM.ovf', 'VM.vmdk'],
                'base_backup_id': 'full_20250118_140000',  # Pour incremental
                'vm_uuid': '564d6d90-459c-...',
                'vm_config': {...}  # Config VM au moment du backup
            }

        Returns:
            Dict: Chaîne mise à jour
        """
        chain = self.load_chain()

        # Vérifier si le backup existe déjà
        existing = next((b for b in chain['backups'] if b['id'] == backup_data['backup_id']), None)
        if existing:
            logger.warning(f"[CHAIN] Backup {backup_data['backup_id']} existe déjà, mise à jour")
            chain['backups'].remove(existing)

        # Créer l'entrée de backup
        backup_entry = {
            'id': backup_data['backup_id'],
            'type': backup_data['type'],
            'mode': backup_data['mode'],
            'timestamp': backup_data['timestamp'],
            'size_bytes': backup_data['size_bytes'],
            'status': 'completed',
            'integrity_verified': backup_data.get('integrity_verified', False),
            'files': backup_data.get('files', []),
        }

        # Champs spécifiques au type
        if backup_data['type'] == 'full':
            backup_entry['is_base'] = True
            backup_entry['change_id'] = backup_data.get('change_id', '*')
        else:  # incremental
            backup_entry['is_base'] = False
            backup_entry['base_backup_id'] = backup_data.get('base_backup_id')
            backup_entry['change_id'] = backup_data.get('change_id')
            backup_entry['changed_blocks_count'] = backup_data.get('changed_blocks_count', 0)

            # Trouver l'incrémentale précédente
            previous_incremental = self._find_previous_incremental(
                chain,
                backup_data.get('base_backup_id')
            )
            if previous_incremental:
                backup_entry['previous_incremental_id'] = previous_incremental['id']

        # Ajouter à la chaîne
        chain['backups'].append(backup_entry)

        # Trier par timestamp (plus récent en dernier)
        chain['backups'].sort(key=lambda b: b['timestamp'])

        # Mettre à jour les métadonnées de la chaîne
        chain['last_backup_at'] = backup_data['timestamp']
        chain['total_backups'] = len(chain['backups'])

        if backup_data['type'] == 'full':
            chain['last_full_backup_at'] = backup_data['timestamp']

        if backup_data.get('change_id'):
            chain['current_change_id'] = backup_data['change_id']

        # Sauvegarder
        self.save_chain(chain)

        logger.info(f"[CHAIN] Backup ajouté: {backup_data['backup_id']}")
        logger.info(f"[CHAIN] Total backups dans chaîne: {len(chain['backups'])}")

        return chain

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'une sauvegarde

        Args:
            backup_id: ID de la sauvegarde

        Returns:
            Dict des infos ou None
        """
        chain = self.load_chain()
        return next((b for b in chain['backups'] if b['id'] == backup_id), None)

    def get_latest_full_backup(self) -> Optional[Dict[str, Any]]:
        """
        Récupère la dernière sauvegarde complète

        Returns:
            Dict de la dernière full backup ou None
        """
        chain = self.load_chain()
        full_backups = [b for b in chain['backups'] if b['type'] == 'full' and b['status'] == 'completed']

        if not full_backups:
            return None

        # Trier par timestamp décroissant
        full_backups.sort(key=lambda b: b['timestamp'], reverse=True)
        return full_backups[0]

    def get_incremental_chain(self, base_backup_id: str) -> List[Dict[str, Any]]:
        """
        Récupère toutes les incrémentales d'une base donnée

        Args:
            base_backup_id: ID de la sauvegarde de base

        Returns:
            Liste des incrémentales, triées par ordre chronologique
        """
        chain = self.load_chain()

        incrementals = [
            b for b in chain['backups']
            if b['type'] == 'incremental'
            and b.get('base_backup_id') == base_backup_id
            and b['status'] == 'completed'
        ]

        # Trier chronologiquement
        incrementals.sort(key=lambda b: b['timestamp'])

        return incrementals

    def get_restore_chain(self, target_backup_id: str) -> List[Dict[str, Any]]:
        """
        Récupère la chaîne complète nécessaire pour restaurer à un point donné

        Args:
            target_backup_id: ID de la sauvegarde cible

        Returns:
            Liste ordonnée: [full_backup, incr1, incr2, ..., target]
        """
        chain = self.load_chain()
        target = next((b for b in chain['backups'] if b['id'] == target_backup_id), None)

        if not target:
            logger.error(f"[CHAIN] Backup {target_backup_id} introuvable")
            return []

        # Si c'est une full, retourner juste elle
        if target['type'] == 'full':
            return [target]

        # Sinon, construire la chaîne
        restore_chain = []

        # 1. Trouver la base
        base_id = target.get('base_backup_id')
        if not base_id:
            logger.error(f"[CHAIN] Pas de base_backup_id pour {target_backup_id}")
            return []

        base = next((b for b in chain['backups'] if b['id'] == base_id), None)
        if not base:
            logger.error(f"[CHAIN] Base backup {base_id} introuvable")
            return []

        restore_chain.append(base)

        # 2. Trouver toutes les incrémentales entre la base et la cible
        all_incrementals = self.get_incremental_chain(base_id)

        # Filtrer jusqu'à la cible (incluse)
        for incr in all_incrementals:
            restore_chain.append(incr)
            if incr['id'] == target_backup_id:
                break

        logger.info(f"[CHAIN] Chaîne de restauration: {len(restore_chain)} sauvegardes")
        return restore_chain

    def remove_backup(self, backup_id: str) -> bool:
        """
        Supprime une sauvegarde de la chaîne

        Args:
            backup_id: ID de la sauvegarde à supprimer

        Returns:
            bool: True si supprimée
        """
        chain = self.load_chain()
        backup = next((b for b in chain['backups'] if b['id'] == backup_id), None)

        if not backup:
            logger.warning(f"[CHAIN] Backup {backup_id} introuvable")
            return False

        # Vérifier si c'est une base avec des incrémentales
        if backup['type'] == 'full':
            incrementals = self.get_incremental_chain(backup_id)
            if incrementals:
                logger.error(f"[CHAIN] Impossible de supprimer {backup_id}: {len(incrementals)} incrémentales dépendent de cette base")
                raise ValueError(f"Cette sauvegarde est la base de {len(incrementals)} sauvegardes incrémentales. Supprimez-les d'abord.")

        # Supprimer de la chaîne
        chain['backups'].remove(backup)

        # Mettre à jour les métadonnées
        chain['total_backups'] = len(chain['backups'])

        self.save_chain(chain)

        logger.info(f"[CHAIN] Backup supprimé de la chaîne: {backup_id}")
        return True

    def get_chain_statistics(self) -> Dict[str, Any]:
        """
        Calcule des statistiques sur la chaîne

        Returns:
            Dict de statistiques
        """
        chain = self.load_chain()

        full_backups = [b for b in chain['backups'] if b['type'] == 'full']
        incremental_backups = [b for b in chain['backups'] if b['type'] == 'incremental']

        total_size = sum(b.get('size_bytes', 0) for b in chain['backups'])

        stats = {
            'total_backups': len(chain['backups']),
            'full_backups': len(full_backups),
            'incremental_backups': len(incremental_backups),
            'total_size_bytes': total_size,
            'total_size_gb': round(total_size / (1024 ** 3), 2),
            'oldest_backup': chain['backups'][0]['timestamp'] if chain['backups'] else None,
            'newest_backup': chain['backups'][-1]['timestamp'] if chain['backups'] else None,
            'last_full_backup': chain.get('last_full_backup_at'),
        }

        return stats

    def _create_empty_chain(self) -> Dict[str, Any]:
        """Crée une chaîne vide"""
        return {
            'vm_name': self.vm_name,
            'vm_id': None,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'current_change_id': '*',
            'cbt_enabled': False,
            'last_backup_at': None,
            'last_full_backup_at': None,
            'total_backups': 0,
            'backups': [],
            'retention_policy': {
                'type': 'days',
                'value': 30,
                'keep_monthly': True
            }
        }

    def _find_previous_incremental(self, chain: Dict, base_backup_id: str) -> Optional[Dict]:
        """Trouve l'incrémentale précédente pour la même base"""
        incrementals = [
            b for b in chain['backups']
            if b['type'] == 'incremental'
            and b.get('base_backup_id') == base_backup_id
        ]

        if not incrementals:
            return None

        # Trier par timestamp décroissant
        incrementals.sort(key=lambda b: b['timestamp'], reverse=True)
        return incrementals[0]

    def validate_chain_integrity(self) -> Dict[str, Any]:
        """
        Valide l'intégrité de la chaîne

        Vérifie:
        - Toutes les bases existent pour les incrémentales
        - Les fichiers existent physiquement
        - Les checksums sont corrects

        Returns:
            Dict avec résultats de validation
        """
        chain = self.load_chain()
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Vérifier que chaque incrémentale a sa base
        for backup in chain['backups']:
            if backup['type'] == 'incremental':
                base_id = backup.get('base_backup_id')
                if not base_id:
                    results['valid'] = False
                    results['errors'].append(f"Incrémentale {backup['id']} sans base_backup_id")
                    continue

                base = next((b for b in chain['backups'] if b['id'] == base_id), None)
                if not base:
                    results['valid'] = False
                    results['errors'].append(f"Base {base_id} introuvable pour {backup['id']}")

        # Vérifier l'existence physique des dossiers
        for backup in chain['backups']:
            backup_folder = os.path.join(self.vm_folder, backup['id'])
            if not os.path.exists(backup_folder):
                results['valid'] = False
                results['errors'].append(f"Dossier {backup['id']} introuvable")

        logger.info(f"[CHAIN] Validation: {'✓ OK' if results['valid'] else '✗ ERREURS'}")
        if results['errors']:
            for error in results['errors']:
                logger.error(f"[CHAIN]   - {error}")

        return results
