"""
OVF Export Service using VMware HttpNfcLease API
Correctly handles thin-provisioned disks by exporting only used data
"""
import os
import logging
import hashlib
import requests
import urllib3
from datetime import datetime
from django.utils import timezone
from pyVim.task import WaitForTask
from pyVmomi import vim

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class OVFExportLeaseService:
    """
    Service for exporting VMs to OVF format using HttpNfcLease API
    This correctly handles thin-provisioned disks
    """

    def __init__(self, vm_obj, export_job):
        """
        Args:
            vm_obj: pyVmomi VM object
            export_job: OVFExportJob model instance
        """
        self.vm = vm_obj
        self.export_job = export_job
        self.vm_name = vm_obj.name

        # Get ESXi credentials
        esxi_server = export_job.virtual_machine.server
        self.esxi_host = esxi_server.hostname
        self.esxi_user = esxi_server.username
        self.esxi_pass = esxi_server.password


    def export_ovf(self):
        """
        Export VM to OVF format using HttpNfcLease API

        Returns:
            bool: True if export successful
        """
        lease = None

        try:
            logger.info(f"[OVF-EXPORT] ========================================")
            logger.info(f"[OVF-EXPORT] Starting OVF export for {self.vm_name}")
            logger.info(f"[OVF-EXPORT] Using HttpNfcLease API (handles thin-provisioned disks)")
            logger.info(f"[OVF-EXPORT] ========================================")

            self.export_job.status = 'running'
            self.export_job.started_at = timezone.now()
            self.export_job.progress_percentage = 5
            self.export_job.downloaded_bytes = 0
            self.export_job.total_bytes = 0
            self.export_job.download_speed_mbps = 0
            self.export_job.save()

            # Create export directory
            export_dir = self.export_job.export_full_path
            os.makedirs(export_dir, exist_ok=True)
            logger.info(f"[OVF-EXPORT] Export directory: {export_dir}")

            # Step 1: Create export lease
            logger.info(f"[OVF-EXPORT] Step 1/5: Creating export lease...")
            lease = self.vm.ExportVm()

            # Wait for lease to be ready
            logger.info(f"[OVF-EXPORT] Waiting for lease to be ready...")
            while lease.state == vim.HttpNfcLease.State.initializing:
                pass

            if lease.state != vim.HttpNfcLease.State.ready:
                error_msg = f"Lease failed to initialize: {lease.state}"
                logger.error(f"[OVF-EXPORT] {error_msg}")
                raise Exception(error_msg)

            logger.info(f"[OVF-EXPORT] Lease ready")
            self.export_job.progress_percentage = 8
            self.export_job.save()

            # Step 2: Pré-scan pour obtenir la taille EXACTE des fichiers qui seront exportés
            logger.info(f"[OVF-EXPORT] Step 2/5: Pre-scanning export files sizes...")
            device_urls = lease.info.deviceUrl
            logger.info(f"[OVF-EXPORT] Found {len(device_urls)} files to export")

            total_bytes = 0
            file_info_list = []

            for i, device_url in enumerate(device_urls):
                url = device_url.url.replace('*', self.esxi_host)
                target_id = device_url.targetId if hasattr(device_url, 'targetId') else f"file-{i}"

                # Déterminer le nom du fichier
                filename = None
                if (target_id and 'disk' in target_id.lower()) or 'vmdk' in url.lower():
                    filename = f"{self.vm_name}-disk-{i}.vmdk"
                elif 'ovf' in url.lower() or target_id == 'descriptor':
                    filename = f"{self.vm_name}.ovf"
                else:
                    if '/' in url:
                        filename = url.split('/')[-1]
                    else:
                        filename = target_id or f"file-{i}"

                # Requête GET avec stream=True pour obtenir Content-Length sans télécharger
                # (ESXi ne supporte pas HEAD, retourne HTTP 501)
                try:
                    get_response = requests.get(
                        url,
                        auth=(self.esxi_user, self.esxi_pass),
                        verify=False,
                        stream=True,  # Ne pas télécharger le contenu
                        timeout=10
                    )

                    if get_response.status_code == 200:
                        real_size = int(get_response.headers.get('Content-Length', 0))

                        # Fermer immédiatement la connexion sans télécharger le contenu
                        get_response.close()

                        if real_size > 0:
                            total_bytes += real_size
                            size_mb = real_size / (1024 * 1024)
                            logger.info(f"[OVF-EXPORT] Pre-scan: {filename} = {size_mb:.2f} MB")

                            file_info_list.append({
                                'url': url,
                                'filename': filename,
                                'size': real_size,
                                'index': i
                            })
                        else:
                            logger.warning(f"[OVF-EXPORT] Pre-scan: {filename} = taille inconnue (Content-Length=0)")
                            file_info_list.append({
                                'url': url,
                                'filename': filename,
                                'size': 0,
                                'index': i
                            })
                    else:
                        # Fichier optionnel qui n'existe pas (ex: NVRAM)
                        logger.warning(f"[OVF-EXPORT] Pre-scan: {filename} non disponible (HTTP {get_response.status_code})")
                        get_response.close()

                except Exception as e:
                    logger.warning(f"[OVF-EXPORT] Pre-scan GET failed for {filename}: {e}")
                    # Ajouter quand même à la liste avec taille 0
                    file_info_list.append({
                        'url': url,
                        'filename': filename,
                        'size': 0,
                        'index': i
                    })

            # Stocker la taille totale EXACTE des fichiers qui seront exportés
            self.export_job.total_bytes = total_bytes
            self.export_job.save()

            total_gb = total_bytes / (1024 * 1024 * 1024)
            logger.info(f"[OVF-EXPORT] ========================================")
            logger.info(f"[OVF-EXPORT] Taille totale EXACTE à exporter: {total_gb:.2f} GB ({total_bytes / (1024*1024):.2f} MB)")
            logger.info(f"[OVF-EXPORT] Nombre de fichiers: {len(file_info_list)}")
            logger.info(f"[OVF-EXPORT] ========================================")

            self.export_job.progress_percentage = 10
            self.export_job.save()

            # Step 3: Download files (avec la taille exacte connue depuis le pré-scan)
            logger.info(f"[OVF-EXPORT] Step 3/5: Downloading VM files...")
            downloaded_files = []
            downloaded_bytes = 0

            for file_info in file_info_list:
                url = file_info['url']
                filename = file_info['filename']
                file_size = file_info['size']
                file_index = file_info['index']

                dest_path = os.path.join(export_dir, filename)

                # Download file
                size_mb = file_size / (1024*1024) if file_size > 0 else 0
                logger.info(f"[OVF-EXPORT] Downloading {filename} ({size_mb:.2f} MB)")
                logger.info(f"[OVF-EXPORT] URL: {url}")

                try:
                    # Vérifier si l'export a été annulé avant de télécharger
                    self.export_job.refresh_from_db()
                    if self.export_job.status == 'cancelled':
                        logger.info(f"[OVF-EXPORT] Export annulé par l'utilisateur")
                        raise Exception("Export annulé par l'utilisateur")

                    # Télécharger le fichier (total_bytes est déjà précis depuis le pré-scan)
                    total_bytes = self._download_file(url, dest_path, file_size, downloaded_bytes, total_bytes, file_index, len(file_info_list))

                    # Get actual file size after download (lease fileSize may be 0 or incorrect)
                    actual_size_bytes = os.path.getsize(dest_path)
                    actual_size_mb = actual_size_bytes / (1024 * 1024)

                    # Si le fichier téléchargé est plus gros que prévu, ajuster total_bytes
                    expected_remaining = total_bytes - downloaded_bytes
                    if actual_size_bytes > expected_remaining:
                        # Le fichier est plus gros que prévu, ajuster le total
                        size_diff = actual_size_bytes - expected_remaining
                        total_bytes += size_diff
                        self.export_job.total_bytes = total_bytes
                        logger.warning(f"[OVF-EXPORT] Ajustement total_bytes: +{size_diff / (1024*1024):.2f} MB -> {total_bytes / (1024*1024):.2f} MB total")

                    # Incrémenter avec la VRAIE taille téléchargée, pas celle du lease
                    downloaded_bytes += actual_size_bytes

                    downloaded_files.append({
                        'filename': filename,
                        'size_mb': actual_size_mb,
                        'path': dest_path
                    })
                    logger.info(f"[OVF-EXPORT] Downloaded: {filename} (actual size: {actual_size_mb:.2f} MB)")

                except requests.exceptions.HTTPError as e:
                    # HTTP errors (404, 403, etc.) - skip optional files
                    if 'nvram' in filename.lower() or e.response.status_code == 404:
                        logger.warning(f"[OVF-EXPORT] Skipping optional file {filename} (HTTP {e.response.status_code})")
                        continue
                    else:
                        logger.error(f"[OVF-EXPORT] HTTP error downloading {filename}: {e}")
                        raise
                except Exception as e:
                    # Other errors (timeout, connection, etc.)
                    logger.error(f"[OVF-EXPORT] Error downloading {filename}: {e}")
                    if 'nvram' in filename.lower():
                        logger.warning(f"[OVF-EXPORT] Skipping NVRAM file (optional)")
                        continue
                    else:
                        raise

            # Update progress to 85% (téléchargement terminé)
            self.export_job.progress_percentage = 85
            self.export_job.save()

            # Step 4: Generate OVF descriptor (if not already downloaded)
            logger.info(f"[OVF-EXPORT] Step 4/5: Generating OVF descriptor...")
            ovf_files = [f for f in downloaded_files if f['filename'].endswith('.ovf')]

            if not ovf_files:
                # Generate OVF descriptor manually
                logger.info(f"[OVF-EXPORT] Generating OVF descriptor...")
                ovf_content = self._generate_ovf_descriptor(downloaded_files)
                ovf_file = os.path.join(export_dir, f"{self.vm_name}.ovf")
                with open(ovf_file, 'w', encoding='utf-8') as f:
                    f.write(ovf_content)
                logger.info(f"[OVF-EXPORT] OVF descriptor created: {ovf_file}")
                downloaded_files.append({
                    'filename': f"{self.vm_name}.ovf",
                    'size_mb': os.path.getsize(ovf_file) / (1024 * 1024),
                    'path': ovf_file
                })

            self.export_job.progress_percentage = 92
            self.export_job.save()

            # Step 5: Generate manifest
            logger.info(f"[OVF-EXPORT] Step 5/5: Generating manifest...")
            self._generate_manifest(export_dir, downloaded_files)
            self.export_job.progress_percentage = 95
            self.export_job.save()

            # Complete the lease
            logger.info(f"[OVF-EXPORT] Completing lease...")
            try:
                lease.Complete()
                logger.info(f"[OVF-EXPORT] Lease completed successfully")
            except Exception as lease_error:
                # Lease completion can fail if it timed out or was auto-closed
                # This is not critical if all files were downloaded successfully
                logger.warning(f"[OVF-EXPORT] Lease completion failed (non-critical): {lease_error}")
                logger.warning(f"[OVF-EXPORT] All files were downloaded successfully, continuing...")

            # Calculate total size
            total_size_mb = sum(f['size_mb'] for f in downloaded_files)
            self.export_job.export_size_mb = total_size_mb
            self.export_job.progress_percentage = 100
            self.export_job.status = 'completed'
            self.export_job.completed_at = timezone.now()
            self.export_job.save()

            logger.info(f"[OVF-EXPORT] ========================================")
            logger.info(f"[OVF-EXPORT] Export completed successfully!")
            logger.info(f"[OVF-EXPORT] Total size: {total_size_mb:.2f} MB")
            logger.info(f"[OVF-EXPORT] Files exported: {len(downloaded_files)}")
            logger.info(f"[OVF-EXPORT] Location: {export_dir}")
            logger.info(f"[OVF-EXPORT] ========================================")

            return True

        except Exception as e:
            logger.error(f"[OVF-EXPORT] ========================================")
            logger.error(f"[OVF-EXPORT] Export failed: {e}")
            logger.error(f"[OVF-EXPORT] ========================================")

            # Vérifier si c'est une annulation ou une vraie erreur
            is_cancelled = "annulé" in str(e).lower() or self.export_job.status == 'cancelled'

            if not is_cancelled:
                logger.exception(e)

            # Abort the lease if it exists
            if lease and lease.state == vim.HttpNfcLease.State.ready:
                try:
                    lease.Abort()
                    logger.info(f"[OVF-EXPORT] Lease aborté")
                except:
                    pass

            # Si c'est une annulation, ne pas changer le statut (il est déjà 'cancelled')
            # Sinon, mettre le statut à 'failed'
            if not is_cancelled:
                self.export_job.status = 'failed'
                self.export_job.error_message = str(e)

            self.export_job.completed_at = timezone.now()
            self.export_job.save()

            return False

    def _download_file(self, url, dest_path, file_size, downloaded_so_far, total_size, file_index, total_files):
        """
        Download a file from the lease URL with progress tracking
        Ajuste dynamiquement total_size si Content-Length diffère

        Returns:
            int: total_size ajusté (peut être différent de l'input)
        """
        import time

        response = requests.get(
            url,
            auth=(self.esxi_user, self.esxi_pass),
            verify=False,
            stream=True,
            timeout=(30, 600)  # (connect timeout, read timeout between chunks)
        )

        # Check response status - let caller handle errors
        if response.status_code != 200:
            response.raise_for_status()

        # Obtenir la taille réelle depuis Content-Length HTTP
        real_file_size = int(response.headers.get('Content-Length', 0))

        # Ajuster total_size si la taille réelle diffère
        if real_file_size > 0 and real_file_size != file_size:
            size_diff = real_file_size - file_size
            old_total = total_size
            total_size = max(0, total_size + size_diff)

            # Mettre à jour immédiatement dans la BDD
            self.export_job.total_bytes = total_size
            self.export_job.save()

            logger.info(f"[OVF-EXPORT] Ajustement: fichier {real_file_size / (1024*1024):.2f} MB (prévu {file_size / (1024*1024):.2f} MB)")
            logger.info(f"[OVF-EXPORT] Total ajusté: {old_total / (1024*1024):.2f} MB -> {total_size / (1024*1024):.2f} MB")

        # Utiliser la vraie taille pour ce fichier
        file_size = real_file_size if real_file_size > 0 else file_size

        downloaded = 0
        last_logged_mb = 0
        last_progress = self.export_job.progress_percentage
        start_time = time.time()
        last_speed_update = start_time

        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Calculer la progression
                    global_downloaded = downloaded_so_far + downloaded
                    downloaded_mb = global_downloaded / (1024 * 1024)

                    # Mettre à jour tous les 1 MB téléchargés
                    if downloaded_mb >= last_logged_mb + 1 or downloaded >= file_size:
                        # Vérifier si l'export a été annulé pendant le téléchargement
                        self.export_job.refresh_from_db()
                        if self.export_job.status == 'cancelled':
                            logger.info(f"[OVF-EXPORT] Export annulé pendant le téléchargement à {downloaded_mb:.1f} MB")
                            raise Exception("Export annulé par l'utilisateur")

                        # Calculer la vitesse de téléchargement (tous les 2 secondes)
                        current_time = time.time()
                        if current_time - last_speed_update >= 2.0:
                            elapsed_time = current_time - start_time
                            if elapsed_time > 0:
                                speed_mbps = global_downloaded / (1024 * 1024) / elapsed_time
                                self.export_job.download_speed_mbps = round(speed_mbps, 2)
                            last_speed_update = current_time

                        # Mettre à jour les bytes téléchargés
                        self.export_job.downloaded_bytes = global_downloaded

                        if total_size > 0:
                            # CAS 1: Règle de trois si taille totale connue
                            # 100% = total_size octets, x% = global_downloaded octets
                            download_percentage = (global_downloaded / total_size) * 100

                            # Progression: 10% (setup) + 75% (download) + 15% (finalization)
                            # Download représente 10-85% de la progression totale (75%)
                            global_progress = 10 + int((download_percentage / 100) * 75)
                            global_progress = min(global_progress, 85)

                            total_mb = total_size / (1024 * 1024)
                            logger.info(f"[OVF-EXPORT] Téléchargé: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({download_percentage:.1f}%) - Progression: {global_progress}%")
                        else:
                            # CAS 2: Progression basée sur le nombre de fichiers si taille inconnue
                            # Chaque fichier représente une part égale de 10% à 85% (75% total)
                            if total_files > 0:
                                # Progression du fichier actuel (0-100%)
                                if file_size > 0:
                                    file_progress = (downloaded / file_size) * 100
                                else:
                                    file_progress = 100 if downloaded > 0 else 0

                                # Progression globale: 10% + (fichiers complétés + progression fichier actuel) / total fichiers * 75%
                                files_completed = file_index
                                files_with_current = files_completed + (file_progress / 100)
                                global_progress = 10 + int((files_with_current / total_files) * 75)
                                global_progress = min(global_progress, 85)

                                logger.info(f"[OVF-EXPORT] Fichier {file_index + 1}/{total_files}: {downloaded_mb:.1f} MB ({file_progress:.1f}%) - Progression: {global_progress}%")
                            else:
                                global_progress = last_progress

                        # Sauvegarder seulement si la progression a changé
                        if global_progress != last_progress:
                            self.export_job.progress_percentage = global_progress
                            self.export_job.save()
                            last_progress = global_progress

                        last_logged_mb = int(downloaded_mb)

        # Retourner le total_size ajusté
        return total_size

    def _generate_ovf_descriptor(self, downloaded_files):
        """
        Generate OVF descriptor XML
        """
        # Basic OVF template
        ovf_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Envelope vmw:buildId="build-123456" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <References>
