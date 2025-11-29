"""
OVF Export Service for VMware ESXi
Uses proven snapshot + VMDK download approach (same as VMBackupService)
Then generates OVF descriptor and manifest
"""
import os
import logging
import hashlib
from datetime import datetime
from django.utils import timezone

# Import the proven VMBackupService
from backups.vm_backup_service import VMBackupService

logger = logging.getLogger(__name__)


class OVFExportService:
    """
    Service for exporting VMs to OVF format
    Uses VMBackupService (proven to work) + OVF descriptor generation
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

    def export_ovf(self):
        """
        Export VM to OVF format
        Uses the proven VMBackupService approach with base disk detection

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            logger.info(f"[OVF-EXPORT] ========================================")
            logger.info(f"[OVF-EXPORT] Starting OVF export for {self.vm_name}")
            logger.info(f"[OVF-EXPORT] Using snapshot + base VMDK download method")
            logger.info(f"[OVF-EXPORT] ========================================")

            self.export_job.status = 'running'
            self.export_job.started_at = timezone.now()
            self.export_job.progress_percentage = 5
            self.export_job.save()

            # Check if VM has existing snapshots - warn if true
            if self.vm.snapshot:
                logger.warning(f"[OVF-EXPORT] ⚠️ VM has existing snapshots - will export base disks")
                logger.warning(f"[OVF-EXPORT] For best results, consolidate snapshots before export")

            # Create export directory
            os.makedirs(self.export_job.export_full_path, exist_ok=True)
            logger.info(f"[OVF-EXPORT] Export directory: {self.export_job.export_full_path}")

            # Step 1: Create snapshot for consistency (10% progress)
            logger.info(f"[OVF-EXPORT] Step 1/5: Creating consistency snapshot...")
            snapshot_name = f"ovf_export_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            snapshot_task = self.vm.CreateSnapshot_Task(
                name=snapshot_name,
                description="OVF Export Snapshot",
                memory=False,
                quiesce=False
            )
            from pyVim.task import WaitForTask
            WaitForTask(snapshot_task)
            logger.info(f"[OVF-EXPORT] Snapshot created: {snapshot_name}")
            self.export_job.progress_percentage = 10
            self.export_job.save()

            # Step 2: Download base VMDK files (10-75% progress)
            logger.info(f"[OVF-EXPORT] Step 2/5: Downloading base VMDK files...")
            vmdk_files = self._download_base_vmdks()
            self.export_job.progress_percentage = 75
            self.export_job.save()

            logger.info(f"[OVF-EXPORT] Downloaded {len(vmdk_files)} VMDK files")
            for vmdk in vmdk_files:
                logger.info(f"[OVF-EXPORT]   - {vmdk['filename']}: {vmdk.get('size_mb', 0):.2f} MB")

            # Step 3: Save VM configuration (80% progress)
            logger.info(f"[OVF-EXPORT] Step 3/5: Saving VM configuration...")
            self._save_vm_config()
            self.export_job.progress_percentage = 80
            self.export_job.save()

            # Step 4: Remove snapshot (85% progress)
            logger.info(f"[OVF-EXPORT] Step 4/5: Removing snapshot...")
            self._remove_snapshot(snapshot_name)
            self.export_job.progress_percentage = 85
            self.export_job.save()

            # Step 5: Generate OVF descriptor and manifest (90-95% progress)
            logger.info(f"[OVF-EXPORT] Step 5/6: Generating OVF descriptor and manifest...")
            self._generate_ovf_files(vmdk_files)
            self.export_job.progress_percentage = 90
            self.export_job.save()

            # Step 6: Create OVA archive if export_format is 'ova' (95-100% progress)
            final_path = self.export_job.export_full_path
            if self.export_job.export_format == 'ova':
                logger.info(f"[OVF-EXPORT] Step 6/6: Creating OVA archive...")
                final_path = self._create_ova_archive()
                # Update export_full_path to point to the OVA file
                self.export_job.export_full_path = final_path
                self.export_job.progress_percentage = 95
                self.export_job.save()
            else:
                logger.info(f"[OVF-EXPORT] Step 6/6: Skipping OVA creation (format: {self.export_job.export_format})")

            # Calculate total size
            total_size_mb = self._calculate_directory_size(final_path)
            self.export_job.export_size_mb = total_size_mb
            self.export_job.progress_percentage = 100
            self.export_job.status = 'completed'
            self.export_job.completed_at = timezone.now()
            self.export_job.save()

            logger.info(f"[OVF-EXPORT] ========================================")
            logger.info(f"[OVF-EXPORT] ✅ Export completed successfully!")
            logger.info(f"[OVF-EXPORT] Format: {self.export_job.export_format.upper()}")
            logger.info(f"[OVF-EXPORT] Total size: {total_size_mb:.2f} MB")
            logger.info(f"[OVF-EXPORT] Location: {final_path}")
            logger.info(f"[OVF-EXPORT] ========================================")

            return True

        except Exception as e:
            logger.error(f"[OVF-EXPORT] ========================================")
            logger.error(f"[OVF-EXPORT] ❌ Export failed: {e}")
            logger.error(f"[OVF-EXPORT] ========================================")
            logger.exception(e)

            self.export_job.status = 'failed'
            self.export_job.error_message = str(e)
            self.export_job.completed_at = timezone.now()
            self.export_job.save()

            # Try to clean up snapshot if it exists
            try:
                if 'snapshot_name' in locals():
                    self._remove_snapshot(snapshot_name)
            except:
                pass

            return False

    def _download_base_vmdks(self):
        """
        Download base VMDK files (not snapshot deltas)

        Returns:
            list: List of downloaded VMDK file info dicts
        """
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        vmdk_files = []
        export_dir = self.export_job.export_full_path

        # Get ESXi credentials
        esxi_server = self.export_job.virtual_machine.server
        esxi_host = esxi_server.hostname
        esxi_user = esxi_server.username
        esxi_pass = esxi_server.password

        # Get datacenter
        dc = self.vm.runtime.host.parent
        while not hasattr(dc, 'vmFolder'):
            dc = dc.parent

        # Iterate through virtual disks
        for device in self.vm.config.hardware.device:
            if hasattr(device, 'backing') and hasattr(device.backing, 'fileName'):
                vmdk_path = device.backing.fileName  # Format: [datastore] path/file.vmdk

                logger.info(f"[OVF-EXPORT] Found disk backing: {vmdk_path}")

                # Extract datastore and file path
                datastore_name = vmdk_path.split(']')[0].strip('[')
                file_path = vmdk_path.split(']')[1].strip().lstrip('/')

                # Get base disk name (remove snapshot suffixes like -000001)
                # For example: "VM-000001.vmdk" -> "VM.vmdk"
                original_path = file_path
                if '-' in file_path and any(file_path.endswith(f'-{i:06d}.vmdk') for i in range(1000)):
                    # This is a snapshot delta, find the base disk
                    base_name = file_path.rsplit('-', 1)[0] + '.vmdk'
                    logger.info(f"[OVF-EXPORT] Detected snapshot delta {file_path}, using base disk: {base_name}")
                    file_path = base_name

                # VMware disk structure for OVF export:
                # - VM.vmdk = descriptor file (text, ~1KB) - referenced by OVF
                # - VM-flat.vmdk = actual data file (binary, GB/TB) - referenced by descriptor
                # For OVF, we need BOTH files!

                descriptor_path = file_path
                base_name_no_ext = file_path[:-5] if file_path.endswith('.vmdk') else file_path
                flat_file_path = f"{base_name_no_ext}-flat.vmdk"

                # Check if flat file exists
                flat_exists = False
                flat_vmdk_url = f"https://{esxi_host}/folder/{flat_file_path}?dcPath={dc.name}&dsName={datastore_name}"

                logger.info(f"[OVF-EXPORT] Checking for flat disk: {flat_file_path}")
                try:
                    test_response = requests.head(
                        flat_vmdk_url,
                        auth=(esxi_user, esxi_pass),
                        verify=False,
                        timeout=(10, 30)  # (connect timeout, read timeout)
                    )
                    flat_exists = (test_response.status_code == 200)
                    if flat_exists:
                        logger.info(f"[OVF-EXPORT] ✓ Flat disk found: {flat_file_path}")
                    else:
                        logger.warning(f"[OVF-EXPORT] Flat disk not found (status {test_response.status_code})")
                except Exception as e:
                    logger.warning(f"[OVF-EXPORT] Could not check for flat disk: {e}")

                # Download descriptor file (always needed for OVF)
                logger.info(f"[OVF-EXPORT] Downloading descriptor: {descriptor_path}")
                desc_url = f"https://{esxi_host}/folder/{descriptor_path}?dcPath={dc.name}&dsName={datastore_name}"
                desc_dest = os.path.join(export_dir, os.path.basename(descriptor_path))

                self._download_file(desc_url, desc_dest, esxi_user, esxi_pass)
                logger.info(f"[OVF-EXPORT] ✓ Descriptor downloaded")

                # Download flat file if it exists (contains actual data)
                total_vmdk_size = 0
                if flat_exists:
                    logger.info(f"[OVF-EXPORT] Downloading flat disk: {flat_file_path}")
                    flat_dest = os.path.join(export_dir, os.path.basename(flat_file_path))

                    try:
                        response = requests.get(
                            flat_vmdk_url,
                            auth=(esxi_user, esxi_pass),
                            verify=False,
                            stream=True,
                            timeout=(30, 600)  # (connect timeout, read timeout between chunks)
                        )
                        response.raise_for_status()

                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        last_logged_progress = 0

                        logger.info(f"[OVF-EXPORT] Flat file size: {total_size / (1024*1024):.2f} MB")

                        with open(flat_dest, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192 * 1024):  # 8MB chunks
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)

                                    # Update progress every 5%
                                    if total_size > 0:
                                        download_progress = (downloaded / total_size) * 100
                                        if download_progress >= last_logged_progress + 5 or downloaded >= total_size:
                                            # Calculate global progress: 10% (snapshot) + download progress (10-75%)
                                            # Download represents 65% of total progress (from 10% to 75%)
                                            global_progress = 10 + int((download_progress / 100) * 65)

                                            # Update database with real-time progress
                                            self.export_job.progress_percentage = global_progress
                                            self.export_job.save()

                                            logger.info(f"[OVF-EXPORT] Download: {download_progress:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB) - Global: {global_progress}%")
                                            last_logged_progress = int(download_progress / 5) * 5

                        flat_size_mb = os.path.getsize(flat_dest) / (1024 * 1024)
                        logger.info(f"[OVF-EXPORT] ✓ Flat disk downloaded: {flat_size_mb:.2f} MB")
                        total_vmdk_size = flat_size_mb

                    except Exception as e:
                        logger.error(f"[OVF-EXPORT] Error downloading flat file: {e}")
                        raise
                else:
                    logger.warning(f"[OVF-EXPORT] No flat file found - disk might be thin provisioned or use different format")
                    total_vmdk_size = os.path.getsize(desc_dest) / (1024 * 1024)

                vmdk_info = {
                    'filename': descriptor_path,
                    'size_gb': device.capacityInKB / (1024 * 1024),
                    'size_mb': total_vmdk_size,
                    'dest_path': desc_dest,
                    'datastore': datastore_name
                }
                vmdk_files.append(vmdk_info)
                logger.info(f"[OVF-EXPORT] ✓ Disk export complete: {os.path.basename(descriptor_path)} ({total_vmdk_size:.2f} MB)")

        return vmdk_files

    def _download_file(self, url, dest_path, username, password):
        """Download a single file (for small files like descriptors)"""
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        response = requests.get(
            url,
            auth=(username, password),
            verify=False,
            timeout=(30, 60)  # (connect timeout, read timeout)
        )
        response.raise_for_status()

        with open(dest_path, 'wb') as f:
            f.write(response.content)

        return dest_path

    def _save_vm_config(self):
        """Save VM configuration to JSON"""
        import json
        config_file = os.path.join(self.export_job.export_full_path, 'vm_config.json')

        vm_config = {
            'name': self.vm.name,
            'guest_os': self.vm.config.guestId,
            'guest_full_name': self.vm.config.guestFullName,
            'num_cpu': self.vm.config.hardware.numCPU,
            'memory_mb': self.vm.config.hardware.memoryMB,
            'version': self.vm.config.version
        }

        with open(config_file, 'w') as f:
            json.dump(vm_config, f, indent=2)

        logger.info(f"[OVF-EXPORT] VM configuration saved: {config_file}")

    def _remove_snapshot(self, snapshot_name):
        """Remove snapshot by name"""
        from pyVim.task import WaitForTask

        def find_snapshot(snapshots, name):
            for snapshot in snapshots:
                if snapshot.name == name:
                    return snapshot.snapshot
                if hasattr(snapshot, 'childSnapshotList') and snapshot.childSnapshotList:
                    result = find_snapshot(snapshot.childSnapshotList, name)
                    if result:
                        return result
            return None

        if self.vm.snapshot:
            snapshot_obj = find_snapshot(self.vm.snapshot.rootSnapshotList, snapshot_name)
            if snapshot_obj:
                logger.info(f"[OVF-EXPORT] Removing snapshot: {snapshot_name}")
                remove_task = snapshot_obj.RemoveSnapshot_Task(removeChildren=False)
                WaitForTask(remove_task)
                logger.info(f"[OVF-EXPORT] Snapshot removed successfully")
            else:
                logger.warning(f"[OVF-EXPORT] Snapshot {snapshot_name} not found")
        else:
            logger.warning(f"[OVF-EXPORT] No snapshots found on VM")

    def _generate_ovf_files(self, vmdk_files):
        """
        Generate OVF descriptor and manifest files

        Args:
            vmdk_files: List of VMDK file info dicts
        """
        export_dir = self.export_job.export_full_path
        ovf_file = os.path.join(export_dir, f"{self.vm_name}.ovf")
        mf_file = os.path.join(export_dir, f"{self.vm_name}.mf")

        # Generate OVF descriptor
        logger.info(f"[OVF-EXPORT] Generating OVF descriptor...")
        self._generate_ovf_descriptor(ovf_file, vmdk_files)

        # Generate manifest with checksums
        logger.info(f"[OVF-EXPORT] Generating manifest with checksums...")
        self._generate_manifest(export_dir, mf_file)

    def _generate_ovf_descriptor(self, ovf_file, vmdk_files):
        """Generate OVF descriptor XML"""
        try:
            vm_config = self.vm.config

            # Generate References section with VMDK files
            references = ""
            disks = ""
            disk_items = ""

            for idx, vmdk in enumerate(vmdk_files):
                # Get the actual filename (basename)
                vmdk_filename = os.path.basename(vmdk['filename'])
                file_path = os.path.join(os.path.dirname(ovf_file), vmdk_filename)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                capacity = int(vmdk.get('size_gb', 10) * 1024 * 1024 * 1024)  # Convert GB to bytes

                file_id = f"file{idx}"
                disk_id = f"vmdisk{idx}"

                references += f'    <File ovf:href="{vmdk_filename}" ovf:id="{file_id}" ovf:size="{file_size}" />\n'
                disks += f'    <Disk ovf:capacity="{capacity}" ovf:capacityAllocationUnits="byte" ovf:diskId="{disk_id}" ovf:fileRef="{file_id}" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized" />\n'

                disk_items += f"""      <Item>
        <rasd:AddressOnParent>{idx}</rasd:AddressOnParent>
        <rasd:ElementName>Hard Disk {idx + 1}</rasd:ElementName>
        <rasd:HostResource>ovf:/disk/{disk_id}</rasd:HostResource>
        <rasd:InstanceID>{10 + idx}</rasd:InstanceID>
        <rasd:Parent>3</rasd:Parent>
        <rasd:ResourceType>17</rasd:ResourceType>
      </Item>
"""

            # Create OVF content
            ovf_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Envelope vmw:buildId="build-{vm_config.version}" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <References>
{references}  </References>
  <DiskSection>
    <Info>Virtual disk information</Info>
{disks}  </DiskSection>
  <NetworkSection>
    <Info>Logical networks</Info>
    <Network ovf:name="VM Network">
      <Description>VM Network</Description>
    </Network>
  </NetworkSection>
  <VirtualSystem ovf:id="{self.vm_name}">
    <Info>A virtual machine: {self.vm_name}</Info>
    <Name>{self.vm_name}</Name>
    <OperatingSystemSection ovf:id="{vm_config.guestId}" vmw:osType="{vm_config.guestId}">
      <Info>Guest Operating System</Info>
      <Description>{vm_config.guestFullName}</Description>
    </OperatingSystemSection>
    <VirtualHardwareSection>
      <Info>Virtual hardware requirements</Info>
      <System>
        <vssd:ElementName>Virtual Hardware Family</vssd:ElementName>
        <vssd:InstanceID>0</vssd:InstanceID>
        <vssd:VirtualSystemIdentifier>{self.vm_name}</vssd:VirtualSystemIdentifier>
        <vssd:VirtualSystemType>vmx-{vm_config.version.split("-")[1] if "-" in str(vm_config.version) else "07"}</vssd:VirtualSystemType>
      </System>
      <Item>
        <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
        <rasd:Description>Number of Virtual CPUs</rasd:Description>
        <rasd:ElementName>{vm_config.hardware.numCPU} virtual CPU(s)</rasd:ElementName>
        <rasd:InstanceID>1</rasd:InstanceID>
        <rasd:ResourceType>3</rasd:ResourceType>
        <rasd:VirtualQuantity>{vm_config.hardware.numCPU}</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
        <rasd:Description>Memory Size</rasd:Description>
        <rasd:ElementName>{vm_config.hardware.memoryMB}MB of memory</rasd:ElementName>
        <rasd:InstanceID>2</rasd:InstanceID>
        <rasd:ResourceType>4</rasd:ResourceType>
        <rasd:VirtualQuantity>{vm_config.hardware.memoryMB}</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:Address>0</rasd:Address>
        <rasd:Description>SCSI Controller</rasd:Description>
        <rasd:ElementName>SCSI Controller 0</rasd:ElementName>
        <rasd:InstanceID>3</rasd:InstanceID>
        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
        <rasd:ResourceType>6</rasd:ResourceType>
      </Item>
{disk_items}    </VirtualHardwareSection>
  </VirtualSystem>
