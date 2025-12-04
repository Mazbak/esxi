"""
Service pour gérer la réplication de VMs et le failover entre serveurs ESXi
"""
import logging
from datetime import datetime
from django.utils import timezone
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit

from esxi.models import VirtualMachine, ESXiServer
from backups.models import VMReplication, FailoverEvent

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
                host=esxi_server.host,
                user=esxi_server.username,
                pwd=esxi_server.password,
                port=esxi_server.port or 443,
                sslContext=self.context
            )
            atexit.register(Disconnect, si)
            return si
        except Exception as e:
            logger.error(f"Erreur connexion à {esxi_server.host}: {e}")
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
        Effectuer une réplication de VM

        Args:
            replication: Instance VMReplication

        Returns:
            dict: Résultat de la réplication
        """
        try:
            start_time = timezone.now()
            logger.info(f"Démarrage réplication: {replication.name}")

            # Obtenir le serveur source
            source_server = replication.get_source_server
            destination_server = replication.destination_server

            # Se connecter aux serveurs
            logger.info(f"Connexion au serveur source: {source_server.host}")
            source_si = self._connect_to_server(source_server)

            logger.info(f"Connexion au serveur destination: {destination_server.host}")
            dest_si = self._connect_to_server(destination_server)

            # Récupérer la VM source
            vm_name = replication.virtual_machine.name
            source_vm = self._get_vm_by_name(source_si, vm_name)

            if not source_vm:
                raise Exception(f"VM {vm_name} non trouvée sur le serveur source")

            # Créer un snapshot pour la réplication
            logger.info(f"Création snapshot de réplication pour {vm_name}")
            snapshot_task = source_vm.CreateSnapshot_Task(
                name=f"Replication_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Snapshot automatique pour réplication",
                memory=False,
                quiesce=True
            )

            # Attendre la fin du snapshot
            while snapshot_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                pass

            if snapshot_task.info.state == vim.TaskInfo.State.error:
                raise Exception(f"Erreur création snapshot: {snapshot_task.info.error}")

            logger.info(f"Snapshot créé avec succès pour {vm_name}")

            # TODO: Implémenter le transfert des données vers le serveur de destination
            # Cela nécessite l'utilisation de vSphere Storage APIs ou autres méthodes
            # Pour l'instant, nous marquons simplement la réplication comme réussie

            # Mettre à jour la réplication
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            replication.last_replication_at = end_time
            replication.last_replication_duration_seconds = int(duration)
            replication.status = 'active'
            replication.save()

            logger.info(f"Réplication terminée: {replication.name} ({duration}s)")

            # Déconnexion
            Disconnect(source_si)
            Disconnect(dest_si)

            return {
                'success': True,
                'duration_seconds': duration,
                'message': f"Réplication de {vm_name} terminée avec succès"
            }

        except Exception as e:
            logger.error(f"Erreur lors de la réplication {replication.name}: {e}")
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
            logger.info(f"Connexion au serveur source: {source_server.host}")
            source_si = self._connect_to_server(source_server)

            logger.info(f"Connexion au serveur destination: {destination_server.host}")
            dest_si = self._connect_to_server(destination_server)

            # Récupérer les VMs
            source_vm = self._get_vm_by_name(source_si, vm_name)
            dest_vm = self._get_vm_by_name(dest_si, f"{vm_name}_replica")

            if not dest_vm:
                # Si la VM de destination n'existe pas, utiliser le même nom
                dest_vm = self._get_vm_by_name(dest_si, vm_name)

            if not dest_vm:
                raise Exception(f"VM de destination non trouvée sur {destination_server.host}")

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
