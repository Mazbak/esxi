#!/bin/bash

# Script de diagnostic pour le backup ESXi

echo "=========================================="
echo "Diagnostic de sauvegarde ESXi"
echo "=========================================="
echo ""

# 1. Vérifier les logs Django
echo "1. Recherche des logs de backup récents..."
echo "   (dernières 50 lignes contenant [BACKUP] ou [EXPORT])"
echo ""

if [ -f "debug.log" ]; then
    echo "--- Logs trouvés dans debug.log ---"
    tail -100 debug.log | grep -E "\[BACKUP\]|\[EXPORT\]" | tail -50
    echo ""
elif [ -f "django.log" ]; then
    echo "--- Logs trouvés dans django.log ---"
    tail -100 django.log | grep -E "\[BACKUP\]|\[EXPORT\]" | tail -50
    echo ""
else
    echo "⚠ Aucun fichier de log trouvé (debug.log ou django.log)"
    echo ""
fi

# 2. Vérifier les dossiers de backup
echo "2. Recherche des dossiers de sauvegarde..."
echo ""

# Chemins possibles de backup
POSSIBLE_PATHS=(
    "/tmp/backups"
    "/var/backups/esxi"
    "./backups"
    "../backups"
    "/home/backups"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "✓ Dossier trouvé: $path"
        echo "  Contenu:"
        ls -lah "$path" 2>/dev/null | head -20
        echo ""
    fi
done

# 3. Vérifier les migrations
echo "3. État des migrations backups..."
python manage.py showmigrations backups 2>/dev/null || echo "⚠ manage.py non accessible"
echo ""

# 4. Instructions
echo "=========================================="
echo "Instructions de débogage:"
echo "=========================================="
echo ""
echo "1. Lancez votre serveur Django avec :"
echo "   python manage.py runserver"
echo ""
echo "2. Dans un autre terminal, surveillez les logs en temps réel :"
echo "   tail -f debug.log | grep -E '\[BACKUP\]|\[EXPORT\]'"
echo ""
echo "3. Créez une sauvegarde depuis l'interface web"
echo ""
echo "4. Observez les logs pour voir ce qui se passe"
echo ""
echo "5. Vérifiez le dossier de sauvegarde spécifié dans votre job"
echo ""
