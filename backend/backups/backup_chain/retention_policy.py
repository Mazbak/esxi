"""
Retention Policy Manager - Gestion automatique de la rétention des sauvegardes
Applique des politiques de nettoyage (30 jours, conservation mensuelle, etc.)
"""

import os
import shutil
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RetentionPolicyManager:
    """
    Gestionnaire de politiques de rétention

    Politiques supportées:
    - days: Conserver X jours (ex: 30 jours)
    - count: Conserver X sauvegardes (ex: 10 dernières)
    - custom: Politique personnalisée avec règles complexes

    Options:
    - keep_monthly: Conserver une sauvegarde par mois même si ancienne
    - keep_weekly: Conserver une sauvegarde par semaine
    - keep_full_always: Ne jamais supprimer les full backups
    """

    def __init__(self, chain_manager):
        """
        Initialise le gestionnaire de rétention

        Args:
            chain_manager: Instance de BackupChainManager
        """
        self.chain_manager = chain_manager
        self.vm_name = chain_manager.vm_name

        logger.info(f"[RETENTION] Gestionnaire initialisé pour {self.vm_name}")

    def apply_policy(self, policy: Dict[str, Any] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Applique la politique de rétention

        Args:
            policy: Dictionnaire de politique ou None pour utiliser celle de la chaîne
            dry_run: Si True, simule sans supprimer

        Returns:
            Dict avec résultats: {
                'deleted_count': int,
                'deleted_backups': List[str],
                'kept_count': int,
                'freed_space_bytes': int,
                'errors': List[str]
            }
        """
        chain = self.chain_manager.load_chain()

        # Utiliser la politique de la chaîne si non fournie
        if policy is None:
            policy = chain.get('retention_policy', {
                'type': 'days',
                'value': 30,
                'keep_monthly': True
            })

        logger.info(f"[RETENTION] Application politique: {policy['type']} = {policy.get('value')}")
        logger.info(f"[RETENTION] Options: keep_monthly={policy.get('keep_monthly', False)}")

        results = {
            'deleted_count': 0,
            'deleted_backups': [],
            'kept_count': 0,
            'freed_space_bytes': 0,
            'errors': []
        }

        # Identifier les sauvegardes à supprimer
        backups_to_delete = self._identify_backups_to_delete(chain, policy)

        if not backups_to_delete:
            logger.info("[RETENTION] Aucune sauvegarde à supprimer")
            results['kept_count'] = len(chain['backups'])
            return results

        logger.info(f"[RETENTION] {len(backups_to_delete)} sauvegardes à supprimer")

        # Supprimer les sauvegardes
        for backup in backups_to_delete:
            try:
                if dry_run:
                    logger.info(f"[RETENTION] [DRY-RUN] Supprimerait: {backup['id']}")
                else:
                    success = self._delete_backup_physical(backup)
                    if success:
                        self.chain_manager.remove_backup(backup['id'])
                        results['deleted_backups'].append(backup['id'])
                        results['deleted_count'] += 1
                        results['freed_space_bytes'] += backup.get('size_bytes', 0)
                        logger.info(f"[RETENTION] ✓ Supprimé: {backup['id']}")

            except Exception as e:
                error_msg = f"Erreur suppression {backup['id']}: {e}"
                logger.error(f"[RETENTION] {error_msg}")
                results['errors'].append(error_msg)

        # Compter les sauvegardes conservées
        results['kept_count'] = len(chain['backups']) - results['deleted_count']

        # Logs de résumé
        freed_gb = results['freed_space_bytes'] / (1024 ** 3)
        logger.info(f"[RETENTION] === RÉSUMÉ ===")
        logger.info(f"[RETENTION] Supprimées: {results['deleted_count']}")
        logger.info(f"[RETENTION] Conservées: {results['kept_count']}")
        logger.info(f"[RETENTION] Espace libéré: {freed_gb:.2f} GB")

        if results['errors']:
            logger.warning(f"[RETENTION] Erreurs: {len(results['errors'])}")

        return results

    def _identify_backups_to_delete(self, chain: Dict, policy: Dict) -> List[Dict]:
        """
        Identifie les sauvegardes à supprimer selon la politique

        Args:
            chain: Chaîne de sauvegarde
            policy: Politique de rétention

        Returns:
            Liste des sauvegardes à supprimer
        """
        all_backups = chain['backups']

        if not all_backups:
            return []

        # Déterminer la date limite selon le type de politique
        if policy['type'] == 'days':
            cutoff_date = datetime.utcnow() - timedelta(days=policy['value'])
            cutoff_date_str = cutoff_date.isoformat() + 'Z'

            # Trouver les sauvegardes anciennes
            candidates = [
                b for b in all_backups
                if b['timestamp'] < cutoff_date_str
            ]

        elif policy['type'] == 'count':
            # Conserver seulement les X dernières
            keep_count = policy['value']
            if len(all_backups) <= keep_count:
                return []

            # Trier par timestamp décroissant
            sorted_backups = sorted(all_backups, key=lambda b: b['timestamp'], reverse=True)
            candidates = sorted_backups[keep_count:]

        else:
            logger.warning(f"[RETENTION] Type de politique non supporté: {policy['type']}")
            return []

        # Appliquer les filtres de conservation
        backups_to_delete = []

        for backup in candidates:
            # Vérifier si doit être conservée
            if self._should_keep_backup(backup, policy, all_backups):
                logger.debug(f"[RETENTION] Conservation: {backup['id']} (règle spéciale)")
                continue

            backups_to_delete.append(backup)

        return backups_to_delete

    def _should_keep_backup(self, backup: Dict, policy: Dict, all_backups: List[Dict]) -> bool:
        """
        Détermine si une sauvegarde doit être conservée malgré la politique

        Args:
            backup: Sauvegarde à évaluer
            policy: Politique de rétention
            all_backups: Toutes les sauvegardes

        Returns:
            True si doit être conservée
        """
        # Option: Conserver les full backups avec des incrémentales actives
        if backup['type'] == 'full':
            # Vérifier si des incrémentales dépendent de cette base
            incrementals = [
                b for b in all_backups
                if b['type'] == 'incremental'
                and b.get('base_backup_id') == backup['id']
            ]

            if incrementals:
                # Si des incrémentales existent et ne sont pas toutes à supprimer
                # alors conserver la base
                recent_incrementals = [
                    i for i in incrementals
                    if i['timestamp'] >= (datetime.utcnow() - timedelta(days=policy.get('value', 30))).isoformat()
                ]

                if recent_incrementals:
                    logger.debug(f"[RETENTION] Conservation base {backup['id']}: {len(recent_incrementals)} incrémentales actives")
                    return True

        # Option: Conserver une sauvegarde mensuelle
        if policy.get('keep_monthly', False):
            backup_date = datetime.fromisoformat(backup['timestamp'].replace('Z', '+00:00'))

            # Vérifier si c'est la première sauvegarde du mois
            same_month_backups = [
                b for b in all_backups
                if datetime.fromisoformat(b['timestamp'].replace('Z', '+00:00')).year == backup_date.year
                and datetime.fromisoformat(b['timestamp'].replace('Z', '+00:00')).month == backup_date.month
            ]

            # Trier et prendre la première du mois
            same_month_backups.sort(key=lambda b: b['timestamp'])
            if same_month_backups and same_month_backups[0]['id'] == backup['id']:
                logger.debug(f"[RETENTION] Conservation mensuelle: {backup['id']}")
                return True

        # Option: Conserver une sauvegarde hebdomadaire
        if policy.get('keep_weekly', False):
            backup_date = datetime.fromisoformat(backup['timestamp'].replace('Z', '+00:00'))

            # Vérifier si c'est la première sauvegarde de la semaine
            week_start = backup_date - timedelta(days=backup_date.weekday())
            week_end = week_start + timedelta(days=7)

            same_week_backups = [
                b for b in all_backups
                if week_start <= datetime.fromisoformat(b['timestamp'].replace('Z', '+00:00')) < week_end
            ]

            same_week_backups.sort(key=lambda b: b['timestamp'])
            if same_week_backups and same_week_backups[0]['id'] == backup['id']:
                logger.debug(f"[RETENTION] Conservation hebdomadaire: {backup['id']}")
                return True

        return False

    def _delete_backup_physical(self, backup: Dict) -> bool:
        """
        Supprime physiquement les fichiers d'une sauvegarde

        Args:
            backup: Sauvegarde à supprimer

        Returns:
            True si suppression réussie
        """
        backup_folder = os.path.join(self.chain_manager.vm_folder, backup['id'])

        if not os.path.exists(backup_folder):
            logger.warning(f"[RETENTION] Dossier introuvable: {backup_folder}")
            return False

        try:
            # Supprimer récursivement
            shutil.rmtree(backup_folder)
            logger.info(f"[RETENTION] Dossier supprimé: {backup_folder}")
            return True

        except Exception as e:
            logger.error(f"[RETENTION] Erreur suppression {backup_folder}: {e}")
            raise

    def get_retention_preview(self, policy: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prévisualise l'application de la politique sans supprimer

        Args:
            policy: Politique à prévisualiser

        Returns:
            Dict avec aperçu des suppressions
        """
        results = self.apply_policy(policy=policy, dry_run=True)

        chain = self.chain_manager.load_chain()

        preview = {
            'current_count': len(chain['backups']),
            'will_delete': results['deleted_count'],
            'will_keep': results['kept_count'],
            'freed_space_gb': round(results['freed_space_bytes'] / (1024 ** 3), 2),
            'backups_to_delete': results['deleted_backups'],
            'policy': policy or chain.get('retention_policy')
        }

        return preview

    def update_chain_policy(self, policy: Dict[str, Any]):
        """
        Met à jour la politique de rétention dans la chaîne

        Args:
            policy: Nouvelle politique
        """
        chain = self.chain_manager.load_chain()
        chain['retention_policy'] = policy
        self.chain_manager.save_chain(chain)

        logger.info(f"[RETENTION] Politique mise à jour: {policy}")
