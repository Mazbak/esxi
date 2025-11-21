"""
backup_service.py

Service pour gérer les backups des VMs ESXi avec gestion de chaînes
"""

import os
import re
import logging
from django.utils import timezone
from esxi.vmware_service import VMwareService
from backups.models import BackupJob, RemoteStorageConfig
from backups.incremental_backup_service import IncrementalBackupService
from backups.backup_chain.chain_manager import BackupChainManager
from backups.backup_chain.integrity_checker import IntegrityChecker
from backups.backup_chain.retention_policy import RetentionPolicyManager
from backups.notification_service import notification_service

logger = logging.getLogger(__name__)

def normalize_windows_path(path):
    """
    Normalise un chemin Windows en corrigeant les syntaxes incorrectes.

    Exemples:
    - '/D:\backup' -> 'D:\backup'
    - '/D:/backup' -> 'D:\backup'
    - 'D:/backup' -> 'D:\backup'
    """
    if not path:
        return path

    # Détecter et corriger les chemins Windows malformés avec slash au début
    # Pattern: /D:\path ou /D:/path
    match = re.match(r'^/([A-Za-z]:)[/\\](.*)$', path)
    if match:
        drive = match.group(1)
        rest = match.group(2)
        corrected = f"{drive}\\{rest}"
        logger.info(f"[PATH] Chemin corrigé: '{path}' -> '{corrected}'")
        return corrected

    # Remplacer les slashes par des backslashes pour Windows
    if ':' in path and '/' in path:
        corrected = path.replace('/', '\\')
        if corrected != path:
            logger.info(f"[PATH] Slashes corrigés: '{path}' -> '{corrected}'")
        return corrected

    return path