</Envelope>
"""

            # Write OVF file
            with open(ovf_file, 'w', encoding='utf-8') as f:
                f.write(ovf_content)

            logger.info(f"[OVF-EXPORT] ✓ OVF descriptor created: {ovf_file}")

        except Exception as e:
            logger.error(f"[OVF-EXPORT] Error generating OVF descriptor: {e}")
            raise

    def _generate_manifest(self, export_dir, mf_file):
        """Generate manifest file with SHA256 checksums"""
        try:
            with open(mf_file, 'w') as mf:
                # Calculate checksum for OVF and VMDK files
                for filename in sorted(os.listdir(export_dir)):
                    if filename.endswith(('.ovf', '.vmdk')):
                        file_path = os.path.join(export_dir, filename)
                        sha256_hash = hashlib.sha256()

                        logger.info(f"[OVF-EXPORT] Calculating SHA256 for {filename}...")

                        with open(file_path, 'rb') as f:
                            for chunk in iter(lambda: f.read(8192 * 1024), b""):
                                sha256_hash.update(chunk)

                        checksum = sha256_hash.hexdigest()
                        mf.write(f"SHA256({filename})= {checksum}\n")
                        logger.info(f"[OVF-EXPORT] ✓ {filename}: {checksum[:16]}...")

            logger.info(f"[OVF-EXPORT] ✓ Manifest created: {mf_file}")

        except Exception as e:
            logger.error(f"[OVF-EXPORT] Error generating manifest: {e}")
            # Don't fail the export if manifest generation fails
            pass

    def _calculate_directory_size(self, directory):
        """Calculate total directory size in MB"""
        # Si c'est un fichier (OVA), retourner sa taille directement
        if os.path.isfile(directory):
            return os.path.getsize(directory) / (1024 * 1024)

        # Sinon calculer la taille du répertoire
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)

        return total_size / (1024 * 1024)

    def _create_ova_archive(self):
        """
        Create OVA archive from OVF files
        OVA is a TAR archive containing the OVF descriptor, manifest, and VMDK files

        Returns:
            str: Path to the created OVA file
        """
        import tarfile

        export_dir = self.export_job.export_full_path
        ova_filename = f"{self.vm_name}.ova"
        ova_path = os.path.join(os.path.dirname(export_dir), ova_filename)

        logger.info(f"[OVF-EXPORT] Creating OVA archive: {ova_path}")

        try:
            # OVA format specification requires specific file order:
            # 1. .ovf file MUST be first
            # 2. .mf file (manifest) should be second
            # 3. .vmdk files follow

            files_to_archive = []
            ovf_file = None
            mf_file = None
            vmdk_files = []
            other_files = []

            # Scan directory and categorize files
            for filename in os.listdir(export_dir):
                file_path = os.path.join(export_dir, filename)
                if os.path.isfile(file_path):
                    if filename.endswith('.ovf'):
                        ovf_file = filename
                    elif filename.endswith('.mf'):
                        mf_file = filename
                    elif filename.endswith('.vmdk'):
                        vmdk_files.append(filename)
                    elif not filename.endswith('.json'):  # Skip vm_config.json
                        other_files.append(filename)

            # Build ordered file list (OVF spec requirement)
            if ovf_file:
                files_to_archive.append(ovf_file)
            if mf_file:
                files_to_archive.append(mf_file)
            files_to_archive.extend(sorted(vmdk_files))
            files_to_archive.extend(sorted(other_files))

            logger.info(f"[OVF-EXPORT] Files to archive ({len(files_to_archive)}):")
            for f in files_to_archive:
                logger.info(f"[OVF-EXPORT]   - {f}")

            # Create TAR archive
            with tarfile.open(ova_path, 'w') as tar:
                for filename in files_to_archive:
                    file_path = os.path.join(export_dir, filename)
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    logger.info(f"[OVF-EXPORT] Adding to archive: {filename} ({file_size_mb:.2f} MB)")

                    # Add file to tar with just the filename (no directory structure)
                    tar.add(file_path, arcname=filename)

            ova_size_mb = os.path.getsize(ova_path) / (1024 * 1024)
            logger.info(f"[OVF-EXPORT] ✓ OVA archive created: {ova_size_mb:.2f} MB")

            # Clean up the OVF directory (keep only the OVA file)
            logger.info(f"[OVF-EXPORT] Cleaning up OVF directory...")
            import shutil
            shutil.rmtree(export_dir)
            logger.info(f"[OVF-EXPORT] ✓ OVF directory removed")

            return ova_path

        except Exception as e:
            logger.error(f"[OVF-EXPORT] Error creating OVA archive: {e}")
            raise
