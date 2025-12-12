import logging
from celery import shared_task
from django.utils import timezone

from backups.models import BackupJob, BackupSchedule, OVFExportJob, SnapshotSchedule, Snapshot
from backups.backup_service import BackupService
from backups.backup_scheduler_service import BackupSchedulerService
from esxi.email_service import EmailNotificationService

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

                    # Exécuter le job de manière asynchrone selon le type
                    if isinstance(job, OVFExportJob):
                        execute_ovf_export.delay(job.id)
                        logger.info(f"[CELERY-SCHEDULER] ✓ OVFExportJob {job.id} créé et lancé pour schedule {schedule.id}")
                    else:
                        execute_backup_job.delay(job.id)
                        logger.info(f"[CELERY-SCHEDULER] ✓ BackupJob {job.id} créé et lancé pour schedule {schedule.id}")

                    executed_count += 1
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
def check_and_execute_snapshot_schedules():
    """
    Tâche périodique pour vérifier et exécuter les schedules de snapshot

    Cette tâche doit être exécutée régulièrement (ex: toutes les heures)
    pour vérifier si des snapshots planifiés doivent être créés.
    """
    logger.info("[CELERY-SNAPSHOT-SCHEDULER] === VÉRIFICATION DES SNAPSHOT SCHEDULES ===")

    # Récupérer tous les schedules actifs
    active_schedules = SnapshotSchedule.objects.filter(is_active=True)

    logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] {active_schedules.count()} snapshot schedule(s) actif(s)")

    executed_count = 0
    skipped_count = 0
    failed_count = 0

    for schedule in active_schedules:
        try:
            logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] Vérification snapshot schedule {schedule.id} ({schedule.virtual_machine.name})")

            # Vérifier si le schedule doit être exécuté maintenant
            now = timezone.now()

            # Si next_run n'est pas défini, le calculer
            if not schedule.next_run:
                schedule.next_run = schedule.calculate_next_run()
                schedule.save()
                logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] Next run calculé: {schedule.next_run}")

            # Vérifier si c'est le moment d'exécuter
            if schedule.next_run and schedule.next_run <= now:
                logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] ✓ Exécution du snapshot schedule {schedule.id}")

                # Lancer la tâche de création de snapshot
                execute_snapshot.delay(
                    schedule_id=schedule.id,
                    vm_id=schedule.virtual_machine.id,
                    include_memory=schedule.include_memory
                )

                # Mettre à jour le schedule
                schedule.last_run = now
                schedule.next_run = schedule.calculate_next_run()
                schedule.save()

                executed_count += 1
                logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] ✓ Snapshot task lancée, prochain run: {schedule.next_run}")
            else:
                skipped_count += 1
                time_until = (schedule.next_run - now).total_seconds() / 60
                logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] ⊘ Schedule {schedule.id} non éligible (prochain run dans {time_until:.0f} min)")

        except Exception as e:
            failed_count += 1
            logger.error(
                f"[CELERY-SNAPSHOT-SCHEDULER] ✗ Erreur traitement snapshot schedule {schedule.id}: {e}",
                exc_info=True
            )

    logger.info("[CELERY-SNAPSHOT-SCHEDULER] === RÉSUMÉ ===")
    logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] Exécutés: {executed_count}")
    logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] Ignorés: {skipped_count}")
    logger.info(f"[CELERY-SNAPSHOT-SCHEDULER] Échecs: {failed_count}")

    return {
        'executed': executed_count,
        'skipped': skipped_count,
        'failed': failed_count
    }