"""

        # Add file references
        for i, file_info in enumerate(downloaded_files):
            if file_info['filename'].endswith('.vmdk'):
                ovf_template += f'    <File ovf:href="{file_info["filename"]}" ovf:id="file{i}" ovf:size="{int(file_info["size_mb"] * 1024 * 1024)}"/>\n'

        ovf_template += """  </References>
  <VirtualSystem ovf:id="vm">
    <Info>A virtual machine</Info>
    <Name>""" + self.vm_name + """</Name>
  </VirtualSystem>
</Envelope>"""

        return ovf_template

    def _generate_manifest(self, export_dir, downloaded_files):
        """
        Generate .mf manifest file with SHA256 checksums
        """
        manifest_file = os.path.join(export_dir, f"{self.vm_name}.mf")

        logger.info(f"[OVF-EXPORT] Generating manifest with checksums...")

        with open(manifest_file, 'w') as mf:
            for file_info in downloaded_files:
                filename = file_info['filename']
                filepath = file_info['path']

                if os.path.exists(filepath):
                    logger.info(f"[OVF-EXPORT] Calculating SHA256 for {filename}...")
                    checksum = self._calculate_checksum(filepath)
                    mf.write(f"SHA256({filename})= {checksum}\n")
                    logger.info(f"[OVF-EXPORT] {filename}: {checksum[:16]}...")

        logger.info(f"[OVF-EXPORT] Manifest created: {manifest_file}")

    def _calculate_checksum(self, filepath):
        """
        Calculate SHA256 checksum of a file
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def execute_ovf_export(vm_obj, export_job):
    """
    Helper function to execute OVF export

    Args:
        vm_obj: pyVmomi VM object
        export_job: OVFExportJob instance

    Returns:
        bool: True if successful
    """
    service = OVFExportLeaseService(vm_obj, export_job)
    return service.export_ovf()
