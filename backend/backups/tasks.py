import logging
from celery import shared_task
from django.utils import timezone

from backups.models import BackupJob, BackupSchedule
from backups.backup_service import BackupService
from backups.backup_scheduler_service import BackupSchedulerService

logger = logging.getLogger(__name__)


@shared_task
def execute_backup_job(job_id):
    """
    Tâche Celery pour exécuter un backup job

    Args:
        job_id: ID du BackupJob à exécuter
    """
    try:
        job = BackupJob.objects.get(id=job_id)
        logger.info(f"[CELERY] Exécution du backup job {job_id}")

        BackupService(job).execute_backup()

        logger.info(f"[CELERY] Backup job {job_id} terminé")

    except BackupJob.DoesNotExist:
        logger.error(f"[CELERY] Backup job {job_id} introuvable")
    except Exception as e:
        logger.error(f"[CELERY] Erreur exécution job {job_id}: {e}", exc_info=True)


@shared_task
def check_and_execute_schedules():
    """
    Tâche périodique pour vérifier et exécuter les schedules de backup

    Cette tâche doit être exécutée régulièrement (ex: toutes les heures)
    pour vérifier si des backups planifiés doivent être lancés.
    """
    logger.info("[CELERY-SCHEDULER] === VÉRIFICATION DES SCHEDULES ===")

    # Récupérer tous les schedules actifs
    active_schedules = BackupSchedule.objects.filter(is_enabled=True)

    logger.info(f"[CELERY-SCHEDULER] {active_schedules.count()} schedule(s) actif(s)")

    executed_count = 0
    skipped_count = 0
    failed_count = 0

    for schedule in active_schedules:
        try:
            logger.info(f"[CELERY-SCHEDULER] Vérification schedule {schedule.id} ({schedule.virtual_machine.name})")

            # Créer le service de planification
            scheduler = BackupSchedulerService(schedule)

            # Vérifier si le schedule doit être exécuté
            if scheduler.should_run_now():
                logger.info(f"[CELERY-SCHEDULER] ✓ Exécution du schedule {schedule.id}")

                # Créer le backup job
                job = scheduler.create_scheduled_backup_job()

                if job:
                    # Mettre à jour le schedule
                    schedule.last_run_at = timezone.now()
                    schedule.next_run = scheduler.get_next_run_time()
                    schedule.save()

                    # Exécuter le job de manière asynchrone
                    execute_backup_job.delay(job.id)

                    executed_count += 1
                    logger.info(f"[CELERY-SCHEDULER] ✓ Job {job.id} créé et lancé pour schedule {schedule.id}")
                else:
                    failed_count += 1
                    logger.error(f"[CELERY-SCHEDULER] ✗ Échec création job pour schedule {schedule.id}")
            else:
                skipped_count += 1
                logger.info(f"[CELERY-SCHEDULER] ⊘ Schedule {schedule.id} non éligible pour exécution")

        except Exception as e:
            failed_count += 1
            logger.error(
                f"[CELERY-SCHEDULER] ✗ Erreur traitement schedule {schedule.id}: {e}",
                exc_info=True
            )

    logger.info("[CELERY-SCHEDULER] === RÉSUMÉ ===")
    logger.info(f"[CELERY-SCHEDULER] Exécutés: {executed_count}")
    logger.info(f"[CELERY-SCHEDULER] Ignorés: {skipped_count}")
    logger.info(f"[CELERY-SCHEDULER] Échecs: {failed_count}")

    return {
        'executed': executed_count,
        'skipped': skipped_count,
        'failed': failed_count
    }


@shared_task
def cleanup_old_backups():
    """
    Tâche périodique pour nettoyer les anciens backups selon les politiques de rétention

    Cette tâche applique automatiquement les politiques de rétention définies
    dans les chaînes de backup.
    """
    logger.info("[CELERY-CLEANUP] === NETTOYAGE DES ANCIENS BACKUPS ===")

    from backups.models import RemoteStorageConfig, VirtualMachine
    from backups.backup_chain.chain_manager import BackupChainManager
    from backups.backup_chain.retention_policy import RetentionPolicyManager

    try:
        # Récupérer le remote storage par défaut
        remote_storage = RemoteStorageConfig.objects.get(is_default=True, is_active=True)

        # Récupérer toutes les VMs
        vms = VirtualMachine.objects.all()

        total_deleted = 0
        total_kept = 0
        errors = []

        for vm in vms:
            try:
                logger.info(f"[CELERY-CLEANUP] Traitement de {vm.name}")

                # Initialiser les managers
                chain_manager = BackupChainManager(remote_storage, vm.name)
                retention_manager = RetentionPolicyManager(chain_manager)

                # Appliquer la politique de rétention
                results = retention_manager.apply_policy(dry_run=False)

                total_deleted += results['deleted_count']
                total_kept += results['kept_count']

                if results['deleted_count'] > 0:
                    logger.info(
                        f"[CELERY-CLEANUP] ✓ {vm.name}: {results['deleted_count']} backup(s) supprimé(s), "
                        f"{results['kept_count']} conservé(s)"
                    )

            except Exception as e:
                error_msg = f"Erreur pour {vm.name}: {e}"
                errors.append(error_msg)
                logger.error(f"[CELERY-CLEANUP] {error_msg}", exc_info=True)

        logger.info("[CELERY-CLEANUP] === RÉSUMÉ ===")
        logger.info(f"[CELERY-CLEANUP] Total supprimés: {total_deleted}")
        logger.info(f"[CELERY-CLEANUP] Total conservés: {total_kept}")

        if errors:
            logger.warning(f"[CELERY-CLEANUP] Erreurs: {len(errors)}")

        return {
            'deleted': total_deleted,
            'kept': total_kept,
            'errors': errors
        }

    except RemoteStorageConfig.DoesNotExist:
        logger.error("[CELERY-CLEANUP] Aucun remote storage configuré")
        return {'error': 'No remote storage configured'}
    except Exception as e:
        logger.error(f"[CELERY-CLEANUP] Erreur globale: {e}", exc_info=True)
        return {'error': str(e)}