@shared_task
def execute_snapshot(schedule_id, vm_id, include_memory=False):
    """
    Tâche pour créer un snapshot automatique

    Args:
        schedule_id: ID du SnapshotSchedule
        vm_id: ID de la VirtualMachine
        include_memory: Inclure la mémoire RAM dans le snapshot
    """
    from datetime import datetime
    from esxi.models import VirtualMachine
    from esxi.vmware_service import VMwareService

    logger.info(f"[CELERY-SNAPSHOT] === CRÉATION SNAPSHOT AUTOMATIQUE ===")
    logger.info(f"[CELERY-SNAPSHOT] Schedule ID: {schedule_id}, VM ID: {vm_id}")

    snapshot = None

    try:
        # Récupérer la VM et le schedule
        vm = VirtualMachine.objects.get(id=vm_id)
        schedule = SnapshotSchedule.objects.get(id=schedule_id)

        logger.info(f"[CELERY-SNAPSHOT] VM: {vm.name}, Include memory: {include_memory}")

        # Générer le nom du snapshot
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        snapshot_name = f"auto-{vm.name}-{timestamp}"

        # Créer l'enregistrement Snapshot
        snapshot = Snapshot.objects.create(
            virtual_machine=vm,
            schedule=schedule,
            snapshot_name=snapshot_name,
            description=f"Snapshot automatique créé par planification - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            status='creating',
            include_memory=include_memory
        )

        logger.info(f"[CELERY-SNAPSHOT] Snapshot DB créé: {snapshot.id}")

        # Connexion au serveur ESXi
        esxi_server = vm.server
        vmware = VMwareService(
            host=esxi_server.hostname,
            user=esxi_server.username,
            password=esxi_server.password,
            port=esxi_server.port
        )

        if vmware.connect():
            try:
                # Créer le snapshot sur ESXi
                logger.info(f"[CELERY-SNAPSHOT] Création snapshot ESXi: {snapshot_name}")

                success = vmware.create_snapshot(
                    vm_id=vm.vm_id,
                    snapshot_name=snapshot_name,
                    description=snapshot.description,
                    memory=include_memory
                )

                if success:
                    snapshot.status = 'completed'
                    snapshot.save()
                    logger.info(f"[CELERY-SNAPSHOT] ✓ Snapshot créé avec succès: {snapshot_name}")

                    # Send success email notification
                    try:
                        EmailNotificationService.send_backup_success_notification(
                            vm_name=vm.name,
                            backup_path=f"Snapshot: {snapshot_name}"
                        )
                    except Exception as email_error:
                        logger.warning(f"[CELERY-SNAPSHOT] Email notification failed: {email_error}")

                    # Appliquer la politique de rétention
                    cleanup_old_snapshots(schedule, vm)

                    return {'status': 'success', 'snapshot_id': snapshot.id, 'snapshot_name': snapshot_name}
                else:
                    snapshot.status = 'failed'
                    snapshot.save()
                    logger.error(f"[CELERY-SNAPSHOT] ✗ Échec création snapshot: {snapshot_name}")

                    # Send failure email notification
                    try:
                        EmailNotificationService.send_backup_failure_notification(
                            vm_name=vm.name,
                            error_message="La création du snapshot a échoué"
                        )
                    except Exception as email_error:
                        logger.warning(f"[CELERY-SNAPSHOT] Email notification failed: {email_error}")

                    return {'status': 'failed', 'error': 'Snapshot creation failed'}

            finally:
                vmware.disconnect()
        else:
            snapshot.status = 'failed'
            snapshot.save()
            logger.error(f"[CELERY-SNAPSHOT] ✗ Connexion ESXi échouée")

            # Send failure email notification
            try:
                EmailNotificationService.send_backup_failure_notification(
                    vm_name=vm.name,
                    error_message="Échec de connexion au serveur ESXi"
                )
            except Exception as email_error:
                logger.warning(f"[CELERY-SNAPSHOT] Email notification failed: {email_error}")

            return {'status': 'failed', 'error': 'ESXi connection failed'}

    except VirtualMachine.DoesNotExist:
        logger.error(f"[CELERY-SNAPSHOT] VM {vm_id} introuvable")
        return {'status': 'failed', 'error': f'VM {vm_id} not found'}
    except SnapshotSchedule.DoesNotExist:
        logger.error(f"[CELERY-SNAPSHOT] Schedule {schedule_id} introuvable")
        return {'status': 'failed', 'error': f'Schedule {schedule_id} not found'}
    except Exception as e:
        logger.error(f"[CELERY-SNAPSHOT] ✗ Erreur création snapshot: {e}", exc_info=True)
        if snapshot:
            snapshot.status = 'failed'
            snapshot.save()

            # Send failure email notification
            try:
                EmailNotificationService.send_backup_failure_notification(
                    vm_name=vm.name,
                    error_message=str(e)
                )
            except Exception as email_error:
                logger.warning(f"[CELERY-SNAPSHOT] Email notification failed: {email_error}")

        return {'status': 'failed', 'error': str(e)}


