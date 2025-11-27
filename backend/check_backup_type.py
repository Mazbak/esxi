import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/user/esxi/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sauvegarde.settings')
django.setup()

from backups.models import VMBackupJob, OVFExportJob

# Chercher backups en cours
vm_backup = VMBackupJob.objects.filter(status='running').first()
ovf_export = OVFExportJob.objects.filter(status='running').first()

print("\n=== BACKUPS EN COURS ===\n")

if vm_backup:
    gb = vm_backup.downloaded_bytes / (1024**3)
    print(f"⚠️  VMBackupJob en cours (MAUVAISE METHODE)")
    print(f"   VM: {vm_backup.virtual_machine.name}")
    print(f"   Téléchargé: {gb:.2f} GB")
    print(f"   Progression: {vm_backup.progress_percentage}%")
    print(f"   ⚠️  Télécharge le VMDK complet (inefficace)")
    print(f"\n   RECOMMANDATION: Annuler et utiliser OVFExportJob\n")

if ovf_export:
    gb = ovf_export.downloaded_bytes / (1024**3)
    total_gb = ovf_export.total_bytes / (1024**3) if ovf_export.total_bytes else 0
    print(f"✅ OVFExportJob en cours (BONNE METHODE)")
    print(f"   VM: {ovf_export.virtual_machine.name}")
    print(f"   Téléchargé: {gb:.2f} GB / {total_gb:.2f} GB")
    print(f"   Progression: {ovf_export.progress_percentage}%")
    print(f"   ✅ Utilise HttpNfcLease (thin-provisioning OK)\n")

if not vm_backup and not ovf_export:
    print("Aucun backup en cours\n")

# Statistiques globales
print("=== STATISTIQUES BACKUPS ===\n")
total_vm = VMBackupJob.objects.count()
total_ovf = OVFExportJob.objects.count()
print(f"Total VMBackupJob (ancienne méthode): {total_vm}")
print(f"Total OVFExportJob (bonne méthode): {total_ovf}\n")

# Comparer les tailles moyennes
from django.db.models import Avg
avg_vm = VMBackupJob.objects.filter(status='completed').aggregate(Avg('backup_size_mb'))
avg_ovf = OVFExportJob.objects.filter(status='completed').aggregate(Avg('export_size_mb'))

if avg_vm['backup_size_mb__avg']:
    print(f"Taille moyenne VMBackupJob: {avg_vm['backup_size_mb__avg']/1024:.2f} GB")
if avg_ovf['export_size_mb__avg']:
    print(f"Taille moyenne OVFExportJob: {avg_ovf['export_size_mb__avg']/1024:.2f} GB")