@shared_task
def check_backup_health():
    """
    Tâche périodique pour vérifier la santé du système de backup
    et envoyer des alertes automatiques en cas de problèmes

    Cette tâche doit être exécutée régulièrement (ex: toutes les 6 heures)
    pour surveiller l'état de santé global des backups.
    """
    logger.info("[CELERY-HEALTH] === VÉRIFICATION DE LA SANTÉ DES BACKUPS ===")

    from backups.health_monitoring_service import health_monitor
    from backups.notification_service import notification_service

    try:
        # Récupérer l'état de santé global
        health_data = health_monitor.get_overall_health()

        logger.info(f"[CELERY-HEALTH] Statut: {health_data['status']}")
        logger.info(f"[CELERY-HEALTH] Score: {health_data['score']}/100")
        logger.info(f"[CELERY-HEALTH] Problèmes détectés: {len(health_data['issues'])}")
        logger.info(f"[CELERY-HEALTH] Avertissements: {len(health_data['warnings'])}")

        # Envoyer des notifications pour les problèmes critiques et warnings
        critical_issues = [i for i in health_data['issues'] if i['severity'] == 'critical']
        warning_issues = [i for i in health_data['issues'] if i['severity'] == 'warning']

        # Notification pour les problèmes critiques
        if critical_issues:
            logger.warning(f"[CELERY-HEALTH] ⚠️  {len(critical_issues)} problème(s) critique(s) détecté(s)")

            # Envoyer une alerte pour chaque type de problème critique
            for issue in critical_issues:
                try:
                    event_type = 'backup_failure' if issue['type'] == 'recent_failures' else 'backup_warning'

                    notification_service.send_notification(
                        event_type=event_type,
                        vm=None,
                        backup_job=None,
                        health_issue=issue,
                        health_status=health_data['status'],
                        health_score=health_data['score']
                    )
                    logger.info(f"[CELERY-HEALTH] ✓ Notification envoyée pour: {issue['type']}")
                except Exception as notif_error:
                    logger.error(f"[CELERY-HEALTH] Erreur envoi notification: {notif_error}")

        # Log des problèmes de type warning
        if warning_issues:
            logger.info(f"[CELERY-HEALTH] ⚠️  {len(warning_issues)} avertissement(s) détecté(s)")
            for issue in warning_issues:
                logger.info(f"[CELERY-HEALTH]   - {issue['type']}: {issue['message']}")

        # Log des recommandations
        if health_data['recommendations']:
            logger.info(f"[CELERY-HEALTH] 💡 {len(health_data['recommendations'])} recommandation(s):")
            for rec in health_data['recommendations']:
                logger.info(f"[CELERY-HEALTH]   - [{rec['priority']}] {rec['message']}")

        # Si le score est très bas, envoyer une alerte de santé globale
        if health_data['score'] < 50:
            logger.critical(f"[CELERY-HEALTH] ⚠️  SCORE CRITIQUE: {health_data['score']}/100")

            try:
                notification_service.send_notification(
                    event_type='backup_warning',
                    vm=None,
                    backup_job=None,
                    health_status=health_data['status'],
                    health_score=health_data['score'],
                    issues_count=len(health_data['issues']),
                    critical_count=len(critical_issues)
                )
            except Exception as notif_error:
                logger.error(f"[CELERY-HEALTH] Erreur envoi alerte globale: {notif_error}")

        logger.info("[CELERY-HEALTH] === FIN VÉRIFICATION SANTÉ ===")

        return {
            'status': health_data['status'],
            'score': health_data['score'],
            'issues_count': len(health_data['issues']),
            'critical_count': len(critical_issues),
            'warning_count': len(warning_issues)
        }

    except Exception as e:
        logger.error(f"[CELERY-HEALTH] Erreur lors de la vérification de santé: {e}", exc_info=True)
        return {'error': str(e)}


