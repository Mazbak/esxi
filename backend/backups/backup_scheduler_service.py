"""
Backup Scheduler Service - Gestion intelligente des planifications Full + Incremental

Ce service détermine automatiquement le type de backup à exécuter (Full ou Incremental)
en fonction de la configuration de planification et de l'historique des backups.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from django.utils import timezone

from backups.models import BackupJob, BackupSchedule, RemoteStorageConfig
from backups.backup_chain.chain_manager import BackupChainManager

logger = logging.getLogger(__name__)


class BackupSchedulerService:
    """
    Service de planification intelligente des backups

    Stratégies supportées:
    - full_only: Toujours faire des Full backups
    - incremental_only: Toujours faire des Incremental (si base existe)
    - full_weekly: Full tous les X jours, Incremental le reste du temps
    - smart: Décision automatique basée sur la taille/nombre d'incrementaux
    """

    def __init__(self, schedule: BackupSchedule):
        """
        Initialise le service de planification

        Args:
            schedule: Instance de BackupSchedule
        """
        self.schedule = schedule
        self.vm = schedule.virtual_machine

        # Initialiser le chain manager si possible
        self.chain_manager = None
        self._init_chain_manager()

    def _init_chain_manager(self):
        """Initialise le BackupChainManager"""
        try:
            # Récupérer le remote storage
            remote_storage = None

            if hasattr(self.schedule, 'remote_storage') and self.schedule.remote_storage:
                remote_storage = self.schedule.remote_storage
            else:
                try:
                    remote_storage = RemoteStorageConfig.objects.get(
                        is_default=True,
                        is_active=True
                    )
                except RemoteStorageConfig.DoesNotExist:
                    logger.warning("[SCHEDULER] Aucun remote storage configuré")
                    return

            if remote_storage:
                self.chain_manager = BackupChainManager(remote_storage, self.vm.name)
                logger.info(f"[SCHEDULER] Chain manager initialisé pour {self.vm.name}")

        except Exception as e:
            logger.error(f"[SCHEDULER] Erreur initialisation chain manager: {e}", exc_info=True)

    def determine_backup_type(self) -> Tuple[str, str]:
        """
        Détermine le type et le mode de backup à exécuter

        Returns:
            Tuple (job_type, backup_mode) où:
            - job_type: 'full' ou 'incremental'
            - backup_mode: 'ovf' ou 'cbt'
        """
        logger.info(f"[SCHEDULER] Détermination du type de backup pour {self.vm.name}")

        # Récupérer la stratégie de planification
        strategy = getattr(self.schedule, 'backup_strategy', 'full_weekly')
        logger.info(f"[SCHEDULER] Stratégie: {strategy}")

        # Déterminer le mode de backup (ovf ou cbt)
        backup_mode = self._determine_backup_mode()

        # Déterminer le type de backup selon la stratégie
        if strategy == 'full_only':
            job_type = 'full'
            logger.info("[SCHEDULER] Stratégie full_only → Full backup")

        elif strategy == 'incremental_only':
            job_type = self._check_incremental_possible()
            logger.info(f"[SCHEDULER] Stratégie incremental_only → {job_type}")

        elif strategy == 'full_weekly':
            job_type = self._full_weekly_logic()
            logger.info(f"[SCHEDULER] Stratégie full_weekly → {job_type}")

        elif strategy == 'smart':
            job_type = self._smart_logic()
            logger.info(f"[SCHEDULER] Stratégie smart → {job_type}")

        else:
            # Par défaut: full_weekly
            job_type = self._full_weekly_logic()
            logger.info(f"[SCHEDULER] Stratégie par défaut (full_weekly) → {job_type}")

        logger.info(f"[SCHEDULER] ✓ Décision finale: {job_type} ({backup_mode})")

        return job_type, backup_mode

    def _determine_backup_mode(self) -> str:
        """
        Détermine le mode de backup (ovf ou cbt)

        Returns:
            'ovf' ou 'cbt'
        """
        # Vérifier si CBT est activé pour la VM
        if hasattr(self.vm, 'is_cbt_enabled') and self.vm.is_cbt_enabled:
            logger.info("[SCHEDULER] CBT activé pour la VM → Mode CBT")
            return 'cbt'
        else:
            logger.info("[SCHEDULER] CBT non activé → Mode OVF")
            return 'ovf'

    def _check_incremental_possible(self) -> str:
        """
        Vérifie si un backup incrémental est possible

        Returns:
            'incremental' si possible, sinon 'full'
        """
        if not self.chain_manager:
            logger.warning("[SCHEDULER] Pas de chain manager → Full backup requis")
            return 'full'

        # Vérifier s'il existe une base full
        latest_full = self.chain_manager.get_latest_full_backup()

        if not latest_full:
            logger.info("[SCHEDULER] Aucune base full trouvée → Full backup requis")
            return 'full'

        logger.info(f"[SCHEDULER] Base full trouvée: {latest_full['id']} → Incremental possible")
        return 'incremental'

    def _full_weekly_logic(self) -> str:
        """
        Logique Full hebdomadaire + Incremental quotidien

        Stratégie:
        - Full backup tous les X jours (défini par full_backup_interval, défaut 7 jours)
        - Incremental le reste du temps (si base existe)

        Returns:
            'full' ou 'incremental'
        """
        # Récupérer l'intervalle de full backup (défaut 7 jours)
        full_interval_days = getattr(self.schedule, 'full_backup_interval_days', 7)

        if not self.chain_manager:
            logger.info("[SCHEDULER] Pas de chain manager → Full backup")
            return 'full'

        # Récupérer la dernière full backup
        latest_full = self.chain_manager.get_latest_full_backup()

        if not latest_full:
            logger.info("[SCHEDULER] Aucune full backup → Full backup requis")
            return 'full'

        # Calculer le temps écoulé depuis la dernière full
        last_full_date = datetime.fromisoformat(latest_full['timestamp'].replace('Z', '+00:00'))
        now = timezone.now()
        days_since_full = (now - last_full_date).days

        logger.info(f"[SCHEDULER] Jours depuis dernière full: {days_since_full}/{full_interval_days}")

        if days_since_full >= full_interval_days:
            logger.info(f"[SCHEDULER] {days_since_full} jours écoulés → Full backup")
            return 'full'
        else:
            logger.info(f"[SCHEDULER] {days_since_full} jours écoulés → Incremental backup")
            return 'incremental'

    def _smart_logic(self) -> str:
        """
        Logique intelligente basée sur plusieurs critères

        Critères:
        - Nombre d'incrementaux depuis la dernière full (max 10)
        - Taille cumulée des incrementaux vs full (> 50% de la full)
        - Temps écoulé depuis la dernière full (max 14 jours)

        Returns:
            'full' ou 'incremental'
        """
        if not self.chain_manager:
            return 'full'

        latest_full = self.chain_manager.get_latest_full_backup()

        if not latest_full:
            logger.info("[SCHEDULER] Aucune full → Full backup")
            return 'full'

        # Critère 1: Nombre d'incrementaux
        incrementals = self.chain_manager.get_incremental_chain(latest_full['id'])
        num_incrementals = len(incrementals)

        logger.info(f"[SCHEDULER] Nombre d'incrementaux: {num_incrementals}")

        if num_incrementals >= 10:
            logger.info("[SCHEDULER] Trop d'incrementaux (>= 10) → Full backup")
            return 'full'

        # Critère 2: Temps écoulé
        last_full_date = datetime.fromisoformat(latest_full['timestamp'].replace('Z', '+00:00'))
        now = timezone.now()
        days_since_full = (now - last_full_date).days

        logger.info(f"[SCHEDULER] Jours depuis full: {days_since_full}")

        if days_since_full >= 14:
            logger.info("[SCHEDULER] Trop ancien (>= 14 jours) → Full backup")
            return 'full'

        # Critère 3: Taille cumulée (optionnel)
        full_size = latest_full.get('size_bytes', 0)
        incremental_sizes = sum(incr.get('size_bytes', 0) for incr in incrementals)

        if full_size > 0:
            ratio = incremental_sizes / full_size
            logger.info(f"[SCHEDULER] Ratio incrementaux/full: {ratio:.2%}")

            if ratio > 0.5:
                logger.info("[SCHEDULER] Incrementaux > 50% de la full → Full backup")
                return 'full'

        logger.info("[SCHEDULER] Tous les critères OK → Incremental backup")
        return 'incremental'

    def create_scheduled_backup_job(self) -> Optional[BackupJob]:
        """
        Crée un BackupJob basé sur la planification

        Returns:
            BackupJob créé ou None si erreur
        """
        try:
            # Déterminer le type et le mode
            job_type, backup_mode = self.determine_backup_type()

            logger.info(f"[SCHEDULER] Création du job: {job_type} ({backup_mode})")

            # Récupérer la configuration de backup
            backup_config = self.schedule.backup_configuration

            # Créer le BackupJob
            job = BackupJob.objects.create(
                virtual_machine=self.vm,
                backup_configuration=backup_config,
                job_type=job_type,
                backup_mode=backup_mode,
                backup_location=backup_config.backup_location if backup_config else None,
                status='pending',
                remote_storage=getattr(self.schedule, 'remote_storage', None),
                scheduled_by=self.schedule
            )

            logger.info(f"[SCHEDULER] ✓ Job créé: {job.id} ({job_type}/{backup_mode})")

            return job

        except Exception as e:
            logger.error(f"[SCHEDULER] Erreur création job: {e}", exc_info=True)
            return None

    def should_run_now(self) -> bool:
        """
        Vérifie si le schedule doit être exécuté maintenant

        Returns:
            bool: True si le backup doit être exécuté
        """
        if not self.schedule.is_enabled:
            logger.info(f"[SCHEDULER] Schedule {self.schedule.id} désactivé")
            return False

        now = timezone.now()

        # Vérifier la dernière exécution
        if self.schedule.last_run_at:
            # Calculer le temps écoulé depuis la dernière exécution
            time_since_last = now - self.schedule.last_run_at

            # Vérifier l'intervalle minimum (éviter les doubles exécutions)
            min_interval = timedelta(hours=1)

            if time_since_last < min_interval:
                logger.info(
                    f"[SCHEDULER] Dernière exécution il y a {time_since_last.total_seconds() / 60:.1f} min "
                    f"→ Attente de {min_interval}"
                )
                return False

        # Vérifier le schedule (cron-like ou interval)
        # Pour l'instant, simple vérification basée sur l'intervalle
        if hasattr(self.schedule, 'interval_hours'):
            interval_hours = self.schedule.interval_hours

            if self.schedule.last_run_at:
                hours_since_last = (now - self.schedule.last_run_at).total_seconds() / 3600

                if hours_since_last >= interval_hours:
                    logger.info(f"[SCHEDULER] {hours_since_last:.1f}h écoulées → Exécution")
                    return True
                else:
                    logger.info(f"[SCHEDULER] {hours_since_last:.1f}h/{interval_hours}h → Attente")
                    return False
            else:
                # Première exécution
                logger.info("[SCHEDULER] Première exécution → OK")
                return True

        # Par défaut, exécuter si dernière exécution > 24h
        if self.schedule.last_run_at:
            hours_since_last = (now - self.schedule.last_run_at).total_seconds() / 3600

            if hours_since_last >= 24:
                logger.info(f"[SCHEDULER] {hours_since_last:.1f}h depuis dernière exec → Exécution")
                return True

        logger.info("[SCHEDULER] Conditions non remplies → Pas d'exécution")
        return False

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Calcule la prochaine exécution prévue

        Returns:
            datetime de la prochaine exécution ou None
        """
        if not self.schedule.is_enabled:
            return None

        now = timezone.now()

        # Si jamais exécuté, exécuter maintenant
        if not self.schedule.last_run_at:
            return now

        # Calculer en fonction de l'intervalle
        if hasattr(self.schedule, 'interval_hours'):
            next_run = self.schedule.last_run_at + timedelta(hours=self.schedule.interval_hours)
            return next_run

        # Par défaut: toutes les 24h
        return self.schedule.last_run_at + timedelta(hours=24)