def cleanup_old_snapshots(schedule, vm):
    """
    Nettoie les anciens snapshots selon la politique de rétention

    Args:
        schedule: SnapshotSchedule avec retention_count
        vm: VirtualMachine
    """
    try:
        # Récupérer tous les snapshots de ce schedule pour cette VM, triés par date
        snapshots = Snapshot.objects.filter(
            virtual_machine=vm,
            schedule=schedule,
            status='completed'
        ).order_by('-created_at')

        retention_count = schedule.retention_count
        total_count = snapshots.count()

        logger.info(f"[CELERY-SNAPSHOT-CLEANUP] Total snapshots: {total_count}, Rétention: {retention_count}")

        # Si on dépasse la limite de rétention
        if total_count > retention_count:
            snapshots_to_delete = snapshots[retention_count:]

            logger.info(f"[CELERY-SNAPSHOT-CLEANUP] {len(snapshots_to_delete)} snapshot(s) à supprimer")

            # Supprimer les anciens snapshots
            for snap in snapshots_to_delete:
                try:
                    # Supprimer sur ESXi
                    esxi_server = vm.server
                    vmware = VMwareService(
                        host=esxi_server.hostname,
                        user=esxi_server.username,
                        password=esxi_server.password,
                        port=esxi_server.port
                    )

                    if vmware.connect():
                        try:
                            vmware.delete_snapshot(vm.vm_id, snap.snapshot_name)
                            logger.info(f"[CELERY-SNAPSHOT-CLEANUP] ✓ Snapshot supprimé sur ESXi: {snap.snapshot_name}")
                        finally:
                            vmware.disconnect()

                    # Supprimer de la DB
                    snap.delete()
                    logger.info(f"[CELERY-SNAPSHOT-CLEANUP] ✓ Snapshot supprimé de la DB: {snap.snapshot_name}")

                except Exception as e:
                    logger.error(f"[CELERY-SNAPSHOT-CLEANUP] ✗ Erreur suppression {snap.snapshot_name}: {e}")

    except Exception as e:
        logger.error(f"[CELERY-SNAPSHOT-CLEANUP] ✗ Erreur nettoyage: {e}", exc_info=True)


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
    from esxi.vmware_service import VMwareService

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


# REMOVED: SureBackup verification task (module removed)
# The execute_backup_verification function has been removed as the SureBackup module
# has been deprecated and removed from the system.


@shared_task
def check_and_execute_replications():
    """
    Tâche périodique pour vérifier et exécuter les réplications automatiques

    Cette tâche doit être exécutée régulièrement (ex: toutes les 5 minutes)
    pour vérifier si des réplications doivent être lancées selon leur intervalle configuré.
    """
    logger.info("[CELERY-REPLICATION] === VÉRIFICATION DES RÉPLICATIONS ===")

    from backups.models import VMReplication

    # Récupérer toutes les réplications actives
    active_replications = VMReplication.objects.filter(is_active=True)

    logger.info(f"[CELERY-REPLICATION] {active_replications.count()} réplication(s) active(s)")

    executed_count = 0
    skipped_count = 0
    failed_count = 0

    for replication in active_replications:
        try:
            logger.info(f"[CELERY-REPLICATION] Vérification réplication {replication.id} ({replication.name})")

            # Vérifier si la réplication doit être exécutée
            now = timezone.now()
            should_run = False

            if not replication.last_replication_at:
                # Jamais répliquée, on lance
                should_run = True
                reason = "Première réplication"
            else:
                # Calculer le temps écoulé depuis la dernière réplication
                minutes_since_last = (now - replication.last_replication_at).total_seconds() / 60

                if minutes_since_last >= replication.replication_interval_minutes:
                    should_run = True
                    reason = f"Intervalle écoulé ({minutes_since_last:.0f} min >= {replication.replication_interval_minutes} min)"
                else:
                    time_remaining = replication.replication_interval_minutes - minutes_since_last
                    reason = f"Intervalle non écoulé (reste {time_remaining:.0f} min)"

            if should_run:
                logger.info(f"[CELERY-REPLICATION] ✓ Exécution réplication {replication.id}: {reason}")

                # Lancer la tâche de réplication en arrière-plan
                execute_replication.delay(replication.id)

                executed_count += 1
                logger.info(f"[CELERY-REPLICATION] ✓ Tâche de réplication {replication.id} lancée")
            else:
                skipped_count += 1
                logger.info(f"[CELERY-REPLICATION] ⊘ Réplication {replication.id} non éligible: {reason}")

        except Exception as e:
            failed_count += 1
            logger.error(
                f"[CELERY-REPLICATION] ✗ Erreur traitement réplication {replication.id}: {e}",
                exc_info=True
            )

    logger.info("[CELERY-REPLICATION] === RÉSUMÉ ===")
    logger.info(f"[CELERY-REPLICATION] Exécutées: {executed_count}")
    logger.info(f"[CELERY-REPLICATION] Ignorées: {skipped_count}")
    logger.info(f"[CELERY-REPLICATION] Échecs: {failed_count}")

    return {
        'executed': executed_count,
        'skipped': skipped_count,
        'failed': failed_count
    }


