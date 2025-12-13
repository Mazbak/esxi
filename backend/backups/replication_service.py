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
        Établir une connexion à un serveur ESXi en utilisant VMwareService
        avec pré-test de connectivité TCP pour environnements multi-interface.

        Args:
            esxi_server: Instance ESXiServer

        Returns:
            ServiceInstance: Connexion pyVmomi

        Raises:
            Exception: Si la connexion échoue
        """
        try:
            logger.info(f"[REPLICATION] Connexion à {esxi_server.hostname} via VMwareService...")

            # Utiliser VMwareService qui inclut le pré-test TCP et la détection d'interface
            from esxi.vmware_service import VMwareService

            vmware = VMwareService(
                host=esxi_server.hostname,
                user=esxi_server.username,
                password=esxi_server.password,
                port=esxi_server.port or 443
            )

            # Appeler connect() qui fait le pré-test TCP automatiquement
            if not vmware.connect(timeout=60):
                raise Exception(f"Impossible de se connecter à {esxi_server.hostname}")

            logger.info(f"[REPLICATION] Connexion établie à {esxi_server.hostname}")

            # Retourner le service_instance pour compatibilité avec le code existant
            return vmware.service_instance

        except Exception as e:
            logger.error(f"[REPLICATION] Erreur connexion à {esxi_server.hostname}: {e}")
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

    def _download_vmdk_with_retry(self, url, local_path, esxi_user, esxi_pass, device_url,
                                    downloaded, file_index, total_size, last_lease_update, last_ui_update,
                                    chunk_counter, lease, progress_callback, replication_id):
        """
        Télécharge un fichier VMDK avec système de retry automatique en cas d'erreur réseau
        Supporte la reprise du téléchargement avec HTTP Range headers
        Utilise un thread de keepalive pour maintenir le lease ESXi actif

        Returns:
            tuple: (bytes_downloaded, last_lease_update, last_ui_update, chunk_counter, file_size)
        """
        import logging
        import threading
        import time
        logger = logging.getLogger(__name__)

        filename = os.path.basename(device_url.targetId)
        max_retries = 3
        retry_count = 0
        download_complete = False
        file_downloaded = 0
        file_size = 0

        # Thread de keepalive pour maintenir le lease actif
        keepalive_stop = threading.Event()
        keepalive_last_progress = [0]  # Liste pour pouvoir modifier dans le thread

        def lease_keepalive_thread():
            """Thread qui met à jour le lease toutes les 30 secondes pour éviter l'expiration"""
            logger.info(f"[KEEPALIVE] Thread de keepalive du lease démarré")
            while not keepalive_stop.is_set():
                try:
                    # Attendre 30 secondes (ou jusqu'à ce qu'on demande l'arrêt)
                    if keepalive_stop.wait(timeout=30):
                        break  # Stop demandé

                    # Mettre à jour le lease avec la dernière progression connue
                    current_progress = keepalive_last_progress[0]
                    lease.HttpNfcLeaseProgress(current_progress)
                    logger.debug(f"[KEEPALIVE] Lease mis à jour: {current_progress}%")

                except Exception as e:
                    logger.warning(f"[KEEPALIVE] Erreur lors de la mise à jour du lease: {e}")

            logger.info(f"[KEEPALIVE] Thread de keepalive arrêté")

        # Démarrer le thread de keepalive
        keepalive_thread = threading.Thread(target=lease_keepalive_thread, daemon=True)
        keepalive_thread.start()

        try:
            while retry_count <= max_retries and not download_complete:
                download_start_time = time.time()

                try:
                    # Vérifier si un téléchargement partiel existe (pour reprise)
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0 and retry_count > 0:
                        # Reprise du téléchargement
                        bytes_already_downloaded = os.path.getsize(local_path)
                        file_downloaded = bytes_already_downloaded
                        logger.info(f"[REPLICATION] [RETRY] Reprise à {bytes_already_downloaded / (1024*1024):.1f} MB (tentative {retry_count + 1}/{max_retries + 1})")

                        response = requests.get(
                            url,
                            auth=(esxi_user, esxi_pass),
                            verify=False,
                            stream=True,
                            headers={'Range': f'bytes={bytes_already_downloaded}-'},
                            timeout=(30, 600)  # 30s connexion, 600s (10 min) lecture entre chunks
                        )
                        response.raise_for_status()

                        file_mode = 'ab'  # Append mode
                        file_size_from_header = int(response.headers.get('content-length', 0))
                        if file_size_from_header > 0:
                            file_size = bytes_already_downloaded + file_size_from_header
                    else:
                        # Nouveau téléchargement
                        bytes_already_downloaded = 0
                        if retry_count > 0:
                            logger.info(f"[REPLICATION] [RETRY] Nouvelle tentative {retry_count + 1}/{max_retries + 1}")

                        response = requests.get(
                            url,
                            auth=(esxi_user, esxi_pass),
                            verify=False,
                            stream=True,
                            timeout=(30, 600)  # 30s connexion, 600s (10 min) lecture entre chunks
                        )
                        response.raise_for_status()

                        file_mode = 'wb'  # Write mode
                        file_size = int(response.headers.get('content-length', 0))
                        file_downloaded = 0

                    # Si file_size = 0, utiliser estimation basée sur targetSize
                    if file_size == 0 and hasattr(device_url, 'targetSize') and device_url.targetSize > 0:
                        file_size = device_url.targetSize
                        logger.info(f"[REPLICATION] Utilisation targetSize: {file_size / (1024*1024):.2f} MB")

                    with open(local_path, file_mode) as f:
                        chunk_size = 8192 * 1024  # 8 MB chunks pour meilleure performance réseau
                        chunks_received = 0
                        last_speed_update = time.time()
                        speed_mbps = 0

                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                # Vérifier annulation
                                if replication_id:
                                    from django.core.cache import cache
                                    progress_data = cache.get(f'replication_progress_{replication_id}')
                                    if progress_data and progress_data.get('status') == 'cancelled':
                                        logger.info(f"[REPLICATION] Annulation détectée")
                                        raise Exception("Réplication annulée par l'utilisateur")

                                f.write(chunk)
                                downloaded += len(chunk)
                                file_downloaded += len(chunk)
                                chunk_counter += 1
                                chunks_received += 1

                                # Mise à jour du lease (pour les logs et le keepalive thread)
                                if total_size > 0:
                                    lease_progress = int((downloaded / total_size) * 100)
                                else:
                                    lease_progress = int((file_downloaded / file_size) * 100) if file_size > 0 else 0

                                # Mettre à jour la progression pour le keepalive thread
                                keepalive_last_progress[0] = lease_progress

                                # Calcul de la vitesse (tous les 2 secondes)
                                current_time = time.time()
                                if current_time - last_speed_update >= 2.0:
                                    elapsed_time = current_time - download_start_time
                                    if elapsed_time > 0:
                                        speed_mbps = (downloaded / (1024 * 1024)) / elapsed_time
                                    last_speed_update = current_time

                                # Calcul progression UI (25-60%)
                                if total_size > 0:
                                    progress_pct = 25 + (35 * downloaded / total_size)
                                else:
                                    if file_size > 0:
                                        progress_pct = 25 + (35 * file_downloaded / file_size)
                                    else:
                                        # Formule améliorée pour gros fichiers (basée sur vm_backup_service.py)
                                        downloaded_gb = downloaded / (1024 * 1024 * 1024)
                                        if downloaded_gb < 1:
                                            # 0-1 GB: progression de 25% à 32%
                                            progress_pct = 25 + int(downloaded_gb * 7)
                                        elif downloaded_gb < 5:
                                            # 1-5 GB: progression de 32% à 40%
                                            progress_pct = 32 + int((downloaded_gb - 1) * 2)
                                        elif downloaded_gb < 10:
                                            # 5-10 GB: progression de 40% à 47%
                                            progress_pct = 40 + int((downloaded_gb - 5) * 1.4)
                                        elif downloaded_gb < 20:
                                            # 10-20 GB: progression de 47% à 52%
                                            progress_pct = 47 + int((downloaded_gb - 10) * 0.5)
                                        elif downloaded_gb < 50:
                                            # 20-50 GB: progression de 52% à 56%
                                            progress_pct = 52 + int((downloaded_gb - 20) * 0.13)
                                        elif downloaded_gb < 100:
                                            # 50-100 GB: progression de 56% à 58%
                                            progress_pct = 56 + int((downloaded_gb - 50) * 0.04)
                                        elif downloaded_gb < 150:
                                            # 100-150 GB: progression de 58% à 59%
                                            progress_pct = 58 + int((downloaded_gb - 100) * 0.02)
                                        else:
                                            # 150+ GB: reste à 59%
                                            progress_pct = 59
                                        progress_pct = min(progress_pct, 60)  # Cap à 60% max

                                # Arrondir à l'entier le plus proche pour affichage incrémental clair
                                progress_pct_int = int(progress_pct)

                                # Callback UI - Afficher à chaque nouveau pourcentage entier (1%, 2%, 3%...)
                                if progress_pct_int > int(last_ui_update):
                                    if progress_callback:
                                        downloaded_mb = downloaded / (1024 * 1024)
                                        file_mb = file_downloaded / (1024 * 1024)
                                        file_size_mb = file_size / (1024 * 1024)
                                        speed_str = f" ({speed_mbps:.1f} MB/s)" if speed_mbps > 0 else ""
                                        if total_size > 0:
                                            total_mb = total_size / (1024 * 1024)
                                            progress_callback(progress_pct_int, 'exporting',
                                                f'Export VMDK: {downloaded_mb:.1f}/{total_mb:.1f} MB ({progress_pct_int}%){speed_str}')
                                        elif file_size > 0:
                                            progress_callback(progress_pct_int, 'exporting',
                                                f'Export {filename}: {file_mb:.1f}/{file_size_mb:.1f} MB ({progress_pct_int}%){speed_str}')
                                        else:
                                            progress_callback(progress_pct_int, 'exporting',
                                                f'Export {filename}: {file_mb:.1f} MB{speed_str}')
                                        last_ui_update = progress_pct_int
                                        chunk_counter = 0

                    # Téléchargement réussi!
                    download_complete = True
                    total_time = time.time() - download_start_time
                    avg_speed = (file_downloaded / 1024 / 1024) / total_time if total_time > 0 else 0
                    logger.info(f"[REPLICATION] [OK] {filename} téléchargé ({file_downloaded / (1024*1024):.1f} MB en {total_time:.1f}s, {avg_speed:.2f} MB/s)")

                except OSError as e:
                    # Gérer spécifiquement les erreurs d'espace disque (Errno 28)
                    if e.errno == 28:  # ENOSPC: No space left on device
                        logger.error(f"[REPLICATION] [ERROR] Espace disque insuffisant lors du téléchargement de {filename}")
                        # Nettoyer le fichier partiel
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                                logger.info(f"[REPLICATION] Fichier partiel supprimé: {local_path}")
                            except Exception as cleanup_err:
                                logger.warning(f"[REPLICATION] Erreur nettoyage fichier partiel: {cleanup_err}")
                        raise Exception(
                            f"[Errno 28] No space left on device\n\n"
                            f"Espace disque insuffisant pour télécharger {filename}. "
                            f"Taille déjà téléchargée: {file_downloaded / (1024*1024):.1f} MB. "
                            f"Libérez de l'espace disque et réessayez."
                        )
                    else:
                        # Autre erreur OSError
                        raise

                except (requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                        ConnectionResetError) as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"[REPLICATION] [ERROR] Échec après {max_retries + 1} tentatives: {e}")
                        # Nettoyer le fichier partiel en cas d'échec final
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                                logger.info(f"[REPLICATION] Fichier partiel supprimé: {local_path}")
                            except Exception as cleanup_err:
                                logger.warning(f"[REPLICATION] Erreur nettoyage fichier partiel: {cleanup_err}")
                        raise Exception(f"Téléchargement échoué après {max_retries + 1} tentatives: {e}")

                    logger.warning(f"[REPLICATION] [WARNING] Erreur ({e}), reprise dans 3s...")
                    time.sleep(3)

        finally:
            # IMPORTANT: Arrêter le thread de keepalive
            keepalive_stop.set()
            keepalive_thread.join(timeout=5)  # Attendre max 5 secondes

        # Retourner file_downloaded au lieu de file_size car file_size peut être 0 si pas de Content-Length
        return (downloaded, last_lease_update, last_ui_update, chunk_counter, file_downloaded)

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

        # VÉRIFICATION CRITIQUE: Détecter les conditions qui empêchent l'export
        # 1. Vérifier si la VM est allumée
        power_state = vm_obj.runtime.powerState
        if power_state == vim.VirtualMachinePowerState.poweredOn:
            error_msg = (
                f"La VM '{vm_name}' est actuellement allumée (powered on). "
                f"Pour garantir la cohérence des données lors de la réplication, "
                f"la VM doit être éteinte. "
                f"Voulez-vous éteindre la VM automatiquement ?"
            )
            logger.error(f"[REPLICATION] {error_msg}")
            raise Exception(error_msg)

        # 2. Vérifier les snapshots
        if vm_obj.snapshot is not None:
            snapshot_count = len(vm_obj.snapshot.rootSnapshotList)
            error_msg = (
                f"La VM '{vm_name}' possède {snapshot_count} snapshot(s). "
                f"L'export OVF nécessite de supprimer tous les snapshots. "
                f"Veuillez supprimer les snapshots depuis l'interface ESXi avant de répliquer."
            )
            logger.error(f"[REPLICATION] {error_msg}")
            raise Exception(error_msg)

        # 3. Vérifier les disques indépendants
        for device in vm_obj.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualDisk):
                backing = device.backing
                if hasattr(backing, 'diskMode'):
                    if 'independent' in backing.diskMode.lower():
                        error_msg = (
                            f"La VM '{vm_name}' possède des disques en mode 'indépendant'. "
                            f"Les disques indépendants ne peuvent pas être exportés en OVF. "
                            f"Veuillez convertir les disques en mode 'dépendant' depuis l'interface ESXi."
                        )
                        logger.error(f"[REPLICATION] {error_msg}")
                        raise Exception(error_msg)

        logger.info(f"[REPLICATION] Vérifications pré-export réussies pour {vm_name}")

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

                # Utiliser la méthode avec retry automatique et reprise
                downloaded, last_lease_update, last_ui_update, chunk_counter, file_size = self._download_vmdk_with_retry(
                    url=url,
                    local_path=local_path,
                    esxi_user=esxi_user,
                    esxi_pass=esxi_pass,
                    device_url=device_url,
                    downloaded=downloaded,
                    file_index=file_index,
                    total_size=total_size,
                    last_lease_update=last_lease_update,
                    last_ui_update=last_ui_update,
                    chunk_counter=chunk_counter,
                    lease=lease,
                    progress_callback=progress_callback,
                    replication_id=replication_id
                )

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
        """Créer un descripteur OVF valide avec contrôleur SCSI et disques"""
        import xml.etree.ElementTree as ET

        # Namespaces
        namespaces = {
            'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
            'rasd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
            'vssd': 'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData',
            'vmw': 'http://www.vmware.com/schema/ovf'
        }

        for prefix, uri in namespaces.items():
            ET.register_namespace(prefix, uri)

        # Créer le root element
        root = ET.Element(f"{{{namespaces['ovf']}}}Envelope",
                         attrib={
                             f"{{{namespaces['ovf']}}}version": "1.0",
                             "xml:lang": "en-US"
                         })

        # References Section
        references = ET.SubElement(root, f"{{{namespaces['ovf']}}}References")
        for vmdk in vmdk_files:
            file_elem = ET.SubElement(references, f"{{{namespaces['ovf']}}}File",
                                     attrib={
                                         f"{{{namespaces['ovf']}}}href": vmdk['filename'],
                                         f"{{{namespaces['ovf']}}}id": f"file-{vmdk['filename']}",
                                         f"{{{namespaces['ovf']}}}size": str(vmdk['size'])
                                     })

        # DiskSection
        disk_section = ET.SubElement(root, f"{{{namespaces['ovf']}}}DiskSection")
        ET.SubElement(disk_section, f"{{{namespaces['ovf']}}}Info").text = "Virtual disk information"

        for i, vmdk in enumerate(vmdk_files):
            # Capacité en bytes - convertir de bytes à bytes (déjà en bytes)
            capacity_bytes = vmdk['size']
            # L'attribut capacity attend des unités d'allocation, utilisons bytes
            disk = ET.SubElement(disk_section, f"{{{namespaces['ovf']}}}Disk",
                                attrib={
                                    f"{{{namespaces['ovf']}}}capacity": str(capacity_bytes),
                                    f"{{{namespaces['ovf']}}}capacityAllocationUnits": "byte",
                                    f"{{{namespaces['ovf']}}}diskId": f"vmdisk{i+1}",
                                    f"{{{namespaces['ovf']}}}fileRef": f"file-{vmdk['filename']}",
                                    f"{{{namespaces['ovf']}}}format": "http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"
                                })

        # NetworkSection
        network_section = ET.SubElement(root, f"{{{namespaces['ovf']}}}NetworkSection")
        ET.SubElement(network_section, f"{{{namespaces['ovf']}}}Info").text = "Logical networks"
        network = ET.SubElement(network_section, f"{{{namespaces['ovf']}}}Network",
                               attrib={f"{{{namespaces['ovf']}}}name": "VM Network"})
        ET.SubElement(network, f"{{{namespaces['ovf']}}}Description").text = "VM Network"

        # VirtualSystem
        vs = ET.SubElement(root, f"{{{namespaces['ovf']}}}VirtualSystem",
                          attrib={f"{{{namespaces['ovf']}}}id": vm_obj.name})

        ET.SubElement(vs, f"{{{namespaces['ovf']}}}Info").text = f"A virtual machine"
        ET.SubElement(vs, f"{{{namespaces['ovf']}}}Name").text = vm_obj.name

        # VirtualHardwareSection
        vhw = ET.SubElement(vs, f"{{{namespaces['ovf']}}}VirtualHardwareSection")
        ET.SubElement(vhw, f"{{{namespaces['ovf']}}}Info").text = "Virtual hardware requirements"

        # System (obligatoire)
        system = ET.SubElement(vhw, f"{{{namespaces['ovf']}}}System")
        ET.SubElement(system, f"{{{namespaces['vssd']}}}ElementName").text = "Virtual Hardware Family"
        ET.SubElement(system, f"{{{namespaces['vssd']}}}InstanceID").text = "0"
        ET.SubElement(system, f"{{{namespaces['vssd']}}}VirtualSystemType").text = "vmx-11"

        # CPU
        item_cpu = ET.SubElement(vhw, f"{{{namespaces['ovf']}}}Item")
        ET.SubElement(item_cpu, f"{{{namespaces['rasd']}}}AllocationUnits").text = "hertz * 10^6"
        ET.SubElement(item_cpu, f"{{{namespaces['rasd']}}}Description").text = "Number of Virtual CPUs"
        ET.SubElement(item_cpu, f"{{{namespaces['rasd']}}}ElementName").text = "1 virtual CPU(s)"
        ET.SubElement(item_cpu, f"{{{namespaces['rasd']}}}InstanceID").text = "1"
        ET.SubElement(item_cpu, f"{{{namespaces['rasd']}}}ResourceType").text = "3"
        ET.SubElement(item_cpu, f"{{{namespaces['rasd']}}}VirtualQuantity").text = "1"

        # Memory
        item_mem = ET.SubElement(vhw, f"{{{namespaces['ovf']}}}Item")
        ET.SubElement(item_mem, f"{{{namespaces['rasd']}}}AllocationUnits").text = "byte * 2^20"
        ET.SubElement(item_mem, f"{{{namespaces['rasd']}}}Description").text = "Memory Size"
        ET.SubElement(item_mem, f"{{{namespaces['rasd']}}}ElementName").text = "2048MB of memory"
        ET.SubElement(item_mem, f"{{{namespaces['rasd']}}}InstanceID").text = "2"
        ET.SubElement(item_mem, f"{{{namespaces['rasd']}}}ResourceType").text = "4"
        ET.SubElement(item_mem, f"{{{namespaces['rasd']}}}VirtualQuantity").text = "2048"

        # Contrôleur SCSI (OBLIGATOIRE pour les disques!)
        item_scsi = ET.SubElement(vhw, f"{{{namespaces['ovf']}}}Item")
        ET.SubElement(item_scsi, f"{{{namespaces['rasd']}}}Address").text = "0"
        ET.SubElement(item_scsi, f"{{{namespaces['rasd']}}}Description").text = "SCSI Controller"
        ET.SubElement(item_scsi, f"{{{namespaces['rasd']}}}ElementName").text = "SCSI Controller 0"
        ET.SubElement(item_scsi, f"{{{namespaces['rasd']}}}InstanceID").text = "3"
        ET.SubElement(item_scsi, f"{{{namespaces['rasd']}}}ResourceSubType").text = "lsilogic"
        ET.SubElement(item_scsi, f"{{{namespaces['rasd']}}}ResourceType").text = "6"

        # Disques (référencent le contrôleur SCSI)
        for i, vmdk in enumerate(vmdk_files):
            item_disk = ET.SubElement(vhw, f"{{{namespaces['ovf']}}}Item")
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}AddressOnParent").text = str(i)
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}Description").text = "Hard disk"
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}ElementName").text = f"Hard Disk {i+1}"
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}HostResource").text = f"ovf:/disk/vmdisk{i+1}"
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}InstanceID").text = str(4 + i)
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}Parent").text = "3"  # Référence au contrôleur SCSI
            ET.SubElement(item_disk, f"{{{namespaces['rasd']}}}ResourceType").text = "17"

        # Network adapter
        item_net = ET.SubElement(vhw, f"{{{namespaces['ovf']}}}Item")
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}AddressOnParent").text = "7"
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}AutomaticAllocation").text = "true"
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}Connection").text = "VM Network"
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}Description").text = "E1000 ethernet adapter"
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}ElementName").text = "Network adapter 1"
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}InstanceID").text = str(4 + len(vmdk_files))
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}ResourceSubType").text = "E1000"
        ET.SubElement(item_net, f"{{{namespaces['rasd']}}}ResourceType").text = "10"

        # Écrire le fichier OVF
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")  # Pretty print
        tree.write(ovf_path, encoding='utf-8', xml_declaration=True)

        logger.info(f"[REPLICATION] Descripteur OVF créé: {ovf_path}")

        # Logger la taille des disques pour debug
        for vmdk in vmdk_files:
            logger.info(f"[REPLICATION] VMDK dans OVF: {vmdk['filename']} - {vmdk['size'] / (1024*1024):.2f} MB")

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

            # Progression graduelle 1-24% (affichage incrémental clair)
            if progress_callback:
                for pct in range(1, 3):
                    progress_callback(pct, 'initializing', f'Initialisation de la réplication... {pct}%')
                    time.sleep(0.1)

            # Vérifier si la VM replica existe déjà (3-8%)
            logger.info(f"[REPLICATION] Connexion au serveur destination: {destination_server.hostname}")
            if progress_callback:
                for pct in range(3, 6):
                    progress_callback(pct, 'connecting', f'Connexion au serveur destination... {pct}%')
                    time.sleep(0.1)

            dest_si = self._connect_to_server(destination_server)

            if progress_callback:
                progress_callback(6, 'checking', 'Vérification de la VM replica existante... 6%')
                progress_callback(7, 'checking', 'Vérification de la VM replica existante... 7%')

            existing_replica = self._get_vm_by_name(dest_si, replica_vm_name)

            if existing_replica:
                logger.info(f"[REPLICATION] VM replica existe déjà: {replica_vm_name}")
                logger.info(f"[REPLICATION] Suppression de l'ancienne replica pour mise à jour...")

                if progress_callback:
                    for pct in range(8, 11):
                        progress_callback(pct, 'cleaning', f'Préparation de la suppression... {pct}%')
                        time.sleep(0.1)

                # Arrêter la VM si elle tourne
                if existing_replica.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                    if progress_callback:
                        progress_callback(11, 'cleaning', 'Arrêt de l\'ancienne VM replica... 11%')
                    power_off_task = existing_replica.PowerOffVM_Task()
                    while power_off_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                        time.sleep(0.1)

                # Supprimer la VM
                if progress_callback:
                    for pct in range(12, 15):
                        progress_callback(pct, 'cleaning', f'Suppression des fichiers de la replica... {pct}%')
                        time.sleep(0.1)
                destroy_task = existing_replica.Destroy_Task()
                while destroy_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    time.sleep(0.1)

                logger.info(f"[REPLICATION] Ancienne replica supprimée")
                if progress_callback:
                    progress_callback(15, 'cleaned', 'Ancienne replica supprimée - 15%')
            else:
                # Pas de replica existante, progression rapide mais visible
                if progress_callback:
                    for pct in range(8, 16):
                        progress_callback(pct, 'checking', f'Aucune replica existante - Préparation... {pct}%')
                        time.sleep(0.1)

            # Créer un répertoire temporaire pour l'export OVF (16-18%)
            if progress_callback:
                for pct in range(16, 19):
                    progress_callback(pct, 'preparing', f'Création du répertoire temporaire... {pct}%')
                    time.sleep(0.1)

            temp_dir = tempfile.mkdtemp(prefix='replication_')
            logger.info(f"[REPLICATION] Répertoire temporaire: {temp_dir}")

            # Se connecter au serveur source pour l'export (19-24%)
            logger.info(f"[REPLICATION] Connexion au serveur source: {source_server.hostname}")
            if progress_callback:
                for pct in range(19, 23):
                    progress_callback(pct, 'connecting', f'Connexion au serveur source... {pct}%')
                    time.sleep(0.1)

            source_si = self._connect_to_server(source_server)

            if progress_callback:
                for pct in range(23, 25):
                    progress_callback(pct, 'connected', f'Serveur source connecté - Préparation... {pct}%')
                    time.sleep(0.1)

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
                for pct in range(60, 63):
                    progress_callback(pct, 'exported', f'Export OVF terminé avec succès - {pct}%')
                    time.sleep(0.1)

            # Déconnexion du serveur source
            Disconnect(source_si)

            # Déployer sur le serveur destination avec le nom "_replica" (63-70%)
            logger.info(f"[REPLICATION] Déploiement sur serveur destination: {destination_server.hostname}")
            if progress_callback:
                for pct in range(63, 66):
                    progress_callback(pct, 'deploying', f'Préparation du déploiement... {pct}%')
                    time.sleep(0.1)

            vmware_service = VMwareService(
                host=destination_server.hostname,
                user=destination_server.username,
                password=destination_server.password,
                port=destination_server.port or 443
            )

            # SE CONNECTER au serveur de destination
            logger.info(f"[REPLICATION] Connexion au serveur de destination {destination_server.hostname}...")
            if progress_callback:
                for pct in range(66, 69):
                    progress_callback(pct, 'deploying', f'Connexion au serveur de destination... {pct}%')
                    time.sleep(0.1)

            if not vmware_service.connect():
                raise Exception(f"Impossible de se connecter au serveur de destination {destination_server.hostname}")
            logger.info(f"[REPLICATION] [OK] Connecté au serveur de destination")

            # Utiliser le datastore configuré dans la réplication (69-73%)
            if progress_callback:
                for pct in range(69, 73):
                    progress_callback(pct, 'deploying', f'Vérification du datastore de destination... {pct}%')
                    time.sleep(0.1)

            dest_datastore = replication.destination_datastore
            logger.info(f"[REPLICATION] Datastore de destination configuré: {dest_datastore}")

            # Vérifier que le datastore existe sur le serveur de destination
            logger.info(f"[REPLICATION] Vérification du datastore sur {destination_server.hostname}...")
            try:
                datastores_info = vmware_service.get_datastores()
                logger.info(f"[REPLICATION] Datastores disponibles: {[ds['name'] for ds in datastores_info]}")

                # Vérifier que le datastore configuré existe
                datastore_found = False
                for ds in datastores_info:
                    if ds['name'] == dest_datastore:
                        datastore_found = True
                        logger.info(f"[REPLICATION] ✓ Datastore {dest_datastore} trouvé (capacité: {ds['capacity_gb']} GB, libre: {ds['free_space_gb']} GB)")
                        break

                if not datastore_found:
                    raise Exception(f"Le datastore '{dest_datastore}' n'existe pas sur le serveur {destination_server.hostname}. Datastores disponibles: {[ds['name'] for ds in datastores_info]}")

            except Exception as ds_err:
                logger.error(f"[REPLICATION] Erreur lors de la vérification du datastore: {ds_err}", exc_info=True)
                raise Exception(f"Erreur vérification datastore: {ds_err}")

            # Déployer l'OVF (73% → 90%)
            if progress_callback:
                for pct in range(73, 76):
                    progress_callback(pct, 'deploying', f'Début du déploiement de l\'OVF... {pct}%')
                    time.sleep(0.1)

            # Créer un callback wrapper pour mapper 0-100% du déploiement vers 76-90% de la progression totale
            def deploy_progress_callback(deploy_pct, status='deploying', message='Déploiement en cours...'):
                if progress_callback:
                    # Mapper 0-100% du déploiement vers 76-90% de la progression totale
                    total_pct = int(76 + (14 * deploy_pct / 100))
                    progress_callback(total_pct, status, f'{message} - {total_pct}%')

            logger.info(f"[REPLICATION] Déploiement OVF avec support d'annulation (replication_id={replication_id})")

            deploy_success = vmware_service.deploy_ovf(
                ovf_path=ovf_path,
                vm_name=replica_vm_name,
                datastore_name=dest_datastore,
                network_name='VM Network',
                power_on=False,  # Ne pas démarrer la replica automatiquement
                progress_callback=deploy_progress_callback,
                restore_id=replication_id,  # Utiliser replication_id pour vérifier les annulations
                disk_provisioning='thin'  # Forcer thin provisioning pour économiser l'espace
            )

            if not deploy_success:
                raise Exception("Échec du déploiement OVF sur le serveur destination")

            logger.info(f"[REPLICATION] VM replica déployée: {replica_vm_name}")

            if progress_callback:
                for pct in range(90, 93):
                    progress_callback(pct, 'deployed', f'VM replica {replica_vm_name} déployée - {pct}%')
                    time.sleep(0.1)

            # Nettoyer le répertoire temporaire (93-96%)
            if progress_callback:
                for pct in range(93, 96):
                    progress_callback(pct, 'cleaning', f'Suppression des fichiers temporaires... {pct}%')
                    time.sleep(0.1)

            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"[REPLICATION] Répertoire temporaire nettoyé")

            if progress_callback:
                progress_callback(96, 'cleaned', 'Nettoyage terminé - 96%')
                progress_callback(97, 'updating', 'Mise à jour des métadonnées... 97%')

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            replication.last_replication_at = end_time
            replication.last_replication_duration_seconds = int(duration)
            replication.status = 'active'
            replication.save()

            logger.info(f"[REPLICATION] Terminée: {replication.name} ({duration:.2f}s)")

            if progress_callback:
                progress_callback(98, 'saving', 'Enregistrement de l\'état de réplication... 98%')
                time.sleep(0.1)
                progress_callback(99, 'disconnecting', 'Déconnexion des serveurs... 99%')

            # Déconnexion
            Disconnect(dest_si)

            if progress_callback:
                time.sleep(0.2)
                progress_callback(100, 'completed', f'[OK] Réplication terminée avec succès en {duration:.1f}s - 100%')

            # Déconnecter le service VMware de destination
            try:
                vmware_service.disconnect()
                logger.info(f"[REPLICATION] Déconnecté du serveur de destination")
            except:
                pass

            return {
                'success': True,
                'duration_seconds': duration,
                'message': f"Réplication de {vm_name} terminée avec succès. VM replica: {replica_vm_name}"
            }

        except Exception as e:
            logger.error(f"[REPLICATION] Erreur: {replication.name}: {e}")

            # Détecter l'erreur d'espace disque insuffisant
            error_message = str(e)
            if '[Errno 28]' in error_message or 'No space left on device' in error_message:
                # Message d'erreur clair et actionnable pour l'utilisateur
                user_message = (
                    "❌ Espace disque insuffisant\n\n"
                    "Le disque contenant les fichiers temporaires est plein. "
                    "La réplication nécessite de l'espace disque temporaire pour exporter la VM.\n\n"
                    "💡 Solutions possibles :\n"
                    "• Libérer de l'espace disque sur le serveur (supprimer fichiers inutiles, vider /tmp)\n"
                    "• Nettoyer les anciennes sauvegardes et exports OVF\n"
                    "• Vérifier l'espace disponible avec : df -h /tmp\n"
                    "• Configurer un répertoire temporaire sur un disque avec plus d'espace"
                )
                detailed_error = (
                    f"Espace disque insuffisant pour créer les fichiers temporaires de réplication. "
                    f"Répertoire temporaire : {temp_dir if temp_dir else '/tmp'}. "
                    f"Libérez de l'espace disque et réessayez."
                )
            else:
                user_message = f"Erreur: {error_message}"
                detailed_error = error_message

            if progress_callback:
                progress_callback(-1, 'error', user_message)

            # Déconnecter le service VMware de destination si créé
            try:
                if 'vmware_service' in locals():
                    vmware_service.disconnect()
                    logger.info(f"[REPLICATION] Déconnecté du serveur de destination (erreur)")
            except:
                pass

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
                'error': detailed_error,
                'message': user_message
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

            # Activer le flag failover_active sur la réplication
            replication.failover_active = True
            replication.save()
            logger.info(f"Failover actif marqué pour réplication {replication.id}")

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

    def execute_failback(self, replication, triggered_by=None):
        """
        Exécuter un failback (retour à la normale)
        Arrête la VM slave (destination) et rallume la VM master (source)

        Args:
            replication: Instance VMReplication
            triggered_by: User ayant déclenché le failback (None si automatique)

        Returns:
            dict: Résultat du failback
        """
        try:
            logger.info(f"[FAILBACK] === DÉBUT FAILBACK pour réplication {replication.id} ===")

            if not replication.failover_active:
                logger.warning(f"[FAILBACK] Aucun failover actif pour {replication.name}")
                return {
                    'success': False,
                    'error': 'Aucun failover actif',
                    'message': 'Aucun failover actif pour cette réplication'
                }

            source_server = replication.get_source_server
            destination_server = replication.destination_server
            vm_name = replication.virtual_machine.name
            replica_vm_name = f"{vm_name}_replica"

            # Se connecter aux serveurs
            logger.info(f"[FAILBACK] Connexion au serveur source: {source_server.hostname}")
            source_si = self._connect_to_server(source_server)

            logger.info(f"[FAILBACK] Connexion au serveur destination: {destination_server.hostname}")
            dest_si = self._connect_to_server(destination_server)

            # Récupérer les VMs
            source_vm = self._get_vm_by_name(source_si, vm_name)
            dest_vm = self._get_vm_by_name(dest_si, replica_vm_name)

            if not dest_vm:
                # Si la VM de destination n'existe pas avec _replica, chercher avec le nom normal
                dest_vm = self._get_vm_by_name(dest_si, vm_name)

            if not source_vm:
                logger.error(f"[FAILBACK] VM source non trouvée: {vm_name}")
                Disconnect(source_si)
                Disconnect(dest_si)
                return {
                    'success': False,
                    'error': 'VM source non trouvée',
                    'message': f'VM source {vm_name} non trouvée sur {source_server.hostname}'
                }

            # Arrêter la VM slave (destination)
            if dest_vm and dest_vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                logger.info(f"[FAILBACK] Arrêt de la VM slave: {replica_vm_name}")
                power_off_task = dest_vm.PowerOffVM_Task()

                # Attendre la fin de l'arrêt
                while power_off_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    pass

                if power_off_task.info.state == vim.TaskInfo.State.error:
                    raise Exception(f"Erreur arrêt VM slave: {power_off_task.info.error}")

                logger.info(f"[FAILBACK] VM slave arrêtée: {replica_vm_name}")
            else:
                logger.info(f"[FAILBACK] VM slave déjà arrêtée ou inexistante")

            # Redémarrer la VM master (source)
            if source_vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:
                logger.info(f"[FAILBACK] Démarrage de la VM master: {vm_name}")
                power_on_task = source_vm.PowerOnVM_Task()

                # Attendre le démarrage
                while power_on_task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    pass

                if power_on_task.info.state == vim.TaskInfo.State.error:
                    raise Exception(f"Erreur démarrage VM master: {power_on_task.info.error}")

                logger.info(f"[FAILBACK] VM master démarrée: {vm_name}")
            else:
                logger.info(f"[FAILBACK] VM master déjà démarrée: {vm_name}")

            # Désactiver le flag failover_active
            replication.failover_active = False
            replication.save()
            logger.info(f"[FAILBACK] Failover désactivé pour réplication {replication.id}")

            # Déconnexion
            Disconnect(source_si)
            Disconnect(dest_si)

            logger.info(f"[FAILBACK] === FAILBACK TERMINÉ AVEC SUCCÈS ===")

            return {
                'success': True,
                'message': f"Failback de {vm_name} terminé avec succès. VM master rallumée, VM slave arrêtée.",
                'master_powered_on': True,
                'slave_powered_off': True
            }

        except Exception as e:
            logger.error(f"[FAILBACK] ✗ Erreur lors du failback: {e}", exc_info=True)

            return {
                'success': False,
                'error': str(e),
                'message': f"Erreur lors du failback: {e}"
            }

    def check_and_trigger_auto_failback(self, replication):
        """
        Vérifier si un failback automatique doit être déclenché
        (quand master revient en ligne après un failover)

        Args:
            replication: Instance VMReplication

        Returns:
            dict: Résultat de la vérification
        """
        # Vérifier que le failback automatique est activé
        if not replication.failback_enabled:
            return {'should_failback': False, 'reason': 'Failback automatique désactivé'}

        # Vérifier qu'un failover est actuellement actif
        if not replication.failover_active:
            return {'should_failback': False, 'reason': 'Aucun failover actif'}

        # Vérifier que la VM master est revenue en ligne
        source_server = replication.get_source_server

        try:
            # Tenter de se connecter au serveur source
            si = self._connect_to_server(source_server)

            # Vérifier la VM
            vm = self._get_vm_by_name(si, replication.virtual_machine.name)

            if not vm:
                Disconnect(si)
                return {'should_failback': False, 'reason': 'VM master non trouvée'}

            # Vérifier l'état de la VM
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                # VM master revenue en ligne !
                Disconnect(si)
                return {
                    'should_failback': True,
                    'reason': f'VM master {replication.virtual_machine.name} revenue en ligne'
                }

            Disconnect(si)
            return {'should_failback': False, 'reason': 'VM master toujours éteinte'}

        except Exception as e:
            logger.error(f"[FAILBACK-CHECK] Erreur vérification auto-failback pour {replication.name}: {e}")
            return {'should_failback': False, 'reason': f'Serveur source inaccessible: {e}'}

    def delete_replicated_vm(self, replication):
        """
        Supprimer la VM répliquée du serveur de destination

        Args:
            replication: Instance VMReplication

        Returns:
            dict: Résultat de la suppression avec 'success' (bool) et 'message' (str)
        """
        try:
            logger.info(f"[REPLICATION DELETE] Début de la suppression de la VM répliquée: {replication.virtual_machine.name}")

            # Connexion au serveur de destination
            dest_server = replication.destination_server
            logger.info(f"[REPLICATION DELETE] Connexion au serveur de destination: {dest_server.hostname}")

            si = self._connect_to_server(dest_server)

            # Trouver la VM répliquée sur le serveur de destination
            # La VM répliquée a le suffixe "_replica"
            vm_name = replication.virtual_machine.name
            replica_vm_name = f"{vm_name}_replica"
            logger.info(f"[REPLICATION DELETE] Recherche de la VM replica: {replica_vm_name}")

            vm = self._get_vm_by_name(si, replica_vm_name)

            if not vm:
                logger.warning(f"[REPLICATION DELETE] VM replica {replica_vm_name} non trouvée sur le serveur de destination")
                Disconnect(si)
                return {
                    'success': True,
                    'message': f'VM replica {replica_vm_name} non trouvée sur le serveur de destination (peut-être déjà supprimée)'
                }

            # Vérifier l'état de la VM
            power_state = vm.runtime.powerState
            logger.info(f"[REPLICATION DELETE] État de la VM: {power_state}")

            # Si la VM est allumée, l'éteindre d'abord
            if power_state == vim.VirtualMachinePowerState.poweredOn:
                logger.info(f"[REPLICATION DELETE] Extinction de la VM replica {replica_vm_name}...")
                try:
                    task = vm.PowerOffVM_Task()
                    # Attendre que la tâche se termine (timeout 60s)
                    import time
                    timeout = 60
                    elapsed = 0
                    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                        time.sleep(1)
                        elapsed += 1
                        if elapsed >= timeout:
                            logger.warning(f"[REPLICATION DELETE] Timeout lors de l'extinction de la VM replica")
                            break

                    if task.info.state == vim.TaskInfo.State.error:
                        logger.error(f"[REPLICATION DELETE] Erreur lors de l'extinction: {task.info.error}")
                    else:
                        logger.info(f"[REPLICATION DELETE] VM replica éteinte avec succès")
                except Exception as e:
                    logger.warning(f"[REPLICATION DELETE] Erreur lors de l'extinction (la VM sera supprimée quand même): {e}")

            # Supprimer la VM
            logger.info(f"[REPLICATION DELETE] Suppression de la VM replica {replica_vm_name}...")
            try:
                task = vm.Destroy_Task()
                # Attendre que la tâche se termine (timeout 120s)
                import time
                timeout = 120
                elapsed = 0
                while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                    time.sleep(1)
                    elapsed += 1
                    if elapsed >= timeout:
                        logger.error(f"[REPLICATION DELETE] Timeout lors de la suppression de la VM replica")
                        Disconnect(si)
                        return {
                            'success': False,
                            'message': f'Timeout lors de la suppression de la VM replica {replica_vm_name}'
                        }

                if task.info.state == vim.TaskInfo.State.error:
                    error_msg = str(task.info.error.msg) if task.info.error else 'Erreur inconnue'
                    logger.error(f"[REPLICATION DELETE] Erreur lors de la suppression: {error_msg}")
                    Disconnect(si)
                    return {
                        'success': False,
                        'message': f'Erreur lors de la suppression de la VM replica {replica_vm_name}: {error_msg}'
                    }

                logger.info(f"[REPLICATION DELETE] VM replica {replica_vm_name} supprimée avec succès du serveur {dest_server.hostname}")
                Disconnect(si)
                return {
                    'success': True,
                    'message': f'VM replica {replica_vm_name} supprimée avec succès du serveur de destination'
                }

            except Exception as e:
                logger.error(f"[REPLICATION DELETE] Exception lors de la suppression de la VM: {e}", exc_info=True)
                Disconnect(si)
                return {
                    'success': False,
                    'message': f'Exception lors de la suppression de la VM replica {replica_vm_name}: {str(e)}'
                }

        except Exception as e:
            logger.error(f"[REPLICATION DELETE] Erreur lors de la connexion ou recherche de la VM: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Erreur lors de la suppression: {str(e)}'
            }
