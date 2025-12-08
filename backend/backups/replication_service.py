"""
Service pour gérer la réplication de VMs et le failover entre serveurs ESXi
"""
import logging
import os
import tempfile
import shutil
import requests
import urllib3
import xml.etree.ElementTree as ET
from datetime import datetime
from django.utils import timezone
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit

from esxi.models import VirtualMachine, ESXiServer
from backups.models import VMReplication, FailoverEvent
from esxi.vmware_service import VMwareService

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    def _export_vm_to_ovf(self, si, vm_name, export_path, esxi_host, esxi_user, esxi_pass, progress_callback=None, replication_id=None):
        """
        Exporter une VM en format OVF en utilisant HttpNfcLease API
        Version simplifiée sans dépendances sur les modèles Django

        Args:
            si: ServiceInstance pyVmomi
            vm_name: Nom de la VM à exporter
            export_path: Chemin où exporter l'OVF
            esxi_host: Hostname du serveur ESXi
            esxi_user: Username ESXi
            esxi_pass: Password ESXi
            progress_callback: Callback optionnel pour progression
            replication_id: ID de réplication pour vérifier l'annulation

        Returns:
            str: Chemin vers le fichier OVF généré
        """
        vm_obj = self._get_vm_by_name(si, vm_name)
        if not vm_obj:
            raise Exception(f"VM {vm_name} non trouvée")

        logger.info(f"[REPLICATION] Début export OVF de {vm_name}")

        # Créer un lease d'export
        lease = vm_obj.ExportVm()

        # Attendre que le lease soit prêt
        while lease.state == vim.HttpNfcLease.State.initializing:
            pass

        if lease.state != vim.HttpNfcLease.State.ready:
            raise Exception(f"Export lease échoué: {lease.state}")

        try:
            # Télécharger les fichiers VMDK
            vmdk_files = []
            device_urls = lease.info.deviceUrl

            # Calculer total_size depuis l'API si disponible
            total_size = sum(d.targetSize for d in device_urls if hasattr(d, 'targetSize'))

            # Si total_size = 0 (métadonnées incomplètes), faire une passe pour récupérer les tailles réelles
            if total_size == 0:
                logger.info(f"[REPLICATION] targetSize non disponible, récupération tailles réelles via HTTP HEAD...")
                for device_url in device_urls:
                    if not device_url.url.endswith('.vmdk'):
                        continue
                    url = device_url.url.replace('*', esxi_host)
                    try:
                        # HEAD request pour obtenir Content-Length sans télécharger
                        head_response = requests.head(
                            url,
                            auth=(esxi_user, esxi_pass),
                            verify=False,
                            timeout=10
                        )
                        file_size = int(head_response.headers.get('content-length', 0))
                        total_size += file_size
                    except Exception as e:
                        logger.warning(f"[REPLICATION] Impossible de récupérer la taille de {url}: {e}")

                logger.info(f"[REPLICATION] Taille totale calculée depuis HTTP: {total_size / (1024*1024):.2f} MB")
            else:
                logger.info(f"[REPLICATION] Taille totale depuis API: {total_size / (1024*1024):.2f} MB")

            downloaded = 0
            last_lease_update = 0  # Dernier pourcentage où on a mis à jour le lease
            last_ui_update = 0  # Dernier pourcentage où on a mis à jour l'UI
            chunk_counter = 0  # Compteur de chunks

            file_index = 0
            for device_url in device_urls:
                if not device_url.url.endswith('.vmdk'):
                    continue

                # Remplacer * par l'IP du serveur ESXi
                url = device_url.url.replace('*', esxi_host)
                filename = os.path.basename(device_url.targetId)
                local_path = os.path.join(export_path, filename)

                logger.info(f"[REPLICATION] Téléchargement {filename}...")

                # Télécharger le VMDK
                response = requests.get(
                    url,
                    auth=(esxi_user, esxi_pass),
                    verify=False,
                    stream=True
                )
                response.raise_for_status()

                file_size = int(response.headers.get('content-length', 0))
                file_downloaded = 0

                # Si file_size = 0, utiliser une estimation basée sur la taille du disque
                if file_size == 0 and hasattr(device_url, 'targetSize') and device_url.targetSize > 0:
                    file_size = device_url.targetSize
                    logger.info(f"[REPLICATION] Utilisation targetSize comme estimation: {file_size / (1024*1024):.2f} MB")

                with open(local_path, 'wb') as f:
                    chunk_size = 65536  # 64KB chunks pour meilleure performance
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            # VÉRIFIER L'ANNULATION AVANT CHAQUE CHUNK
                            if replication_id:
                                from django.core.cache import cache
                                progress_data = cache.get(f'replication_progress_{replication_id}')
                                if progress_data and progress_data.get('status') == 'cancelled':
                                    logger.info(f"[REPLICATION] Annulation détectée, arrêt du téléchargement")
                                    raise Exception("Réplication annulée par l'utilisateur")

                            f.write(chunk)
                            downloaded += len(chunk)
                            file_downloaded += len(chunk)
                            chunk_counter += 1

                            # Mettre à jour la progression du lease ET du callback
                            # Calculer le pourcentage pour le lease (0-100)
                            if total_size > 0:
                                lease_progress = int((downloaded / total_size) * 100)
                            else:
                                # Si total_size = 0, utiliser la progression du fichier actuel
                                lease_progress = int((file_downloaded / file_size) * 100) if file_size > 0 else 0

                            # Mettre à jour le lease tous les 2% pour garder le lease actif
                            if lease_progress >= last_lease_update + 2:
                                try:
                                    lease.HttpNfcLeaseProgress(lease_progress)
                                    last_lease_update = lease_progress
                                    logger.debug(f"[REPLICATION] Lease progress: {lease_progress}%")
                                except:
                                    pass  # Ignorer les erreurs de mise à jour du lease

                            # Calculer la progression UI (25-60%)
                            if total_size > 0:
                                progress_pct = 25 + (35 * downloaded / total_size)
                            else:
                                # Si total_size = 0, estimer la progression sur 35% de 25 à 60
                                # Utiliser une progression linéaire basée sur les données téléchargées
                                if file_size > 0:
                                    progress_pct = 25 + (35 * file_downloaded / file_size)
                                else:
                                    # Pas de taille connue, progression constante à 25% pendant le téléchargement
                                    progress_pct = 25

                            # Mettre à jour l'UI très fréquemment : tous les 0.5% OU tous les 10 chunks (~640KB)
                            # Cela garantit une progression fluide et visible même pour les petits fichiers
                            if (progress_pct >= last_ui_update + 0.5) or (chunk_counter >= 10):
                                if progress_callback:
                                    downloaded_mb = downloaded / (1024 * 1024)
                                    file_mb = file_downloaded / (1024 * 1024)
                                    file_size_mb = file_size / (1024 * 1024)
                                    if total_size > 0:
                                        total_mb = total_size / (1024 * 1024)
                                        progress_callback(
                                            progress_pct,
                                            'exporting',
                                            f'Export VMDK: {downloaded_mb:.1f}/{total_mb:.1f} MB ({int(progress_pct)}%)'
                                        )
                                    elif file_size > 0:
                                        progress_callback(
                                            progress_pct,
                                            'exporting',
                                            f'Export {filename}: {file_mb:.1f}/{file_size_mb:.1f} MB ({int(progress_pct)}%)'
                                        )
                                    else:
                                        # Taille inconnue, afficher seulement les MB téléchargés
                                        progress_callback(
                                            progress_pct,
                                            'exporting',
                                            f'Export {filename}: {file_mb:.1f} MB téléchargés...'
                                        )
                                    last_ui_update = progress_pct
                                    chunk_counter = 0

                vmdk_files.append({
                    'path': local_path,
                    'filename': filename,
                    'size': file_size
                })
                logger.info(f"[REPLICATION] {filename} téléchargé: {file_size / (1024*1024):.2f} MB")
                file_index += 1

            # Créer le descripteur OVF
            ovf_path = os.path.join(export_path, f"{vm_name}.ovf")
            self._create_simple_ovf_descriptor(vm_obj, vmdk_files, ovf_path)

            # Compléter le lease seulement s'il est encore actif
            try:
                if lease.state == vim.HttpNfcLease.State.ready:
                    lease.HttpNfcLeaseComplete()
                    logger.info(f"[REPLICATION] Lease complété avec succès")
            except Exception as lease_err:
                logger.warning(f"[REPLICATION] Impossible de compléter le lease (probablement déjà fermé): {lease_err}")

            logger.info(f"[REPLICATION] Export OVF terminé: {ovf_path}")
            return ovf_path

        except Exception as e:
            # Annuler le lease seulement s'il est encore actif
            try:
                if lease.state in [vim.HttpNfcLease.State.ready, vim.HttpNfcLease.State.initializing]:
                    lease.HttpNfcLeaseAbort()
            except:
                pass  # Ignorer les erreurs lors de l'annulation
            raise

    def _create_simple_ovf_descriptor(self, vm_obj, vmdk_files, ovf_path):
        """Créer un descripteur OVF simplifié"""
        # Créer la structure OVF de base
        ovf_ns = "http://schemas.dmtf.org/ovf/envelope/1"
        rasd_ns = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"
        vssd_ns = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"

        ET.register_namespace('ovf', ovf_ns)
        ET.register_namespace('rasd', rasd_ns)
        ET.register_namespace('vssd', vssd_ns)

        root = ET.Element(f"{{{ovf_ns}}}Envelope")

        # Références
        references = ET.SubElement(root, f"{{{ovf_ns}}}References")
        for vmdk in vmdk_files:
            file_elem = ET.SubElement(references, f"{{{ovf_ns}}}File")
            file_elem.set(f"{{{ovf_ns}}}href", vmdk['filename'])
            file_elem.set(f"{{{ovf_ns}}}id", vmdk['filename'])
            file_elem.set(f"{{{ovf_ns}}}size", str(vmdk['size']))

        # DiskSection
        disk_section = ET.SubElement(root, f"{{{ovf_ns}}}DiskSection")
        ET.SubElement(disk_section, f"{{{ovf_ns}}}Info").text = "Virtual disk information"

        for i, vmdk in enumerate(vmdk_files):
            disk = ET.SubElement(disk_section, f"{{{ovf_ns}}}Disk")
            disk.set(f"{{{ovf_ns}}}diskId", f"vmdisk{i+1}")
            disk.set(f"{{{ovf_ns}}}fileRef", vmdk['filename'])
            disk.set(f"{{{ovf_ns}}}capacity", str(vmdk['size']))

        # VirtualSystem
        vs = ET.SubElement(root, f"{{{ovf_ns}}}VirtualSystem")
        vs.set(f"{{{ovf_ns}}}id", vm_obj.name)
        ET.SubElement(vs, f"{{{ovf_ns}}}Info").text = f"Virtual Machine {vm_obj.name}"
        ET.SubElement(vs, f"{{{ovf_ns}}}Name").text = vm_obj.name

        # Écrire le fichier OVF
        tree = ET.ElementTree(root)
        tree.write(ovf_path, encoding='utf-8', xml_declaration=True)

        logger.info(f"[REPLICATION] Descripteur OVF créé: {ovf_path}")

    def replicate_vm(self, replication, progress_callback=None, replication_id=None):
        """
        Effectuer une réplication complète de VM

        Processus :
        1. Exporter la VM source en OVF (temporaire)
        2. Déployer sur le serveur destination avec suffix "_replica"
        3. La VM replica est prête pour le failover instantané

        Args:
            replication: Instance VMReplication
            progress_callback: Fonction callback pour la progression (optionnel)
            replication_id: ID de réplication pour vérifier l'annulation (optionnel)

        Returns:
            dict: Résultat de la réplication
        """
        temp_dir = None
        try:
            import time
            start_time = timezone.now()
            logger.info(f"[REPLICATION] Démarrage: {replication.name}")

            if progress_callback:
                progress_callback(0, 'starting', 'Démarrage de la réplication...')

            source_server = replication.get_source_server
            destination_server = replication.destination_server
            vm_name = replication.virtual_machine.name
            replica_vm_name = f"{vm_name}_replica"

            # Progression graduelle 0-2%
            if progress_callback:
                progress_callback(1, 'initializing', 'Initialisation de la réplication...')
                time.sleep(0.3)
                progress_callback(2, 'initializing', 'Vérification des serveurs...')

            # Vérifier si la VM replica existe déjà (3-8%)
            logger.info(f"[REPLICATION] Connexion au serveur destination: {destination_server.hostname}")
            if progress_callback:
                progress_callback(3, 'connecting', f'Connexion au serveur destination...')
                time.sleep(0.2)
                progress_callback(5, 'connecting', f'Établissement de la connexion à {destination_server.hostname}...')

            dest_si = self._connect_to_server(destination_server)

            if progress_callback:
                progress_callback(7, 'checking', 'Vérification de la VM replica existante...')

            existing_replica = self._get_vm_by_name(dest_si, replica_vm_name)

            if existing_replica:
                logger.info(f"[REPLICATION] VM replica existe déjà: {replica_vm_name}")
                logger.info(f"[REPLICATION] Suppression de l'ancienne replica pour mise à jour...")

                if progress_callback:
                    progress_callback(8, 'cleaning', 'Préparation de la suppression...')
                    time.sleep(0.2)
                    progress_callback(10, 'cleaning', 'Suppression de l\'ancienne replica...')

                # Arrêter la VM si elle tourne
                if existing_replica.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                    if progress_callback:
                        progress_callback(11, 'cleaning', 'Arrêt de l\'ancienne VM replica...')
                    power_off_task = existing_replica.PowerOffVM_Task()
                    while power_off_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                        time.sleep(0.1)

                # Supprimer la VM
                if progress_callback:
                    progress_callback(13, 'cleaning', 'Suppression des fichiers de la replica...')
                destroy_task = existing_replica.Destroy_Task()
                while destroy_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    time.sleep(0.1)

                logger.info(f"[REPLICATION] Ancienne replica supprimée")
                if progress_callback:
                    progress_callback(15, 'cleaned', 'Ancienne replica supprimée')
            else:
                # Pas de replica existante, progression rapide
                if progress_callback:
                    progress_callback(10, 'checking', 'Aucune replica existante trouvée')
                    time.sleep(0.2)
                    progress_callback(15, 'ready', 'Prêt pour la réplication')

            # Créer un répertoire temporaire pour l'export OVF (16-18%)
            if progress_callback:
                progress_callback(16, 'preparing', 'Création du répertoire temporaire...')

            temp_dir = tempfile.mkdtemp(prefix='replication_')
            logger.info(f"[REPLICATION] Répertoire temporaire: {temp_dir}")

            if progress_callback:
                progress_callback(18, 'preparing', 'Préparation de l\'export OVF...')
                time.sleep(0.2)

            # Se connecter au serveur source pour l'export (19-24%)
            logger.info(f"[REPLICATION] Connexion au serveur source: {source_server.hostname}")
            if progress_callback:
                progress_callback(19, 'connecting', f'Connexion au serveur source...')
                time.sleep(0.2)
                progress_callback(21, 'connecting', f'Établissement de la connexion à {source_server.hostname}...')

            source_si = self._connect_to_server(source_server)

            if progress_callback:
                progress_callback(23, 'connected', 'Serveur source connecté')
                time.sleep(0.2)
                progress_callback(24, 'preparing', f'Préparation de l\'export de {vm_name}...')

            # Exporter la VM source en OVF (25% → 60%)
            logger.info(f"[REPLICATION] Export de la VM source: {vm_name}")
            if progress_callback:
                progress_callback(25, 'exporting', f'Export de la VM {vm_name} en cours...')

            ovf_path = self._export_vm_to_ovf(
                source_si,
                vm_name,
                temp_dir,
                source_server.hostname,
                source_server.username,
                source_server.password,
                progress_callback,
                replication_id
            )
            logger.info(f"[REPLICATION] Export OVF terminé: {ovf_path}")

            if progress_callback:
                progress_callback(60, 'exported', 'Export OVF terminé avec succès')

            # Déconnexion du serveur source
            Disconnect(source_si)

            # Déployer sur le serveur destination avec le nom "_replica" (65%)
            logger.info(f"[REPLICATION] Déploiement sur serveur destination: {destination_server.hostname}")
            if progress_callback:
                progress_callback(65, 'deploying', f'Déploiement de la replica sur {destination_server.hostname}...')

            vmware_service = VMwareService(
                host=destination_server.hostname,
                user=destination_server.username,
                password=destination_server.password,
                port=destination_server.port or 443
            )

            # Récupérer le premier datastore disponible (70%)
            if progress_callback:
                progress_callback(70, 'deploying', 'Recherche du datastore de destination...')

            datastores_info = vmware_service.get_datastores()
            if not datastores_info or not datastores_info.get('datastores'):
                raise Exception("Aucun datastore disponible sur le serveur destination")

            dest_datastore = datastores_info['datastores'][0]['name']
            logger.info(f"[REPLICATION] Datastore destination: {dest_datastore}")

            # Déployer l'OVF (75% → 90%)
            if progress_callback:
                progress_callback(75, 'deploying', 'Déploiement de l\'OVF en cours...')

            # Créer un callback wrapper pour mapper 0-100% du déploiement vers 75-90% de la progression totale
            def deploy_progress_callback(deploy_pct, status, message):
                if progress_callback:
                    # Mapper 0-100% du déploiement vers 75-90% de la progression totale
                    total_pct = 75 + (15 * deploy_pct / 100)
                    progress_callback(total_pct, status, message)

            deploy_success = vmware_service.deploy_ovf(
                ovf_path=ovf_path,
                vm_name=replica_vm_name,
                datastore_name=dest_datastore,
                network_name='VM Network',
                power_on=False,  # Ne pas démarrer la replica automatiquement
                progress_callback=deploy_progress_callback
            )

            if not deploy_success:
                raise Exception("Échec du déploiement OVF sur le serveur destination")

            logger.info(f"[REPLICATION] VM replica déployée: {replica_vm_name}")

            if progress_callback:
                progress_callback(90, 'deployed', f'VM replica {replica_vm_name} déployée')
                time.sleep(0.3)
                progress_callback(92, 'finalizing', 'Vérification de la VM replica...')
                time.sleep(0.2)

            # Nettoyer le répertoire temporaire (93-96%)
            if progress_callback:
                progress_callback(93, 'cleaning', 'Début du nettoyage...')
                time.sleep(0.2)
                progress_callback(94, 'cleaning', 'Suppression des fichiers temporaires...')

            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"[REPLICATION] Répertoire temporaire nettoyé")

            if progress_callback:
                progress_callback(96, 'cleaned', 'Nettoyage terminé')
                time.sleep(0.2)

            # Mettre à jour la réplication (97-99%)
            if progress_callback:
                progress_callback(97, 'updating', 'Mise à jour des métadonnées de réplication...')

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            replication.last_replication_at = end_time
            replication.last_replication_duration_seconds = int(duration)
            replication.status = 'active'
            replication.save()

            logger.info(f"[REPLICATION] Terminée: {replication.name} ({duration:.2f}s)")

            if progress_callback:
                progress_callback(98, 'saving', 'Enregistrement de l\'état de réplication...')
                time.sleep(0.2)
                progress_callback(99, 'disconnecting', 'Déconnexion des serveurs...')

            # Déconnexion
            Disconnect(dest_si)

            if progress_callback:
                time.sleep(0.3)
                progress_callback(100, 'completed', f'✅ Réplication terminée avec succès en {duration:.1f}s')

            return {
                'success': True,
                'duration_seconds': duration,
                'message': f"Réplication de {vm_name} terminée avec succès. VM replica: {replica_vm_name}"
            }

        except Exception as e:
            logger.error(f"[REPLICATION] Erreur: {replication.name}: {e}")

            if progress_callback:
                progress_callback(-1, 'error', f'Erreur: {str(e)}')

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