@shared_task
def execute_replication(replication_id):
    """
    Tâche pour exécuter une réplication de VM en arrière-plan

    Args:
        replication_id: ID de la VMReplication à exécuter
    """
    from backups.models import VMReplication
    from backups.replication_service import ReplicationService

    logger.info(f"[CELERY-REPLICATION-EXEC] === DÉBUT RÉPLICATION {replication_id} ===")

    try:
        # Récupérer la réplication avec les relations
        replication = VMReplication.objects.select_related(
            'source_server',
            'destination_server',
            'virtual_machine',
            'virtual_machine__server'
        ).get(id=replication_id)

        vm_name = replication.virtual_machine.name
        logger.info(f"[CELERY-REPLICATION-EXEC] VM: {vm_name}, Intervalle: {replication.replication_interval_minutes} min")

        # Vérifier que la réplication est toujours active
        if not replication.is_active:
            logger.warning(f"[CELERY-REPLICATION-EXEC] Réplication {replication_id} désactivée, annulation")
            return {'status': 'cancelled', 'reason': 'Replication is inactive'}

        # TOUJOURS vérifier si une replica existe déjà (même VM)
        service = ReplicationService()
        replica_vm_name = f"{vm_name}_replica"

        try:
            dest_si = service._connect_to_server(replication.destination_server)
            existing_replica = service._get_vm_by_name(dest_si, replica_vm_name)
            from pyVim.connect import Disconnect
            Disconnect(dest_si)

            if existing_replica:
                logger.warning(f"[CELERY-REPLICATION-EXEC] ⚠️ REPLICA EXISTANTE DÉTECTÉE: {replica_vm_name}")
                logger.warning(f"[CELERY-REPLICATION-EXEC] La réplication automatique est ANNULÉE pour éviter l'écrasement")
                logger.warning(f"[CELERY-REPLICATION-EXEC] Action requise: Supprimez manuellement la replica ou lancez une réplication manuelle")

                # Envoyer une notification à l'utilisateur
                try:
                    EmailNotificationService.send_replication_failure_notification(
                        vm_name=vm_name,
                        source_server=replication.source_server.hostname,
                        destination_server=replication.destination_server.hostname,
                        error_message=f"Une replica '{replica_vm_name}' existe déjà sur {replication.destination_server.hostname}. "
                                     f"Supprimez-la manuellement avant de lancer une nouvelle réplication."
                    )
                except Exception as email_error:
                    logger.warning(f"[CELERY-REPLICATION-EXEC] Email notification failed: {email_error}")

                return {
                    'status': 'skipped',
                    'reason': f'Replica {replica_vm_name} already exists on destination server. Manual deletion required.',
                    'replication_id': replication_id
                }
        except Exception as check_error:
            logger.warning(f"[CELERY-REPLICATION-EXEC] Erreur vérification replica: {check_error}")
            # En cas d'erreur de vérification, continuer quand même (pour ne pas bloquer)

        logger.info(f"[CELERY-REPLICATION-EXEC] ✓ Aucune replica existante, démarrage de la réplication...")

        # Mettre à jour le statut
        replication.status = 'syncing'
        replication.save()

        # Fonction de callback pour logger la progression
        def progress_callback(progress_percent, status_val, message):
            logger.info(f"[CELERY-REPLICATION-EXEC] {replication_id}: {progress_percent}% - {status_val} - {message}")

        result = service.replicate_vm(
            replication,
            progress_callback=progress_callback,
            replication_id=None  # Pas d'ID pour annulation dans le contexte Celery
        )

        logger.info(f"[CELERY-REPLICATION-EXEC] ✓ Réplication terminée avec succès: {vm_name}")

        # Envoyer notification de succès
        try:
            # Calculer la durée de la réplication si disponible
            duration_seconds = None
            if replication.last_replication_duration_seconds:
                duration_seconds = replication.last_replication_duration_seconds

            EmailNotificationService.send_replication_success_notification(
                vm_name=vm_name,
                source_server=replication.source_server.hostname,
                destination_server=replication.destination_server.hostname,
                duration_seconds=duration_seconds
            )
        except Exception as email_error:
            logger.warning(f"[CELERY-REPLICATION-EXEC] Email notification failed: {email_error}")

        return {'status': 'success', 'replication_id': replication_id}

    except VMReplication.DoesNotExist:
        logger.error(f"[CELERY-REPLICATION-EXEC] Réplication {replication_id} introuvable")
        return {'status': 'failed', 'error': f'Replication {replication_id} not found'}
    except Exception as e:
        logger.error(f"[CELERY-REPLICATION-EXEC] ✗ Erreur réplication: {e}", exc_info=True)

        # Mettre à jour le statut en cas d'erreur
        try:
            replication = VMReplication.objects.get(id=replication_id)
            replication.status = 'error'
            replication.save()

            # Envoyer notification d'échec
            try:
                EmailNotificationService.send_replication_failure_notification(
                    vm_name=replication.virtual_machine.name,
                    source_server=replication.source_server.hostname,
                    destination_server=replication.destination_server.hostname,
                    error_message=str(e)
                )
            except Exception as email_error:
                logger.warning(f"[CELERY-REPLICATION-EXEC] Email notification failed: {email_error}")

        except:
            pass

        return {'status': 'failed', 'error': str(e)}


