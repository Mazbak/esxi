"""
Configuration Celery pour le projet ESXi Backup Manager
"""
import os
from celery import Celery
from celery.schedules import crontab

# Définir le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sauvegarde.settings')

app = Celery('sauvegarde')

# Charger la configuration depuis les settings Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les applications Django
app.autodiscover_tasks()

# Configuration des tâches périodiques (Celery Beat)
app.conf.beat_schedule = {
    # Vérifier et exécuter les schedules de backup toutes les heures
    'check-and-execute-schedules': {
        'task': 'backups.tasks.check_and_execute_schedules',
        'schedule': crontab(minute=0),  # Toutes les heures à la minute 0
    },
    # Vérifier et exécuter les schedules de snapshot toutes les minutes
    'check-and-execute-snapshot-schedules': {
        'task': 'backups.tasks.check_and_execute_snapshot_schedules',
        'schedule': crontab(minute='*'),  # Toutes les minutes
    },
    # Vérifier et exécuter les réplications automatiques toutes les 5 minutes
    'check-and-execute-replications': {
        'task': 'backups.tasks.check_and_execute_replications',
        'schedule': crontab(minute='*/5'),  # Toutes les 5 minutes
    },
    # Vérifier et déclencher les auto-failovers toutes les minutes
    'check-and-trigger-auto-failovers': {
        'task': 'backups.tasks.check_and_trigger_auto_failovers',
        'schedule': crontab(minute='*'),  # Toutes les minutes pour réaction rapide
    },
    # Nettoyer les anciens backups tous les jours à 3h du matin
    'cleanup-old-backups': {
        'task': 'backups.tasks.cleanup_old_backups',
        'schedule': crontab(hour=3, minute=0),  # Tous les jours à 3h00
    },
    # Vérifier la santé des backups toutes les 6 heures
    'check-backup-health': {
        'task': 'backups.tasks.check_backup_health',
        'schedule': crontab(minute=0, hour='*/6'),  # Toutes les 6 heures
    },
}

# Configuration du timezone
app.conf.timezone = 'Europe/Paris'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
