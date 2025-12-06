"""
Service pour gérer la réplication de VMs et le failover entre serveurs ESXi
"""
import logging
import os
import tempfile
import shutil
from datetime import datetime
from django.utils import timezone
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit

from esxi.models import VirtualMachine, ESXiServer
from backups.models import VMReplication, FailoverEvent
from backups.ovf_export_service import OVFExportService
from esxi.vmware_service import VMwareService

logger = logging.getLogger(__name__)


class ReplicationService:
    """Service de réplication et failover de VMs"""

    def __init__(self):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.context.verify_mode = ssl.CERT_NONE

    def _connect_to_server(self, esxi_server):
        """
        Établir une connexion à un serveur ESXi

        Args:
            esxi_server: Instance ESXiServer

        Returns:
            ServiceInstance: Connexion pyVmomi
        """
        try:
            si = SmartConnect(
                host=esxi_server.hostname,
                user=esxi_server.username,
                pwd=esxi_server.password,
                port=esxi_server.port or 443,
                sslContext=self.context
            )
            atexit.register(Disconnect, si)
            return si
        except Exception as e:
            logger.error(f"Erreur connexion à {esxi_server.hostname}: {e}")
            raise

    def _get_vm_by_name(self, si, vm_name):
        """
        Récupérer une VM par son nom

        Args:
            si: ServiceInstance
            vm_name: Nom de la VM

        Returns:
            vim.VirtualMachine ou None
        """
        content = si.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )

        for vm in container.view:
            if vm.name == vm_name:
                container.Destroy()
                return vm

        container.Destroy()
        return None

    def replicate_vm(self, replication):
        """
        Effectuer une réplication complète de VM

        Processus :
        1. Exporter la VM source en OVF (temporaire)
        2. Déployer sur le serveur destination avec suffix "_replica"
        3. La VM replica est prête pour le failover instantané

        Args:
            replication: Instance VMReplication

        Returns:
            dict: Résultat de la réplication
        """
        temp_dir = None
        try:
            start_time = timezone.now()
            logger.info(f"[REPLICATION] Démarrage: {replication.name}")

            source_server = replication.get_source_server
            destination_server = replication.destination_server
            vm_name = replication.virtual_machine.name
            replica_vm_name = f"{vm_name}_replica"

            # Vérifier si la VM replica existe déjà
            logger.info(f"[REPLICATION] Connexion au serveur destination: {destination_server.hostname}")
            dest_si = self._connect_to_server(destination_server)
            existing_replica = self._get_vm_by_name(dest_si, replica_vm_name)

            if existing_replica:
                logger.info(f"[REPLICATION] VM replica existe déjà: {replica_vm_name}")
                logger.info(f"[REPLICATION] Suppression de l'ancienne replica pour mise à jour...")

                # Arrêter la VM si elle tourne
                if existing_replica.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                    power_off_task = existing_replica.PowerOffVM_Task()
                    while power_off_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                        pass

                # Supprimer la VM
                destroy_task = existing_replica.Destroy_Task()
                while destroy_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    pass

                logger.info(f"[REPLICATION] Ancienne replica supprimée")

            # Créer un répertoire temporaire pour l'export OVF
            temp_dir = tempfile.mkdtemp(prefix='replication_')
            logger.info(f"[REPLICATION] Répertoire temporaire: {temp_dir}")

            # Exporter la VM source en OVF
            logger.info(f"[REPLICATION] Export de la VM source: {vm_name}")
            ovf_service = OVFExportService()
            export_result = ovf_service.export_vm_to_ovf(
                esxi_server=source_server,
                vm_name=vm_name,
                export_path=temp_dir,
                export_format='ovf'
            )

            if not export_result.get('success'):
                raise Exception(f"Erreur export OVF: {export_result.get('error', 'Erreur inconnue')}")

            ovf_path = export_result['ovf_path']
            logger.info(f"[REPLICATION] Export OVF terminé: {ovf_path}")

            # Déployer sur le serveur destination avec le nom "_replica"
            logger.info(f"[REPLICATION] Déploiement sur serveur destination: {destination_server.hostname}")
            vmware_service = VMwareService(destination_server)

            # Récupérer le premier datastore disponible
            datastores_info = vmware_service.get_datastores()
            if not datastores_info or not datastores_info.get('datastores'):
                raise Exception("Aucun datastore disponible sur le serveur destination")

            dest_datastore = datastores_info['datastores'][0]['name']
            logger.info(f"[REPLICATION] Datastore destination: {dest_datastore}")

            # Déployer l'OVF
            deploy_success = vmware_service.deploy_ovf(
                ovf_path=ovf_path,
                vm_name=replica_vm_name,
                datastore_name=dest_datastore,
                network_name='VM Network',
                power_on=False  # Ne pas démarrer la replica automatiquement
            )

            if not deploy_success:
                raise Exception("Échec du déploiement OVF sur le serveur destination")

            logger.info(f"[REPLICATION] VM replica déployée: {replica_vm_name}")

            # Nettoyer le répertoire temporaire
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"[REPLICATION] Répertoire temporaire nettoyé")

            # Mettre à jour la réplication
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            replication.last_replication_at = end_time
            replication.last_replication_duration_seconds = int(duration)
            replication.status = 'active'
            replication.save()

            logger.info(f"[REPLICATION] Terminée: {replication.name} ({duration:.2f}s)")

            # Déconnexion
            Disconnect(dest_si)

            return {
                'success': True,
                'duration_seconds': duration,
                'message': f"Réplication de {vm_name} terminée avec succès. VM replica: {replica_vm_name}"
            }

        except Exception as e:
            logger.error(f"[REPLICATION] Erreur: {replication.name}: {e}")

            # Nettoyer le répertoire temporaire en cas d'erreur
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

            replication.status = 'error'
            replication.save()

            return {
                'success': False,
                'error': str(e),
                'message': f"Erreur lors de la réplication: {e}"
            }

    def execute_failover(self, failover_event, test_mode=False):
        """
        Exécuter un failover (basculement)

        Args:
            failover_event: Instance FailoverEvent
            test_mode: Si True, ne pas arrêter la VM source

        Returns:
            dict: Résultat du failover
        """
        try:
            logger.info(f"Démarrage failover: {failover_event.id}")
            failover_event.status = 'in_progress'
            failover_event.save()

            replication = failover_event.replication
            source_server = replication.get_source_server
            destination_server = replication.destination_server
            vm_name = replication.virtual_machine.name

            # Se connecter aux serveurs
            logger.info(f"Connexion au serveur source: {source_server.hostname}")
            source_si = self._connect_to_server(source_server)

            logger.info(f"Connexion au serveur destination: {destination_server.hostname}")
            dest_si = self._connect_to_server(destination_server)

            # Récupérer les VMs
            source_vm = self._get_vm_by_name(source_si, vm_name)
            dest_vm = self._get_vm_by_name(dest_si, f"{vm_name}_replica")

            if not dest_vm:
                # Si la VM de destination n'existe pas, utiliser le même nom
                dest_vm = self._get_vm_by_name(dest_si, vm_name)

            if not dest_vm:
                raise Exception(f"VM de destination non trouvée sur {destination_server.hostname}")

            # Arrêter la VM source (sauf en mode test)
            if source_vm and source_vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                if not test_mode:
                    logger.info(f"Arrêt de la VM source: {vm_name}")
                    power_off_task = source_vm.PowerOffVM_Task()

                    # Attendre la fin de l'arrêt
                    while power_off_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                        pass

                    if power_off_task.info.state == vim.TaskInfo.State.error:
                        raise Exception(f"Erreur arrêt VM source: {power_off_task.info.error}")

                    failover_event.source_vm_powered_off = True
                    failover_event.save()
                    logger.info(f"VM source arrêtée: {vm_name}")
                else:
                    logger.info(f"Mode test: VM source non arrêtée")

            # Démarrer la VM de destination
            if dest_vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:
                logger.info(f"Démarrage de la VM de destination: {vm_name}")
                power_on_task = dest_vm.PowerOnVM_Task()

                # Attendre le démarrage
                while power_on_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    pass

                if power_on_task.info.state == vim.TaskInfo.State.error:
                    raise Exception(f"Erreur démarrage VM destination: {power_on_task.info.error}")

                failover_event.destination_vm_powered_on = True
                failover_event.save()
                logger.info(f"VM de destination démarrée: {vm_name}")
            else:
                logger.info(f"VM de destination déjà démarrée: {vm_name}")
                failover_event.destination_vm_powered_on = True
                failover_event.save()

            # Marquer le failover comme terminé
            failover_event.status = 'completed'
            failover_event.completed_at = timezone.now()
            failover_event.save()

            # Déconnexion
            Disconnect(source_si)
            Disconnect(dest_si)

            logger.info(f"Failover terminé avec succès: {failover_event.id}")

            return {
                'success': True,
                'message': f"Failover de {vm_name} terminé avec succès",
                'source_powered_off': failover_event.source_vm_powered_off,
                'destination_powered_on': failover_event.destination_vm_powered_on
            }

        except Exception as e:
            logger.error(f"Erreur lors du failover {failover_event.id}: {e}")

            failover_event.status = 'failed'
            failover_event.error_message = str(e)
            failover_event.completed_at = timezone.now()
            failover_event.save()

            return {
                'success': False,
                'error': str(e),
                'message': f"Erreur lors du failover: {e}"
            }

    def check_and_trigger_auto_failover(self, replication):
        """
        Vérifier si un failover automatique doit être déclenché

        Args:
            replication: Instance VMReplication

        Returns:
            dict: Résultat de la vérification
        """
        if replication.failover_mode != 'automatic':
            return {'should_failover': False, 'reason': 'Mode automatique non activé'}

        # Vérifier si le serveur source est indisponible
        source_server = replication.get_source_server

        try:
            # Tenter de se connecter au serveur source
            si = self._connect_to_server(source_server)

            # Vérifier la VM
            vm = self._get_vm_by_name(si, replication.virtual_machine.name)

            if not vm:
                return {'should_failover': False, 'reason': 'VM non trouvée'}

            # Vérifier l'état de la VM
            if vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:
                # VM éteinte, vérifier le délai
                if replication.last_replication_at:
                    minutes_since_last = (timezone.now() - replication.last_replication_at).total_seconds() / 60

                    if minutes_since_last >= replication.auto_failover_threshold_minutes:
                        return {
                            'should_failover': True,
                            'reason': f'VM éteinte depuis {minutes_since_last:.0f} minutes'
                        }

            Disconnect(si)
            return {'should_failover': False, 'reason': 'VM en fonctionnement normal'}

        except Exception as e:
            logger.error(f"Erreur vérification auto-failover pour {replication.name}: {e}")

            # Serveur source inaccessible
            if replication.last_replication_at:
                minutes_since_last = (timezone.now() - replication.last_replication_at).total_seconds() / 60

                if minutes_since_last >= replication.auto_failover_threshold_minutes:
                    return {
                        'should_failover': True,
                        'reason': f'Serveur source inaccessible depuis {minutes_since_last:.0f} minutes'
                    }

            return {'should_failover': False, 'reason': f'Serveur source inaccessible (en attente du délai): {e}'}