@shared_task
def check_and_trigger_auto_failovers():
    """
    Tâche périodique pour vérifier et déclencher les failovers automatiques

    Cette tâche doit être exécutée régulièrement (ex: toutes les minutes)
    pour détecter les pannes et déclencher automatiquement le failover si configuré.
    """
    logger.info("[CELERY-FAILOVER] === VÉRIFICATION AUTO-FAILOVER ===")

    from backups.models import VMReplication, FailoverEvent
    from backups.replication_service import ReplicationService

    # Récupérer toutes les réplications avec failover automatique activé
    auto_failover_replications = VMReplication.objects.filter(
        is_active=True,
        failover_mode='automatic'
    )

    logger.info(f"[CELERY-FAILOVER] {auto_failover_replications.count()} réplication(s) en mode automatique")

    triggered_count = 0
    skipped_count = 0
    failed_count = 0

    service = ReplicationService()

    for replication in auto_failover_replications:
        try:
            logger.info(f"[CELERY-FAILOVER] Vérification réplication {replication.id} ({replication.name})")

            # Vérifier si un failover automatique doit être déclenché
            result = service.check_and_trigger_auto_failover(replication)

            if result.get('should_failover'):
                reason = result.get('reason', 'Panne détectée')
                logger.warning(f"[CELERY-FAILOVER] ⚠️  DÉCLENCHEMENT AUTO-FAILOVER: {reason}")

                # Créer l'événement de failover
                failover_event = FailoverEvent.objects.create(
                    replication=replication,
                    failover_type='automatic',
                    status='initiated',
                    triggered_by=None,  # Automatique, pas d'utilisateur
                    reason=f"Auto-failover: {reason}"
                )

                logger.info(f"[CELERY-FAILOVER] Événement failover créé: {failover_event.id}")

                # Exécuter le failover
                failover_result = service.execute_failover(failover_event, test_mode=False)

                if failover_result['success']:
                    triggered_count += 1
                    logger.info(f"[CELERY-FAILOVER] ✓ Failover réussi: {failover_result['message']}")

                    # Envoyer notification d'urgence
                    try:
                        EmailNotificationService.send_backup_failure_notification(
                            vm_name=replication.virtual_machine.name,
                            error_message=f"AUTO-FAILOVER DÉCLENCHÉ: {reason}. VM basculée vers {replication.destination_server.hostname}"
                        )
                    except Exception as email_error:
                        logger.warning(f"[CELERY-FAILOVER] Email notification failed: {email_error}")
                else:
                    failed_count += 1
                    logger.error(f"[CELERY-FAILOVER] ✗ Failover échoué: {failover_result.get('error')}")

                    # Envoyer notification d'échec critique
                    try:
                        EmailNotificationService.send_backup_failure_notification(
                            vm_name=replication.virtual_machine.name,
                            error_message=f"ÉCHEC AUTO-FAILOVER: {failover_result.get('error')}"
                        )
                    except Exception as email_error:
                        logger.warning(f"[CELERY-FAILOVER] Email notification failed: {email_error}")
            else:
                skipped_count += 1
                logger.info(f"[CELERY-FAILOVER] ⊘ Pas de failover nécessaire: {result.get('reason')}")

        except Exception as e:
            failed_count += 1
            logger.error(
                f"[CELERY-FAILOVER] ✗ Erreur vérification failover {replication.id}: {e}",
                exc_info=True
            )

    logger.info("[CELERY-FAILOVER] === RÉSUMÉ ===")
    logger.info(f"[CELERY-FAILOVER] Déclenchés: {triggered_count}")
    logger.info(f"[CELERY-FAILOVER] Ignorés: {skipped_count}")
    logger.info(f"[CELERY-FAILOVER] Échecs: {failed_count}")

    return {
        'triggered': triggered_count,
        'skipped': skipped_count,
        'failed': failed_count
    }


