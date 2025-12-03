# Exécution Automatique des Snapshots sur Windows

## ⚠️ Important

Pour que les snapshots s'exécutent automatiquement, vous devez lancer **3 services** :

1. **Redis** (message broker)
2. **Celery Worker** (exécute les tâches)
3. **Celery Beat** (planificateur)

## Installation des dépendances

### 1. Installer Redis sur Windows

**Option A - Via MSI Installer (Recommandé)**
```powershell
# Télécharger depuis:
# https://github.com/microsoftarchive/redis/releases

# Installer Redis-x64-3.2.100.msi
# Le service démarrera automatiquement après l'installation
```

**Option B - Via Chocolatey**
```powershell
choco install redis-64
```

**Option C - Via WSL (Windows Subsystem for Linux)**
```powershell
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### 2. Vérifier que Redis fonctionne

```powershell
# Dans PowerShell/CMD
redis-cli ping
# Devrait retourner: PONG
```

## Démarrer les services Celery

### Ouvrez 3 fenêtres PowerShell/CMD

#### Fenêtre 1 - Django Server
```powershell
cd C:\Users\AZUMA\Desktop\esxi\backend
.\venv\Scripts\activate
python manage.py runserver
```

#### Fenêtre 2 - Celery Worker
```powershell
cd C:\Users\AZUMA\Desktop\esxi\backend
.\venv\Scripts\activate
celery -A sauvegarde worker --loglevel=info --pool=solo
```
> **Note**: Sur Windows, utilisez `--pool=solo` ou `--pool=gevent`

#### Fenêtre 3 - Celery Beat
```powershell
cd C:\Users\AZUMA\Desktop\esxi\backend
.\venv\Scripts\activate
celery -A sauvegarde beat --loglevel=info
```

## Vérification

Après avoir lancé les 3 services, vous devriez voir dans la fenêtre Celery Beat :

```
[2025-12-03 09:00:00,000: INFO] beat: Starting...
[2025-12-03 09:00:00,000: INFO] Scheduler: Sending due task check-and-execute-snapshot-schedules
```

Et dans la fenêtre Celery Worker :

```
[2025-12-03 09:00:00,000: INFO] Received task: backups.tasks.check_and_execute_snapshot_schedules
[2025-12-03 09:00:00,000: INFO] [CELERY-SNAPSHOT-SCHEDULER] === VÉRIFICATION DES SNAPSHOT SCHEDULES ===
```

## Fréquence d'exécution

Les snapshots sont vérifiés **toutes les minutes** pour une précision maximale.

## Logs en temps réel

Pour voir les logs détaillés des snapshots :

```powershell
# Dans la fenêtre Celery Worker, recherchez:
grep "CELERY-SNAPSHOT"
```

## Problèmes courants

### Erreur "ConnectionError: Error 10061"
- Redis n'est pas démarré
- Solution : Démarrer Redis (voir ci-dessus)

### Erreur "ImportError: cannot import name 'celery'"
- Venv pas activé
- Solution : `.\venv\Scripts\activate`

### Snapshots ne s'exécutent pas
1. Vérifier que les 3 services tournent (Django, Celery Worker, Celery Beat)
2. Vérifier que la planification est **active** (is_active=True)
3. Vérifier `next_run` dans la base de données :
   ```python
   python manage.py shell
   >>> from backups.models import SnapshotSchedule
   >>> for s in SnapshotSchedule.objects.filter(is_active=True):
   ...     print(f"{s.virtual_machine.name}: next={s.next_run}")
   ```

### Celery Worker se ferme immédiatement
- Sur Windows, il faut utiliser `--pool=solo` ou installer `gevent`
- Solution :
  ```powershell
  pip install gevent
  celery -A sauvegarde worker --pool=gevent --loglevel=info
  ```

## Alternative : Un seul terminal avec start.bat

Créez un fichier `start_celery.bat` :

```batch
@echo off
echo Demarrage des services Celery...

start "Redis" redis-server
timeout /t 2

start "Django" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python manage.py runserver"
timeout /t 3

start "Celery Worker" cmd /k "cd /d %~dp0 && venv\Scripts\activate && celery -A sauvegarde worker --pool=solo --loglevel=info"
timeout /t 2

start "Celery Beat" cmd /k "cd /d %~dp0 && venv\Scripts\activate && celery -A sauvegarde beat --loglevel=info"

echo Tous les services sont demarres!
pause
```

Puis lancez simplement :
```powershell
.\start_celery.bat
```

## Arrêter les services

```powershell
# Dans chaque fenêtre, appuyez sur Ctrl+C

# Ou tuez tous les processus :
taskkill /F /IM python.exe
taskkill /F /IM redis-server.exe
```

## Production : Installer comme service Windows

Pour que Celery démarre automatiquement au démarrage de Windows :

1. Installer NSSM (Non-Sucking Service Manager)
2. Créer des services Windows pour Celery Worker et Beat

```powershell
# Télécharger NSSM depuis: https://nssm.cc/download
nssm install CeleryWorker "C:\Users\AZUMA\Desktop\esxi\backend\venv\Scripts\celery.exe" "-A sauvegarde worker --pool=solo"
nssm install CeleryBeat "C:\Users\AZUMA\Desktop\esxi\backend\venv\Scripts\celery.exe" "-A sauvegarde beat"
nssm install RedisServer "C:\Program Files\Redis\redis-server.exe"

# Démarrer les services
nssm start RedisServer
nssm start CeleryWorker
nssm start CeleryBeat
```

## Logs et monitoring

Les logs sont affichés dans la console. Pour les sauvegarder :

```powershell
# Worker
celery -A sauvegarde worker --pool=solo --loglevel=info > worker.log 2>&1

# Beat
celery -A sauvegarde beat --loglevel=info > beat.log 2>&1
```

## Support

Si vous rencontrez des problèmes, vérifiez dans cet ordre :
1. Redis est démarré : `redis-cli ping`
2. Django tourne : http://localhost:8000/api/
3. Celery Worker tourne : Vérifier la fenêtre worker
4. Celery Beat tourne : Vérifier la fenêtre beat
5. Planification active : Vérifier dans l'interface web
