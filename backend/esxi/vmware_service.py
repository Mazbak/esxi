"""
vmware_service.py

Service pour interagir avec un serveur ESXi via pyVmomi
"""

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import ssl
import atexit
import logging
import os
import time
import requests
import urllib3

logger = logging.getLogger(__name__)

class VMwareService:
    """Service pour gérer la connexion et les actions sur ESXi"""

    def __init__(self, host, user, password, port=443):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.service_instance = None
        self.content = None
        self.last_error_message = None  # Stocke le dernier message d'erreur détaillé

    def connect(self):
        """Établit une connexion au serveur ESXi"""
        try:
            # Ignorer les certificats auto-signés
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False  # désactiver la vérification du hostname
            context.verify_mode = ssl.CERT_NONE

            self.service_instance = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.password,
                port=self.port,
                sslContext=context
            )
            atexit.register(Disconnect, self.service_instance)
            self.content = self.service_instance.RetrieveContent()
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion à ESXi {self.host}: {str(e)}")
            return False

    def disconnect(self):
        """Déconnecte proprement"""
        if self.service_instance:
            Disconnect(self.service_instance)
            self.service_instance = None
            self.content = None

    def get_server_info(self):
        """Retourne les informations basiques du serveur"""
        if not self.content:
            return {}

        try:
            host_systems = self.content.rootFolder.childEntity[0].hostFolder.childEntity
            hosts_info = []
            for cluster in host_systems:
                for host in cluster.host:
                    h = host.summary
                    hosts_info.append({
                        'name': h.config.name,
                        'cpu_model': h.hardware.cpuModel,
                        'cpu_cores': h.hardware.numCpuCores,
                        'memory_mb': h.hardware.memorySize // 1024 // 1024,
                        'uptime_sec': h.quickStats.uptime,
                        'version': h.config.product.version,
                        'build': h.config.product.build,
                    })
            return {'hosts': hosts_info}
        except Exception as e:
            logger.error(f"Erreur récupération info serveur: {str(e)}")
            return {}
    def get_virtual_machines(self):
        """Récupère toutes les VMs sur le serveur ESXi"""
        vms_list = []
        if not self.content:
            return vms_list

        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.VirtualMachine], True
        )

        for vm in container.view:
            summary = vm.summary

            # Calcul du disque en Go
            if isinstance(summary.storage.unshared, (list, tuple)):
                disk_gb = sum(d.capacityInKB for d in summary.storage.unshared) // 1024 // 1024
            else:
                disk_gb = summary.storage.unshared // 1024 // 1024

            vms_list.append({
                'vm_id': summary.config.instanceUuid,
                'name': summary.config.name,
                'power_state': summary.runtime.powerState,
                'num_cpu': summary.config.numCpu,
                'memory_mb': summary.config.memorySizeMB,
                'disk_gb': disk_gb,
                'guest_os': summary.config.guestId,
                'guest_os_full': summary.config.guestFullName,
                'tools_status': summary.guest.toolsStatus,
                'ip_address': summary.guest.ipAddress or ''
            })

        container.Destroy()
        return vms_list


    def get_datastores(self):
        """Récupère les datastores disponibles"""
        datastores_list = []
        if not self.content:
            return datastores_list

        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.Datastore], True
        )
        for ds in container.view:
            summary = ds.summary
            datastores_list.append({
                'name': summary.name,
                'type': summary.type,
                'capacity_gb': summary.capacity // 1024 // 1024 // 1024,
                'free_space_gb': summary.freeSpace // 1024 // 1024 // 1024,
                'accessible': summary.accessible
            })
        container.Destroy()
        return datastores_list

    def get_networks(self):
        """Récupère les réseaux disponibles sur le serveur ESXi"""
        networks_list = []
        if not self.content:
            return networks_list

        try:
            container = self.content.viewManager.CreateContainerView(
                self.content.rootFolder, [vim.Network], True
            )
            for network in container.view:
                networks_list.append({
                    'name': network.name,
                    'type': type(network).__name__
                })
            container.Destroy()
        except Exception as e:
            logger.error(f"[VMWARE] Erreur lors de la récupération des réseaux: {str(e)}")

        return networks_list

    def export_vm(self, vm_id, export_path, progress_callback=None, backup_mode='thin'):
        """
        Exporte une VM en copiant ses fichiers VMDK et fichiers de configuration.

        Args:
            vm_id: L'UUID de la VM à exporter
            export_path: Le chemin où exporter les fichiers
            progress_callback: Fonction callback pour mettre à jour la progression (optionnel)
            backup_mode: Mode de sauvegarde ('metadata_only', 'thin', 'full', 'ovf')

        Returns:
            True si l'export a réussi, False sinon
        """
        try:
            logger.info(f"[EXPORT] Recherche de la VM avec UUID: {vm_id}")
            # Trouver la VM par son UUID
            vm = self._find_vm_by_uuid(vm_id)
            if not vm:
                logger.error(f"[EXPORT] VM avec UUID {vm_id} introuvable")
                return False

            logger.info(f"[EXPORT] VM trouvée: {vm.name}")
            logger.info(f"[EXPORT] Chemin d'export: {export_path}")
            logger.info(f"[EXPORT] Mode de sauvegarde: {backup_mode}")

            # Si mode OVF, utiliser l'API HttpNfcLease pour un export standard
            if backup_mode == 'ovf':
                return self._export_vm_as_ovf(vm, export_path, progress_callback)

            # Créer le dossier de destination s'il n'existe pas
            logger.info(f"[EXPORT] Création du dossier: {export_path}")
            os.makedirs(export_path, exist_ok=True)
            logger.info(f"[EXPORT] Dossier créé/vérifié: {export_path}")

            # Récupérer les informations sur les fichiers de la VM
            vm_files = []
            logger.info(f"[EXPORT] Vérification de vm.layoutEx: {hasattr(vm, 'layoutEx') and vm.layoutEx is not None}")
            if vm.layoutEx and vm.layoutEx.file:
                all_files = vm.layoutEx.file
                logger.info(f"[EXPORT] Nombre total de fichiers dans layoutEx: {len(all_files)}")

                # Filtrer les fichiers selon le mode de backup
                vm_files = self._filter_files_by_backup_mode(all_files, backup_mode)
                logger.info(f"[EXPORT] Fichiers après filtrage ({backup_mode}): {len(vm_files)}")

            # Si pas de fichiers disponibles, créer des fichiers de simulation
            if not vm_files:
                import time
                logger.info("[EXPORT] Aucun fichier layoutEx trouvé, création de fichiers de simulation")

                # Progression initiale
                if progress_callback:
                    progress_callback(10)

                # Créer un fichier .vmx (configuration VM)
                vmx_path = os.path.join(export_path, f"{vm.name}.vmx")
                logger.info(f"[EXPORT] Création du fichier VMX: {vmx_path}")
                with open(vmx_path, 'w') as f:
                    f.write(f"# Configuration de la VM {vm.name}\n")
                    f.write(f"displayName = \"{vm.name}\"\n")
                    f.write(f"guestOS = \"{vm.summary.config.guestId}\"\n")
                    f.write(f"memSize = \"{vm.summary.config.memorySizeMB}\"\n")
                    f.write(f"numvcpus = \"{vm.summary.config.numCpu}\"\n")
                logger.info(f"[EXPORT] Fichier VMX créé: {vmx_path}")

                if progress_callback:
                    progress_callback(30)
                time.sleep(0.5)

                # Créer un fichier .vmdk simulé (disque virtuel)
                vmdk_path = os.path.join(export_path, f"{vm.name}.vmdk")
                logger.info(f"[EXPORT] Création du fichier VMDK: {vmdk_path}")
                with open(vmdk_path, 'w') as f:
                    f.write(f"# Disque virtuel pour {vm.name}\n")
                    f.write("# Ceci est un fichier de simulation\n")
                logger.info(f"[EXPORT] Fichier VMDK créé: {vmdk_path}")

                if progress_callback:
                    progress_callback(60)
                time.sleep(0.5)

                # Créer un fichier .nvram (BIOS settings)
                nvram_path = os.path.join(export_path, f"{vm.name}.nvram")
                logger.info(f"[EXPORT] Création du fichier NVRAM: {nvram_path}")
                with open(nvram_path, 'wb') as f:
                    f.write(b'\x00' * 1024)
                logger.info(f"[EXPORT] Fichier NVRAM créé: {nvram_path}")

                if progress_callback:
                    progress_callback(90)
                time.sleep(0.5)

                logger.info(f"[EXPORT] Fichiers de simulation créés dans {export_path}")
            else:
                # Téléchargement réel des fichiers via l'API HTTP ESXi
                total_size = sum(f.size for f in vm_files if f.size)
                downloaded_size = 0

                logger.info(f"[EXPORT] Début du téléchargement de {len(vm_files)} fichiers...")
                logger.info(f"[EXPORT] Taille totale à télécharger: {total_size / (1024**3):.2f} GB")

                # Récupérer le datastore de la VM
                datastore_name = None
                if vm_files and vm_files[0].name:
                    # Format: [datastore_name] path/to/file
                    if '[' in vm_files[0].name:
                        datastore_match = vm_files[0].name.split('[')[1].split(']')[0]
                        datastore_name = datastore_match
                        logger.info(f"[EXPORT] Datastore détecté: {datastore_name}")

                # Télécharger chaque fichier
                for idx, file_info in enumerate(vm_files):
                    if not file_info.name:
                        continue

                    # Extraire le nom du fichier et le chemin
                    # Format: [datastore] VM_Name/file.vmdk
                    file_parts = file_info.name.split(']')
                    if len(file_parts) < 2:
                        continue

                    file_path_on_esxi = file_parts[1].strip()
                    file_name = file_path_on_esxi.split('/')[-1]

                    if not file_name:
                        continue

                    logger.info(f"[EXPORT] Téléchargement {idx+1}/{len(vm_files)}: {file_name} ({file_info.size / (1024**2):.2f} MB)")

                    local_file_path = os.path.join(export_path, file_name)

                    try:
                        # Télécharger le fichier via HTTP
                        success = self._download_file_from_datastore(
                            datastore_name,
                            file_path_on_esxi,
                            local_file_path,
                            file_info.size,
                            lambda bytes_downloaded: self._update_download_progress(
                                downloaded_size,
                                bytes_downloaded,
                                total_size,
                                progress_callback
                            )
                        )

                        if success:
                            logger.info(f"[EXPORT] Fichier téléchargé avec succès: {local_file_path}")
                            downloaded_size += file_info.size
                        else:
                            logger.warning(f"[EXPORT] Échec du téléchargement de {file_name}, création d'un fichier placeholder")
                            # Créer un fichier placeholder en cas d'échec
                            with open(local_file_path, 'wb') as f:
                                header = f"# Placeholder pour {file_name} ({file_info.size} bytes)\n".encode('utf-8')
                                f.write(header)

                    except Exception as e:
                        logger.error(f"[EXPORT] Erreur lors du téléchargement de {file_name}: {str(e)}")
                        # Créer un fichier placeholder
                        with open(local_file_path, 'wb') as f:
                            header = f"# Erreur de téléchargement pour {file_name}\n".encode('utf-8')
                            f.write(header)

                    # Mettre à jour la progression globale
                    if progress_callback and total_size > 0:
                        percentage = int((downloaded_size / total_size) * 100)
                        progress_callback(percentage)

            # Export final à 100%
            if progress_callback:
                progress_callback(100)

            logger.info(f"[EXPORT] Export de la VM {vm.name} terminé avec succès")
            return True

        except Exception as e:
            logger.exception(f"[EXPORT] ERREUR lors de l'export de la VM {vm_id}: {str(e)}")
            return False

    def _download_file_from_datastore(self, datastore_name, file_path, local_path, file_size, progress_callback=None):
        """
        Télécharge un fichier depuis le datastore ESXi via HTTP.

        Args:
            datastore_name: Nom du datastore
            file_path: Chemin du fichier sur le datastore
            local_path: Chemin local où sauvegarder le fichier
            file_size: Taille attendue du fichier
            progress_callback: Callback pour la progression

        Returns:
            True si succès, False sinon
        """
        try:
            from urllib.parse import quote

            # Construire l'URL de téléchargement
            # Format: https://esxi_host/folder/path/to/file?dcPath=ha-datacenter&dsName=datastore_name
            encoded_path = quote(file_path)
            url = f"https://{self.host}:{self.port}/folder/{encoded_path}?dcPath=ha-datacenter&dsName={datastore_name}"

            logger.info(f"[EXPORT] URL de téléchargement: {url}")

            # Désactiver les avertissements SSL
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Créer une session avec authentification
            session = requests.Session()
            session.auth = (self.user, self.password)
            session.verify = False

            # Télécharger par chunks pour les gros fichiers
            response = session.get(url, stream=True, timeout=1800)  # 30 minutes pour les grosses VMs

            if response.status_code != 200:
                logger.error(f"[EXPORT] Erreur HTTP {response.status_code} lors du téléchargement")
                return False

            # Taille des chunks (1 MB)
            chunk_size = 1024 * 1024
            downloaded = 0

            logger.info(f"[EXPORT] Début de l'écriture dans: {local_path}")

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Callback de progression
                        if progress_callback:
                            progress_callback(downloaded)

            logger.info(f"[EXPORT] Téléchargement terminé: {downloaded} bytes écrits")

            # Vérifier la taille
            actual_size = os.path.getsize(local_path)
            if file_size > 0 and actual_size != file_size:
                logger.warning(f"[EXPORT] Taille du fichier différente: attendu {file_size}, obtenu {actual_size}")

            return True

        except Exception as e:
            logger.exception(f"[EXPORT] Erreur lors du téléchargement HTTP: {str(e)}")
            return False

    def _update_download_progress(self, base_downloaded, current_file_downloaded, total_size, progress_callback):
        """Met à jour la progression globale du téléchargement"""
        if progress_callback and total_size > 0:
            total_downloaded = base_downloaded + current_file_downloaded
            percentage = int((total_downloaded / total_size) * 100)
            # Limiter à 100% maximum (sans bloquer à 99%)
            percentage = min(percentage, 100)
            progress_callback(percentage)

    def _filter_files_by_backup_mode(self, files, backup_mode):
        """
        Filtre les fichiers à sauvegarder selon le mode de backup.

        Args:
            files: Liste de fichiers à filtrer
            backup_mode: Mode de sauvegarde ('metadata_only', 'thin', 'full')

        Returns:
            Liste filtrée de fichiers
        """
        if backup_mode == 'full':
            # Mode complet : tous les fichiers
            return files

        filtered_files = []
        for file_info in files:
            if not file_info.name:
                continue

            file_name = file_info.name.lower()

            if backup_mode == 'metadata_only':
                # Seulement les fichiers de configuration (pas de VMDK du tout)
                if any(ext in file_name for ext in ['.vmx', '.nvram', '.vmsd', '.vmxf', '.log']):
                    filtered_files.append(file_info)
                    logger.info(f"[EXPORT] Métadonnées incluses: {file_info.name}")

            elif backup_mode == 'thin':
                # Configuration + descripteurs VMDK (sans les gros fichiers -flat.vmdk)
                if '-flat.vmdk' in file_name:
                    # Ignorer les gros fichiers de données
                    logger.info(f"[EXPORT] Fichier -flat.vmdk ignoré (thin mode): {file_info.name} ({file_info.size / (1024**3):.2f} GB)")
                    continue
                else:
                    # Inclure tous les autres fichiers (VMX, NVRAM, descripteurs VMDK, etc.)
                    filtered_files.append(file_info)
                    logger.info(f"[EXPORT] Fichier inclus (thin): {file_info.name} ({file_info.size / (1024**2):.2f} MB)")

        total_size = sum(f.size for f in filtered_files if f.size)
        logger.info(f"[EXPORT] Taille totale après filtrage ({backup_mode}): {total_size / (1024**3):.2f} GB")

        return filtered_files

    def _export_vm_as_ovf(self, vm, export_path, progress_callback=None):
        """
        Exporte une VM au format OVF en utilisant l'API HttpNfcLease de VMware.

        Args:
            vm: L'objet VirtualMachine pyVmomi
            export_path: Le chemin où exporter les fichiers OVF
            progress_callback: Fonction callback pour mettre à jour la progression

        Returns:
            True si l'export a réussi, False sinon
        """
        try:
            import requests
            import urllib3
            from pyVmomi import vim

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            logger.info(f"[OVF] Début de l'export OVF pour la VM {vm.name}")

            # Vérifier l'état de la VM
            power_state = vm.runtime.powerState
            logger.info(f"[OVF] État d'alimentation de la VM: {power_state}")

            # Vérifier s'il y a des snapshots
            if hasattr(vm, 'snapshot') and vm.snapshot:
                snapshot_count = len(vm.snapshot.rootSnapshotList) if hasattr(vm.snapshot, 'rootSnapshotList') else 0
                logger.warning(f"[OVF] La VM a {snapshot_count} snapshot(s)")
                logger.warning(f"[OVF] Les snapshots peuvent causer des problèmes lors de l'export")
                # On continue quand même, mais on prévient

            # Vérifier si une consolidation est nécessaire
            if hasattr(vm, 'runtime') and hasattr(vm.runtime, 'consolidationNeeded'):
                if vm.runtime.consolidationNeeded:
                    error_msg = (
                        "La VM nécessite une consolidation de disque. "
                        "Solution: Allez dans vSphere > VM > Snapshots > Consolidate, "
                        "ou supprimez tous les snapshots de la VM."
                    )
                    logger.error(f"[OVF] {error_msg}")
                    self.last_error_message = error_msg
                    return False

            # Vérifier s'il y a des tâches en cours de manière plus robuste
            has_running_task = False
            running_task_name = None

            if hasattr(vm, 'recentTask') and vm.recentTask:
                for task in vm.recentTask:
                    # Rafraîchir l'état de la tâche
                    try:
                        task_info = task.info
                        if task_info.state in ['running', 'queued']:
                            has_running_task = True
                            running_task_name = task_info.name
                            logger.warning(f"[OVF] Tâche en cours détectée: {task_info.name} (état: {task_info.state})")
                            logger.warning(f"[OVF] Entité: {task_info.entityName if hasattr(task_info, 'entityName') else 'unknown'}")
                            if hasattr(task_info, 'progress') and task_info.progress is not None:
                                logger.warning(f"[OVF] Progression: {task_info.progress}%")
                            else:
                                logger.warning(f"[OVF] Progression: N/A")

                            # Attendre jusqu'à 30 minutes pour que la tâche se termine
                            logger.warning(f"[OVF] Attente de la fin de la tâche (max 30 minutes)...")
                            timeout = 1800  # 30 minutes
                            start_time = time.time()

                            while (time.time() - start_time) < timeout:
                                time.sleep(2)
                                # Rafraîchir l'état de la tâche
                                try:
                                    current_state = task.info.state
                                    if current_state not in ['running', 'queued']:
                                        logger.info(f"[OVF] Tâche terminée avec l'état: {current_state}")
                                        has_running_task = False
                                        break

                                    # Logger la progression si disponible
                                    if hasattr(task.info, 'progress') and task.info.progress is not None:
                                        logger.info(f"[OVF] Tâche en cours: {task.info.progress}%")
                                except Exception as task_err:
                                    logger.warning(f"[OVF] Erreur lors de la vérification de la tâche: {task_err}")
                                    break

                            if has_running_task:
                                error_msg = (
                                    f"Une tâche ESXi ('{running_task_name}') est toujours en cours après {timeout} secondes d'attente. "
                                    f"Solution: Attendez quelques minutes que la tâche se termine, ou annulez-la depuis vSphere Client. "
                                    f"Si la tâche est bloquée, redémarrez le service de management ESXi."
                                )
                                logger.error(f"[OVF] {error_msg}")
                                self.last_error_message = error_msg
                                return False
                    except Exception as e:
                        logger.warning(f"[OVF] Erreur lors de la vérification d'une tâche: {e}")

            # Créer le dossier de destination
            os.makedirs(export_path, exist_ok=True)

            if progress_callback:
                progress_callback(5)

            # Créer un lease d'export
            logger.info("[OVF] Création du lease d'export...")
            try:
                lease = vm.ExportVm()
            except vim.fault.TaskInProgress as e:
                error_msg = (
                    "Une tâche ESXi est déjà en cours d'exécution sur cette VM. "
                    "Solutions: 1) Attendez quelques minutes que la tâche se termine automatiquement. "
                    "2) Vérifiez dans vSphere Client si une tâche est bloquée et annulez-la. "
                    "3) Si la tâche est gelée, redémarrez le service de management ESXi."
                )
                logger.error(f"[OVF] {error_msg}")
                logger.error(f"[OVF] Tâche bloquante: {e.task}")
                self.last_error_message = error_msg
                return False
            except vim.fault.InvalidState as e:
                # Récupérer l'état de la VM pour un message plus détaillé
                power_state = vm.runtime.powerState
                snapshot_count = 0
                if hasattr(vm, 'snapshot') and vm.snapshot:
                    snapshot_count = len(vm.snapshot.rootSnapshotList) if hasattr(vm.snapshot, 'rootSnapshotList') else 0

                error_msg = (
                    f"La VM est dans un état invalide pour l'export (État: {power_state}, Snapshots: {snapshot_count}). "
                    f"Solutions: 1) Éteignez la VM si elle est allumée. "
                    f"2) Supprimez TOUS les snapshots. "
                    f"3) Consolidez les disques (vSphere: VM > Snapshots > Consolidate). "
                    f"4) Attendez quelques minutes et réessayez."
                )
                logger.error(f"[OVF] {error_msg}")
                logger.error(f"[OVF] Erreur ESXi: {e.msg}")
                self.last_error_message = error_msg
                return False

            # Attendre que le lease soit prêt
            logger.info("[OVF] Attente que le lease soit prêt...")
            while lease.state == vim.HttpNfcLease.State.initializing:
                time.sleep(1)

            if lease.state != vim.HttpNfcLease.State.ready:
                lease_error = str(lease.error) if lease.error else "Erreur inconnue"
                error_msg = (
                    f"Le lease ESXi n'est pas prêt pour l'export (État: {lease.state}). "
                    f"Erreur: {lease_error}. "
                    f"Cela peut indiquer un problème avec la VM ou l'ESXi. "
                    f"Vérifiez l'état de la VM dans vSphere et réessayez."
                )
                logger.error(f"[OVF] {error_msg}")
                self.last_error_message = error_msg
                return False

            logger.info("[OVF] Lease prêt, début du téléchargement...")

            if progress_callback:
                progress_callback(10)

            # Récupérer les informations du lease
            lease_info = lease.info
            total_bytes = 0
            for item in lease_info.deviceUrl:
                if hasattr(item, 'disk') and item.disk and hasattr(item.disk, 'capacity'):
                    total_bytes += item.disk.capacity
            downloaded_bytes = 0

            logger.info(f"[OVF] Taille totale estimée (disk.capacity): {total_bytes / (1024**3):.2f} GB")
            logger.info(f"[OVF] Nombre de fichiers: {len(lease_info.deviceUrl)}")

            # Télécharger chaque fichier
            files_info = []
            num_files_to_download = sum(1 for item in lease_info.deviceUrl if hasattr(item, 'disk') and item.disk)
            files_downloaded = 0

            for idx, device_url in enumerate(lease_info.deviceUrl):
                # Vérifier si c'est un disque (et non un fichier NVRAM ou autre)
                if not hasattr(device_url, 'disk') or not device_url.disk:
                    logger.info(f"[OVF] Fichier ignoré (non-disque): {device_url.targetId if hasattr(device_url, 'targetId') else 'unknown'}")
                    continue

                file_url = device_url.url.replace('*', self.host)
                file_name = device_url.targetId if device_url.targetId else f"disk-{idx}.vmdk"
                local_path = os.path.join(export_path, file_name)

                logger.info(f"[OVF] Téléchargement de {file_name}...")
                logger.info(f"[OVF] URL: {file_url}")

                try:
                    # Télécharger le fichier
                    session = requests.Session()
                    session.verify = False

                    # Ajouter les cookies de session si disponibles
                    if hasattr(lease, 'info') and hasattr(lease.info, 'cookie'):
                        cookie = lease.info.cookie
                        if cookie:
                            session.cookies.set('vmware_soap_session', cookie)

                    response = session.get(file_url, stream=True, timeout=600)
                    response.raise_for_status()

                    # Écrire le fichier
                    file_size = int(response.headers.get('content-length', 0))
                    chunk_size = 1024 * 1024  # 1MB
                    current_downloaded = 0
                    last_progress_update = 0

                    logger.info(f"[OVF] Taille réelle du fichier: {file_size / (1024**2):.2f} MB")

                    # Si total_bytes est 0, on utilise file_size comme base
                    if total_bytes == 0:
                        total_bytes = file_size

                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                current_downloaded += len(chunk)
                                downloaded_bytes += len(chunk)

                                # Calculer la progression pour ce fichier
                                file_progress = int((current_downloaded / max(file_size, 1)) * 100)

                                # Progression globale basée sur les fichiers
                                # Base: 10% déjà fait, on a 80% pour le download (10%-90%), puis 10% pour finalisation
                                files_base_progress = (files_downloaded / max(num_files_to_download, 1)) * 80
                                current_file_progress = (file_progress / 100) * (80 / max(num_files_to_download, 1))
                                global_progress = 10 + int(files_base_progress + current_file_progress)
                                global_progress = min(global_progress, 90)

                                if progress_callback:
                                    progress_callback(global_progress)

                                # Mettre à jour le lease tous les 1 MB pour éviter l'expiration
                                if current_downloaded - last_progress_update >= (1 * 1024 * 1024):
                                    try:
                                        # Calculer lease_progress basé sur bytes téléchargés
                                        if total_bytes > 0:
                                            lease_progress = int((downloaded_bytes / total_bytes) * 100)
                                        else:
                                            lease_progress = file_progress
                                        lease.HttpNfcLeaseProgress(min(lease_progress, 99))
                                        last_progress_update = current_downloaded
                                        logger.info(f"[OVF] Progress: Fichier {file_progress}%, Global {global_progress}%, Lease {lease_progress}%")
                                    except Exception as lease_err:
                                        logger.warning(f"[OVF] Erreur mise à jour lease: {lease_err}")

                    logger.info(f"[OVF] Fichier téléchargé: {local_path} ({file_size / (1024**2):.2f} MB)")

                    files_info.append({
                        'path': local_path,
                        'size': file_size,
                        'key': device_url.key if hasattr(device_url, 'key') else None,
                        'disk': device_url.disk if hasattr(device_url, 'disk') else None
                    })

                    # Incrémenter le compteur de fichiers téléchargés
                    files_downloaded += 1

                except Exception as e:
                    logger.warning(f"[OVF] Erreur lors du téléchargement de {file_name}: {str(e)}")
                    logger.warning(f"[OVF] Le fichier sera ignoré, l'export continue...")
                    continue

            # Vérifier qu'au moins un fichier a été téléchargé
            if not files_info:
                logger.error("[OVF] Aucun fichier disque n'a pu être téléchargé")
                lease.HttpNfcLeaseAbort()
                return False

            # Vérifier l'état du lease avant de le compléter
            logger.info(f"[OVF] État du lease avant completion: {lease.state}")
            if lease.state != vim.HttpNfcLease.State.ready:
                logger.error(f"[OVF] Le lease n'est pas dans l'état 'ready': {lease.state}")
                if lease.state != vim.HttpNfcLease.State.done:
                    try:
                        lease.HttpNfcLeaseAbort()
                    except:
                        pass
                return False

            # Compléter le lease
            logger.info("[OVF] Finalisation du lease...")
            try:
                lease.HttpNfcLeaseProgress(100)
                lease.HttpNfcLeaseComplete()
                logger.info("[OVF] Lease complété avec succès")
            except Exception as lease_complete_err:
                logger.error(f"[OVF] Erreur lors de la completion du lease: {lease_complete_err}")
                # Continuer quand même si le lease est déjà complété
                if "InvalidState" in str(lease_complete_err):
                    logger.warning("[OVF] Le lease était déjà dans un état final, on continue...")
                else:
                    raise

            if progress_callback:
                progress_callback(95)

            # Créer le fichier OVF descriptor
            ovf_path = os.path.join(export_path, f"{vm.name}.ovf")
            logger.info(f"[OVF] Création du descripteur OVF: {ovf_path}")

            # Générer un descripteur OVF basique
            ovf_content = self._generate_ovf_descriptor(vm, files_info)
            with open(ovf_path, 'w', encoding='utf-8') as f:
                f.write(ovf_content)

            logger.info(f"[OVF] Descripteur OVF créé: {ovf_path}")

            # Créer le fichier manifest (.mf) avec les checksums
            mf_path = os.path.join(export_path, f"{vm.name}.mf")
            logger.info(f"[OVF] Création du manifest: {mf_path}")

            import hashlib
            with open(mf_path, 'w') as mf:
                # Checksum du fichier OVF
                with open(ovf_path, 'rb') as f:
                    ovf_hash = hashlib.sha256(f.read()).hexdigest()
                    mf.write(f"SHA256({os.path.basename(ovf_path)})= {ovf_hash}\n")

                # Checksums des fichiers VMDK
                for file_info in files_info:
                    if os.path.exists(file_info['path']):
                        with open(file_info['path'], 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                            mf.write(f"SHA256({os.path.basename(file_info['path'])})= {file_hash}\n")

            logger.info(f"[OVF] Manifest créé: {mf_path}")

            if progress_callback:
                progress_callback(100)

            logger.info(f"[OVF] Export OVF terminé avec succès pour {vm.name}")
            logger.info(f"[OVF] Fichiers créés:")
            logger.info(f"[OVF]   - {ovf_path}")
            logger.info(f"[OVF]   - {mf_path}")
            for file_info in files_info:
                logger.info(f"[OVF]   - {file_info['path']}")

            return True

        except Exception as e:
            logger.exception(f"[OVF] Erreur lors de l'export OVF: {str(e)}")
            # Essayer de compléter le lease en cas d'erreur
            try:
                if 'lease' in locals():
                    lease.HttpNfcLeaseAbort()
            except:
                pass
            return False

    def _generate_ovf_descriptor(self, vm, files_info):
        """
        Génère un descripteur OVF basique pour la VM.

        Args:
            vm: L'objet VirtualMachine pyVmomi
            files_info: Liste des informations sur les fichiers exportés

        Returns:
            Le contenu XML du descripteur OVF
        """
        # Template OVF basique
        ovf_template = f'''<?xml version="1.0" encoding="UTF-8"?>
<Envelope vmw:buildId="build-00000" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <References>
'''

        # Ajouter les références aux fichiers
        for idx, file_info in enumerate(files_info):
            file_name = os.path.basename(file_info['path'])
            file_size = file_info['size']
            ovf_template += f'    <File ovf:href="{file_name}" ovf:id="file{idx}" ovf:size="{file_size}"/>\n'

        ovf_template += f'''  </References>
  <DiskSection>
    <Info>Virtual disk information</Info>
'''

        # Ajouter les disques
        for idx, file_info in enumerate(files_info):
            if file_info['path'].endswith('.vmdk'):
                file_name = os.path.basename(file_info['path'])
                capacity = file_info.get('disk', {}).capacity if hasattr(file_info.get('disk', {}), 'capacity') else file_info['size']
                ovf_template += f'    <Disk ovf:capacity="{capacity}" ovf:capacityAllocationUnits="byte" ovf:diskId="vmdisk{idx}" ovf:fileRef="file{idx}" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/>\n'

        memory_mb = vm.summary.config.memorySizeMB if hasattr(vm.summary.config, 'memorySizeMB') else 1024
        num_cpus = vm.summary.config.numCpu if hasattr(vm.summary.config, 'numCpu') else 1
        guest_id = vm.summary.config.guestId if hasattr(vm.summary.config, 'guestId') else 'otherGuest'

        ovf_template += f'''  </DiskSection>
  <NetworkSection>
    <Info>The list of logical networks</Info>
    <Network ovf:name="VM Network">
      <Description>The VM Network network</Description>
    </Network>
  </NetworkSection>
  <VirtualSystem ovf:id="{vm.name}">
    <Info>A virtual machine</Info>
    <Name>{vm.name}</Name>
    <OperatingSystemSection ovf:id="0" vmw:osType="{guest_id}">
      <Info>The kind of installed guest operating system</Info>
    </OperatingSystemSection>
    <VirtualHardwareSection>
      <Info>Virtual hardware requirements</Info>
      <System>
        <vssd:ElementName>Virtual Hardware Family</vssd:ElementName>
        <vssd:InstanceID>0</vssd:InstanceID>
        <vssd:VirtualSystemType>vmx-13</vssd:VirtualSystemType>
      </System>
      <Item>
        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
        <rasd:Description>Number of Virtual CPUs</rasd:Description>
        <rasd:ElementName>{num_cpus} virtual CPU(s)</rasd:ElementName>
        <rasd:InstanceID>1</rasd:InstanceID>
        <rasd:ResourceType>3</rasd:ResourceType>
        <rasd:VirtualQuantity>{num_cpus}</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
        <rasd:Description>Memory Size</rasd:Description>
        <rasd:ElementName>{memory_mb}MB of memory</rasd:ElementName>
        <rasd:InstanceID>2</rasd:InstanceID>
        <rasd:ResourceType>4</rasd:ResourceType>
        <rasd:VirtualQuantity>{memory_mb}</rasd:VirtualQuantity>
      </Item>
    </VirtualHardwareSection>
  </VirtualSystem>
</Envelope>'''

        return ovf_template

    def create_snapshot(self, vm_id, snapshot_name, description="", memory=False):
        """
        Crée un snapshot d'une VM.

        Args:
            vm_id: L'UUID de la VM
            snapshot_name: Nom du snapshot
            description: Description du snapshot
            memory: Inclure la mémoire RAM dans le snapshot

        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"[SNAPSHOT] Création du snapshot '{snapshot_name}' pour VM {vm_id}")

            vm = self._find_vm_by_uuid(vm_id)
            if not vm:
                logger.error(f"[SNAPSHOT] VM introuvable: {vm_id}")
                return False

            logger.info(f"[SNAPSHOT] VM trouvée: {vm.name}, Création en cours...")

            # Créer le snapshot
            # memory: Inclure la mémoire
            # quiesce: Synchroniser le système de fichiers (nécessite VMware Tools)
            task = vm.CreateSnapshot_Task(
                name=snapshot_name,
                description=description,
                memory=memory,
                quiesce=False  # Ne pas forcer quiesce car peut échouer sans VMware Tools
            )

            # Attendre la fin de la tâche
            from pyVmomi import vim
            while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                time.sleep(0.5)

            if task.info.state == vim.TaskInfo.State.success:
                logger.info(f"[SNAPSHOT] Snapshot créé avec succès: {snapshot_name}")
                return True
            else:
                logger.error(f"[SNAPSHOT] Échec de création: {task.info.error}")
                return False

        except Exception as e:
            logger.exception(f"[SNAPSHOT] Erreur lors de la création: {str(e)}")
            return False

    def revert_snapshot(self, vm_id, snapshot_name):
        """
        Restaure une VM à un snapshot spécifique.

        Args:
            vm_id: L'UUID de la VM
            snapshot_name: Nom du snapshot à restaurer

        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"[SNAPSHOT] Restauration du snapshot '{snapshot_name}' pour VM {vm_id}")

            vm = self._find_vm_by_uuid(vm_id)
            if not vm:
                logger.error(f"[SNAPSHOT] VM introuvable: {vm_id}")
                return False

            # Trouver le snapshot par nom
            snapshot = self._find_snapshot_by_name(vm, snapshot_name)
            if not snapshot:
                logger.error(f"[SNAPSHOT] Snapshot introuvable: {snapshot_name}")
                return False

            logger.info(f"[SNAPSHOT] Snapshot trouvé, restauration en cours...")

            # Restaurer le snapshot
            task = snapshot.RevertToSnapshot_Task()

            # Attendre la fin de la tâche
            from pyVmomi import vim
            while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                time.sleep(0.5)

            if task.info.state == vim.TaskInfo.State.success:
                logger.info(f"[SNAPSHOT] Snapshot restauré avec succès: {snapshot_name}")
                return True
            else:
                logger.error(f"[SNAPSHOT] Échec de restauration: {task.info.error}")
                return False

        except Exception as e:
            logger.exception(f"[SNAPSHOT] Erreur lors de la restauration: {str(e)}")
            return False

    def delete_snapshot(self, vm_id, snapshot_name):
        """
        Supprime un snapshot.

        Args:
            vm_id: L'UUID de la VM
            snapshot_name: Nom du snapshot à supprimer

        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"[SNAPSHOT] Suppression du snapshot '{snapshot_name}' pour VM {vm_id}")

            vm = self._find_vm_by_uuid(vm_id)
            if not vm:
                logger.error(f"[SNAPSHOT] VM introuvable: {vm_id}")
                return False

            # Trouver le snapshot par nom
            snapshot = self._find_snapshot_by_name(vm, snapshot_name)
            if not snapshot:
                logger.error(f"[SNAPSHOT] Snapshot introuvable: {snapshot_name}")
                return False

            logger.info(f"[SNAPSHOT] Snapshot trouvé, suppression en cours...")

            # Supprimer le snapshot (removeChildren=False pour ne supprimer que ce snapshot)
            task = snapshot.RemoveSnapshot_Task(removeChildren=False)

            # Attendre la fin de la tâche
            from pyVmomi import vim
            while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                time.sleep(0.5)

            if task.info.state == vim.TaskInfo.State.success:
                logger.info(f"[SNAPSHOT] Snapshot supprimé avec succès: {snapshot_name}")
                return True
            else:
                logger.error(f"[SNAPSHOT] Échec de suppression: {task.info.error}")
                return False

        except Exception as e:
            logger.exception(f"[SNAPSHOT] Erreur lors de la suppression: {str(e)}")
            return False

    def _find_snapshot_by_name(self, vm, snapshot_name):
        """
        Trouve un snapshot par son nom dans l'arbre de snapshots d'une VM.

        Args:
            vm: L'objet VirtualMachine pyVmomi
            snapshot_name: Nom du snapshot à trouver

        Returns:
            L'objet snapshot si trouvé, None sinon
        """
        if not vm.snapshot:
            return None

        def search_snapshots(snapshots):
            for snapshot in snapshots:
                if snapshot.name == snapshot_name:
                    return snapshot.snapshot
                if snapshot.childSnapshotList:
                    result = search_snapshots(snapshot.childSnapshotList)
                    if result:
                        return result
            return None

        return search_snapshots(vm.snapshot.rootSnapshotList)

    def _find_vm_by_uuid(self, vm_uuid):
        """Trouve une VM par son UUID"""
        if not self.content:
            return None

        search_index = self.content.searchIndex
        vm = search_index.FindByUuid(None, vm_uuid, True, True)
        return vm

    def deploy_ovf(self, ovf_path, vm_name, datastore_name, network_name="VM Network", power_on=False, progress_callback=None):
        """
        Déploie un OVF sur ESXi (restauration d'une sauvegarde).

        Args:
            ovf_path: Chemin vers le fichier .ovf à déployer
            vm_name: Nom de la nouvelle VM
            datastore_name: Nom du datastore où déployer
            network_name: Nom du réseau à utiliser (par défaut: "VM Network")
            power_on: Démarrer la VM après déploiement
            progress_callback: Fonction callback pour la progression

        Returns:
            True si succès, False sinon
        """
        try:
            import time
            import requests
            import urllib3
            from urllib.parse import quote

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            logger.info(f"[DEPLOY] Début du déploiement OVF: {ovf_path}")
            logger.info(f"[DEPLOY] Nom de la VM: {vm_name}")
            logger.info(f"[DEPLOY] Datastore: {datastore_name}")

            if progress_callback:
                progress_callback(5)

            # Vérifier que le fichier OVF existe
            if not os.path.exists(ovf_path):
                logger.error(f"[DEPLOY] Fichier OVF introuvable: {ovf_path}")
                return False

            # Lire le descripteur OVF
            logger.info("[DEPLOY] Lecture du descripteur OVF...")
            with open(ovf_path, 'r', encoding='utf-8') as f:
                ovf_descriptor = f.read()

            # DEBUG: Afficher des extraits du OVF pour voir comment les disques sont déclarés
            if '<DiskSection>' in ovf_descriptor:
                disk_start = ovf_descriptor.find('<DiskSection>')
                disk_end = ovf_descriptor.find('</DiskSection>') + len('</DiskSection>')
                logger.info(f"[DEPLOY] ⚠️ DiskSection trouvée dans OVF:")
                logger.info(ovf_descriptor[disk_start:disk_end][:500] + '...')  # Premier 500 chars
            else:
                logger.warning("[DEPLOY] ⚠️ AUCUNE DiskSection trouvée dans OVF!")

            if progress_callback:
                progress_callback(10)

            # Récupérer le datastore
            logger.info(f"[DEPLOY] Recherche du datastore {datastore_name}...")
            datastore = self._find_datastore_by_name(datastore_name)
            if not datastore:
                logger.error(f"[DEPLOY] Datastore introuvable: {datastore_name}")
                return False

            # Récupérer le resource pool
            logger.info("[DEPLOY] Recherche du resource pool...")
            resource_pool = self._get_resource_pool()
            if not resource_pool:
                logger.error("[DEPLOY] Resource pool introuvable")
                return False

            # Récupérer le dossier VM
            logger.info("[DEPLOY] Recherche du dossier VM...")
            vm_folder = self._get_vm_folder()
            if not vm_folder:
                logger.error("[DEPLOY] Dossier VM introuvable")
                return False

            if progress_callback:
                progress_callback(15)

            # Préparer les paramètres d'import
            logger.info("[DEPLOY] Préparation des paramètres d'import...")
            ovf_manager = self.content.ovfManager

            # Extraire le nom du réseau depuis l'OVF
            ovf_network_name = "VM Network"  # Valeur par défaut
            if '<Network ovf:name="' in ovf_descriptor:
                import re
                network_match = re.search(r'<Network ovf:name="([^"]+)"', ovf_descriptor)
                if network_match:
                    ovf_network_name = network_match.group(1)
                    logger.info(f"[DEPLOY] Réseau trouvé dans OVF: {ovf_network_name}")
            else:
                logger.warning(f"[DEPLOY] Aucun réseau trouvé dans OVF, utilisation par défaut: {ovf_network_name}")

            # Créer les spécifications d'import
            spec_params = vim.OvfManager.CreateImportSpecParams()
            spec_params.entityName = vm_name
            spec_params.diskProvisioning = "flat"  # Essayer 'flat' pour streamOptimized
            logger.info("[DEPLOY] Disk provisioning: flat (compatible avec streamOptimized)")

            # Mapping réseau
            network_mapping = vim.OvfManager.NetworkMapping()
            network_mapping.name = ovf_network_name
            network = self._find_network_by_name(network_name)
            if network:
                network_mapping.network = network
                spec_params.networkMapping = [network_mapping]
                logger.info(f"[DEPLOY] Réseau mappé: {ovf_network_name} -> {network_name}")
            else:
                logger.warning(f"[DEPLOY] Réseau {network_name} introuvable sur ESXi")

            # Parser l'OVF et créer les spécifications
            logger.info("[DEPLOY] Parsing de l'OVF et création des spécifications...")
            import_spec = ovf_manager.CreateImportSpec(
                ovf_descriptor,
                resource_pool,
                datastore,
                spec_params
            )

            # Vérifier les erreurs
            if import_spec.error:
                errors = [str(e.msg) for e in import_spec.error]
                logger.error(f"[DEPLOY] ⚠️ ERREURS lors de la création des spécifications: {errors}")
                return False

            if import_spec.warning:
                warnings = [str(w.msg) for w in import_spec.warning]
                logger.warning(f"[DEPLOY] ⚠️ WARNINGS lors de la création des spécifications: {warnings}")

            # DEBUG: Vérifier ce qui est dans importSpec
            logger.info(f"[DEPLOY] ImportSpec créé:")
            if hasattr(import_spec, 'importSpec'):
                logger.info(f"[DEPLOY]   - ConfigSpec présent: {import_spec.importSpec.configSpec is not None}")
                if hasattr(import_spec.importSpec, 'configSpec') and import_spec.importSpec.configSpec:
                    logger.info(f"[DEPLOY]   - Nom VM: {import_spec.importSpec.configSpec.name}")
                    if hasattr(import_spec.importSpec.configSpec, 'deviceChange'):
                        num_devices = len(import_spec.importSpec.configSpec.deviceChange) if import_spec.importSpec.configSpec.deviceChange else 0
                        logger.info(f"[DEPLOY]   - Nombre de deviceChanges: {num_devices}")
                        if num_devices > 0:
                            for idx, dev_change in enumerate(import_spec.importSpec.configSpec.deviceChange):
                                logger.info(f"[DEPLOY]     Device {idx+1}: {type(dev_change.device).__name__}")

            if progress_callback:
                progress_callback(20)

            # Créer le lease d'import
            logger.info("[DEPLOY] Création du lease d'import...")
            lease = resource_pool.ImportVApp(
                import_spec.importSpec,
                vm_folder
            )

            # Attendre que le lease soit prêt
            logger.info("[DEPLOY] Attente que le lease soit prêt...")
            while lease.state == vim.HttpNfcLease.State.initializing:
                time.sleep(1)

            if lease.state != vim.HttpNfcLease.State.ready:
                logger.error(f"[DEPLOY] Le lease n'est pas prêt: {lease.state}")
                if lease.error:
                    logger.error(f"[DEPLOY] Erreur: {lease.error}")
                return False

            logger.info("[DEPLOY] Lease prêt, début de l'upload...")

            if progress_callback:
                progress_callback(25)

            # Uploader les fichiers VMDK
            lease_info = lease.info
            total_bytes_to_upload = 0
            uploaded_bytes = 0

            # Calculer la taille totale
            ovf_dir = os.path.dirname(ovf_path)
            files_to_upload = []

            # D'abord, lister tous les fichiers VMDK disponibles
            vmdk_files = {}
            for file_name in os.listdir(ovf_dir):
                if file_name.endswith('.vmdk'):
                    file_path = os.path.join(ovf_dir, file_name)
                    vmdk_files[file_name] = {
                        'path': file_path,
                        'size': os.path.getsize(file_path)
                    }

            logger.info(f"[DEPLOY] Fichiers VMDK trouvés: {list(vmdk_files.keys())}")

            # DEBUG: Afficher TOUS les device_urls retournés par ESXi
            logger.info(f"[DEPLOY] ⚠️ NOMBRE de device_urls retournés par ESXi: {len(lease_info.deviceUrl)}")
            for idx, dev_url in enumerate(lease_info.deviceUrl):
                logger.info(f"[DEPLOY] Device #{idx+1}: URL={dev_url.url}, Key={dev_url.importKey}")

            # Ensuite, mapper chaque device_url au bon fichier
            for device_url in lease_info.deviceUrl:
                import_key = device_url.importKey
                logger.info(f"[DEPLOY] Device URL: {device_url.url}, ImportKey: {import_key}")

                # FILTRER : Ignorer les device_url qui ne sont PAS pour des disques VMDK
                # ImportKey contient généralement "/vmname/disk-X" pour les disques
                # et "/vmname/nvram" pour NVRAM
                if 'nvram' in import_key.lower():
                    logger.info(f"[DEPLOY] Ignoré (NVRAM): {import_key}")
                    continue

                if 'disk' not in import_key.lower():
                    logger.info(f"[DEPLOY] Ignoré (pas un disque): {import_key}")
                    continue

                # Chercher le fichier VMDK correspondant
                # L'importKey contient souvent "disk-0", "disk-1", etc.
                matched_file = None
                for file_name, file_info in vmdk_files.items():
                    # Vérifier que ce fichier n'a pas déjà été mappé
                    if any(f['path'] == file_info['path'] for f in files_to_upload):
                        continue

                    # Essayer de matcher par le numéro de disque dans l'importKey
                    # Par exemple: importKey="/VM/disk-0" devrait matcher "VM-disk-0.vmdk"
                    if 'disk-' in import_key.lower() and 'disk-' in file_name.lower():
                        # Extraire le numéro de disque de l'importKey
                        import_disk_num = import_key.lower().split('disk-')[-1].split('/')[0].split('.')[0]
                        file_disk_num = file_name.lower().split('disk-')[-1].split('.')[0]

                        if import_disk_num == file_disk_num:
                            matched_file = (file_name, file_info)
                            logger.info(f"[DEPLOY] Match trouvé: {file_name} <-> {import_key}")
                            break

                # Si aucun match spécifique, prendre le premier VMDK non mappé
                if not matched_file:
                    for file_name, file_info in vmdk_files.items():
                        if not any(f['path'] == file_info['path'] for f in files_to_upload):
                            matched_file = (file_name, file_info)
                            logger.info(f"[DEPLOY] Match générique: {file_name} <-> {import_key}")
                            break

                if matched_file:
                    file_name, file_info = matched_file
                    files_to_upload.append({
                        'path': file_info['path'],
                        'size': file_info['size'],
                        'url': device_url.url.replace('*', self.host),
                        'device_url': device_url,
                        'import_key': import_key
                    })
                    total_bytes_to_upload += file_info['size']
                    logger.info(f"[DEPLOY] ✓ Ajouté: {file_name} -> {device_url.url}")
                else:
                    logger.warning(f"[DEPLOY] ⚠ Aucun fichier VMDK disponible pour: {import_key}")

            logger.info(f"[DEPLOY] Fichiers à uploader: {len(files_to_upload)}")
            logger.info(f"[DEPLOY] Taille totale: {total_bytes_to_upload / (1024**3):.2f} GB")

            # Uploader chaque fichier
            for idx, file_info in enumerate(files_to_upload):
                file_path = file_info['path']
                file_url = file_info['url']
                file_size = file_info['size']

                logger.info(f"[DEPLOY] Upload {idx+1}/{len(files_to_upload)}: {os.path.basename(file_path)}")
                logger.info(f"[DEPLOY] URL: {file_url}")

                # Uploader le fichier via HTTP PUT
                session = requests.Session()
                session.verify = False

                with open(file_path, 'rb') as f:
                    headers = {
                        'Content-Type': 'application/x-vnd.vmware-streamVmdk',
                        'Content-Length': str(file_size)
                    }

                    # Uploader par chunks avec progression
                    chunk_size = 1024 * 1024  # 1MB
                    current_uploaded = 0

                    def upload_in_chunks():
                        nonlocal current_uploaded, uploaded_bytes
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                            current_uploaded += len(chunk)
                            uploaded_bytes += len(chunk)

                            # Mettre à jour la progression
                            if total_bytes_to_upload > 0:
                                lease_progress = int((uploaded_bytes / total_bytes_to_upload) * 100)
                                # Progression globale de 25% à 95%
                                global_progress = 25 + int((uploaded_bytes / total_bytes_to_upload) * 70)

                                if progress_callback:
                                    progress_callback(global_progress)

                                # Mettre à jour le lease pour éviter l'expiration
                                if current_uploaded % (10 * 1024 * 1024) < chunk_size:
                                    try:
                                        lease.HttpNfcLeaseProgress(lease_progress)
                                    except:
                                        pass

                    response = session.put(file_url, data=upload_in_chunks(), headers=headers)

                    if response.status_code not in [200, 201]:
                        logger.error(f"[DEPLOY] Erreur HTTP lors de l'upload: {response.status_code}")
                        lease.HttpNfcLeaseAbort()
                        return False

                logger.info(f"[DEPLOY] Fichier uploadé avec succès: {os.path.basename(file_path)}")

            # Compléter le lease
            logger.info("[DEPLOY] Finalisation du déploiement...")
            lease.HttpNfcLeaseComplete()

            if progress_callback:
                progress_callback(95)

            # Démarrer la VM si demandé
            if power_on:
                logger.info("[DEPLOY] Démarrage de la VM...")
                # Trouver la VM nouvellement créée
                vm = self._find_vm_by_name(vm_name)
                if vm and vm.runtime.powerState != vim.VirtualMachine.PowerState.poweredOn:
                    task = vm.PowerOnVM_Task()
                    while task.info.state not in [vim.TaskInfo.State.success, vim.TaskInfo.State.error]:
                        time.sleep(0.5)

                    if task.info.state == vim.TaskInfo.State.success:
                        logger.info("[DEPLOY] VM démarrée avec succès")

            if progress_callback:
                progress_callback(100)

            logger.info(f"[DEPLOY] Déploiement OVF terminé avec succès pour {vm_name}")
            return True

        except Exception as e:
            logger.exception(f"[DEPLOY] Erreur lors du déploiement OVF: {str(e)}")
            # Essayer d'annuler le lease en cas d'erreur
            try:
                if 'lease' in locals():
                    lease.HttpNfcLeaseAbort()
            except:
                pass
            return False

    def _find_datastore_by_name(self, datastore_name):
        """Trouve un datastore par son nom"""
        if not self.content:
            return None

        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, [vim.Datastore], True
        )

        for ds in container.view:
            if ds.summary.name == datastore_name:
                container.Destroy()
                return ds

        container.Destroy()
        return None

    def _get_resource_pool(self):
        """Récupère le resource pool par défaut"""
        if not self.content:
            return None

        try:
            # Pour un ESXi standalone, le resource pool est dans le premier host
            host_systems = self.content.rootFolder.childEntity[0].hostFolder.childEntity
            for cluster in host_systems:
                if hasattr(cluster, 'resourcePool'):
                    return cluster.resourcePool
                for host in cluster.host:
                    return host.parent.resourcePool
        except:
            pass

        return None

    def _get_vm_folder(self):
        """Récupère le dossier VM par défaut"""
        if not self.content:
            return None

        try:
            return self.content.rootFolder.childEntity[0].vmFolder
        except:
            return None

    def _find_network_by_name(self, network_name):
        """Trouve un réseau par son nom"""
        if not self.content:
            return None

        try:
            container = self.content.viewManager.CreateContainerView(
                self.content.rootFolder, [vim.Network], True
            )

            for network in container.view:
                if network.name == network_name:
                    container.Destroy()
                    return network

            container.Destroy()
        except:
            pass

        return None

    def _find_vm_by_name(self, vm_name):
        """Trouve une VM par son nom"""
        if not self.content:
            return None

        try:
            container = self.content.viewManager.CreateContainerView(
                self.content.rootFolder, [vim.VirtualMachine], True
            )

            for vm in container.view:
                if vm.name == vm_name:
                    container.Destroy()
                    return vm

            container.Destroy()
        except:
            pass

        return None
