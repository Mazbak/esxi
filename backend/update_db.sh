#!/bin/bash

# Script to update database with latest migrations

echo "=========================================="
echo "ESXi Backup Manager - Database Update"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "✓ Activating virtual environment..."
    source ../venv/bin/activate
else
    echo "⚠ No virtual environment found. Proceeding without activation..."
fi

echo ""
echo "1. Checking for pending migrations..."
python manage.py showmigrations backups

echo ""
echo "2. Applying migrations..."
python manage.py migrate backups

echo ""
echo "3. Verification - Current migrations status:"
python manage.py showmigrations backups

echo ""
echo "=========================================="
echo "✓ Database update complete!"
echo "=========================================="
echo ""
echo "You can now restart your Django server:"
echo "  python manage.py runserver"
echo ""
