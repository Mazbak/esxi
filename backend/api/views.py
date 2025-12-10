"""
API Views for ESXi Backup Manager
"""
import logging
import os
from datetime import datetime
from django.core.cache import cache
from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Sum, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

from esxi.models import ESXiServer, VirtualMachine, DatastoreInfo, EmailSettings
from esxi.email_service import EmailNotificationService
from backups.models import (
    BackupConfiguration, BackupJob, BackupLog,
    BackupSchedule, SnapshotSchedule, Snapshot,
    RemoteStorageConfig, NotificationConfig, NotificationLog,
    StoragePath, VMReplication, FailoverEvent,
    BackupVerification, BackupVerificationSchedule, OVFExportJob
)
from esxi.vmware_service import VMwareService
from backups.backup_service import BackupService
from api.serializers import (
    ESXiServerSerializer, VirtualMachineSerializer,
    DatastoreInfoSerializer, BackupConfigurationSerializer,
    BackupJobSerializer, BackupJobCreateSerializer,
    BackupScheduleSerializer, DashboardStatsSerializer,
    SnapshotScheduleSerializer, SnapshotScheduleCreateSerializer,
    SnapshotSerializer, RemoteStorageConfigSerializer,
    RemoteStorageConfigCreateSerializer, RemoteStorageTestSerializer,
    RestoreVMSerializer, RestoreVMDKSerializer, FileRecoverySerializer,
    ListFilesSerializer, SearchFilesSerializer, ValidateRestoreSerializer,
    NotificationConfigSerializer, NotificationLogSerializer, TestNotificationSerializer,
    StoragePathSerializer, VMReplicationSerializer, FailoverEventSerializer,
    ReplicationLogSerializer, BackupVerificationSerializer, BackupVerificationScheduleSerializer,
    EmailSettingsSerializer
)
from backups.tasks import execute_backup_job, execute_backup_verification  # Celery tasks


# ==========================================================
# 🔹 AUTHENTICATION
# ==========================================================
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """Login endpoint - returns auth token"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })

    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Logout endpoint - deletes auth token"""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """Get current authenticated user"""
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    })