class BackupService:
    """Service pour exécuter un backup d'une VM avec gestion de chaînes"""

    def __init__(self, backup_job: BackupJob):
        self.job = backup_job
        self.vm = backup_job.virtual_machine
        self.server = self.vm.server

        # Initialiser les managers de chaînes si remote storage est configuré
        self.chain_manager = None
        self.integrity_checker = None
        self.retention_manager = None

        self._init_chain_managers()

    def _init_chain_managers(self):
        """Initialise les managers de chaînes de backup"""
        try:
            # Récupérer le remote storage depuis le job ou le storage par défaut
            remote_storage = None

            if hasattr(self.job, 'remote_storage') and self.job.remote_storage:
                remote_storage = self.job.remote_storage
            else:
                # Essayer de récupérer le remote storage par défaut
                try:
                    remote_storage = RemoteStorageConfig.objects.get(
                        is_default=True,
                        is_active=True
                    )
                except RemoteStorageConfig.DoesNotExist:
                    logger.warning("[BACKUP-CHAIN] Aucun remote storage configuré, les chaînes ne seront pas gérées")
                    return

            if remote_storage:
                logger.info(f"[BACKUP-CHAIN] Initialisation des managers pour {self.vm.name}")

                self.chain_manager = BackupChainManager(remote_storage, self.vm.name)
                self.integrity_checker = IntegrityChecker(self.chain_manager)
                self.retention_manager = RetentionPolicyManager(self.chain_manager)

                logger.info("[BACKUP-CHAIN] Managers initialisés avec succès")

        except Exception as e:
            logger.error(f"[BACKUP-CHAIN] Erreur initialisation managers: {e}", exc_info=True)

    def execute_backup(self):
        """
        Exécute le backup d'une VM.
        Retourne True si succès, False sinon.
        """
        logger.info(f"[BACKUP] Début du backup pour VM {self.vm.name} (ID: {self.vm.id})")

        # Vérifier que la VM existe
        if not self.vm or not self.server:
            logger.error("[BACKUP] VM ou serveur introuvable pour le backup")
            self.job.status = 'failed'
            self.job.save()
            return False

        logger.info(f"[BACKUP] Serveur: {self.server.hostname}, VM UUID: {self.vm.vm_id}")
        logger.info(f"[BACKUP] Emplacement de sauvegarde: {self.job.backup_location}")

        # Connexion à l'ESXi
        vmware = VMwareService(
            host=self.server.hostname,
            user=self.server.username,
            password=self.server.password,
            port=self.server.port
        )

        logger.info(f"[BACKUP] Tentative de connexion à ESXi {self.server.hostname}...")
        if not vmware.connect():
            logger.error(f"[BACKUP] Impossible de se connecter au serveur {self.server.hostname}")
            self.job.status = 'failed'
            self.job.save()
            return False

        logger.info("[BACKUP] Connexion ESXi réussie")

        # Set status to running if not already set
        if self.job.status != 'running':
            self.job.status = 'running'
            self.job.started_at = timezone.now()
            self.job.save()
            logger.info("[BACKUP] Job marqué comme 'running'")

        try:
            # Normaliser et définir le chemin de destination du backup
            normalized_location = normalize_windows_path(self.job.backup_location)

            # Créer un nom de dossier avec timestamp: VmName_DD-MM-YYYY_HH-MM-SS
            timestamp = timezone.now().strftime('%d-%m-%Y_%H-%M-%S')
            folder_name = f"{self.vm.name}_{timestamp}"
            backup_dir = os.path.join(normalized_location, folder_name)

            # Sauvegarder le chemin complet dans le job
            self.job.backup_full_path = backup_dir
            self.job.save(update_fields=['backup_full_path'])

            logger.info(f"[BACKUP] Création du répertoire de backup: {backup_dir}")

            try:
                os.makedirs(backup_dir, exist_ok=True)
                logger.info(f"[BACKUP] Répertoire créé/vérifié: {backup_dir}")
            except OSError as path_error:
                # Erreur de chemin Windows malformé
                if "WinError 123" in str(path_error) or "syntaxe du nom de fichier" in str(path_error).lower():
                    error_msg = (
                        f"Chemin de sauvegarde invalide: '{self.job.backup_location}'. "
                        f"Sur Windows, utilisez le format 'D:\\backup' (pas '/D:\\backup'). "
                        f"Corrigez le chemin dans la configuration de la sauvegarde."
                    )
                    logger.error(f"[BACKUP] {error_msg}")
                    self.job.status = 'failed'
                    self.job.error_message = error_msg
                    self.job.completed_at = timezone.now()
                    self.job.save()
                    raise ValueError(error_msg) from path_error
                else:
                    # Autre erreur de chemin
                    raise

            # Définir le callback de progression
            def update_progress(percentage):
                self.job.progress_percentage = percentage
                self.job.save(update_fields=['progress_percentage'])
                logger.info(f"[BACKUP] Progression: {percentage}%")

            # Déterminer le mode de sauvegarde
            backup_mode = getattr(self.job, 'backup_mode', 'ovf')
            job_type = getattr(self.job, 'job_type', 'full')

            logger.info(f"[BACKUP] Type: {job_type}, Mode: {backup_mode}")

            # Pour les sauvegardes incrémentales, trouver la sauvegarde de base
            if job_type == 'incremental':
                base_backup = BackupJob.objects.filter(
                    virtual_machine=self.vm,
                    status='completed',
                    job_type='full',
                    backup_mode=backup_mode  # Même mode de backup
                ).order_by('-completed_at').first()

                if base_backup:
                    self.job.base_backup = base_backup
                    self.job.save()
                    logger.info(f"[BACKUP] Sauvegarde de base trouvée: {base_backup.id}")
                else:
                    logger.warning("[BACKUP] Aucune sauvegarde de base trouvée pour l'incrémentale")

            # Si c'est une sauvegarde incrémentale avec CBT
            if job_type == 'incremental' and backup_mode == 'cbt':
                logger.info(f"[BACKUP] Début de la sauvegarde incrémentale CBT pour {self.vm.name}...")

                # Trouver l'objet VM pyVmomi
                vm_obj = vmware._find_vm_by_uuid(self.vm.vm_id)
                if not vm_obj:
                    logger.error("[BACKUP] VM pyVmomi introuvable pour sauvegarde incrémentale")
                    self.job.status = 'failed'
                    self.job.error_message = "VM introuvable dans ESXi"
                    self.job.save()
                    return False

                # Trouver la dernière sauvegarde complète comme base
                base_backup_path = None
                base_backup = BackupJob.objects.filter(
                    virtual_machine=self.vm,
                    status='completed',
                    job_type='full'
                ).order_by('-completed_at').first()

                if base_backup:
                    # Utiliser backup_full_path si disponible, sinon construire avec backup_location et nom de VM
                    if base_backup.backup_full_path:
                        base_backup_path = normalize_windows_path(base_backup.backup_full_path)
                    elif base_backup.backup_location:
                        base_backup_path = os.path.join(
                            normalize_windows_path(base_backup.backup_location),
                            self.vm.name
                        )

                    if base_backup_path:
                        logger.info(f"[BACKUP] Sauvegarde de base trouvée: {base_backup_path}")
                        self.job.base_backup = base_backup
                        self.job.save()
                    else:
                        logger.warning("[BACKUP] Sauvegarde de base trouvée mais sans chemin valide")
                else:
                    logger.warning("[BACKUP] Aucune sauvegarde de base trouvée, sauvegarde complète sera effectuée")

                # Créer le service de sauvegarde incrémentale
                incremental_service = IncrementalBackupService(vmware, vm_obj, self.job)

                # Exécuter la sauvegarde incrémentale
                success = incremental_service.execute_incremental_backup(
                    backup_path=backup_dir,
                    base_backup_path=base_backup_path,
                    progress_callback=update_progress
                )

            else:
                # Sauvegarde complète OVF classique
                logger.info(f"[BACKUP] Début de l'export OVF pour {self.vm.name}...")
                success = vmware.export_vm(
                    self.vm.vm_id,
                    backup_dir,
                    progress_callback=update_progress,
                    backup_mode=backup_mode
                )

            logger.info(f"[BACKUP] Sauvegarde terminée, résultat: {success}")

            if success:
                # Vérifier que les fichiers ont bien été créés
                import glob
                files = glob.glob(os.path.join(backup_dir, '*'))
                logger.info(f"[BACKUP] Fichiers créés dans {backup_dir}: {files}")

                # Calculer la taille réelle du backup
                total_size_bytes = 0
                for file_path in files:
                    if os.path.isfile(file_path):
                        total_size_bytes += os.path.getsize(file_path)

                backup_size_mb = total_size_bytes / (1024 * 1024)
                self.job.backup_size_mb = backup_size_mb
                self.job.status = 'completed'
                self.job.completed_at = timezone.now()
                self.job.calculate_duration()
                self.job.save()
                logger.info(f"[BACKUP] Backup de {self.vm.name} terminé avec succès ({backup_size_mb:.2f} MB)")

                # Envoyer notification de succès
                try:
                    notification_service.send_notification(
                        'backup_success',
                        vm=self.vm,
                        backup_job=self.job
                    )
                except Exception as notif_error:
                    logger.warning(f"[BACKUP] Erreur envoi notification: {notif_error}")

                # Ajouter le backup à la chaîne si les managers sont initialisés
                if self.chain_manager:
                    try:
                        self._add_backup_to_chain(
                            backup_id=folder_name,
                            backup_type=job_type,
                            backup_mode=backup_mode,
                            backup_dir=backup_dir,
                            size_bytes=total_size_bytes,
                            files=[os.path.basename(f) for f in files]
                        )

                        # Vérifier l'intégrité du backup
                        if self.integrity_checker:
                            logger.info("[BACKUP-CHAIN] Vérification d'intégrité...")
                            self._verify_backup_integrity(folder_name, backup_dir)

                        # Appliquer la politique de rétention si configurée
                        if self.retention_manager:
                            logger.info("[BACKUP-CHAIN] Application de la politique de rétention...")
                            retention_results = self.retention_manager.apply_policy()
                            logger.info(
                                f"[BACKUP-CHAIN] Rétention: {retention_results['deleted_count']} "
                                f"backup(s) supprimé(s), {retention_results['kept_count']} conservé(s)"
                            )

                    except Exception as e:
                        logger.error(f"[BACKUP-CHAIN] Erreur gestion chaîne: {e}", exc_info=True)
            else:
                # Récupérer le message d'erreur détaillé depuis VMware service
                error_msg = vmware.last_error_message or "L'export OVF a échoué sans message d'erreur spécifique"
                self.job.status = 'failed'
                self.job.error_message = error_msg
                self.job.completed_at = timezone.now()
                self.job.calculate_duration()
                self.job.save()
                logger.error(f"[BACKUP] Backup de {self.vm.name} échoué: {error_msg}")

                # Envoyer notification d'échec
                try:
                    notification_service.send_notification(
                        'backup_failure',
                        vm=self.vm,
                        backup_job=self.job
                    )
                except Exception as notif_error:
                    logger.warning(f"[BACKUP] Erreur envoi notification: {notif_error}")

                return False

            return True

        except Exception as e:
            logger.exception(f"[BACKUP] ERREUR lors du backup de {self.vm.name}: {str(e)}")
            self.job.status = 'failed'
            self.job.error_message = str(e)
            self.job.completed_at = timezone.now()
            self.job.calculate_duration()
            self.job.save()

            # Envoyer notification d'échec
            try:
                notification_service.send_notification(
                    'backup_failure',
                    vm=self.vm,
                    backup_job=self.job
                )
            except Exception as notif_error:
                logger.warning(f"[BACKUP] Erreur envoi notification: {notif_error}")

            return False

        finally:
            logger.info("[BACKUP] Déconnexion de l'ESXi")
            vmware.disconnect()

    def _add_backup_to_chain(self, backup_id: str, backup_type: str, backup_mode: str,
                            backup_dir: str, size_bytes: int, files: list):
        """
        Ajoute un backup à la chaîne

        Args:
            backup_id: ID du backup (nom du dossier avec timestamp)
            backup_type: Type de backup ('full' ou 'incremental')
            backup_mode: Mode de backup ('ovf' ou 'cbt')
            backup_dir: Chemin complet du répertoire de backup
            size_bytes: Taille totale en octets
            files: Liste des fichiers créés
        """
        logger.info(f"[BACKUP-CHAIN] Ajout du backup {backup_id} à la chaîne")

        try:
            # Déterminer le change_id et la base_backup_id pour les incrémentales
            change_id = '*'  # Pour les full backups
            base_backup_id = None

            if backup_type == 'incremental':
                # Récupérer la dernière full backup comme base
                latest_full = self.chain_manager.get_latest_full_backup()

                if latest_full:
                    base_backup_id = latest_full['id']
                    logger.info(f"[BACKUP-CHAIN] Base backup: {base_backup_id}")

                    # Pour CBT, récupérer le change_id
                    if backup_mode == 'cbt':
                        # Le change_id devrait être sauvegardé dans les métadonnées du backup
                        # Pour l'instant, utiliser un placeholder
                        change_id = 'current_change_id'
                else:
                    logger.warning("[BACKUP-CHAIN] Pas de full backup de base trouvée pour l'incrémentale")

            # Préparer les données du backup
            backup_data = {
                'backup_id': backup_id,
                'type': backup_type,
                'mode': backup_mode,
                'timestamp': timezone.now().isoformat(),
                'change_id': change_id,
                'size_bytes': size_bytes,
                'files': files,
                'vm_uuid': self.vm.vm_id,
            }

            if backup_type == 'incremental' and base_backup_id:
                backup_data['base_backup_id'] = base_backup_id

            # Ajouter à la chaîne
            updated_chain = self.chain_manager.add_backup(backup_data)

            logger.info(
                f"[BACKUP-CHAIN] ✓ Backup ajouté à la chaîne. "
                f"Total backups: {updated_chain['total_backups']}"
            )

        except Exception as e:
            logger.error(f"[BACKUP-CHAIN] Erreur ajout à la chaîne: {e}", exc_info=True)
            raise

    def _verify_backup_integrity(self, backup_id: str, backup_dir: str):
        """
        Vérifie l'intégrité d'un backup

        Args:
            backup_id: ID du backup
            backup_dir: Répertoire du backup
        """
        try:
            logger.info(f"[BACKUP-CHAIN] Calcul des checksums pour {backup_id}...")

            # Calculer les checksums
            checksums = self.integrity_checker.calculate_checksums(backup_dir)

            logger.info(f"[BACKUP-CHAIN] {len(checksums)} fichiers vérifiés")

            # Créer le manifeste
            self.integrity_checker.create_manifest(backup_id, checksums)

            logger.info(f"[BACKUP-CHAIN] ✓ Manifeste d'intégrité créé pour {backup_id}")

        except Exception as e:
            logger.error(f"[BACKUP-CHAIN] Erreur vérification intégrité: {e}", exc_info=True)
            # Ne pas faire échouer le backup en cas d'erreur d'intégrité
            # Juste logger l'erreur