@shared_task
def check_and_trigger_auto_failbacks():
    """
    Tâche périodique pour vérifier et déclencher les failbacks automatiques
    (quand la VM master revient en ligne après un failover)

    Cette tâche doit être exécutée régulièrement (ex: toutes les minutes)
    pour détecter quand le master est revenu et déclencher le failback.
    """
    logger.info("[CELERY-FAILBACK] === VÉRIFICATION AUTO-FAILBACK ===")

    from backups.models import VMReplication
    from backups.replication_service import ReplicationService

    # Récupérer toutes les réplications avec failover actif et failback automatique activé
    active_failover_replications = VMReplication.objects.filter(
        is_active=True,
        failover_active=True,  # Failover actuellement actif
        failback_enabled=True  # Failback automatique activé
    )

    logger.info(f"[CELERY-FAILBACK] {active_failover_replications.count()} réplication(s) en failover actif avec failback auto")

    triggered_count = 0
    skipped_count = 0
    failed_count = 0

    service = ReplicationService()

    for replication in active_failover_replications:
        try:
            logger.info(f"[CELERY-FAILBACK] Vérification réplication {replication.id} ({replication.name})")

            # Vérifier si un failback automatique doit être déclenché
            result = service.check_and_trigger_auto_failback(replication)

            if result.get('should_failback'):
                reason = result.get('reason', 'VM master revenue en ligne')
                logger.info(f"[CELERY-FAILBACK] ✓ DÉCLENCHEMENT AUTO-FAILBACK: {reason}")

                # Exécuter le failback
                failback_result = service.execute_failback(replication, triggered_by=None)

                if failback_result['success']:
                    triggered_count += 1
                    logger.info(f"[CELERY-FAILBACK] ✓ Failback réussi: {failback_result['message']}")

                    # Envoyer notification de succès
                    try:
                        EmailNotificationService.send_backup_success_notification(
                            vm_name=replication.virtual_machine.name,
                            backup_path=f"AUTO-FAILBACK RÉUSSI: VM {replication.virtual_machine.name} revenue sur {replication.get_source_server.hostname}"
                        )
                    except Exception as email_error:
                        logger.warning(f"[CELERY-FAILBACK] Email notification failed: {email_error}")
                else:
                    failed_count += 1
                    logger.error(f"[CELERY-FAILBACK] ✗ Failback échoué: {failback_result.get('error')}")

                    # Envoyer notification d'échec
                    try:
                        EmailNotificationService.send_backup_failure_notification(
                            vm_name=replication.virtual_machine.name,
                            error_message=f"ÉCHEC AUTO-FAILBACK: {failback_result.get('error')}"
                        )
                    except Exception as email_error:
                        logger.warning(f"[CELERY-FAILBACK] Email notification failed: {email_error}")
            else:
                skipped_count += 1
                logger.info(f"[CELERY-FAILBACK] ⊘ Pas de failback nécessaire: {result.get('reason')}")

        except Exception as e:
            failed_count += 1
            logger.error(
                f"[CELERY-FAILBACK] ✗ Erreur vérification failback {replication.id}: {e}",
                exc_info=True
            )

    logger.info("[CELERY-FAILBACK] === RÉSUMÉ ===")
    logger.info(f"[CELERY-FAILBACK] Déclenchés: {triggered_count}")
    logger.info(f"[CELERY-FAILBACK] Ignorés: {skipped_count}")
    logger.info(f"[CELERY-FAILBACK] Échecs: {failed_count}")

    return {
        'triggered': triggered_count,
        'skipped': skipped_count,
        'failed': failed_count
    }
