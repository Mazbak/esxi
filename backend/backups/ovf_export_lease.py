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
            self.export_job.progress_percentage = 1
            self.export_job.downloaded_bytes = 0
            self.export_job.total_bytes = 0
            self.export_job.download_speed_mbps = 0
            self.export_job.save()

            # Create export directory
            export_dir = self.export_job.export_full_path
            os.makedirs(export_dir, exist_ok=True)
            logger.info(f"[OVF-EXPORT] Export directory: {export_dir}")

            # Step 1: Create export lease
            logger.info(f"[OVF-EXPORT] Step 1/4: Creating export lease...")
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
            self.export_job.progress_percentage = 1
            self.export_job.save()

            # Step 1.5: Estimate total export size using VM size ratio
            logger.info(f"[OVF-EXPORT] Step 1.5/4: Estimating export size...")

            # Get VM total size from storage usage
            vm_total_bytes = 0
            if hasattr(self.vm, 'storage') and self.vm.storage:
                if hasattr(self.vm.storage, 'perDatastoreUsage') and self.vm.storage.perDatastoreUsage:
                    for usage in self.vm.storage.perDatastoreUsage:
                        if hasattr(usage, 'committed'):
                            vm_total_bytes += usage.committed

            # Apply ratio to estimate OVF export size
            # Empirically determined: OVF exports are typically ~34.6% of total VM size
            # Based on real measurements: 2.83 GB export / 8.17 GB VM = 0.3464
            # This accounts for thin provisioning, compression, and exclusion of swap/logs
            OVF_EXPORT_RATIO = 0.346
            estimated_total_bytes = int(vm_total_bytes * OVF_EXPORT_RATIO)

            # Set estimated total bytes (this will be our baseline for progress)
            if estimated_total_bytes > 0:
                self.export_job.total_bytes = estimated_total_bytes
                self.export_job.save()

                vm_total_gb = vm_total_bytes / (1024**3)
                estimated_gb = estimated_total_bytes / (1024**3)
                logger.info(f"[OVF-EXPORT] VM total size: {vm_total_gb:.2f} GB")
                logger.info(f"[OVF-EXPORT] Estimated OVF size: {estimated_gb:.2f} GB (ratio: {OVF_EXPORT_RATIO:.0%})")
            else:
                logger.warning(f"[OVF-EXPORT] Could not estimate VM size, will use progressive calculation")

            # Step 2: Download files
            logger.info(f"[OVF-EXPORT] Step 2/4: Downloading VM files...")
            device_urls = lease.info.deviceUrl
            logger.info(f"[OVF-EXPORT] Found {len(device_urls)} files to download")

            downloaded_files = []
            downloaded_bytes = 0
            total_bytes = estimated_total_bytes  # Start with estimation

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

                dest_path = os.path.join(export_dir, filename)

                logger.info(f"[OVF-EXPORT] Downloading {filename}...")
                logger.info(f"[OVF-EXPORT] URL: {url}")

                try:
                    # Vérifier si l'export a été annulé avant de télécharger
                    self.export_job.refresh_from_db()
                    if self.export_job.status == 'cancelled':
                        logger.info(f"[OVF-EXPORT] Export annulé par l'utilisateur")
                        raise Exception("Export annulé par l'utilisateur")

                    # Télécharger le fichier (total_bytes sera ajusté dynamiquement)
                    downloaded_bytes, total_bytes = self._download_file(
                        url, dest_path, downloaded_bytes, total_bytes, i, len(device_urls)
                    )

                    # Get actual file size after download
                    actual_size_bytes = os.path.getsize(dest_path)
                    actual_size_mb = actual_size_bytes / (1024 * 1024)

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

            # Update progress to 90% (téléchargement terminé)
            self.export_job.progress_percentage = 90
            self.export_job.save()

            # Step 3: Generate OVF descriptor (if not already downloaded)
            logger.info(f"[OVF-EXPORT] Step 3/4: Generating OVF descriptor...")
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

            self.export_job.progress_percentage = 95
            self.export_job.save()

            # Step 4: Generate manifest
            logger.info(f"[OVF-EXPORT] Step 4/4: Generating manifest...")
            self._generate_manifest(export_dir, downloaded_files)
            self.export_job.progress_percentage = 98
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
            actual_total_bytes = int(total_size_mb * 1024 * 1024)
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

            # Step 5: Convert to OVA if requested
            if hasattr(self.export_job, 'export_format') and self.export_job.export_format == 'ova':
                logger.info(f"[OVF-EXPORT] Step 5/5: Converting to OVA format...")

                ova_path = self._convert_to_ova(export_dir, downloaded_files)
                if ova_path:
                    logger.info(f"[OVF-EXPORT] OVA created: {ova_path}")
                    # Update export path to point to OVA file
                    self.export_job.export_full_path = ova_path
                    ova_size_mb = os.path.getsize(ova_path) / (1024 * 1024)
                    self.export_job.export_size_mb = ova_size_mb
                    # Ensure progress stays at 100% after OVA conversion
                    self.export_job.progress_percentage = 100
                    self.export_job.status = 'completed'
                    self.export_job.save()
                    logger.info(f"[OVF-EXPORT] OVA size: {ova_size_mb:.2f} MB")

            # Validation: Compare estimated vs actual size
            if estimated_total_bytes > 0:
                actual_gb = actual_total_bytes / (1024**3)
                estimated_gb = estimated_total_bytes / (1024**3)
                accuracy_percentage = (actual_total_bytes / estimated_total_bytes) * 100
                difference_gb = (actual_total_bytes - estimated_total_bytes) / (1024**3)

                logger.info(f"[OVF-EXPORT] ----------------------------------------")
                logger.info(f"[OVF-EXPORT] SIZE ESTIMATION VALIDATION:")
                logger.info(f"[OVF-EXPORT]   Estimated: {estimated_gb:.2f} GB")
                logger.info(f"[OVF-EXPORT]   Actual:    {actual_gb:.2f} GB")
                logger.info(f"[OVF-EXPORT]   Accuracy:  {accuracy_percentage:.1f}%")
                logger.info(f"[OVF-EXPORT]   Difference: {difference_gb:+.2f} GB")

                # Log if estimation was significantly off (>20% difference)
                if abs(accuracy_percentage - 100) > 20:
                    logger.warning(f"[OVF-EXPORT] Estimation was off by more than 20% - consider adjusting OVF_EXPORT_RATIO")
                else:
                    logger.info(f"[OVF-EXPORT] Estimation within acceptable range")

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

    def _download_file(self, url, dest_path, downloaded_so_far, total_size, file_index, total_files):
        """
        Download a file from the lease URL with progress tracking
        Calcule total_size dynamiquement en ajoutant chaque fichier

        Returns:
            tuple: (downloaded_bytes, total_size) mis à jour
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

        # DEBUG: Logger tous les headers disponibles
        logger.info(f"[OVF-EXPORT] Response headers: {dict(response.headers)}")

        # Obtenir la taille réelle depuis Content-Length HTTP
        file_size = int(response.headers.get('Content-Length', 0))

        if file_size > 0:
            # Ajouter cette taille au total (construction progressive)
            total_size += file_size

            # Mettre à jour immédiatement dans la BDD
            self.export_job.total_bytes = total_size
            self.export_job.save()

            size_mb = file_size / (1024 * 1024)
            total_gb = total_size / (1024 * 1024 * 1024)
            logger.info(f"[OVF-EXPORT] Fichier: {size_mb:.2f} MB | Total: {total_gb:.2f} GB")
        else:
            logger.warning(f"[OVF-EXPORT] Taille fichier inconnue (Content-Length absent)")

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

                            # Progression: 1% (setup) + 89% (download) + 10% (finalization)
                            # Download représente 1-90% de la progression totale (89%)
                            global_progress = 1 + int((download_percentage / 100) * 89)
                            global_progress = min(global_progress, 90)

                            total_mb = total_size / (1024 * 1024)
                            logger.info(f"[OVF-EXPORT] Téléchargé: {downloaded_mb:.1f} MB / {total_mb:.1f} MB ({download_percentage:.1f}%) - Progression: {global_progress}%")
                        else:
                            # CAS 2: Progression basée sur le nombre de fichiers si taille inconnue
                            # Chaque fichier représente une part égale de 1% à 90% (89% total)
                            if total_files > 0:
                                # Progression du fichier actuel (0-100%)
                                if file_size > 0:
                                    file_progress = (downloaded / file_size) * 100
                                else:
                                    file_progress = 100 if downloaded > 0 else 0

                                # Progression globale: 1% + (fichiers complétés + progression fichier actuel) / total fichiers * 89%
                                files_completed = file_index
                                files_with_current = files_completed + (file_progress / 100)
                                global_progress = 1 + int((files_with_current / total_files) * 89)
                                global_progress = min(global_progress, 90)

                                logger.info(f"[OVF-EXPORT] Fichier {file_index + 1}/{total_files}: {downloaded_mb:.1f} MB ({file_progress:.1f}%) - Progression: {global_progress}%")
                            else:
                                global_progress = last_progress

                        # Sauvegarder seulement si la progression a changé
                        if global_progress != last_progress:
                            self.export_job.progress_percentage = global_progress
                            self.export_job.save()
                            last_progress = global_progress

                        last_logged_mb = int(downloaded_mb)

        # Retourner downloaded_bytes et total_size mis à jour
        return (downloaded_so_far + downloaded, total_size)

    def _generate_ovf_descriptor(self, downloaded_files):
        """
        Generate complete OVF descriptor XML with all required sections
        """
        # Get VM info for hardware specs
        memory_mb = getattr(self.vm.config.hardware, 'memoryMB', 1024)
        num_cpus = getattr(self.vm.config.hardware, 'numCPU', 1)
        guest_id = getattr(self.vm.config, 'guestId', 'otherGuest')

        # Detect VM hardware version for ESXi compatibility (5.0+)
        # ESXi 5.0=vmx-08, 5.1=vmx-09, 5.5=vmx-10, 6.0=vmx-11, 6.5=vmx-13, 6.7=vmx-14, 7.0=vmx-17+, 8.0=vmx-20
        vm_version = getattr(self.vm.config, 'version', 'vmx-08')
        if isinstance(vm_version, str) and 'vmx-' in vm_version:
            vmx_version = vm_version.split('vmx-')[1]
        else:
            vmx_version = '08'  # Safe fallback for ESXi 5.0+

        logger.info(f"[OVF-EXPORT] VM hardware version: vmx-{vmx_version} (ensures ESXi 5.0+ compatibility)")

        # Basic OVF template with proper XML structure
        ovf_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Envelope vmw:buildId="build-123456" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <References>
"""

        # Add file references
        file_refs = []
        disk_refs = []
        for i, file_info in enumerate(downloaded_files):
            if file_info['filename'].endswith('.vmdk'):
                size_bytes = int(file_info["size_mb"] * 1024 * 1024)
                ovf_template += f'    <File ovf:href="{file_info["filename"]}" ovf:id="file{i}" ovf:size="{size_bytes}"/>\n'
                file_refs.append((i, file_info["filename"], size_bytes))

        ovf_template += """  </References>
  <DiskSection>
    <Info>Virtual disk information</Info>
"""

        # Add disk entries
        for i, filename, size_bytes in file_refs:
            # Use a reasonable capacity (actual VMDK size * 2 for safety)
            capacity = size_bytes * 2
            ovf_template += f'    <Disk ovf:capacity="{capacity}" ovf:capacityAllocationUnits="byte" ovf:diskId="vmdisk{i}" ovf:fileRef="file{i}" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/>\n'

        ovf_template += """  </DiskSection>
  <NetworkSection>
    <Info>The list of logical networks</Info>
    <Network ovf:name="VM Network">
      <Description>The VM Network network</Description>
    </Network>
  </NetworkSection>
  <VirtualSystem ovf:id=\"""" + self.vm_name + """\">
    <Info>A virtual machine</Info>
    <Name>""" + self.vm_name + """</Name>
    <OperatingSystemSection ovf:id="0" vmw:osType=\"""" + guest_id + """\">
      <Info>The kind of installed guest operating system</Info>
    </OperatingSystemSection>
    <VirtualHardwareSection>
      <Info>Virtual hardware requirements</Info>
      <System>
        <vssd:ElementName>Virtual Hardware Family</vssd:ElementName>
        <vssd:InstanceID>0</vssd:InstanceID>
        <vssd:VirtualSystemType>vmx-""" + vmx_version + """</vssd:VirtualSystemType>
      </System>
      <Item>
        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
        <rasd:Description>Number of Virtual CPUs</rasd:Description>
        <rasd:ElementName>""" + str(num_cpus) + """ virtual CPU(s)</rasd:ElementName>
        <rasd:InstanceID>1</rasd:InstanceID>
        <rasd:ResourceType>3</rasd:ResourceType>
        <rasd:VirtualQuantity>""" + str(num_cpus) + """</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
        <rasd:Description>Memory Size</rasd:Description>
        <rasd:ElementName>""" + str(memory_mb) + """MB of memory</rasd:ElementName>
        <rasd:InstanceID>2</rasd:InstanceID>
        <rasd:ResourceType>4</rasd:ResourceType>
        <rasd:VirtualQuantity>""" + str(memory_mb) + """</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:Address>0</rasd:Address>
        <rasd:Description>SCSI Controller</rasd:Description>
        <rasd:ElementName>SCSI Controller 0</rasd:ElementName>
        <rasd:InstanceID>3</rasd:InstanceID>
        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
        <rasd:ResourceType>6</rasd:ResourceType>
      </Item>
"""

        # Add disks
        for i, filename, size_bytes in file_refs:
            item_id = 4 + i  # Start at 4 (SCSI controller is 3)
            ovf_template += f"""      <Item>
        <rasd:AddressOnParent>{i}</rasd:AddressOnParent>
        <rasd:ElementName>Disk {i+1}</rasd:ElementName>
        <rasd:HostResource>ovf:/disk/vmdisk{i}</rasd:HostResource>
        <rasd:InstanceID>{item_id}</rasd:InstanceID>
        <rasd:Parent>3</rasd:Parent>
        <rasd:ResourceType>17</rasd:ResourceType>
      </Item>
"""

        ovf_template += """    </VirtualHardwareSection>
  </VirtualSystem>
</Envelope>"""

        logger.info(f"[OVF-EXPORT] Generated complete OVF descriptor with {len(file_refs)} disk(s), {num_cpus} CPU(s), {memory_mb}MB RAM")

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

    def _convert_to_ova(self, export_dir, downloaded_files):
        """
        Convert OVF directory to OVA (tar archive)

        Args:
            export_dir: Directory containing OVF files
            downloaded_files: List of downloaded file info

        Returns:
            str: Path to created OVA file, or None if failed
        """
        import tarfile
        import shutil

        try:
            # OVA file path (same location as export_dir, but with .ova extension)
            parent_dir = os.path.dirname(export_dir)
            ova_filename = f"{self.vm_name}.ova"
            ova_path = os.path.join(parent_dir, ova_filename)

            logger.info(f"[OVF-EXPORT] Creating OVA archive: {ova_path}")

            # Create tar archive
            # Note: OVA is a tar file (not tar.gz) according to OVF specification
            with tarfile.open(ova_path, 'w') as tar:
                # OVA spec requires files in specific order:
                # 1. .ovf file first
                # 2. .mf file (if exists)
                # 3. all other files (.vmdk, etc.)

                # Sort files: .ovf first, then .mf, then others
                ovf_files = [f for f in downloaded_files if f['filename'].endswith('.ovf')]
                mf_files = [f for f in downloaded_files if f['filename'].endswith('.mf')]
                other_files = [f for f in downloaded_files if not f['filename'].endswith(('.ovf', '.mf'))]

                # Also check for .mf file in export_dir (generated separately)
                mf_path = os.path.join(export_dir, f"{self.vm_name}.mf")
                if os.path.exists(mf_path) and not any(f['filename'].endswith('.mf') for f in mf_files):
                    mf_files.append({
                        'filename': f"{self.vm_name}.mf",
                        'path': mf_path,
                        'size_mb': os.path.getsize(mf_path) / (1024 * 1024)
                    })

                ordered_files = ovf_files + mf_files + other_files

                # Add files to tar in correct order
                for file_info in ordered_files:
                    filepath = file_info['path']
                    filename = file_info['filename']

                    if os.path.exists(filepath):
                        logger.info(f"[OVF-EXPORT] Adding to OVA: {filename}")
                        # Add file to tar with just the filename (no directory structure)
                        tar.add(filepath, arcname=filename)
                    else:
                        logger.warning(f"[OVF-EXPORT] File not found, skipping: {filepath}")

            # Verify OVA was created
            if os.path.exists(ova_path):
                ova_size_mb = os.path.getsize(ova_path) / (1024 * 1024)
                logger.info(f"[OVF-EXPORT] OVA created successfully: {ova_size_mb:.2f} MB")

                # Clean up OVF directory
                logger.info(f"[OVF-EXPORT] Cleaning up OVF directory...")
                shutil.rmtree(export_dir)
                logger.info(f"[OVF-EXPORT] ✓ OVF directory removed, keeping only OVA file")

                return ova_path
            else:
                logger.error(f"[OVF-EXPORT] OVA file was not created")
                return None

        except Exception as e:
            logger.error(f"[OVF-EXPORT] Error converting to OVA: {e}", exc_info=True)
            return None


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