# ==========================================================
# 🔹 ESXi SERVERS
# ==========================================================
class ESXiServerViewSet(viewsets.ModelViewSet):
    """ViewSet for ESXi Server management"""
    queryset = ESXiServer.objects.all()
    serializer_class = ESXiServerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to ESXi server"""
        server = self.get_object()
        vmware = VMwareService(
            host=server.hostname,
            user=server.username,
            password=server.password,
            port=server.port
        )
        try:
            if vmware.connect():
                server.connection_status = 'connected'
                server.last_connection = timezone.now()
                server.save()
                server_info = vmware.get_server_info()
                vmware.disconnect()
                return Response({
                    'status': 'success',
                    'message': 'Connexion réussie',
                    'server_info': server_info
                })
            else:
                raise Exception("Connexion impossible")
        except Exception as e:
            server.connection_status = 'error'
            server.save()
            return Response({'status': 'error', 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def sync_vms(self, request, pk=None):
        """Synchronise les VMs depuis le serveur ESXi"""
        server = self.get_object()
        vmware = VMwareService(
            host=server.hostname,
            user=server.username,
            password=server.password,
            port=server.port
        )
        if not vmware.connect():
            return Response({'status': 'error',
                             'message': 'Échec de la connexion à ESXi'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Sync VMs
        vms_data = vmware.get_virtual_machines()
        synced_count = 0
        for vm_data in vms_data:
            VirtualMachine.objects.update_or_create(
                server=server,
                vm_id=vm_data['vm_id'],
                defaults={
                    'name': vm_data['name'],
                    'power_state': vm_data['power_state'],
                    'num_cpu': vm_data['num_cpu'],
                    'memory_mb': vm_data['memory_mb'],
                    'disk_gb': vm_data['disk_gb'],
                    'guest_os': vm_data['guest_os'],
                    'guest_os_full': vm_data['guest_os_full'],
                    'tools_status': vm_data['tools_status'],
                    'ip_address': vm_data['ip_address'],
                }
            )
            synced_count += 1

        # Sync datastores
        datastores_data = vmware.get_datastores()
        for ds_data in datastores_data:
            DatastoreInfo.objects.update_or_create(
                server=server,
                name=ds_data['name'],
                defaults={
                    'type': ds_data['type'],
                    'capacity_gb': ds_data['capacity_gb'],
                    'free_space_gb': ds_data['free_space_gb'],
                    'accessible': ds_data['accessible'],
                }
            )

        vmware.disconnect()

        return Response({
            'status': 'success',
            'message': f'{synced_count} machines virtuelles synchronisées',
            'vms_count': synced_count,
            'datastores_count': len(datastores_data)
        })

    @action(detail=True, methods=['get'])
    def get_datastores(self, request, pk=None):
        """Récupère les datastores disponibles pour ce serveur ESXi"""
        server = self.get_object()
        vmware = VMwareService(
            host=server.hostname,
            user=server.username,
            password=server.password,
            port=server.port
        )

        if not vmware.connect():
            return Response(
                {'status': 'error', 'message': 'Échec de la connexion à ESXi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        datastores = vmware.get_datastores()
        vmware.disconnect()

        return Response({
            'status': 'success',
            'datastores': datastores
        })

    @action(detail=True, methods=['get'])
    def get_networks(self, request, pk=None):
        """Récupère les réseaux disponibles pour ce serveur ESXi"""
        server = self.get_object()
        vmware = VMwareService(
            host=server.hostname,
            user=server.username,
            password=server.password,
            port=server.port
        )

        if not vmware.connect():
            return Response(
                {'status': 'error', 'message': 'Échec de la connexion à ESXi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        networks = vmware.get_networks()
        vmware.disconnect()

        return Response({
            'status': 'success',
            'networks': networks
        })

    @action(detail=True, methods=['post'])
    def restore_ovf(self, request, pk=None):
        """Restaure un fichier OVF/OVA sur ce serveur ESXi"""
        server = self.get_object()

        # Récupérer les paramètres
        ovf_path = request.data.get('ovf_path')
        vm_name = request.data.get('vm_name')
        datastore_name = request.data.get('datastore_name')
        network_name = request.data.get('network_name', 'VM Network')
        power_on = request.data.get('power_on', False)

        if not ovf_path or not vm_name or not datastore_name:
            return Response(
                {'status': 'error', 'message': 'Paramètres manquants (ovf_path, vm_name, datastore_name requis)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le fichier existe
        import os
        import tarfile
        import tempfile
        import shutil

        if not os.path.exists(ovf_path):
            return Response(
                {'status': 'error', 'message': f'Fichier introuvable: {ovf_path}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        temp_dir = None
        try:
            logger.info(f"[RESTORE] Début de la restauration: {ovf_path} vers {server.hostname}")

            # Si c'est un fichier OVA, l'extraire d'abord
            actual_ovf_path = ovf_path
            if ovf_path.lower().endswith('.ova'):
                logger.info(f"[RESTORE] Extraction du fichier OVA...")
                temp_dir = tempfile.mkdtemp(prefix='ova_extract_')

                # Extraire le contenu de l'OVA (fichier TAR)
                with tarfile.open(ovf_path, 'r') as tar:
                    tar.extractall(path=temp_dir)

                # Trouver le fichier .ovf dans le répertoire extrait
                ovf_files = [f for f in os.listdir(temp_dir) if f.endswith('.ovf')]
                if not ovf_files:
                    raise Exception("Aucun fichier OVF trouvé dans l'archive OVA")

                actual_ovf_path = os.path.join(temp_dir, ovf_files[0])
                logger.info(f"[RESTORE] Fichier OVF extrait: {actual_ovf_path}")

            # Connexion au serveur ESXi
            vmware = VMwareService(
                host=server.hostname,
                user=server.username,
                password=server.password,
                port=server.port
            )

            if not vmware.connect():
                raise Exception("Impossible de se connecter au serveur ESXi")

            # Générer un ID unique pour suivre la progression
            import uuid
            import threading
            restore_id = str(uuid.uuid4())

            # Initialiser la progression dans le cache
            cache.set(f'restore_progress_{restore_id}', {
                'progress': 0,
                'status': 'starting',
                'message': 'Initialisation de la restauration...'
            }, timeout=3600)  # 1 heure

            # Callback pour mettre à jour la progression
            def progress_callback(progress_percent):
                try:
                    # Messages descriptifs selon l'étape de progression
                    # 0-2%: Préparation
                    # 2-94%: Transfert
                    # 94-100%: Finalisation
                    if progress_percent < 2:
                        message = 'Préparation de la restauration...'
                        status_val = 'preparing'
                    elif progress_percent < 94:
                        message = f'Transfert des disques vers ESXi... {int(progress_percent)}%'
                        status_val = 'uploading'
                    elif progress_percent < 100:
                        message = 'Finalisation de la restauration...'
                        status_val = 'completing'
                    else:
                        message = 'Restauration terminée avec succès'
                        status_val = 'completed'

                    progress_data = {
                        'progress': int(progress_percent),  # Arrondir pour affichage
                        'status': status_val,
                        'message': message
                    }
                    cache.set(f'restore_progress_{restore_id}', progress_data, timeout=3600)
                    logger.info(f"[RESTORE] Progression mise à jour: {int(progress_percent)}% (ID: {restore_id})")
                except Exception as e:
                    logger.error(f"[RESTORE] Erreur mise à jour progression: {e}")

            # Fonction pour exécuter le déploiement en arrière-plan
            def deploy_in_background():
                try:
                    logger.info(f"[RESTORE] Déploiement de l'OVF sur {datastore_name}... (ID: {restore_id})")
                    success = vmware.deploy_ovf(
                        ovf_path=actual_ovf_path,
                        vm_name=vm_name,
                        datastore_name=datastore_name,
                        network_name=network_name,
                        power_on=power_on,
                        progress_callback=progress_callback,
                        restore_id=restore_id  # Passer l'ID pour vérifier l'annulation
                    )

                    if success:
                        logger.info(f"[RESTORE] Restauration réussie: {vm_name}")
                        cache.set(f'restore_progress_{restore_id}', {
                            'progress': 100,
                            'status': 'completed',
                            'message': 'Restauration terminée avec succès'
                        }, timeout=3600)
                    else:
                        logger.error(f"[RESTORE] Échec du déploiement OVF")
                        cache.set(f'restore_progress_{restore_id}', {
                            'progress': 0,
                            'status': 'error',
                            'message': 'Échec du déploiement OVF'
                        }, timeout=3600)
                except Exception as e:
                    logger.exception(f"[RESTORE] Erreur dans le thread: {e}")
                    cache.set(f'restore_progress_{restore_id}', {
                        'progress': 0,
                        'status': 'error',
                        'message': f'Erreur: {str(e)}'
                    }, timeout=3600)
                finally:
                    vmware.disconnect()
                    # Nettoyer le répertoire temporaire
                    if temp_dir and os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                            logger.info(f"[RESTORE] Répertoire temporaire nettoyé: {temp_dir}")
                        except Exception as e:
                            logger.warning(f"[RESTORE] Impossible de nettoyer {temp_dir}: {e}")

            # Lancer le déploiement dans un thread séparé
            thread = threading.Thread(target=deploy_in_background, daemon=True)
            thread.start()

            # Retourner immédiatement avec le restore_id
            return Response({
                'status': 'started',
                'message': 'Restauration démarrée en arrière-plan',
                'restore_id': restore_id
            })

        except Exception as e:
            logger.exception(f"[RESTORE] Erreur lors de la restauration: {str(e)}")

            # Si on a un restore_id, mettre à jour la progression avec l'erreur
            if 'restore_id' in locals():
                cache.set(f'restore_progress_{restore_id}', {
                    'progress': 0,
                    'status': 'error',
                    'message': f'Erreur: {str(e)}'
                }, timeout=3600)

            return Response(
                {'status': 'error', 'message': str(e), 'restore_id': locals().get('restore_id')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        # Note: Le nettoyage du répertoire temporaire se fait dans le thread en arrière-plan

    @action(detail=False, methods=['get'], url_path='restore-progress/(?P<restore_id>[^/.]+)')
    def restore_progress(self, request, restore_id=None):
        """Récupère la progression d'une restauration en cours"""
        progress_data = cache.get(f'restore_progress_{restore_id}')

        if progress_data is None:
            return Response(
                {'status': 'error', 'message': 'ID de restauration introuvable ou expiré'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(progress_data)

    @action(detail=False, methods=['post'], url_path='cancel-restore/(?P<restore_id>[^/.]+)')
    def cancel_restore(self, request, restore_id=None):
        """Annule une restauration en cours"""
        try:
            # Récupérer les données de progression
            progress_data = cache.get(f'restore_progress_{restore_id}')

            if progress_data is None:
                return Response(
                    {'status': 'error', 'message': 'ID de restauration introuvable ou expiré'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Vérifier si la restauration est annulable
            if progress_data['status'] in ['completed', 'error', 'cancelled']:
                return Response(
                    {'status': 'error', 'message': f'La restauration est déjà {progress_data["status"]}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Marquer comme annulée dans le cache
            logger.info(f"[RESTORE] Annulation demandée pour: {restore_id}")
            cache.set(f'restore_cancel_{restore_id}', True, timeout=3600)
            cache.set(f'restore_progress_{restore_id}', {
                'progress': progress_data.get('progress', 0),
                'status': 'cancelled',
                'message': 'Restauration annulée par l\'utilisateur'
            }, timeout=3600)

            return Response({
                'status': 'success',
                'message': 'Demande d\'annulation envoyée'
            })

        except Exception as e:
            logger.exception(f"[RESTORE] Erreur lors de l'annulation: {str(e)}")
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================================
# 🔹 VIRTUAL MACHINES
# ==========================================================
class VirtualMachineViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for Virtual Machines"""
    queryset = VirtualMachine.objects.all()
    serializer_class = VirtualMachineSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['server', 'power_state']
    search_fields = ['name', 'guest_os', 'ip_address']
    ordering_fields = ['name', 'created_at', 'memory_mb', 'disk_gb']

    @action(detail=True, methods=['post'])
    def remove_all_snapshots(self, request, pk=None):
        """
        Supprime tous les snapshots d'une VM.
        Utilisé pour préparer une VM à la réplication.
        """
        vm = self.get_object()
        server = vm.server

        try:
            # Créer le service VMware
            vmware = VMwareService(
                host=server.hostname,
                user=server.username,
                password=server.password,
                port=server.port or 443
            )

            # Connexion
            if not vmware.connect():
                return Response(
                    {'error': f'Impossible de se connecter au serveur {server.hostname}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Supprimer tous les snapshots
            result = vmware.remove_all_snapshots(vm.vm_id)

            # Déconnexion
            vmware.disconnect()

            if result['success']:
                return Response({
                    'success': True,
                    'message': result['message'],
                    'snapshots_removed': result['snapshots_removed']
                })
            else:
                return Response(
                    {'error': result['message']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception(f"Erreur lors de la suppression des snapshots: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def power_off(self, request, pk=None):
        """
        Éteint une VM.
        """
        vm = self.get_object()
        server = vm.server

        try:
            # Créer le service VMware
            vmware = VMwareService(
                host=server.hostname,
                user=server.username,
                password=server.password,
                port=server.port or 443
            )

            # Connexion
            if not vmware.connect():
                return Response(
                    {'error': f'Impossible de se connecter au serveur {server.hostname}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Éteindre la VM
            result = vmware.power_off_vm(vm.vm_id)

            # Déconnexion
            vmware.disconnect()

            if result['success']:
                return Response({
                    'success': True,
                    'message': result['message'],
                    'was_powered_on': result['was_powered_on']
                })
            else:
                return Response(
                    {'error': result['message']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception(f"Erreur lors de l'extinction de la VM: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def power_on(self, request, pk=None):
        """
        Allume une VM.
        """
        vm = self.get_object()
        server = vm.server

        try:
            # Créer le service VMware
            vmware = VMwareService(
                host=server.hostname,
                user=server.username,
                password=server.password,
                port=server.port or 443
            )

            # Connexion
            if not vmware.connect():
                return Response(
                    {'error': f'Impossible de se connecter au serveur {server.hostname}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Allumer la VM
            result = vmware.power_on_vm(vm.vm_id)

            # Déconnexion
            vmware.disconnect()

            if result['success']:
                return Response({
                    'success': True,
                    'message': result['message']
                })
            else:
                return Response(
                    {'error': result['message']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception(f"Erreur lors de l'allumage de la VM: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================================
# 🔹 DATASTORES
# ==========================================================
class DatastoreInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for Datastore Info"""
    queryset = DatastoreInfo.objects.all()
    serializer_class = DatastoreInfoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['server', 'accessible']


# ==========================================================
# 🔹 BACKUP CONFIGURATIONS
# ==========================================================
class BackupConfigurationViewSet(viewsets.ModelViewSet):
    """Manage Backup Configurations"""
    queryset = BackupConfiguration.objects.all()
    serializer_class = BackupConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ==========================================================
# 🔹 BACKUP JOBS
# ==========================================================
class BackupJobViewSet(viewsets.ModelViewSet):
    """Manage Backup Jobs"""
    queryset = BackupJob.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'job_type', 'virtual_machine']
    ordering_fields = ['created_at', 'started_at', 'completed_at']

    def get_serializer_class(self):
        return BackupJobCreateSerializer if self.action == 'create' else BackupJobSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """Supprime le job de backup ET le dossier physique associé"""
        import os
        import shutil
        from backups.backup_service import normalize_windows_path

        # Récupérer le chemin du dossier de sauvegarde
        backup_folder = instance.backup_full_path if instance.backup_full_path else None

        if not backup_folder and instance.backup_location:
            # Fallback pour les anciennes sauvegardes sans backup_full_path
            backup_folder = os.path.join(
                normalize_windows_path(instance.backup_location),
                instance.virtual_machine.name
            )

        # Supprimer d'abord l'entrée en base de données
        instance.delete()

        # Ensuite tenter de supprimer le dossier physique
        if backup_folder:
            backup_folder = normalize_windows_path(backup_folder)
            try:
                if os.path.exists(backup_folder):
                    logger.info(f"[DELETE] Suppression du dossier de sauvegarde: {backup_folder}")
                    shutil.rmtree(backup_folder)
                    logger.info(f"[DELETE] Dossier supprimé avec succès: {backup_folder}")
                else:
                    logger.warning(f"[DELETE] Le dossier n'existe pas: {backup_folder}")
            except PermissionError as e:
                logger.error(f"[DELETE] Permission refusée pour supprimer {backup_folder}: {e}")
            except Exception as e:
                logger.error(f"[DELETE] Erreur lors de la suppression du dossier {backup_folder}: {e}")

    # === Actions ===
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a backup asynchronously"""
        job = self.get_object()
        if job.status not in ['pending', 'failed']:
            logger.warning(f"Tentative de démarrage du job {job.id} avec statut '{job.status}'")
            return Response({
                'status': 'error',
                'message': f'Job déjà en cours ou terminé (statut actuel: {job.status})',
                'current_status': job.status
            }, status=400)

        try:
            job.status = 'running'
            job.started_at = timezone.now()
            job.progress_percentage = 0
            job.save()

            # Try to use Celery if available, otherwise run in a thread
            # Vérifier si Celery est disponible en testant la connexion au broker
            use_celery = False
            try:
                from celery import current_app
                # Essayer de pinger le broker Celery avec un timeout court
                inspect = current_app.control.inspect(timeout=1.0)
                active = inspect.active()
                if active is not None:
                    use_celery = True
                    logger.info(f"[BACKUP] Celery disponible, utilisation de Celery")
                else:
                    logger.warning(f"[BACKUP] Celery broker non accessible, utilisation du fallback sur threads")
            except Exception as e:
                logger.warning(f"[BACKUP] Celery non disponible ({e}), utilisation du fallback sur threads")

            if use_celery:
                # Lancer avec Celery
                execute_backup_job.delay(job.id)
                message = 'Sauvegarde lancée en tâche de fond (Celery)'
            else:
                # Fallback : exécuter dans un thread séparé
                from backups.backup_service import BackupService
                import threading

                def run_backup(job_id):
                    try:
                        # Reload job from database to ensure fresh data
                        backup_job = BackupJob.objects.get(id=job_id)
                        BackupService(backup_job).execute_backup()
                    except Exception as e:
                        logger.error(f"Erreur lors du backup: {str(e)}")

                # Start backup in background thread
                backup_thread = threading.Thread(target=run_backup, args=(job.id,), daemon=True)
                backup_thread.start()
                message = 'Sauvegarde lancée en tâche de fond (Thread)'

            # Try to create log, but don't fail if it doesn't work
            try:
                BackupLog.objects.create(job=job, level='info', message=message)
            except Exception:
                pass  # Log creation is optional

            return Response({'status': 'success', 'message': message})
        except Exception as e:
            job.status = 'failed'
            job.save()
            try:
                BackupLog.objects.create(job=job, level='error', message=str(e))
            except Exception:
                pass  # Log creation is optional
            return Response({'status': 'error', 'message': str(e)}, status=500)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running job"""
        job = self.get_object()
        if job.status != 'running':
            return Response({'status': 'error', 'message': 'Job non en cours'}, status=400)
        job.status = 'cancelled'
        job.completed_at = timezone.now()
        job.calculate_duration()
        job.save()
        BackupLog.objects.create(job=job, level='warning', message='Sauvegarde annulée par utilisateur')
        return Response({'status': 'success', 'message': 'Sauvegarde annulée'})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Backup job statistics"""
        total = self.queryset.count()
        completed = self.queryset.filter(status='completed').count()
        failed = self.queryset.filter(status='failed').count()
        running = self.queryset.filter(status='running').count()
        total_size = self.queryset.filter(status='completed').aggregate(Sum('backup_size_mb'))['backup_size_mb__sum'] or 0

        return Response({
            'total_backups': total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'total_size_gb': round(total_size / 1024, 2)
        })

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore/deploy an OVF backup to ESXi"""
        job = self.get_object()

        # Vérifier que c'est bien un backup OVF complété
        if job.backup_mode != 'ovf':
            return Response({
                'status': 'error',
                'message': 'Seuls les backups OVF peuvent être restaurés'
            }, status=400)

        if job.status != 'completed':
            return Response({
                'status': 'error',
                'message': 'Seuls les backups complétés peuvent être restaurés'
            }, status=400)

        # Récupérer les paramètres de restauration
        vm_name = request.data.get('vm_name')
        datastore_name = request.data.get('datastore_name')
        esxi_server_id = request.data.get('esxi_server_id')
        network_name = request.data.get('network_name', 'VM Network')
        power_on = request.data.get('power_on', False)

        if not vm_name or not datastore_name or not esxi_server_id:
            return Response({
                'status': 'error',
                'message': 'vm_name, datastore_name et esxi_server_id sont requis'
            }, status=400)

        try:
            # Récupérer le serveur ESXi
            esxi_server = ESXiServer.objects.get(id=esxi_server_id)

            # Trouver le fichier OVF dans le dossier de backup
            import os
            from backups.backup_service import normalize_windows_path

            # Utiliser backup_full_path si disponible, sinon backup_location
            backup_folder = job.backup_full_path if job.backup_full_path else job.backup_location
            backup_folder = normalize_windows_path(backup_folder)
            ovf_file = None

            if os.path.exists(backup_folder):
                for file_name in os.listdir(backup_folder):
                    if file_name.endswith('.ovf'):
                        ovf_file = os.path.join(backup_folder, file_name)
                        break

            if not ovf_file:
                return Response({
                    'status': 'error',
                    'message': f'Fichier OVF introuvable dans le dossier de backup: {backup_folder}'
                }, status=404)

            # Créer un nouveau job de restauration (optionnel, pour tracking)
            # Pour l'instant, on fait la restauration directement

            # Démarrer la restauration dans un thread
            import threading

            def run_restore():
                try:
                    vmware = VMwareService(
                        host=esxi_server.hostname,
                        user=esxi_server.username,
                        password=esxi_server.password,
                        port=esxi_server.port
                    )

                    if vmware.connect():
                        logger.info(f"[RESTORE] Déploiement de {ovf_file} vers {esxi_server.hostname}")

                        success = vmware.deploy_ovf(
                            ovf_path=ovf_file,
                            vm_name=vm_name,
                            datastore_name=datastore_name,
                            network_name=network_name,
                            power_on=power_on
                        )

                        vmware.disconnect()

                        if success:
                            logger.info(f"[RESTORE] Déploiement réussi: {vm_name}")
                        else:
                            logger.error(f"[RESTORE] Échec du déploiement: {vm_name}")
                    else:
                        logger.error(f"[RESTORE] Échec de connexion à {esxi_server.hostname}")

                except Exception as e:
                    logger.exception(f"[RESTORE] Erreur lors de la restauration: {str(e)}")

            # Lancer la restauration en arrière-plan
            restore_thread = threading.Thread(target=run_restore, daemon=True)
            restore_thread.start()

            return Response({
                'status': 'success',
                'message': f'Restauration de {vm_name} lancée en arrière-plan'
            })

        except ESXiServer.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Serveur ESXi introuvable'
            }, status=404)
        except Exception as e:
            logger.exception(f"[RESTORE] Erreur: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)


# ==========================================================
# 🔹 BACKUP SCHEDULES
# ==========================================================
class BackupScheduleViewSet(viewsets.ModelViewSet):
    """Manage scheduled backups"""
    queryset = BackupSchedule.objects.all()
    serializer_class = BackupScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active', 'frequency', 'virtual_machine']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save()
        return Response({'status': 'success', 'is_active': schedule.is_active})


# ==========================================================
# 🔹 SNAPSHOT SCHEDULES
# ==========================================================
class SnapshotScheduleViewSet(viewsets.ModelViewSet):
    """Manage scheduled snapshots"""
    queryset = SnapshotSchedule.objects.all().select_related('virtual_machine')
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active', 'frequency', 'virtual_machine']

    def get_serializer_class(self):
        if self.action == 'create':
            return SnapshotScheduleCreateSerializer
        return SnapshotScheduleSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activer/désactiver un planning de snapshot"""
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save()
        return Response({'status': 'success', 'is_active': schedule.is_active})

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Exécuter un snapshot maintenant"""
        schedule = self.get_object()
        vm = schedule.virtual_machine

        # Créer un snapshot
        import threading
        from datetime import datetime

        snapshot_name = f"snapshot-{vm.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        def create_snapshot_task(vm_id, snap_name, include_memory, schedule_id):
            from backups.models import Snapshot
            from esxi.vmware_service import VMwareService

            snapshot = Snapshot.objects.create(
                virtual_machine_id=vm_id,
                schedule_id=schedule_id,
                snapshot_name=snap_name,
                include_memory=include_memory,
                status='creating'
            )

            try:
                vm_obj = VirtualMachine.objects.get(id=vm_id)
                server = vm_obj.server

                vmware = VMwareService(
                    host=server.hostname,
                    user=server.username,
                    password=server.password,
                    port=server.port
                )

                if vmware.connect():
                    success = vmware.create_snapshot(
                        vm_obj.vm_id,
                        snap_name,
                        description=f"Snapshot automatique - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        memory=include_memory
                    )

                    if success:
                        snapshot.status = 'completed'
                        snapshot.save()
                        logger.info(f"[SNAPSHOT] Snapshot créé: {snap_name}")
                    else:
                        snapshot.status = 'failed'
                        snapshot.save()
                        logger.error(f"[SNAPSHOT] Échec de création: {snap_name}")

                    vmware.disconnect()
                else:
                    snapshot.status = 'failed'
                    snapshot.save()
                    logger.error(f"[SNAPSHOT] Connexion ESXi échouée")

            except Exception as e:
                snapshot.status = 'failed'
                snapshot.save()
                logger.exception(f"[SNAPSHOT] Erreur: {str(e)}")

        # Lancer en background
        thread = threading.Thread(
            target=create_snapshot_task,
            args=(vm.id, snapshot_name, schedule.include_memory, schedule.id),
            daemon=True
        )
        thread.start()

        # Mettre à jour last_run
        schedule.last_run = timezone.now()
        schedule.save()

        return Response({
            'status': 'success',
            'message': f'Snapshot "{snapshot_name}" en cours de création'
        })


# ==========================================================
# 🔹 SNAPSHOTS
# ==========================================================
class SnapshotViewSet(viewsets.ModelViewSet):
    """Manage VM snapshots"""
    queryset = Snapshot.objects.all().select_related('virtual_machine', 'schedule')
    serializer_class = SnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'virtual_machine']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def revert(self, request, pk=None):
        """Restaurer un snapshot"""
        snapshot = self.get_object()
        vm = snapshot.virtual_machine
        server = vm.server

        try:
            vmware = VMwareService(
                host=server.hostname,
                user=server.username,
                password=server.password,
                port=server.port
            )

            if vmware.connect():
                success = vmware.revert_snapshot(vm.vm_id, snapshot.snapshot_name)
                vmware.disconnect()

                if success:
                    return Response({'status': 'success', 'message': 'Snapshot restauré'})
                else:
                    return Response(
                        {'status': 'error', 'message': 'Échec de la restauration'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    {'status': 'error', 'message': 'Connexion ESXi échouée'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception(f"[SNAPSHOT] Erreur revert: {str(e)}")
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'])
    def delete_snapshot(self, request, pk=None):
        """Supprimer un snapshot dans ESXi"""
        snapshot = self.get_object()
        vm = snapshot.virtual_machine
        server = vm.server

        try:
            vmware = VMwareService(
                host=server.hostname,
                user=server.username,
                password=server.password,
                port=server.port
            )

            if vmware.connect():
                success = vmware.delete_snapshot(vm.vm_id, snapshot.snapshot_name)
                vmware.disconnect()

                # Supprimer de la base de données même si la suppression ESXi a échoué
                # (le snapshot peut avoir été déjà supprimé manuellement du serveur)
                snapshot.delete()

                if success:
                    return Response({'status': 'success', 'message': 'Snapshot supprimé'})
                else:
                    logger.warning(f"[SNAPSHOT] Snapshot {snapshot.snapshot_name} non trouvé sur ESXi, supprimé de la base de données")
                    return Response({'status': 'success', 'message': 'Snapshot supprimé de la base de données (déjà absent du serveur)'})
            else:
                return Response(
                    {'status': 'error', 'message': 'Connexion ESXi échouée'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception(f"[SNAPSHOT] Erreur delete: {str(e)}")
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================================
# 🔹 DASHBOARD
# ==========================================================
class DashboardViewSet(viewsets.ViewSet):
    """Dashboard statistics and summary"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total_backups = BackupJob.objects.count()
        completed = BackupJob.objects.filter(status='completed').count()
        failed = BackupJob.objects.filter(status='failed').count()
        running = BackupJob.objects.filter(status='running').count()
        total_size = BackupJob.objects.filter(status='completed').aggregate(Sum('backup_size_mb'))['backup_size_mb__sum'] or 0

        stats = {
            'total_servers': ESXiServer.objects.filter(is_active=True).count(),
            'total_vms': VirtualMachine.objects.count(),
            'total_backups': total_backups,
            'successful_backups': completed,
            'failed_backups': failed,
            'running_backups': running,
            'total_backup_size_gb': round(total_size / 1024, 2),
            'active_schedules': BackupSchedule.objects.filter(is_active=True).count(),
        }

        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent_backups(self, request):
        """Return latest 10 backup jobs"""
        recent = BackupJob.objects.order_by('-created_at')[:10]
        serializer = BackupJobSerializer(recent, many=True)
        return Response(serializer.data)


# ==========================================================
# 🔹 REMOTE STORAGE CONFIGURATION
# ==========================================================
class RemoteStorageConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet professionnel pour gestion du stockage distant

    Fonctionnalités:
    - CRUD complet des configurations
    - Test de connexion avant sauvegarde
    - Test de configuration existante
    - Vérification intégrité (connectivité, auth, permissions, espace)
    """
    queryset = RemoteStorageConfig.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action in ['create', 'update', 'partial_update']:
            return RemoteStorageConfigCreateSerializer
        return RemoteStorageConfigSerializer

    def perform_create(self, serializer):
        """Associe l'utilisateur créateur"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """
        Teste une configuration de stockage AVANT sauvegarde

        POST /api/remote-storage/test_connection/
        Body: {
            "protocol": "smb",
            "host": "192.168.1.100",
            "port": 445,
            "share_name": "backups",
            "base_path": "esxi",
            "username": "admin",
            "password": "password",
            "domain": "WORKGROUP"
        }

        Returns: {
            "success": true/false,
            "connectivity": {...},
            "authentication": true/false,
            "write_permissions": true/false,
            "available_space_gb": 500.5,
            "message": "...",
            "errors": [...]
        }
        """
        from backups.remote_storage import RemoteStorageManager

        serializer = RemoteStorageTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer une configuration temporaire (non sauvegardée)
        test_config = RemoteStorageConfig(
            name='__test__',
            protocol=serializer.validated_data['protocol'],
            host=serializer.validated_data['host'],
            port=serializer.validated_data.get('port', 445),
            share_name=serializer.validated_data.get('share_name', ''),
            base_path=serializer.validated_data.get('base_path', ''),
            username=serializer.validated_data.get('username', ''),
            domain=serializer.validated_data.get('domain', 'WORKGROUP')
        )

        # Chiffrer le mot de passe si fourni
        password = serializer.validated_data.get('password', '')
        if password:
            test_config.set_password(password)

        logger.info(f"[STORAGE_TEST] Test configuration: {test_config.protocol}://{test_config.host}")

        # Créer le manager
        storage_manager = RemoteStorageManager(test_config)

        result = {
            'success': False,
            'connectivity': {},
            'authentication': False,
            'write_permissions': False,
            'available_space_gb': 0,
            'message': '',
            'errors': []
        }

        try:
            # 1. Test connectivité
            logger.info("[STORAGE_TEST] Test 1/4: Connectivité réseau...")
            connectivity = storage_manager.test_connectivity(timeout=10)
            result['connectivity'] = connectivity

            if not connectivity['overall_success']:
                result['message'] = "Échec test connectivité"
                result['errors'] = connectivity['errors']
                logger.warning(f"[STORAGE_TEST] ✗ Connectivité échouée: {connectivity['errors']}")
                return Response(result, status=status.HTTP_200_OK)

            logger.info("[STORAGE_TEST] ✓ Connectivité OK")

            # 2. Test authentification
            if test_config.protocol in ['smb', 'nfs']:
                logger.info("[STORAGE_TEST] Test 2/4: Authentification...")
                try:
                    auth_success = storage_manager.test_authentication()
                    result['authentication'] = auth_success

                    if not auth_success:
                        result['message'] = "Échec authentification"
                        result['errors'].append("Credentials invalides")
                        logger.warning("[STORAGE_TEST] ✗ Authentification échouée")
                        return Response(result, status=status.HTTP_200_OK)

                    logger.info("[STORAGE_TEST] ✓ Authentification OK")

                except Exception as e:
                    result['message'] = f"Erreur authentification: {str(e)}"
                    result['errors'].append(str(e))
                    logger.error(f"[STORAGE_TEST] ✗ Erreur auth: {e}")
                    return Response(result, status=status.HTTP_200_OK)

            # 3. Test permissions d'écriture
            logger.info("[STORAGE_TEST] Test 3/4: Permissions d'écriture...")
            try:
                write_success = storage_manager.test_write_permissions()
                result['write_permissions'] = write_success

                if not write_success:
                    result['message'] = "Permissions d'écriture insuffisantes"
                    result['errors'].append("Impossible d'écrire sur le stockage")
                    logger.warning("[STORAGE_TEST] ✗ Permissions insuffisantes")
                    return Response(result, status=status.HTTP_200_OK)

                logger.info("[STORAGE_TEST] ✓ Permissions OK")

            except Exception as e:
                result['message'] = f"Erreur test permissions: {str(e)}"
                result['errors'].append(str(e))
                logger.error(f"[STORAGE_TEST] ✗ Erreur permissions: {e}")
                return Response(result, status=status.HTTP_200_OK)

            # 4. Calcul espace disponible
            logger.info("[STORAGE_TEST] Test 4/4: Espace disponible...")
            try:
                available_bytes = storage_manager.get_available_space()
                available_gb = available_bytes / (1024 ** 3)
                result['available_space_gb'] = round(available_gb, 2)
                logger.info(f"[STORAGE_TEST] ✓ Espace disponible: {available_gb:.2f} GB")

            except Exception as e:
                logger.warning(f"[STORAGE_TEST] ! Impossible de calculer l'espace: {e}")
                result['available_space_gb'] = 0

            # Tous les tests réussis
            result['success'] = True
            result['message'] = f"✓ Configuration valide ! Espace disponible: {result['available_space_gb']:.2f} GB"
            logger.info("[STORAGE_TEST] ✓✓✓ TOUS LES TESTS RÉUSSIS ✓✓✓")

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"[STORAGE_TEST] Erreur inattendue: {e}")
            result['message'] = f"Erreur inattendue: {str(e)}"
            result['errors'].append(str(e))
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """
        Teste une configuration EXISTANTE

        POST /api/remote-storage/{id}/test/

        Returns: Mêmes infos que test_connection
        """
        from backups.remote_storage import RemoteStorageManager

        storage_config = self.get_object()
        logger.info(f"[STORAGE_TEST] Test configuration existante: {storage_config.name}")

        storage_manager = RemoteStorageManager(storage_config)

        result = {
            'success': False,
            'connectivity': {},
            'authentication': False,
            'write_permissions': False,
            'available_space_gb': 0,
            'message': '',
            'errors': []
        }

        try:
            # Effectuer tous les tests
            connectivity = storage_manager.test_connectivity(timeout=10)
            result['connectivity'] = connectivity

            if not connectivity['overall_success']:
                storage_config.last_test_at = timezone.now()
                storage_config.last_test_success = False
                storage_config.last_test_message = "Échec connectivité: " + ', '.join(connectivity['errors'])
                storage_config.save()

                result['message'] = storage_config.last_test_message
                result['errors'] = connectivity['errors']
                return Response(result, status=status.HTTP_200_OK)

            # Tests complets
            if storage_config.protocol in ['smb', 'nfs']:
                result['authentication'] = storage_manager.test_authentication()

            result['write_permissions'] = storage_manager.test_write_permissions()

            available_bytes = storage_manager.get_available_space()
            result['available_space_gb'] = round(available_bytes / (1024 ** 3), 2)

            # Succès
            result['success'] = True
            result['message'] = f"✓ Configuration valide ! Espace: {result['available_space_gb']:.2f} GB"

            # Mettre à jour la configuration
            storage_config.last_test_at = timezone.now()
            storage_config.last_test_success = True
            storage_config.last_test_message = result['message']
            storage_config.save()

            logger.info(f"[STORAGE_TEST] ✓ Test réussi pour {storage_config.name}")

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"[STORAGE_TEST] Erreur test: {e}")

            storage_config.last_test_at = timezone.now()
            storage_config.last_test_success = False
            storage_config.last_test_message = f"Erreur: {str(e)}"
            storage_config.save()

            result['message'] = storage_config.last_test_message
            result['errors'].append(str(e))

            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Retourne uniquement les configurations actives

        GET /api/remote-storage/active/
        """
        active_configs = RemoteStorageConfig.objects.filter(is_active=True)
        serializer = self.get_serializer(active_configs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        Retourne la configuration par défaut

        GET /api/remote-storage/default/
        """
        try:
            default_config = RemoteStorageConfig.objects.get(is_default=True, is_active=True)
            serializer = self.get_serializer(default_config)
            return Response(serializer.data)
        except RemoteStorageConfig.DoesNotExist:
            return Response(
                {'detail': 'Aucune configuration par défaut définie'},
                status=status.HTTP_404_NOT_FOUND
            )


# ==========================================================
# 🔹 RESTORATION API
# ==========================================================

class RestoreViewSet(viewsets.ViewSet):
    """
    ViewSet pour les opérations de restauration

    Endpoints:
    - POST /api/restore/vm/ - Restaurer une VM complète
    - POST /api/restore/vmdk/ - Restaurer un VMDK individuel
    - POST /api/restore/files/ - Récupérer des fichiers
    - POST /api/restore/list-files/ - Lister les fichiers dans un backup
    - POST /api/restore/search-files/ - Rechercher des fichiers
    - GET /api/restore/list-vmdks/{backup_id}/ - Lister les VMDK d'un backup
    - POST /api/restore/validate-vm/ - Valider une restauration VM
    - POST /api/restore/validate-vmdk/ - Valider une restauration VMDK
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_restore_services(self, vm_name: str):
        """
        Initialise les services de restauration pour une VM

        Args:
            vm_name: Nom de la VM

        Returns:
            Tuple (vm_restore, vmdk_restore, file_recovery) ou None si erreur
        """
        try:
            from backups.backup_chain.chain_manager import BackupChainManager
            from backups.backup_chain.integrity_checker import IntegrityChecker
            from backups.restore import VMRestoreService, VMDKRestoreService, FileRecoveryService

            # Récupérer le remote storage par défaut
            try:
                remote_storage = RemoteStorageConfig.objects.get(is_default=True, is_active=True)
            except RemoteStorageConfig.DoesNotExist:
                logger.error("[RESTORE-API] Aucun remote storage par défaut configuré")
                return None

            # Initialiser les managers
            chain_manager = BackupChainManager(remote_storage, vm_name)
            integrity_checker = IntegrityChecker(chain_manager)

            # Initialiser VMware service
            vmware_service = VMwareService()

            # Initialiser les services de restauration
            vm_restore = VMRestoreService(chain_manager, integrity_checker, vmware_service)
            vmdk_restore = VMDKRestoreService(chain_manager, integrity_checker, vmware_service)
            file_recovery = FileRecoveryService(chain_manager, integrity_checker, vmdk_restore)

            return vm_restore, vmdk_restore, file_recovery

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur initialisation services: {e}", exc_info=True)
            return None

    @action(detail=False, methods=['post'])
    def vm(self, request):
        """
        Restaure une VM complète depuis un backup

        POST /api/restore/vm/
        {
            "backup_id": "full_18-01-2025_14-00-00",
            "target_datastore": "datastore1",
            "target_vm_name": "Restored_WebServer",
            "restore_mode": "new",
            "power_on": false
        }
        """
        serializer = RestoreVMSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Récupérer le nom de la VM depuis le backup_id
        # Format: full_18-01-2025_14-00-00 ou incr_19-01-2025_08-00-00
        # On doit trouver le backup pour extraire le vm_name
        # Pour l'instant, on va demander au client de fournir le vm_name
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialiser les services
        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services de restauration'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        vm_restore, _, _ = services

        try:
            # Exécuter la restauration
            logger.info(f"[RESTORE-API] Début restauration VM: {data['backup_id']}")

            results = vm_restore.restore_vm_complete(
                backup_id=data['backup_id'],
                target_datastore=data['target_datastore'],
                target_vm_name=data.get('target_vm_name'),
                restore_mode=data.get('restore_mode', 'new')
            )

            if results['success']:
                return Response({
                    'success': True,
                    'message': 'VM restaurée avec succès',
                    'results': results
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Échec de la restauration',
                    'errors': results.get('errors', [])
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur restauration VM: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def vmdk(self, request):
        """
        Restaure un VMDK individuel depuis un backup

        POST /api/restore/vmdk/
        {
            "backup_id": "full_18-01-2025_14-00-00",
            "vmdk_filename": "VM_WebServer.vmdk",
            "target_datastore": "datastore1",
            "target_name": "restored_disk.vmdk",
            "attach_to_vm": "WebServer"
        }
        """
        serializer = RestoreVMDKSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, vmdk_restore, _ = services

        try:
            logger.info(f"[RESTORE-API] Début restauration VMDK: {data['vmdk_filename']}")

            results = vmdk_restore.restore_vmdk(
                backup_id=data['backup_id'],
                vmdk_filename=data['vmdk_filename'],
                target_datastore=data['target_datastore'],
                target_name=data.get('target_name'),
                attach_to_vm=data.get('attach_to_vm')
            )

            if results['success']:
                return Response({
                    'success': True,
                    'message': 'VMDK restauré avec succès',
                    'results': results
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Échec de la restauration',
                    'errors': results.get('errors', [])
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur restauration VMDK: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def files(self, request):
        """
        Récupère des fichiers spécifiques depuis un backup

        POST /api/restore/files/
        {
            "backup_id": "full_18-01-2025_14-00-00",
            "vmdk_filename": "VM_WebServer.vmdk",
            "file_paths": ["/etc/nginx/nginx.conf", "/var/log/app.log"],
            "destination_folder": "C:\\Restored_Files"
        }
        """
        serializer = FileRecoverySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, _, file_recovery = services

        try:
            logger.info(f"[RESTORE-API] Début récupération fichiers: {len(data['file_paths'])} fichiers")

            results = file_recovery.recover_files(
                backup_id=data['backup_id'],
                vmdk_filename=data['vmdk_filename'],
                file_paths=data['file_paths'],
                destination_folder=data['destination_folder']
            )

            return Response({
                'success': results['success'],
                'message': f"{len(results['recovered_files'])} fichiers récupérés",
                'results': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur récupération fichiers: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='list-files')
    def list_files(self, request):
        """
        Liste les fichiers disponibles dans un backup

        POST /api/restore/list-files/
        {
            "backup_id": "full_18-01-2025_14-00-00",
            "vmdk_filename": "VM_WebServer.vmdk",
            "directory_path": "/etc/nginx"
        }
        """
        serializer = ListFilesSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, _, file_recovery = services

        try:
            results = file_recovery.list_files_in_backup(
                backup_id=data['backup_id'],
                vmdk_filename=data['vmdk_filename'],
                directory_path=data.get('directory_path', '/')
            )

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur listage fichiers: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='search-files')
    def search_files(self, request):
        """
        Recherche des fichiers dans un backup

        POST /api/restore/search-files/
        {
            "backup_id": "full_18-01-2025_14-00-00",
            "vmdk_filename": "VM_WebServer.vmdk",
            "search_pattern": "*.conf"
        }
        """
        serializer = SearchFilesSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, _, file_recovery = services

        try:
            results = file_recovery.search_files_in_backup(
                backup_id=data['backup_id'],
                vmdk_filename=data['vmdk_filename'],
                search_pattern=data['search_pattern']
            )

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur recherche fichiers: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='list-vmdks')
    def list_vmdks(self, request, pk=None):
        """
        Liste les VMDK disponibles dans un backup

        GET /api/restore/{backup_id}/list-vmdks/?vm_name=WebServer
        """
        backup_id = pk
        vm_name = request.query_params.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, vmdk_restore, _ = services

        try:
            vmdks = vmdk_restore.list_vmdks_in_backup(backup_id)

            return Response({
                'backup_id': backup_id,
                'vmdks': vmdks,
                'count': len(vmdks)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur listage VMDK: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='validate-vm')
    def validate_vm(self, request):
        """
        Valide qu'une restauration VM est possible

        POST /api/restore/validate-vm/
        {
            "backup_id": "full_18-01-2025_14-00-00"
        }
        """
        serializer = ValidateRestoreSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        vm_restore, _, _ = services

        try:
            results = vm_restore.validate_before_restore(data['backup_id'])

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur validation: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='validate-vmdk')
    def validate_vmdk(self, request):
        """
        Valide qu'une restauration VMDK est possible

        POST /api/restore/validate-vmdk/
        {
            "backup_id": "full_18-01-2025_14-00-00",
            "vmdk_filename": "VM_WebServer.vmdk"
        }
        """
        serializer = ValidateRestoreSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        vm_name = request.data.get('vm_name')

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not data.get('vmdk_filename'):
            return Response(
                {'error': 'Le paramètre vmdk_filename est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        services = self._get_restore_services(vm_name)
        if not services:
            return Response(
                {'error': 'Erreur initialisation des services'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, vmdk_restore, _ = services

        try:
            results = vmdk_restore.validate_vmdk_restore(
                data['backup_id'],
                data['vmdk_filename']
            )

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur validation: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='list-backups')
    def list_backups(self, request, pk=None):
        """
        Liste tous les backups disponibles pour une VM

        GET /api/restore/{vm_name}/list-backups/
        """
        vm_name = pk

        if not vm_name:
            return Response(
                {'error': 'Le paramètre vm_name est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Récupérer le remote storage par défaut
            try:
                remote_storage = RemoteStorageConfig.objects.get(is_default=True, is_active=True)
            except RemoteStorageConfig.DoesNotExist:
                return Response(
                    {'error': 'Aucun remote storage par défaut configuré'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Initialiser le chain manager
            from backups.backup_chain.chain_manager import BackupChainManager
            chain_manager = BackupChainManager(remote_storage, vm_name)

            # Récupérer tous les backups pour cette VM
            backups_list = chain_manager.list_all_backups()

            return Response({
                'vm_name': vm_name,
                'backups': backups_list,
                'count': len(backups_list)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur listage backups: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def list_backup_files(self, request):
        """
        Liste les fichiers de sauvegarde OVA/OVF disponibles dans les chemins de stockage

        GET /api/restore/list-backup-files/?path=/backups

        Query params:
        - path: Chemin à parcourir (optionnel, utilise les chemins de stockage actifs par défaut)

        Returns:
        [
            {
                "name": "vm-backup.ova",
                "path": "/backups/vm-backup.ova",
                "size_mb": 1024.5,
                "type": "ova",
                "modified": "2025-11-29T10:30:00Z"
            }
        ]
        """
        import os
        from datetime import datetime
        from backups.models import StoragePath

        try:
            path_param = request.query_params.get('path')
            backup_files = []

            # Si un chemin spécifique est fourni, l'utiliser
            if path_param:
                paths_to_scan = [path_param]
            else:
                # Sinon, utiliser tous les chemins de stockage actifs
                storage_paths = StoragePath.objects.filter(is_active=True)
                paths_to_scan = [sp.path for sp in storage_paths]

            # Parcourir chaque chemin
            for base_path in paths_to_scan:
                if not os.path.exists(base_path):
                    logger.warning(f"[RESTORE-API] Chemin inexistant: {base_path}")
                    continue

                # Parcourir récursivement pour trouver les fichiers .ova et .ovf
                for root, dirs, files in os.walk(base_path):
                    for filename in files:
                        if filename.endswith(('.ova', '.ovf')):
                            file_path = os.path.join(root, filename)
                            try:
                                stat_info = os.stat(file_path)
                                backup_files.append({
                                    'name': filename,
                                    'path': file_path,
                                    'size_mb': round(stat_info.st_size / (1024 * 1024), 2),
                                    'type': 'ova' if filename.endswith('.ova') else 'ovf',
                                    'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                                    'storage_path': base_path
                                })
                            except Exception as e:
                                logger.error(f"[RESTORE-API] Erreur lecture fichier {file_path}: {e}")

            # Trier par date de modification (plus récent en premier)
            backup_files.sort(key=lambda x: x['modified'], reverse=True)

            return Response({
                'files': backup_files,
                'count': len(backup_files)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[RESTORE-API] Erreur listage fichiers: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================================
# 🔹 BACKUP CHAIN API
# ==========================================================

class BackupChainViewSet(viewsets.GenericViewSet):
    """
    ViewSet pour visualiser et gérer les chaînes de backup

    Endpoints:
    - GET /api/backup-chains/{vm_name}/chain/ - Récupérer la chaîne d'une VM
    - GET /api/backup-chains/{vm_name}/stats/ - Statistiques de la chaîne
    - POST /api/backup-chains/{vm_name}/apply-retention/ - Appliquer la rétention
    - POST /api/backup-chains/{vm_name}/verify-integrity/ - Vérifier l'intégrité
    - GET /api/backup-chains/{vm_name}/backups/ - Lister tous les backups
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_chain_manager(self, vm_name: str):
        """Récupère le BackupChainManager pour une VM"""
        try:
            from backups.backup_chain.chain_manager import BackupChainManager
            from backups.backup_chain.integrity_checker import IntegrityChecker
            from backups.backup_chain.retention_policy import RetentionPolicyManager

            try:
                remote_storage = RemoteStorageConfig.objects.get(is_default=True, is_active=True)
            except RemoteStorageConfig.DoesNotExist:
                logger.error("[CHAIN-API] Aucun remote storage par défaut configuré")
                return None, None, None

            chain_manager = BackupChainManager(remote_storage, vm_name)
            integrity_checker = IntegrityChecker(chain_manager)
            retention_manager = RetentionPolicyManager(chain_manager)

            return chain_manager, integrity_checker, retention_manager

        except Exception as e:
            logger.error(f"[CHAIN-API] Erreur initialisation managers: {e}", exc_info=True)
            return None, None, None

    @action(detail=True, methods=['get'])
    def chain(self, request, pk=None):
        """GET /api/backup-chains/{vm_name}/chain/"""
        vm_name = pk
        chain_manager, _, _ = self._get_chain_manager(vm_name)
        if not chain_manager:
            return Response({'error': 'Erreur initialisation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            chain = chain_manager.load_chain()
            return Response(chain, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[CHAIN-API] Erreur: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """GET /api/backup-chains/{vm_name}/stats/"""
        vm_name = pk
        chain_manager, _, _ = self._get_chain_manager(vm_name)
        if not chain_manager:
            return Response({'error': 'Erreur initialisation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            stats = chain_manager.get_chain_statistics()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='apply-retention')
    def apply_retention(self, request, pk=None):
        """POST /api/backup-chains/{vm_name}/apply-retention/"""
        vm_name = pk
        _, _, retention_manager = self._get_chain_manager(vm_name)
        if not retention_manager:
            return Response({'error': 'Erreur initialisation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            policy = request.data.get('policy')
            dry_run = request.data.get('dry_run', False)
            results = retention_manager.apply_policy(policy=policy, dry_run=dry_run)
            return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-integrity')
    def verify_integrity(self, request, pk=None):
        """POST /api/backup-chains/{vm_name}/verify-integrity/"""
        vm_name = pk
        _, integrity_checker, _ = self._get_chain_manager(vm_name)
        if not integrity_checker:
            return Response({'error': 'Erreur initialisation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            results = integrity_checker.verify_all_backups()
            return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def backups(self, request, pk=None):
        """GET /api/backup-chains/{vm_name}/backups/"""
        vm_name = pk
        chain_manager, _, _ = self._get_chain_manager(vm_name)
        if not chain_manager:
            return Response({'error': 'Erreur initialisation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            chain = chain_manager.load_chain()
            backups = chain.get('backups', [])
            backups_sorted = sorted(backups, key=lambda b: b['timestamp'], reverse=True)
            
            return Response({
                'vm_name': vm_name,
                'backups': backups_sorted,
                'total_count': len(backups_sorted)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================================
# Notification Configuration ViewSet (Phase 6)
# ==========================================================

class NotificationConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les configurations de notification

    Endpoints:
    - GET /api/notifications/ - Liste des configurations
    - POST /api/notifications/ - Créer une configuration
    - GET /api/notifications/{id}/ - Détails d'une configuration
    - PUT/PATCH /api/notifications/{id}/ - Modifier une configuration
    - DELETE /api/notifications/{id}/ - Supprimer une configuration
    - POST /api/notifications/{id}/test/ - Tester une configuration
    - POST /api/notifications/{id}/toggle/ - Activer/désactiver
    """
    queryset = NotificationConfig.objects.all().order_by('-created_at')
    serializer_class = NotificationConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Associer le créateur lors de la création"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """
        POST /api/notifications/{id}/test/
        Envoie une notification de test
        """
        config = self.get_object()
        serializer = TestNotificationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        test_message = serializer.validated_data.get('test_message')

        try:
            from backups.notification_service import notification_service

            # Envoyer une notification de test
            notification_service.send_notification(
                'backup_success',  # Event de test
                vm=None,
                backup_job=None,
                test_mode=True,
                test_message=test_message
            )

            return Response({
                'success': True,
                'message': f'Notification de test envoyée via {config.notification_type}'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[NOTIFICATION-TEST] Erreur: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """
        POST /api/notifications/{id}/toggle/
        Active/désactive la notification
        """
        config = self.get_object()
        config.is_enabled = not config.is_enabled
        config.save()

        return Response({
            'success': True,
            'is_enabled': config.is_enabled,
            'message': f"Notification {'activée' if config.is_enabled else 'désactivée'}"
        }, status=status.HTTP_200_OK)


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter l'historique des notifications

    Endpoints:
    - GET /api/notification-logs/ - Liste des logs (lecture seule)
    - GET /api/notification-logs/{id}/ - Détails d'un log
    - GET /api/notification-logs/stats/ - Statistiques
    """
    queryset = NotificationLog.objects.all().order_by('-sent_at')
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrage optionnel par config, VM, status, event_type"""
        queryset = super().get_queryset()

        # Filtrer par configuration
        config_id = self.request.query_params.get('config_id')
        if config_id:
            queryset = queryset.filter(config_id=config_id)

        # Filtrer par VM
        vm_id = self.request.query_params.get('vm_id')
        if vm_id:
            queryset = queryset.filter(virtual_machine_id=vm_id)

        # Filtrer par statut
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filtrer par type d'événement
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/notification-logs/stats/
        Retourne des statistiques sur les notifications
        """
        from django.db.models import Count, Q
        from datetime import timedelta

        # Stats globales
        total_count = NotificationLog.objects.count()
        sent_count = NotificationLog.objects.filter(status='sent').count()
        failed_count = NotificationLog.objects.filter(status='failed').count()

        # Stats par type d'événement
        event_stats = NotificationLog.objects.values('event_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Stats dernières 24h
        last_24h = timezone.now() - timedelta(hours=24)
        last_24h_count = NotificationLog.objects.filter(sent_at__gte=last_24h).count()
        last_24h_failed = NotificationLog.objects.filter(
            sent_at__gte=last_24h,
            status='failed'
        ).count()

        # Stats derniers 7 jours
        last_7days = timezone.now() - timedelta(days=7)
        last_7days_count = NotificationLog.objects.filter(sent_at__gte=last_7days).count()

        return Response({
            'total_notifications': total_count,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'success_rate': round((sent_count / total_count * 100) if total_count > 0 else 0, 2),
            'by_event_type': list(event_stats),
            'last_24h': {
                'count': last_24h_count,
                'failed': last_24h_failed
            },
            'last_7days': {
                'count': last_7days_count
            }
        }, status=status.HTTP_200_OK)


# ===========================
# HEALTH MONITORING (Phase 6)
# ===========================
class HealthMonitoringViewSet(viewsets.ViewSet):
    """
    API pour le monitoring de santé des backups
    Endpoints: /api/health/*
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def overall(self, request):
        """
        GET /api/health/overall/
        Retourne l'état de santé global du système de backup
        """
        from backups.health_monitoring_service import health_monitor

        try:
            health_data = health_monitor.get_overall_health()
            return Response(health_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[HEALTH] Erreur lors de la récupération de la santé globale: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='vm/(?P<vm_id>[^/.]+)')
    def vm_health(self, request, vm_id=None):
        """
        GET /api/health/vm/{vm_id}/
        Retourne l'état de santé d'une VM spécifique
        """
        from backups.health_monitoring_service import health_monitor

        try:
            health_data = health_monitor.get_vm_health(vm_id)

            if 'error' in health_data:
                return Response(health_data, status=status.HTTP_404_NOT_FOUND)

            return Response(health_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[HEALTH] Erreur lors de la récupération de la santé de la VM {vm_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def issues(self, request):
        """
        GET /api/health/issues/
        Retourne uniquement les problèmes détectés (sans les métriques)
        """
        from backups.health_monitoring_service import health_monitor

        try:
            health_data = health_monitor.get_overall_health()

            return Response({
                'status': health_data['status'],
                'score': health_data['score'],
                'issues': health_data['issues'],
                'warnings': health_data['warnings'],
                'recommendations': health_data['recommendations']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[HEALTH] Erreur lors de la récupération des problèmes: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        GET /api/health/metrics/
        Retourne uniquement les métriques (sans les problèmes)
        """
        from backups.health_monitoring_service import health_monitor

        try:
            health_data = health_monitor.get_overall_health()

            return Response({
                'metrics': health_data['metrics'],
                'last_check': health_data['last_check']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[HEALTH] Erreur lors de la récupération des métriques: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===========================
# OVF EXPORT & VM BACKUP (NOUVEAU)
# ===========================

class OVFExportJobViewSet(viewsets.ModelViewSet):
    """
    API pour les exports OVF
    Endpoints: /api/ovf-exports/*
    """
    from api.serializers import OVFExportJobSerializer, OVFExportJobCreateSerializer
    from backups.models import OVFExportJob

    queryset = OVFExportJob.objects.all().select_related('virtual_machine', 'remote_storage')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            from api.serializers import OVFExportJobCreateSerializer
            return OVFExportJobCreateSerializer
        from api.serializers import OVFExportJobSerializer
        return OVFExportJobSerializer

    def perform_create(self, serializer):
        """Crée un export OVF et le démarre"""
        export_job = serializer.save(created_by=self.request.user, status='pending')

        # Générer le chemin complet avec format: VM-NAME_DD-MM-YYYY_HH-MM
        timestamp = timezone.now().strftime('%d-%m-%Y_%H-%M')
        vm_name = export_job.virtual_machine.name
        export_job.export_full_path = os.path.join(
            export_job.export_location,
            f"{vm_name}_{timestamp}"
        )
        export_job.save()

        # Lancer l'export en arrière-plan (Celery ou Thread)
        # Vérifier si Celery est disponible en testant la connexion au broker
        use_celery = False
        try:
            from backups.tasks import execute_ovf_export
            from celery import current_app
            # Essayer de pinger le broker Celery avec un timeout court
            inspect = current_app.control.inspect(timeout=1.0)
            active = inspect.active()
            if active is not None:
                use_celery = True
                logger.info(f"[OVF-EXPORT] Celery disponible, utilisation de Celery")
            else:
                logger.warning(f"[OVF-EXPORT] Celery broker non accessible, utilisation du fallback sur threads")
        except Exception as e:
            logger.warning(f"[OVF-EXPORT] Celery non disponible ({e}), utilisation du fallback sur threads")

        if use_celery:
            # Lancer avec Celery
            execute_ovf_export.delay(export_job.id)
            logger.info(f"[OVF-EXPORT] Export créé et tâche Celery lancée: {export_job.id}")
        else:
            # Fallback : exécuter dans un thread séparé
            import threading

            def run_export_in_thread():
                """Exécute l'export dans un thread séparé pour ne pas bloquer la requête HTTP"""
                from backups.ovf_export_lease import OVFExportLeaseService
                from esxi.vmware_service import VMwareService

                vm = export_job.virtual_machine
                vmware_service = VMwareService(vm.server.hostname, vm.server.username, vm.server.password)

                try:
                    # Marquer comme en cours
                    export_job.status = 'running'
                    export_job.started_at = timezone.now()
                    export_job.save()

                    vmware_service.connect()
                    vm_obj = vmware_service._find_vm_by_name(vm.name)

                    # Create OVF export service using HttpNfcLease API (handles thin-provisioned disks)
                    ovf_service = OVFExportLeaseService(vm_obj, export_job)
                    success = ovf_service.export_ovf()

                    if not success:
                        logger.error(f"[OVF-EXPORT] Export failed for job {export_job.id}")

                except Exception as export_error:
                    export_job.status = 'failed'
                    export_job.error_message = str(export_error)
                    export_job.completed_at = timezone.now()
                    export_job.save()
                    logger.error(f"[OVF-EXPORT] Erreur export: {export_error}", exc_info=True)
                finally:
                    vmware_service.disconnect()

            # Lancer le thread en arrière-plan
            thread = threading.Thread(target=run_export_in_thread, daemon=True)
            thread.start()
            logger.info(f"[OVF-EXPORT] Export créé et thread lancé: {export_job.id}")

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annule un export en cours"""
        export_job = self.get_object()

        if export_job.status not in ['pending', 'running']:
            return Response(
                {'error': 'Impossible d\'annuler un export qui n\'est pas en cours'},
                status=status.HTTP_400_BAD_REQUEST
            )

        export_job.status = 'cancelled'
        export_job.save()

        logger.info(f"[OVF-EXPORT] Export annulé: {export_job.id}")
        return Response({'message': 'Export annulé'})

    def perform_destroy(self, instance):
        """Supprime l'export et son dossier physique"""
        import shutil

        # Supprimer le dossier physique si il existe
        if instance.export_full_path and os.path.exists(instance.export_full_path):
            try:
                shutil.rmtree(instance.export_full_path)
                logger.info(f"[OVF-EXPORT] Dossier supprimé: {instance.export_full_path}")
            except Exception as e:
                logger.error(f"[OVF-EXPORT] Erreur suppression dossier: {e}")
                # Continue quand même pour supprimer l'entrée en base de données

        # Supprimer l'entrée en base de données
        instance.delete()
        logger.info(f"[OVF-EXPORT] Export supprimé de la base de données: {instance.id}")


class VMBackupJobViewSet(viewsets.ModelViewSet):
    """
    API pour les backups de VMs (snapshot + VMDK copy)
    Endpoints: /api/vm-backups/*
    """
    from api.serializers import VMBackupJobSerializer, VMBackupJobCreateSerializer
    from backups.models import VMBackupJob

    queryset = VMBackupJob.objects.all().select_related('virtual_machine', 'remote_storage', 'base_backup')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            from api.serializers import VMBackupJobCreateSerializer
            return VMBackupJobCreateSerializer
        from api.serializers import VMBackupJobSerializer
        return VMBackupJobSerializer

    def perform_create(self, serializer):
        """Crée un backup et le démarre"""
        backup_job = serializer.save(created_by=self.request.user, status='pending')

        # Générer le chemin complet
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        vm_name = backup_job.virtual_machine.name
        backup_type = backup_job.backup_type
        backup_job.backup_full_path = os.path.join(
            backup_job.backup_location,
            f"{backup_type}_{vm_name}_{timestamp}"
        )
        backup_job.started_at = timezone.now()
        backup_job.save()

        # Lancer le backup en arrière-plan (Celery ou Thread)
        # Vérifier si Celery est disponible en testant la connexion au broker
        use_celery = False
        try:
            from backups.tasks import execute_vm_backup
            from celery import current_app
            # Essayer de pinger le broker Celery avec un timeout court
            inspect = current_app.control.inspect(timeout=1.0)
            active = inspect.active()
            if active is not None:
                use_celery = True
                logger.info(f"[VM-BACKUP] Celery disponible, utilisation de Celery")
            else:
                logger.warning(f"[VM-BACKUP] Celery broker non accessible, utilisation du fallback sur threads")
        except Exception as e:
            logger.warning(f"[VM-BACKUP] Celery non disponible ({e}), utilisation du fallback sur threads")

        if use_celery:
            # Lancer avec Celery
            execute_vm_backup.delay(backup_job.id)
            logger.info(f"[VM-BACKUP] Backup créé et tâche Celery lancée: {backup_job.id} - {backup_type} - {vm_name}")
        else:
            # Fallback : exécuter dans un thread séparé
            import threading

            def run_backup_in_thread():
                """Exécute le backup dans un thread séparé pour ne pas bloquer la requête HTTP"""
                from backups.vm_backup_service import execute_vm_backup as run_backup
                from esxi.vmware_service import VMwareService

                vm = backup_job.virtual_machine
                vmware_service = VMwareService(vm.server.hostname, vm.server.username, vm.server.password)

                try:
                    # Marquer comme en cours
                    backup_job.status = 'running'
                    backup_job.save()

                    vmware_service.connect()
                    vm_obj = vmware_service._find_vm_by_name(vm.name)
                    run_backup(vm_obj, backup_job)

                except Exception as backup_error:
                    backup_job.status = 'failed'
                    backup_job.error_message = str(backup_error)
                    backup_job.completed_at = timezone.now()
                    backup_job.save()
                    logger.error(f"[VM-BACKUP] Erreur backup: {backup_error}", exc_info=True)
                finally:
                    vmware_service.disconnect()

            # Lancer le thread en arrière-plan
            thread = threading.Thread(target=run_backup_in_thread, daemon=True)
            thread.start()
            logger.info(f"[VM-BACKUP] Backup créé et thread lancé: {backup_job.id} - {backup_type} - {vm_name}")

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annule un backup en cours"""
        backup_job = self.get_object()

        if backup_job.status not in ['pending', 'running']:
            return Response(
                {'error': 'Impossible d\'annuler un backup qui n\'est pas en cours'},
                status=status.HTTP_400_BAD_REQUEST
            )

        backup_job.status = 'cancelled'
        backup_job.save()

        logger.info(f"[VM-BACKUP] Backup annulé: {backup_job.id}")
        return Response({'message': 'Backup annulé'})

    @action(detail=False, methods=['get'])
    def available_base_backups(self, request):
        """Retourne les backups full disponibles pour servir de base à un incremental"""
        vm_id = request.query_params.get('vm_id')

        if not vm_id:
            return Response(
                {'error': 'vm_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from backups.models import VMBackupJob
        base_backups = VMBackupJob.objects.filter(
            virtual_machine_id=vm_id,
            backup_type='full',
            status='completed'
        ).order_by('-completed_at')

        from api.serializers import VMBackupJobSerializer
        serializer = VMBackupJobSerializer(base_backups, many=True)
        return Response(serializer.data)


# ==========================================================
# 🔹 STORAGE PATHS - Chemins de sauvegarde
# ==========================================================
class StoragePathViewSet(viewsets.ModelViewSet):
    """Gestion des chemins de sauvegarde prédéfinis"""
    queryset = StoragePath.objects.all()
    serializer_class = StoragePathSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active', 'storage_type', 'is_default']
    ordering_fields = ['name', 'created_at', 'is_default']
    ordering = ['-is_default', 'name']
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Définir ce chemin comme défaut"""
        storage_path = self.get_object()
        
        # Retirer le défaut des autres
        StoragePath.objects.exclude(pk=pk).update(is_default=False)
        
        # Définir celui-ci comme défaut
        storage_path.is_default = True
        storage_path.save()
        
        serializer = self.get_serializer(storage_path)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Retourne uniquement les chemins actifs"""
        active_paths = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_paths, many=True)
        return Response(serializer.data)


# ==========================================================
# 🔹 VM REPLICATION - Réplication de VMs
# ==========================================================
class VMReplicationViewSet(viewsets.ModelViewSet):
    """Gestion de la réplication de VMs entre serveurs ESXi"""
    queryset = VMReplication.objects.all()
    serializer_class = VMReplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['virtual_machine', 'source_server', 'destination_server', 'status', 'is_active']
    ordering_fields = ['created_at', 'last_replication_at', 'name']
    ordering = ['-created_at']

    def create(self, request, *args, **kwargs):
        """Override create pour logger les erreurs de validation"""
        import logging
        logger = logging.getLogger(__name__)

        # Logger les données reçues
        logger.info(f"[REPLICATION CREATE] Données reçues: {request.data}")

        serializer = self.get_serializer(data=request.data)

        # Valider et logger les erreurs si validation échoue
        if not serializer.is_valid():
            logger.error(f"[REPLICATION CREATE] Erreurs de validation: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Si validation OK, créer l'objet
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        logger.info(f"[REPLICATION CREATE] Réplication créée avec succès: {serializer.data.get('id')}")
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def start_replication(self, request, pk=None):
        """Démarrer une réplication manuelle immédiate avec progression"""
        from django.utils import timezone
        from django.core.cache import cache
        import uuid
        import threading
        import logging
        import sys
        logger = logging.getLogger(__name__)

        print("=" * 80, file=sys.stderr)
        print("[DEBUG] start_replication appelée", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        replication = self.get_object()
        print(f"[DEBUG] Réplication récupérée: {replication.id}", file=sys.stderr)

        # CRITIQUE: Pré-charger TOUTES les ForeignKeys avant le thread
        # pour éviter les requêtes DB dans le thread (pas thread-safe avec Django)
        from backups.models import VMReplication
        replication = VMReplication.objects.select_related(
            'source_server',
            'destination_server',
            'virtual_machine',
            'virtual_machine__server'
        ).get(pk=replication.pk)

        print(f"[DEBUG] Relations pré-chargées: {replication.name}", file=sys.stderr)
        logger.info(f"[API] Réplication chargée avec relations: {replication.name}")

        if not replication.is_active:
            print(f"[DEBUG] Réplication inactive, retour erreur", file=sys.stderr)
            return Response(
                {'error': 'La réplication est inactive'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Générer un ID unique pour cette réplication
            replication_id = str(uuid.uuid4())
            print(f"[DEBUG] ID réplication généré: {replication_id}", file=sys.stderr)

            # Initialiser le cache avec une progression de 0% AVANT de démarrer le thread
            initial_progress = {
                'progress': 0,
                'status': 'starting',
                'message': 'Démarrage de la réplication...'
            }
            cache.set(f'replication_progress_{replication_id}', initial_progress, timeout=3600)
            print(f"[DEBUG] Cache initialisé à 0%", file=sys.stderr)

            # Vérifier que le cache a bien été écrit
            test_cache = cache.get(f'replication_progress_{replication_id}')
            print(f"[DEBUG] Vérification cache: {test_cache}", file=sys.stderr)

            logger.info(f"[API] Progression initialisée pour replication_id={replication_id}")

            # Fonction de callback pour la progression
            def progress_callback(progress_percent, status_val, message):
                print(f"[DEBUG CALLBACK] {progress_percent}% - {status_val} - {message}", file=sys.stderr)
                progress_data = {
                    'progress': int(progress_percent) if progress_percent >= 0 else 0,
                    'status': status_val,
                    'message': message
                }
                cache.set(f'replication_progress_{replication_id}', progress_data, timeout=3600)
                logger.info(f"[API] Progression mise à jour: {progress_data}")

            # Fonction pour exécuter la réplication dans un thread
            def run_replication():
                print("=" * 80, file=sys.stderr)
                print("[DEBUG THREAD] Thread de réplication DÉMARRÉ", file=sys.stderr)
                print("=" * 80, file=sys.stderr)
                from backups.replication_service import ReplicationService
                try:
                    logger.info(f"[API] Thread de réplication démarré pour {replication.name}")
                    print(f"[DEBUG THREAD] Création ReplicationService", file=sys.stderr)
                    service = ReplicationService()
                    print(f"[DEBUG THREAD] Appel replicate_vm avec replication_id={replication_id}", file=sys.stderr)
                    service.replicate_vm(replication, progress_callback=progress_callback, replication_id=replication_id)
                    print(f"[DEBUG THREAD] replicate_vm terminé", file=sys.stderr)
                    logger.info(f"[API] Thread de réplication terminé pour {replication.name}")
                except Exception as e:
                    import traceback
                    print(f"[DEBUG THREAD] ERREUR: {e}", file=sys.stderr)
                    print(traceback.format_exc(), file=sys.stderr)
                    logger.error(f"[API] Erreur dans le thread de réplication: {e}", exc_info=True)
                    # Mettre à jour le cache avec l'erreur
                    progress_callback(-1, 'error', str(e))

            # Démarrer la réplication dans un thread séparé
            print(f"[DEBUG] Création thread...", file=sys.stderr)
            thread = threading.Thread(target=run_replication, daemon=True)
            print(f"[DEBUG] Démarrage thread...", file=sys.stderr)
            thread.start()
            print(f"[DEBUG] Thread démarré! Actif: {thread.is_alive()}", file=sys.stderr)
            logger.info(f"[API] Thread lancé pour replication_id={replication_id}")

            # Retourner l'ID immédiatement
            return Response({
                'message': 'Réplication démarrée',
                'replication_id': replication_id
            })

        except Exception as e:
            import traceback
            print(f"[DEBUG] EXCEPTION DANS start_replication: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            logger.error(f"Erreur lors du démarrage de la réplication: {e}\n{traceback.format_exc()}")

            return Response({
                'error': str(e),
                'details': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='replication-progress/(?P<replication_id>[^/.]+)')
    def replication_progress(self, request, replication_id=None):
        """Récupérer la progression d'une réplication en cours"""
        from django.core.cache import cache

        try:
            progress_data = cache.get(f'replication_progress_{replication_id}')

            if progress_data is None:
                return Response(
                    {
                        'progress': 0,
                        'status': 'not_found',
                        'message': 'Aucune réplication en cours avec cet ID'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(progress_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='cancel-replication/(?P<replication_id>[^/.]+)')
    def cancel_replication(self, request, replication_id=None):
        """Arrêter une réplication en cours"""
        from django.core.cache import cache

        try:
            # Mettre à jour le cache pour indiquer l'annulation
            progress_data = cache.get(f'replication_progress_{replication_id}')

            if progress_data is None:
                return Response(
                    {'error': 'Aucune réplication en cours avec cet ID'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Marquer comme annulée dans le cache
            progress_data['status'] = 'cancelled'
            progress_data['message'] = 'Réplication annulée par l\'utilisateur'
            cache.set(f'replication_progress_{replication_id}', progress_data, timeout=3600)

            # Note: Le thread continuera mais l'UI sera informée de l'annulation
            logger.info(f"[API] Réplication {replication_id} marquée comme annulée")

            return Response({
                'message': 'Réplication annulée',
                'replication_id': replication_id
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Mettre en pause une réplication"""
        replication = self.get_object()
        replication.status = 'paused'
        replication.is_active = False
        replication.save()
        
        return Response({'message': 'Réplication mise en pause'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Reprendre une réplication en pause"""
        replication = self.get_object()
        replication.status = 'active'
        replication.is_active = True
        replication.save()
        
        return Response({'message': 'Réplication reprise'})
    
    @action(detail=True, methods=['get'])
    def check_replica_exists(self, request, pk=None):
        """Vérifier si une VM replica existe déjà sur le serveur de destination"""
        import logging
        logger = logging.getLogger(__name__)

        replication = self.get_object()
        vm_name = replication.virtual_machine.name
        replica_vm_name = f"{vm_name}_replica"
        destination_server = replication.destination_server

        try:
            from backups.replication_service import ReplicationService
            service = ReplicationService()

            logger.info(f"[CHECK-REPLICA] Vérification replica: {replica_vm_name} sur {destination_server.hostname}")

            # Se connecter au serveur de destination
            dest_si = service._connect_to_server(destination_server)

            # Vérifier si la replica existe
            existing_replica = service._get_vm_by_name(dest_si, replica_vm_name)

            # Déconnexion
            from pyVim.connect import Disconnect
            Disconnect(dest_si)

            if existing_replica:
                logger.info(f"[CHECK-REPLICA] Replica trouvée: {replica_vm_name}")
                return Response({
                    'exists': True,
                    'replica_name': replica_vm_name,
                    'message': f'Une VM replica "{replica_vm_name}" existe déjà sur le serveur de destination'
                })
            else:
                logger.info(f"[CHECK-REPLICA] Aucune replica trouvée")
                return Response({
                    'exists': False,
                    'message': 'Aucune replica existante'
                })

        except Exception as e:
            logger.error(f"[CHECK-REPLICA] Erreur lors de la vérification: {e}", exc_info=True)
            return Response(
                {'error': str(e), 'exists': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def replication_history(self, request, pk=None):
        """Obtenir l'historique des réplications pour une VMReplication donnée"""
        replication = self.get_object()

        # Limiter à 20 dernières réplications par défaut
        limit = int(request.query_params.get('limit', 20))

        logs = replication.replication_logs.all()[:limit]
        serializer = ReplicationLogSerializer(logs, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def vm_states(self, request, pk=None):
        """Obtenir l'état des VMs source et destination"""
        import logging
        from django.utils import timezone
        logger = logging.getLogger(__name__)

        replication = self.get_object()

        try:
            from backups.replication_service import ReplicationService
            service = ReplicationService()

            # Se connecter aux serveurs
            source_server = replication.get_source_server
            dest_server = replication.destination_server

            source_si = service._connect_to_server(source_server)
            dest_si = service._connect_to_server(dest_server)

            # Obtenir les VMs
            vm_name = replication.virtual_machine.name
            replica_vm_name = f"{vm_name}_replica"

            source_vm = service._get_vm_by_name(source_si, vm_name)
            dest_vm = service._get_vm_by_name(dest_si, replica_vm_name)

            # États
            source_state = source_vm.runtime.powerState if source_vm else None
            dest_state = dest_vm.runtime.powerState if dest_vm else None

            # Calculer le prochain sync
            next_sync = None
            if replication.is_active and replication.last_replication_at:
                next_sync = replication.last_replication_at + timezone.timedelta(
                    minutes=replication.replication_interval_minutes
                )

            # Calculer le temps jusqu'au prochain sync
            time_to_next_sync = None
            if next_sync:
                delta = next_sync - timezone.now()
                time_to_next_sync = int(delta.total_seconds() / 60)  # en minutes

            # Déconnexion
            from pyVim.connect import Disconnect
            Disconnect(source_si)
            Disconnect(dest_si)

            return Response({
                'source_vm': {
                    'name': vm_name,
                    'power_state': source_state,
                    'exists': source_vm is not None
                },
                'destination_vm': {
                    'name': replica_vm_name,
                    'power_state': dest_state,
                    'exists': dest_vm is not None
                },
                'sync_info': {
                    'last_sync': replication.last_replication_at,
                    'next_sync': next_sync,
                    'time_to_next_sync_minutes': time_to_next_sync,
                    'interval_minutes': replication.replication_interval_minutes,
                    'is_active': replication.is_active
                }
            })

        except Exception as e:
            logger.error(f"[VM-STATES] Erreur lors de la récupération des états: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def trigger_failover(self, request, pk=None):
        """Déclencher un failover manuel"""
        replication = self.get_object()

        reason = request.data.get('reason', 'Failover manuel')
        test_mode = request.data.get('test_mode', False)

        # Créer l'événement de failover
        failover_event = FailoverEvent.objects.create(
            replication=replication,
            failover_type='test' if test_mode else 'manual',
            status='initiated',
            triggered_by=request.user,
            reason=reason
        )

        # Exécuter le failover via le service
        from backups.replication_service import ReplicationService
        service = ReplicationService()
        result = service.execute_failover(failover_event, test_mode=test_mode)

        serializer = FailoverEventSerializer(failover_event)

        if result['success']:
            return Response({
                'failover_event': serializer.data,
                'message': result['message'],
                'source_powered_off': result.get('source_powered_off'),
                'destination_powered_on': result.get('destination_powered_on')
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'failover_event': serializer.data,
                'error': result['message']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """
        Supprimer une réplication ET la VM répliquée du serveur de destination
        """
        import logging
        logger = logging.getLogger(__name__)

        replication = self.get_object()
        vm_name = replication.virtual_machine.name
        dest_server_name = replication.destination_server.hostname

        logger.info(f"[REPLICATION DELETE] Demande de suppression de la réplication: {replication.name}")

        # Supprimer la VM du serveur de destination
        from backups.replication_service import ReplicationService
        service = ReplicationService()

        logger.info(f"[REPLICATION DELETE] Suppression de la VM {vm_name} du serveur {dest_server_name}...")
        delete_result = service.delete_replicated_vm(replication)

        if not delete_result['success']:
            logger.warning(f"[REPLICATION DELETE] La suppression de la VM a échoué: {delete_result['message']}")
            # On continue quand même pour supprimer l'entrée DB
            # mais on avertit l'utilisateur
            return Response(
                {
                    'warning': True,
                    'message': f"La réplication a été supprimée de la base de données, mais la VM n'a pas pu être supprimée du serveur de destination: {delete_result['message']}"
                },
                status=status.HTTP_200_OK
            )

        logger.info(f"[REPLICATION DELETE] VM supprimée avec succès: {delete_result['message']}")

        # Supprimer l'entrée de la base de données
        response = super().destroy(request, *args, **kwargs)

        logger.info(f"[REPLICATION DELETE] Réplication {replication.name} supprimée de la base de données")

        return Response(
            {
                'success': True,
                'message': f'Réplication supprimée. {delete_result["message"]}'
            },
            status=status.HTTP_200_OK
        )


class FailoverEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des événements de failover"""
    queryset = FailoverEvent.objects.all()
    serializer_class = FailoverEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['replication', 'failover_type', 'status']
    ordering_fields = ['started_at', 'completed_at']
    ordering = ['-started_at']


# ==========================================================
# 🔹 SUREBACKUP - Vérification de sauvegardes
# ==========================================================
class BackupVerificationViewSet(viewsets.ModelViewSet):
    """Gestion des vérifications de sauvegardes (SureBackup)"""
    queryset = BackupVerification.objects.all()
    serializer_class = BackupVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'test_type', 'esxi_server']
    ordering_fields = ['created_at', 'started_at', 'completed_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'])
    def verify_ovf_export(self, request):
        """Créer une vérification pour un export OVF"""
        ovf_export_id = request.data.get('ovf_export_id')
        esxi_server_id = request.data.get('esxi_server_id')
        test_type = request.data.get('test_type', 'boot_ping')
        
        if not ovf_export_id or not esxi_server_id:
            return Response(
                {'error': 'ovf_export_id et esxi_server_id sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ovf_export = OVFExportJob.objects.get(id=ovf_export_id, status='completed')
            esxi_server = ESXiServer.objects.get(id=esxi_server_id)
        except (OVFExportJob.DoesNotExist, ESXiServer.DoesNotExist) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Créer la vérification
        verification = BackupVerification.objects.create(
            ovf_export=ovf_export,
            esxi_server=esxi_server,
            test_type=test_type,
            status='pending',
            test_datastore=request.data.get('test_datastore', 'datastore1')
        )
        
        # TODO: Lancer la vérification en arrière-plan
        # from backups.surebackup_service import SureBackupService
        # service = SureBackupService()
        # service.start_verification(verification.id)
        
        serializer = self.get_serializer(verification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def start_verification(self, request, pk=None):
        """Démarrer une vérification manuellement"""
        verification = self.get_object()

        if verification.status != 'pending':
            return Response(
                {'error': 'La vérification a déjà été démarrée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Lancer le service de vérification de manière asynchrone
        execute_backup_verification.delay(verification.id)

        serializer = self.get_serializer(verification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques sur les vérifications de sauvegardes"""
        total = BackupVerification.objects.count()
        passed = BackupVerification.objects.filter(status='passed').count()
        failed = BackupVerification.objects.filter(status='failed').count()
        running = BackupVerification.objects.filter(status='running').count()
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return Response({
            'total': total,
            'passed': passed,
            'failed': failed,
            'running': running,
            'success_rate': round(success_rate, 2)
        })


class BackupVerificationScheduleViewSet(viewsets.ModelViewSet):
    """Gestion des planifications de vérifications"""
    queryset = BackupVerificationSchedule.objects.all()
    serializer_class = BackupVerificationScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['virtual_machine', 'frequency', 'is_active']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activer/Désactiver une planification"""
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save()
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)


# ==========================================================
# 🔹 PROMETHEUS METRICS - Pour Grafana
# ==========================================================
@api_view(['GET'])
@permission_classes([permissions.AllowAny])  # Metrics accessibles sans auth
def prometheus_metrics(request):
    """
    Endpoint Prometheus pour Grafana
    Format: métrique{label="value"} valeur timestamp
    """
    from django.db.models import Count, Sum, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    
    metrics = []
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # ===== MÉTRIQUES BACKUPS =====
    total_backups = BackupJob.objects.count()
    metrics.append(f'esxi_backups_total {total_backups}')
    
    backups_completed = BackupJob.objects.filter(status='completed').count()
    metrics.append(f'esxi_backups_completed_total {backups_completed}')
    
    backups_failed = BackupJob.objects.filter(status='failed').count()
    metrics.append(f'esxi_backups_failed_total {backups_failed}')
    
    backups_running = BackupJob.objects.filter(status='running').count()
    metrics.append(f'esxi_backups_running {backups_running}')
    
    # Backups des dernières 24h
    backups_24h = BackupJob.objects.filter(created_at__gte=last_24h).count()
    metrics.append(f'esxi_backups_last_24h {backups_24h}')
    
    # Taux de succès
    success_rate = (backups_completed / total_backups * 100) if total_backups > 0 else 0
    metrics.append(f'esxi_backups_success_rate {success_rate:.2f}')
    
    # ===== MÉTRIQUES EXPORTS OVF =====
    ovf_exports = OVFExportJob.objects.count()
    metrics.append(f'esxi_ovf_exports_total {ovf_exports}')
    
    ovf_completed = OVFExportJob.objects.filter(status='completed').count()
    metrics.append(f'esxi_ovf_exports_completed_total {ovf_completed}')
    
    ovf_failed = OVFExportJob.objects.filter(status='failed').count()
    metrics.append(f'esxi_ovf_exports_failed_total {ovf_failed}')
    
    ovf_running = OVFExportJob.objects.filter(status='running').count()
    metrics.append(f'esxi_ovf_exports_running {ovf_running}')
    
    # Taille totale exportée (en GB)
    total_exported_mb = OVFExportJob.objects.filter(
        status='completed'
    ).aggregate(total=Sum('export_size_mb'))['total'] or 0
    total_exported_gb = total_exported_mb / 1024
    metrics.append(f'esxi_ovf_total_exported_gb {total_exported_gb:.2f}')
    
    # ===== MÉTRIQUES SERVEURS ESXi =====
    esxi_servers = ESXiServer.objects.count()
    metrics.append(f'esxi_servers_total {esxi_servers}')
    
    # ===== MÉTRIQUES VMS =====
    vms_total = VirtualMachine.objects.count()
    metrics.append(f'esxi_vms_total {vms_total}')
    
    vms_powered_on = VirtualMachine.objects.filter(power_state='poweredOn').count()
    metrics.append(f'esxi_vms_powered_on {vms_powered_on}')
    
    vms_powered_off = VirtualMachine.objects.filter(power_state='poweredOff').count()
    metrics.append(f'esxi_vms_powered_off {vms_powered_off}')
    
    # ===== MÉTRIQUES RÉPLICATION =====
    replications_total = VMReplication.objects.count()
    metrics.append(f'esxi_replications_total {replications_total}')
    
    replications_active = VMReplication.objects.filter(status='active', is_active=True).count()
    metrics.append(f'esxi_replications_active {replications_active}')
    
    replications_paused = VMReplication.objects.filter(status='paused').count()
    metrics.append(f'esxi_replications_paused {replications_paused}')
    
    replications_error = VMReplication.objects.filter(status='error').count()
    metrics.append(f'esxi_replications_error {replications_error}')
    
    # Failovers
    failovers_total = FailoverEvent.objects.count()
    metrics.append(f'esxi_failovers_total {failovers_total}')
    
    failovers_completed = FailoverEvent.objects.filter(status='completed').count()
    metrics.append(f'esxi_failovers_completed {failovers_completed}')
    
    failovers_failed = FailoverEvent.objects.filter(status='failed').count()
    metrics.append(f'esxi_failovers_failed {failovers_failed}')
    
    # ===== MÉTRIQUES SUREBACKUP =====
    verifications_total = BackupVerification.objects.count()
    metrics.append(f'esxi_verifications_total {verifications_total}')
    
    verifications_passed = BackupVerification.objects.filter(status='passed').count()
    metrics.append(f'esxi_verifications_passed {verifications_passed}')
    
    verifications_failed = BackupVerification.objects.filter(status='failed').count()
    metrics.append(f'esxi_verifications_failed {verifications_failed}')
    
    verifications_running = BackupVerification.objects.filter(status='running').count()
    metrics.append(f'esxi_verifications_running {verifications_running}')
    
    # Taux de succès des vérifications
    verification_success_rate = (verifications_passed / verifications_total * 100) if verifications_total > 0 else 0
    metrics.append(f'esxi_verifications_success_rate {verification_success_rate:.2f}')
    
    # ===== MÉTRIQUES DATASTORES =====
    datastores = DatastoreInfo.objects.all()
    for ds in datastores:
        if ds.capacity and ds.free_space:
            used_percent = ((ds.capacity - ds.free_space) / ds.capacity) * 100
            # Utilisez des labels pour identifier chaque datastore
            safe_name = ds.name.replace(' ', '_').replace('-', '_')
            metrics.append(f'esxi_datastore_used_percent{{datastore="{ds.name}"}} {used_percent:.2f}')
            metrics.append(f'esxi_datastore_capacity_gb{{datastore="{ds.name}"}} {ds.capacity / (1024**3):.2f}')
            metrics.append(f'esxi_datastore_free_gb{{datastore="{ds.name}"}} {ds.free_space / (1024**3):.2f}')
    
    # ===== MÉTRIQUES SNAPSHOTS =====
    snapshots_total = Snapshot.objects.count()
    metrics.append(f'esxi_snapshots_total {snapshots_total}')
    
    # ===== MÉTRIQUES PERFORMANCES =====
    # Temps moyen de backup (en secondes)
    avg_backup_duration = BackupJob.objects.filter(
        status='completed',
        backup_duration_seconds__isnull=False
    ).aggregate(avg=Avg('backup_duration_seconds'))['avg'] or 0
    metrics.append(f'esxi_backup_avg_duration_seconds {avg_backup_duration:.2f}')
    
    # Temps moyen d'export OVF (en secondes)
    avg_export_duration = OVFExportJob.objects.filter(
        status='completed',
        export_duration_seconds__isnull=False
    ).aggregate(avg=Avg('export_duration_seconds'))['avg'] or 0
    metrics.append(f'esxi_ovf_export_avg_duration_seconds {avg_export_duration:.2f}')
    
    # Construire la réponse au format Prometheus
    response_text = '\n'.join(metrics) + '\n'
    
    from django.http import HttpResponse
    return HttpResponse(response_text, content_type='text/plain; version=0.0.4')



# ==========================================================
# 🔹 EMAIL SETTINGS
# ==========================================================
class EmailSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email notification settings.
    Only one instance exists (singleton pattern).
    """
    queryset = EmailSettings.objects.all()
    serializer_class = EmailSettingsSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get the email settings (singleton)"""
        settings = EmailSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def create(self, request):
        """Override create to update existing settings instead"""
        settings = EmailSettings.get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def update(self, request, pk=None):
        """Update email settings"""
        settings = EmailSettings.get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"[EMAIL] Settings updated: {settings}")
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def test_email(self, request):
        """Send a test email to verify SMTP configuration"""
        try:
            recipient_email = request.data.get("recipient_email")
            
            if not recipient_email:
                # Use admin email if no recipient specified
                settings = EmailSettings.get_settings()
                recipient_email = settings.admin_email

            if not recipient_email:
                return Response(
                    {"status": "error", "message": "Aucun email destinataire spécifié"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Send test email
            success = EmailNotificationService.send_test_email(recipient_email)

            if success:
                return Response({
                    "status": "success",
                    "message": f"Email de test envoyé à {recipient_email}"
                })
            else:
                return Response(
                    {"status": "error", "message": "Échec de l'envoi de l'email de test. Vérifiez les paramètres SMTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"[EMAIL] Error sending test email: {str(e)}")
            return Response(
                {"status": "error", "message": f"Erreur: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

