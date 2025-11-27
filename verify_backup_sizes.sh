#!/bin/bash
# Script pour vérifier la taille réelle des backups

echo "=== Vérification des tailles de backup ==="
echo ""

# 1. Vérifier dans la base de données
echo "1. Tailles enregistrées dans la base de données:"
echo "------------------------------------------------"
cd /home/user/esxi/backend

# Activer virtualenv si nécessaire
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Query avec Django
python3 manage.py shell << 'PYTHON_EOF'
from backups.models import VMBackupJob
import os

jobs = VMBackupJob.objects.filter(status='completed').order_by('-completed_at')[:5]

print("\nDerniers backups complétés:")
print("-" * 100)
for job in jobs:
    downloaded_gb = job.downloaded_bytes / (1024**3) if job.downloaded_bytes else 0
    saved_gb = job.backup_size_mb / 1024 if job.backup_size_mb else 0

    print(f"\nBackup ID: {job.id}")
    print(f"  VM: {job.virtual_machine.name}")
    print(f"  Type: {job.backup_type}")
    print(f"  Complété le: {job.completed_at}")
    print(f"  Chemin: {job.backup_full_path}")
    print(f"  Téléchargé (HTTP): {downloaded_gb:.2f} GB")
    print(f"  Taille sur disque: {saved_gb:.2f} GB")

    if downloaded_gb > 0 and saved_gb > 0:
        diff_pct = ((downloaded_gb - saved_gb) / downloaded_gb) * 100
        print(f"  Différence: {diff_pct:.1f}%")

    # Vérifier la taille réelle sur le filesystem
    if job.backup_full_path and os.path.exists(job.backup_full_path):
        print(f"  ✓ Dossier existe")
        # Calculer taille réelle
        total = 0
        for root, dirs, files in os.walk(job.backup_full_path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        real_gb = total / (1024**3)
        print(f"  Taille réelle filesystem: {real_gb:.2f} GB")
    else:
        print(f"  ✗ Dossier introuvable")

print("\n")
PYTHON_EOF

echo ""
echo "2. Vérification manuelle des dossiers de backup:"
echo "------------------------------------------------"

# Trouver les dossiers de backup récents
find /tmp /var /home -type d -name "*full_*" -o -name "*incremental_*" 2>/dev/null | while read dir; do
    if [ -d "$dir" ]; then
        echo ""
        echo "Dossier: $dir"
        # Taille apparente (taille logique)
        apparent_size=$(du -sb "$dir" 2>/dev/null | cut -f1)
        # Taille réelle (espace occupé sur disque)
        real_size=$(du -s "$dir" 2>/dev/null | awk '{print $1 * 1024}')

        if [ -n "$apparent_size" ] && [ -n "$real_size" ]; then
            apparent_gb=$(echo "scale=2; $apparent_size / 1024 / 1024 / 1024" | bc)
            real_gb=$(echo "scale=2; $real_size / 1024 / 1024 / 1024" | bc)

            echo "  Taille apparente: ${apparent_gb} GB"
            echo "  Espace disque utilisé: ${real_gb} GB"

            # Lister les fichiers VMDK
            find "$dir" -name "*.vmdk" -o -name "*-flat.vmdk" -o -name "*-delta.vmdk" | while read vmdk; do
                vmdk_size=$(stat -c%s "$vmdk" 2>/dev/null)
                vmdk_gb=$(echo "scale=2; $vmdk_size / 1024 / 1024 / 1024" | bc)
                echo "    $(basename "$vmdk"): ${vmdk_gb} GB"
            done
        fi
    fi
done

echo ""
echo "=== Fin de la vérification ==="
