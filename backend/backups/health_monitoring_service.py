"""
Service de monitoring de santé des backups
Analyse l'état global des backups et détecte les problèmes potentiels
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg, Sum, Max
from django.utils import timezone
from .models import (
    BackupJob, BackupSchedule, NotificationConfig
)
from esxi.models import VirtualMachine, DatastoreInfo

logger = logging.getLogger(__name__)


class HealthStatus:
    """États de santé possibles"""
    HEALTHY = 'healthy'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'


class BackupHealthMonitor:
    """
    Service de monitoring de santé des backups
    Fournit des métriques et détecte les problèmes
    """

    def __init__(self):
        self.now = timezone.now()

    def get_overall_health(self):
        """
        Retourne l'état de santé global du système de backup

        Returns:
            dict: {
                'status': 'healthy'|'warning'|'critical',
                'score': 0-100,
                'issues': [...],
                'metrics': {...},
                'recommendations': [...]
            }
        """
        issues = []
        warnings = []
        score = 100

        # 1. Vérifier les VMs sans backup récent
        stale_vms = self._check_stale_backups()
        if stale_vms:
            issues.append({
                'type': 'stale_backups',
                'severity': 'warning',
                'count': len(stale_vms),
                'message': f"{len(stale_vms)} VM(s) sans backup depuis plus de 7 jours",
                'vms': stale_vms
            })
            score -= len(stale_vms) * 5

        # 2. Vérifier les échecs récents
        recent_failures = self._check_recent_failures()
        if recent_failures['count'] > 0:
            severity = 'critical' if recent_failures['rate'] > 0.3 else 'warning'
            issues.append({
                'type': 'recent_failures',
                'severity': severity,
                'count': recent_failures['count'],
                'rate': round(recent_failures['rate'] * 100, 1),
                'message': f"{recent_failures['count']} backup(s) échoué(s) dans les dernières 24h ({round(recent_failures['rate'] * 100, 1)}%)",
                'jobs': recent_failures['jobs']
            })
            score -= recent_failures['count'] * 10

        # 3. Vérifier les chaînes de backup cassées
        broken_chains = self._check_broken_chains()
        if broken_chains:
            issues.append({
                'type': 'broken_chains',
                'severity': 'critical',
                'count': len(broken_chains),
                'message': f"{len(broken_chains)} chaîne(s) de backup cassée(s) (incrementals sans base)",
                'jobs': broken_chains
            })
            score -= len(broken_chains) * 15

        # 4. Vérifier les schedules inactifs/manqués
        inactive_schedules = self._check_inactive_schedules()
        if inactive_schedules:
            issues.append({
                'type': 'inactive_schedules',
                'severity': 'warning',
                'count': len(inactive_schedules),
                'message': f"{len(inactive_schedules)} planification(s) inactive(s)",
                'schedules': inactive_schedules
            })
            score -= len(inactive_schedules) * 3

        # 5. Vérifier l'espace disque des datastores
        storage_warnings = self._check_storage_capacity()
        if storage_warnings:
            for warning in storage_warnings:
                severity = 'critical' if warning['usage_percent'] > 90 else 'warning'
                issues.append({
                    'type': 'storage_capacity',
                    'severity': severity,
                    'datastore': warning['name'],
                    'usage_percent': warning['usage_percent'],
                    'free_gb': warning['free_gb'],
                    'message': f"Datastore {warning['name']} à {warning['usage_percent']}% ({warning['free_gb']} GB libres)"
                })
                score -= 10 if severity == 'critical' else 5

        # 6. Vérifier les backups sans snapshot (CBT non activé)
        cbt_disabled = self._check_cbt_status()
        if cbt_disabled:
            warnings.append({
                'type': 'cbt_disabled',
                'severity': 'info',
                'count': len(cbt_disabled),
                'message': f"{len(cbt_disabled)} VM(s) sans CBT activé (backups moins efficaces)",
                'vms': cbt_disabled
            })

        # Déterminer le statut global
        score = max(0, min(100, score))

        if score >= 90:
            status = HealthStatus.HEALTHY
        elif score >= 70:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.CRITICAL

        # Générer des recommandations
        recommendations = self._generate_recommendations(issues, warnings)

        # Métriques additionnelles
        metrics = self._get_summary_metrics()

        return {
            'status': status,
            'score': score,
            'issues': issues,
            'warnings': warnings,
            'metrics': metrics,
            'recommendations': recommendations,
            'last_check': self.now.isoformat()
        }

    def _check_stale_backups(self, days=7):
        """
        Vérifie les VMs sans backup récent

        Returns:
            list: VMs sans backup depuis N jours
        """
        threshold = self.now - timedelta(days=days)
        stale_vms = []

        # Récupérer toutes les VMs avec leurs derniers backups
        vms = VirtualMachine.objects.all()

        for vm in vms:
            last_backup = BackupJob.objects.filter(
                virtual_machine=vm,
                status='completed'
            ).order_by('-completed_at').first()

            if not last_backup:
                stale_vms.append({
                    'id': vm.id,
                    'name': vm.name,
                    'last_backup': None,
                    'days_ago': 'never'
                })
            elif last_backup.completed_at < threshold:
                days_ago = (self.now - last_backup.completed_at).days
                stale_vms.append({
                    'id': vm.id,
                    'name': vm.name,
                    'last_backup': last_backup.completed_at.isoformat(),
                    'days_ago': days_ago
                })

        return stale_vms

    def _check_recent_failures(self, hours=24):
        """
        Vérifie les échecs de backup récents

        Returns:
            dict: Statistiques des échecs récents
        """
        threshold = self.now - timedelta(hours=hours)

        recent_jobs = BackupJob.objects.filter(
            created_at__gte=threshold
        )

        total = recent_jobs.count()
        failed = recent_jobs.filter(status='failed').count()

        failed_jobs = recent_jobs.filter(status='failed').values(
            'id', 'virtual_machine__name', 'error_message', 'created_at'
        )[:10]  # Limite aux 10 derniers échecs

        return {
            'count': failed,
            'total': total,
            'rate': failed / total if total > 0 else 0,
            'jobs': list(failed_jobs)
        }

    def _check_broken_chains(self):
        """
        Vérifie les chaînes de backup cassées (incrementals sans base valide)

        Returns:
            list: Backups incrementals avec des problèmes de chaîne
        """
        broken = []

        # Trouver tous les backups incrementals
        incremental_jobs = BackupJob.objects.filter(
            job_type='incremental',
            status='completed'
        ).select_related('virtual_machine', 'base_backup')

        for job in incremental_jobs:
            # Vérifier si le base_backup existe et est valide
            if not job.base_backup:
                broken.append({
                    'id': job.id,
                    'vm_name': job.virtual_machine.name,
                    'created_at': job.created_at.isoformat(),
                    'issue': 'Aucun backup de base référencé'
                })
            elif job.base_backup.status != 'completed':
                broken.append({
                    'id': job.id,
                    'vm_name': job.virtual_machine.name,
                    'created_at': job.created_at.isoformat(),
                    'issue': f"Backup de base invalide (status: {job.base_backup.status})"
                })

        return broken

    def _check_inactive_schedules(self):
        """
        Vérifie les schedules inactifs ou qui n'ont pas été exécutés récemment

        Returns:
            list: Schedules avec des problèmes
        """
        inactive = []

        schedules = BackupSchedule.objects.filter(is_active=True, is_enabled=True)

        for schedule in schedules:
            # Vérifier si le schedule a déjà été exécuté
            if not schedule.last_run_at:
                inactive.append({
                    'id': schedule.id,
                    'vm_name': schedule.virtual_machine.name,
                    'frequency': schedule.frequency,
                    'issue': 'Jamais exécuté'
                })
            else:
                # Vérifier si le schedule est en retard
                expected_interval = self._get_expected_interval(schedule)
                if expected_interval:
                    threshold = self.now - timedelta(hours=expected_interval * 1.5)
                    if schedule.last_run_at < threshold:
                        hours_ago = (self.now - schedule.last_run_at).total_seconds() / 3600
                        inactive.append({
                            'id': schedule.id,
                            'vm_name': schedule.virtual_machine.name,
                            'frequency': schedule.frequency,
                            'last_run': schedule.last_run_at.isoformat(),
                            'hours_ago': round(hours_ago, 1),
                            'issue': f'Pas exécuté depuis {round(hours_ago, 1)}h (attendu: {expected_interval}h)'
                        })

        return inactive

    def _get_expected_interval(self, schedule):
        """Retourne l'intervalle attendu en heures pour un schedule"""
        if schedule.interval_hours:
            return schedule.interval_hours

        frequency_map = {
            'hourly': 1,
            'daily': 24,
            'weekly': 168,
            'monthly': 720
        }
        return frequency_map.get(schedule.frequency)

    def _check_storage_capacity(self):
        """
        Vérifie l'espace disque disponible sur les datastores

        Returns:
            list: Datastores avec peu d'espace
        """
        warnings = []

        datastores = DatastoreInfo.objects.all()

        for ds in datastores:
            if ds.capacity_gb > 0:
                usage_percent = ((ds.capacity_gb - ds.free_space_gb) / ds.capacity_gb) * 100

                if usage_percent > 80:  # Seuil de 80%
                    warnings.append({
                        'name': ds.name,
                        'usage_percent': round(usage_percent, 1),
                        'free_gb': round(ds.free_space_gb, 2),
                        'capacity_gb': round(ds.capacity_gb, 2)
                    })

        return warnings

    def _check_cbt_status(self):
        """
        Vérifie les VMs sans CBT activé

        Returns:
            list: VMs sans CBT
        """
        cbt_disabled = []

        # Récupérer les derniers backups par VM
        vms = VirtualMachine.objects.all()

        for vm in vms:
            last_job = BackupJob.objects.filter(
                virtual_machine=vm,
                status='completed'
            ).order_by('-completed_at').first()

            if last_job and not last_job.is_cbt_enabled:
                cbt_disabled.append({
                    'id': vm.id,
                    'name': vm.name,
                    'last_backup': last_job.completed_at.isoformat()
                })

        return cbt_disabled

    def _generate_recommendations(self, issues, warnings):
        """
        Génère des recommandations basées sur les problèmes détectés

        Returns:
            list: Liste de recommandations
        """
        recommendations = []

        for issue in issues:
            if issue['type'] == 'stale_backups':
                recommendations.append({
                    'priority': 'high',
                    'message': f"Configurer des schedules automatiques pour les {issue['count']} VM(s) sans backup récent",
                    'action': 'create_schedules'
                })

            elif issue['type'] == 'recent_failures':
                recommendations.append({
                    'priority': 'critical',
                    'message': f"Investiguer les causes des {issue['count']} échecs récents et corriger les problèmes",
                    'action': 'review_errors'
                })

            elif issue['type'] == 'broken_chains':
                recommendations.append({
                    'priority': 'critical',
                    'message': f"Créer un nouveau Full backup pour les {issue['count']} chaîne(s) cassée(s)",
                    'action': 'create_full_backups'
                })

            elif issue['type'] == 'storage_capacity':
                recommendations.append({
                    'priority': 'high',
                    'message': f"Libérer de l'espace sur {issue['datastore']} ou appliquer la politique de rétention",
                    'action': 'cleanup_storage'
                })

        for warning in warnings:
            if warning['type'] == 'cbt_disabled':
                recommendations.append({
                    'priority': 'medium',
                    'message': f"Activer CBT sur {warning['count']} VM(s) pour améliorer les performances des backups incrementals",
                    'action': 'enable_cbt'
                })

        return recommendations

    def _get_summary_metrics(self):
        """
        Retourne des métriques résumées du système

        Returns:
            dict: Métriques générales
        """
        # Statistiques globales
        total_vms = VirtualMachine.objects.count()
        total_jobs = BackupJob.objects.count()
        completed_jobs = BackupJob.objects.filter(status='completed').count()

        # Dernières 24h
        last_24h = self.now - timedelta(hours=24)
        jobs_24h = BackupJob.objects.filter(created_at__gte=last_24h)
        success_24h = jobs_24h.filter(status='completed').count()
        failed_24h = jobs_24h.filter(status='failed').count()

        # Derniers 7 jours
        last_7d = self.now - timedelta(days=7)
        jobs_7d = BackupJob.objects.filter(created_at__gte=last_7d)
        success_7d = jobs_7d.filter(status='completed').count()

        # Durée moyenne des backups
        avg_duration = BackupJob.objects.filter(
            status='completed',
            duration_seconds__gt=0
        ).aggregate(Avg('duration_seconds'))['duration_seconds__avg'] or 0

        # Taille totale des backups (en MB, converti en bytes)
        total_size_mb = BackupJob.objects.filter(
            status='completed'
        ).aggregate(Sum('backup_size_mb'))['backup_size_mb__sum'] or 0
        total_size = total_size_mb * (1024**2)  # Convert MB to bytes

        # Schedules actifs
        active_schedules = BackupSchedule.objects.filter(
            is_active=True,
            is_enabled=True
        ).count()

        return {
            'total_vms': total_vms,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'success_rate_overall': round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1),
            'jobs_last_24h': jobs_24h.count(),
            'success_last_24h': success_24h,
            'failed_last_24h': failed_24h,
            'success_rate_24h': round((success_24h / jobs_24h.count() * 100) if jobs_24h.count() > 0 else 0, 1),
            'success_last_7d': success_7d,
            'avg_duration_seconds': round(avg_duration, 0),
            'avg_duration_minutes': round(avg_duration / 60, 1),
            'total_backup_size_bytes': total_size,
            'total_backup_size_gb': round(total_size / (1024**3), 2),
            'active_schedules': active_schedules
        }

    def get_vm_health(self, vm_id):
        """
        Retourne l'état de santé d'une VM spécifique

        Args:
            vm_id: ID de la VM

        Returns:
            dict: État de santé détaillé de la VM
        """
        try:
            vm = VirtualMachine.objects.get(id=vm_id)
        except VirtualMachine.DoesNotExist:
            return {'error': 'VM not found'}

        # Statistiques des backups
        total_backups = BackupJob.objects.filter(virtual_machine=vm).count()
        successful = BackupJob.objects.filter(virtual_machine=vm, status='completed').count()
        failed = BackupJob.objects.filter(virtual_machine=vm, status='failed').count()

        # Dernier backup
        last_backup = BackupJob.objects.filter(
            virtual_machine=vm,
            status='completed'
        ).order_by('-completed_at').first()

        # Prochain backup planifié
        next_schedule = BackupSchedule.objects.filter(
            virtual_machine=vm,
            is_active=True,
            is_enabled=True
        ).order_by('next_run').first()

        # Déterminer le statut
        if last_backup:
            days_since = (self.now - last_backup.completed_at).days
            if days_since <= 1:
                status = HealthStatus.HEALTHY
            elif days_since <= 7:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.CRITICAL

        return {
            'vm_id': vm.id,
            'vm_name': vm.name,
            'status': status,
            'total_backups': total_backups,
            'successful_backups': successful,
            'failed_backups': failed,
            'success_rate': round((successful / total_backups * 100) if total_backups > 0 else 0, 1),
            'last_backup': last_backup.completed_at.isoformat() if last_backup else None,
            'days_since_last_backup': (self.now - last_backup.completed_at).days if last_backup else None,
            'next_scheduled_backup': next_schedule.next_run.isoformat() if next_schedule else None,
            'has_active_schedule': next_schedule is not None,
            'cbt_enabled': last_backup.is_cbt_enabled if last_backup else False
        }


# Instance globale du service
health_monitor = BackupHealthMonitor()
