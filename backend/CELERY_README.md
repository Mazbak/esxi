# Exécution Automatique des Snapshots - Celery

## Vue d'ensemble

Les snapshots sont exécutés automatiquement selon les planifications configurées grâce à **Celery** et **Celery Beat**.

## Architecture

- **Celery Worker** : Exécute les tâches en arrière-plan (création de snapshots, backups, etc.)
- **Celery Beat** : Scheduler qui vérifie les planifications et lance les tâches au bon moment
- **Redis** : Message broker pour la communication entre Django et Celery

## Fonctionnement de l'Exécution Automatique

### Fréquence de vérification

- **Snapshots** : Vérifiés **toutes les minutes** pour une précision maximale
- **Backups** : Vérifiés toutes les heures
- **Nettoyage** : Une fois par jour à 3h du matin
- **Vérification santé** : Toutes les 6 heures

### Processus d'exécution

1. **Celery Beat** vérifie toutes les minutes s'il y a des snapshots à exécuter
2. Pour chaque planification active :
   - Vérifie si `next_run <= maintenant`
   - Si oui, lance une tâche `execute_snapshot` via Celery Worker
   - Met à jour `last_run` et calcule le nouveau `next_run`
3. **Celery Worker** exécute la tâche :
   - Se connecte au serveur ESXi
   - Crée le snapshot
   - Applique la politique de rétention (supprime les anciens snapshots)

### Configuration des planifications

Dans l'interface web, vous pouvez configurer :
- **Fréquence** : Hourly, Daily, Weekly, Monthly
- **Heure** : 0-23 (pour daily/weekly/monthly)
- **Minute** : 0-59 (précision à la minute pour hourly)
- **Rétention** : Nombre de snapshots à conserver
- **Mémoire** : Inclure la RAM dans le snapshot

## Services Requis

### 1. Redis (Message Broker)

```bash
# Démarrer Redis
redis-server --daemonize yes

# Vérifier que Redis tourne
ps aux | grep redis-server

# Tester la connexion
redis-cli ping
# Devrait retourner: PONG
```

### 2. Celery Worker

```bash
# Démarrer le worker
cd /home/user/esxi/backend
celery -A sauvegarde worker --loglevel=info > /tmp/celery-worker.log 2>&1 &

# Vérifier les logs
tail -f /tmp/celery-worker.log
```

### 3. Celery Beat (Scheduler)

```bash
# Démarrer Beat
cd /home/user/esxi/backend
celery -A sauvegarde beat --loglevel=info > /tmp/celery-beat.log 2>&1 &

# Vérifier les logs
tail -f /tmp/celery-beat.log
```

## Vérification du Fonctionnement

### Vérifier les processus

```bash
# Tous les services
ps aux | grep -E "redis|celery" | grep -v grep

# Celery Worker uniquement
ps aux | grep "celery.*worker" | grep -v grep

# Celery Beat uniquement
ps aux | grep "celery.*beat" | grep -v grep
```

### Vérifier les logs

```bash
# Logs du worker (création de snapshots)
tail -f /tmp/celery-worker.log

# Logs du beat (planification)
tail -f /tmp/celery-beat.log

# Rechercher les exécutions de snapshots
grep "CELERY-SNAPSHOT" /tmp/celery-worker.log
```

### Tester une planification

1. Créez une planification dans l'interface web :
   - Fréquence : Hourly
   - Minute : (minute actuelle + 2)
   - Actif : Oui

2. Attendez 2-3 minutes

3. Vérifiez les logs :
```bash
tail -50 /tmp/celery-beat.log | grep "check-and-execute-snapshot"
tail -50 /tmp/celery-worker.log | grep "CELERY-SNAPSHOT"
```

## Arrêt des Services

```bash
# Arrêter Celery Worker
pkill -f "celery.*worker"

# Arrêter Celery Beat
pkill -f "celery.*beat"

# Arrêter Redis
redis-cli shutdown
# OU
pkill redis-server
```

## Redémarrage Complet

```bash
# Script de redémarrage complet
cd /home/user/esxi/backend

# Arrêter tout
pkill -f "celery.*worker"
pkill -f "celery.*beat"
redis-cli shutdown

# Démarrer Redis
redis-server --daemonize yes
sleep 2

# Démarrer Celery Worker
celery -A sauvegarde worker --loglevel=info > /tmp/celery-worker.log 2>&1 &
sleep 2

# Démarrer Celery Beat
celery -A sauvegarde beat --loglevel=info > /tmp/celery-beat.log 2>&1 &

echo "Services démarrés !"
```

## Troubleshooting

### Les snapshots ne s'exécutent pas

1. **Vérifier que tous les services tournent** :
   ```bash
   ps aux | grep -E "redis|celery" | grep -v grep
   ```

2. **Vérifier les logs d'erreur** :
   ```bash
   grep -i error /tmp/celery-worker.log
   grep -i error /tmp/celery-beat.log
   ```

3. **Vérifier la planification dans la base de données** :
   ```bash
   python3 manage.py shell
   >>> from backups.models import SnapshotSchedule
   >>> schedules = SnapshotSchedule.objects.filter(is_active=True)
   >>> for s in schedules:
   ...     print(f"{s.virtual_machine.name}: next_run={s.next_run}, last_run={s.last_run}")
   ```

4. **Vérifier la connexion Redis** :
   ```bash
   redis-cli ping
   redis-cli info clients
   ```

### Erreur "Connection refused" Redis

```bash
# Démarrer Redis
redis-server --daemonize yes

# Vérifier qu'il écoute sur le bon port
netstat -tuln | grep 6379
```

### Celery ne trouve pas les tâches

```bash
# Vérifier l'import du module Celery dans __init__.py
cat /home/user/esxi/backend/sauvegarde/__init__.py

# Devrait contenir:
# from .celery import app as celery_app
# __all__ = ('celery_app',)
```

## Configuration de Production

Pour un environnement de production, utilisez :

1. **Supervisor ou systemd** pour gérer les processus
2. **Flower** pour monitorer Celery
3. **Redis avec authentification**
4. **Logs rotatifs**

Exemple de service systemd pour Celery Worker :

```ini
[Unit]
Description=Celery Worker ESXi Backup Manager
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/home/user/esxi/backend
ExecStart=/usr/local/bin/celery -A sauvegarde worker --loglevel=info --logfile=/var/log/celery/worker.log --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring avec Flower

```bash
# Installer Flower
pip install flower

# Démarrer Flower
celery -A sauvegarde flower --port=5555

# Accéder à l'interface web
# http://localhost:5555
```

## Support

Pour toute question ou problème, consultez les logs et vérifiez que tous les services sont en cours d'exécution.