@shared_task
def execute_ovf_export(export_job_id):
    """
    Tâche pour exécuter un export OVF en arrière-plan

    Args:
        export_job_id: ID du OVFExportJob à exécuter
    """
    from backups.models import OVFExportJob
    from backups.ovf_export_lease import OVFExportLeaseService
    from esxi.vmware_service import VMwareService

    logger.info(f"[CELERY-OVF] === DÉBUT EXPORT OVF {export_job_id} ===")

    try:
        export_job = OVFExportJob.objects.get(id=export_job_id)
        vm = export_job.virtual_machine
        esxi_server = vm.server

        logger.info(f"[CELERY-OVF] VM: {vm.name}, Serveur: {esxi_server.hostname}")

        # Connexion au serveur ESXi
        vmware_service = VMwareService(
            host=esxi_server.hostname,
            user=esxi_server.username,
            password=esxi_server.password,
            port=esxi_server.port
        )

        if not vmware_service.connect():
            raise Exception("Impossible de se connecter au serveur ESXi")

        try:
            # Récupérer l'objet VM pyVmomi
            vm_obj = vmware_service._find_vm_by_name(vm.name)
            if not vm_obj:
                raise Exception(f"VM '{vm.name}' introuvable sur le serveur")

            # Create OVF export service (using HttpNfcLease API for thin-provisioned disks)
            ovf_service = OVFExportLeaseService(vm_obj, export_job)

            # Execute OVF export
            export_job.status = 'running'
            export_job.save()

            success = ovf_service.export_ovf()

            if success:
                logger.info(f"[CELERY-OVF] ✓ Export terminé avec succès")
            else:
                logger.error(f"[CELERY-OVF] ✗ Export échoué")

        finally:
            vmware_service.disconnect()

        export_job.save()
        return {'status': export_job.status, 'export_id': export_job_id}

    except OVFExportJob.DoesNotExist:
        logger.error(f"[CELERY-OVF] Export {export_job_id} introuvable")
        return {'error': f'Export {export_job_id} not found'}
    except Exception as e:
        logger.error(f"[CELERY-OVF] Erreur export: {e}", exc_info=True)
        try:
            export_job = OVFExportJob.objects.get(id=export_job_id)
            export_job.status = 'failed'
            export_job.error_message = str(e)
            export_job.save()
        except:
            pass
        return {'error': str(e)}


@shared_task
def execute_vm_backup(backup_job_id):
    """
    Tâche pour exécuter un backup de VM (snapshot + VMDK copy) en arrière-plan

    Args:
        backup_job_id: ID du VMBackupJob à exécuter
    """
    from backups.models import VMBackupJob
    from backups.vm_backup_service import execute_vm_backup as run_backup
    from esxi.vmware_service import VMwareConnectionManager

    logger.info(f"[CELERY-VM-BACKUP] === DÉBUT BACKUP {backup_job_id} ===")

    try:
        backup_job = VMBackupJob.objects.get(id=backup_job_id)
        vm = backup_job.virtual_machine
        esxi_server = vm.server

        logger.info(f"[CELERY-VM-BACKUP] VM: {vm.name}, Type: {backup_job.backup_type}")

        # Connexion au serveur ESXi
        vmware_service = VMwareService(
            host=esxi_server.hostname,
            user=esxi_server.username,
            password=esxi_server.password,
            port=esxi_server.port
        )

        if not vmware_service.connect():
            raise Exception("Impossible de se connecter au serveur ESXi")

        try:
            # Récupérer l'objet VM pyVmomi
            vm_obj = vmware_service._find_vm_by_name(vm.name)
            if not vm_obj:
                raise Exception(f"VM '{vm.name}' introuvable sur le serveur")

            # Exécuter le backup
            success = run_backup(vm_obj, backup_job)

            if success:
                logger.info(f"[CELERY-VM-BACKUP] ✓ Backup terminé avec succès")
            else:
                logger.error(f"[CELERY-VM-BACKUP] ✗ Backup échoué")

        finally:
            vmware_service.disconnect()

        return {'status': backup_job.status, 'backup_id': backup_job_id}

    except VMBackupJob.DoesNotExist:
        logger.error(f"[CELERY-VM-BACKUP] Backup {backup_job_id} introuvable")
        return {'error': f'Backup {backup_job_id} not found'}
    except Exception as e:
        logger.error(f"[CELERY-VM-BACKUP] Erreur backup: {e}", exc_info=True)
        try:
            backup_job = VMBackupJob.objects.get(id=backup_job_id)
            backup_job.status = 'failed'
            backup_job.error_message = str(e)
            backup_job.save()
        except:
            pass
        return {'error': str(e)}
