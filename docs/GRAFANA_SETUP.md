# Guide de Configuration Grafana

## Vue d'ensemble

Ce guide explique comment configurer Grafana avec Prometheus pour visualiser les métriques de l'ESXi Backup Manager.

L'endpoint `/api/metrics` expose plus de 40 métriques couvrant :
- État des sauvegardes (jobs, succès/échecs, taux de réussite)
- Réplication de VMs (statut, événements de failover)
- Vérification de backups (SureBackup - taux de succès)
- Utilisation des datastores (capacité, espace libre)
- État des serveurs ESXi
- Snapshots et planifications

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  ESXi Backup    │      │   Prometheus    │      │    Grafana      │
│    Manager      │─────▶│   (Scraping)    │─────▶│  (Dashboards)   │
│  /api/metrics   │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## Prérequis

- Docker et Docker Compose (recommandé)
- Ou installation native de Prometheus et Grafana
- ESXi Backup Manager backend en cours d'exécution

---

## Installation rapide avec Docker Compose

### 1. Créer la configuration Docker Compose

Créez un fichier `docker-compose.monitoring.yml` à la racine du projet :

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: esxi-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: esxi-grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3001:3000"
    restart: unless-stopped
    networks:
      - monitoring
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
```

### 2. Créer la configuration Prometheus

Créez le fichier `monitoring/prometheus.yml` :

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'esxi_backup_manager'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
```

**Note :** Si vous êtes sur Linux, remplacez `host.docker.internal` par l'IP de votre machine hôte (ex: `192.168.1.100:8000`).

### 3. Créer la configuration de provisioning Grafana

Créez `monitoring/grafana/provisioning/datasources/prometheus.yml` :

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

### 4. Démarrer les services

```bash
# Créer les dossiers nécessaires
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards

# Démarrer Prometheus et Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.monitoring.yml logs -f
```

### 5. Accéder aux interfaces

- **Prometheus :** http://localhost:9090
- **Grafana :** http://localhost:3001 (admin/admin)

---

## Configuration manuelle

### Installation Prometheus (Ubuntu/Debian)

```bash
# Télécharger Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar xvfz prometheus-2.48.0.linux-amd64.tar.gz
cd prometheus-2.48.0.linux-amd64

# Créer la configuration
cat > prometheus.yml <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'esxi_backup_manager'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s
EOF

# Démarrer Prometheus
./prometheus --config.file=prometheus.yml
```

### Installation Grafana (Ubuntu/Debian)

```bash
# Ajouter le dépôt Grafana
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

# Installer Grafana
sudo apt-get update
sudo apt-get install grafana

# Démarrer Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

Grafana sera disponible sur http://localhost:3000 (admin/admin)

---

## Configuration de la source de données Grafana

1. **Connectez-vous à Grafana** (http://localhost:3001 ou :3000)
2. Allez dans **Configuration → Data Sources**
3. Cliquez sur **Add data source**
4. Sélectionnez **Prometheus**
5. Configurez :
   - **Name :** Prometheus
   - **URL :** `http://prometheus:9090` (Docker) ou `http://localhost:9090` (manuel)
   - **Access :** Server (Default)
6. Cliquez sur **Save & Test**

---

## Métriques disponibles

### Métriques de Backups

| Métrique | Description |
|----------|-------------|
| `esxi_backups_total` | Nombre total de jobs de backup |
| `esxi_backups_completed_total` | Nombre de backups complétés |
| `esxi_backups_failed_total` | Nombre de backups échoués |
| `esxi_backups_pending_total` | Nombre de backups en attente |
| `esxi_backups_running_total` | Nombre de backups en cours |
| `esxi_backups_success_rate` | Taux de réussite des backups (%) |

### Métriques de Réplication VM

| Métrique | Description |
|----------|-------------|
| `esxi_replications_total` | Nombre total de réplications configurées |
| `esxi_replications_active` | Réplications actives |
| `esxi_replications_paused` | Réplications en pause |
| `esxi_replications_error` | Réplications en erreur |
| `esxi_replications_syncing` | Réplications en synchronisation |
| `esxi_failover_events_total` | Nombre total d'événements de failover |
| `esxi_failover_events_completed` | Failovers complétés avec succès |
| `esxi_failover_events_failed` | Failovers échoués |

### Métriques SureBackup (Vérification)

| Métrique | Description |
|----------|-------------|
| `esxi_verifications_total` | Nombre total de vérifications |
| `esxi_verifications_passed` | Vérifications réussies |
| `esxi_verifications_failed` | Vérifications échouées |
| `esxi_verifications_pending` | Vérifications en attente |
| `esxi_verifications_running` | Vérifications en cours |
| `esxi_verifications_success_rate` | Taux de succès des vérifications (%) |

### Métriques Datastores

| Métrique | Description |
|----------|-------------|
| `esxi_datastore_used_percent{datastore="nom"}` | Pourcentage d'utilisation par datastore |
| `esxi_datastore_capacity_gb{datastore="nom"}` | Capacité totale en GB |
| `esxi_datastore_free_gb{datastore="nom"}` | Espace libre en GB |

### Métriques Serveurs ESXi

| Métrique | Description |
|----------|-------------|
| `esxi_servers_total` | Nombre de serveurs ESXi configurés |
| `esxi_servers_active` | Serveurs ESXi actifs |

### Métriques Snapshots

| Métrique | Description |
|----------|-------------|
| `esxi_snapshots_total` | Nombre total de snapshots |
| `esxi_snapshot_schedules_active` | Planifications de snapshots actives |

### Métriques Stockage

| Métrique | Description |
|----------|-------------|
| `esxi_storage_paths_total` | Chemins de stockage configurés |
| `esxi_storage_paths_active` | Chemins de stockage actifs |

---

## Exemples de requêtes PromQL

### Taux de réussite des backups

```promql
esxi_backups_success_rate
```

### Backups échoués dans les dernières 24h

```promql
increase(esxi_backups_failed_total[24h])
```

### Utilisation moyenne des datastores

```promql
avg(esxi_datastore_used_percent)
```

### Datastores avec plus de 80% d'utilisation

```promql
esxi_datastore_used_percent > 80
```

### Taux de failover automatique vs manuel

```promql
sum by (failover_type) (esxi_failover_events_total)
```

### Temps moyen de réplication

```promql
avg(esxi_replication_duration_seconds)
```

---

## Création d'un Dashboard

### Dashboard Exemple : Vue d'ensemble

1. Dans Grafana, cliquez sur **+ → Create Dashboard**
2. Cliquez sur **Add new panel**

#### Panel 1 : Taux de succès des backups (Gauge)

```promql
esxi_backups_success_rate
```

- Type : Gauge
- Min : 0
- Max : 100
- Thresholds :
  - Rouge : 0-80
  - Jaune : 80-95
  - Vert : 95-100

#### Panel 2 : Backups par statut (Pie Chart)

```promql
esxi_backups_completed_total
esxi_backups_failed_total
esxi_backups_pending_total
esxi_backups_running_total
```

- Type : Pie chart

#### Panel 3 : Utilisation des datastores (Bar gauge)

```promql
esxi_datastore_used_percent
```

- Type : Bar gauge
- Orientation : Horizontal
- Display mode : Gradient

#### Panel 4 : Backups au fil du temps (Time series)

```promql
increase(esxi_backups_completed_total[1h])
```

- Type : Time series
- Legend : {{job}}

#### Panel 5 : État des réplications (Stat)

```promql
esxi_replications_active
```

- Type : Stat
- Color mode : Background

#### Panel 6 : Vérifications SureBackup (Time series)

```promql
increase(esxi_verifications_passed[1d])
increase(esxi_verifications_failed[1d])
```

---

## Dashboard JSON pré-configuré

Créez un fichier `monitoring/grafana/dashboards/esxi-overview.json` :

```json
{
  "dashboard": {
    "title": "ESXi Backup Manager - Vue d'ensemble",
    "uid": "esxi-overview",
    "version": 1,
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Taux de succès des backups",
        "type": "gauge",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 8},
        "targets": [{
          "expr": "esxi_backups_success_rate",
          "refId": "A"
        }],
        "options": {
          "orientation": "auto",
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "fieldConfig": {
          "defaults": {
            "min": 0,
            "max": 100,
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 80, "color": "yellow"},
                {"value": 95, "color": "green"}
              ]
            },
            "unit": "percent"
          }
        }
      },
      {
        "id": 2,
        "title": "Backups par statut",
        "type": "piechart",
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 8},
        "targets": [
          {"expr": "esxi_backups_completed_total", "legendFormat": "Complétés", "refId": "A"},
          {"expr": "esxi_backups_failed_total", "legendFormat": "Échoués", "refId": "B"},
          {"expr": "esxi_backups_running_total", "legendFormat": "En cours", "refId": "C"},
          {"expr": "esxi_backups_pending_total", "legendFormat": "En attente", "refId": "D"}
        ]
      },
      {
        "id": 3,
        "title": "Utilisation des datastores",
        "type": "bargauge",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
        "targets": [{
          "expr": "esxi_datastore_used_percent",
          "refId": "A"
        }],
        "options": {
          "orientation": "horizontal",
          "displayMode": "gradient"
        },
        "fieldConfig": {
          "defaults": {
            "min": 0,
            "max": 100,
            "thresholds": {
              "mode": "percentage",
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 70, "color": "yellow"},
                {"value": 85, "color": "red"}
              ]
            },
            "unit": "percent"
          }
        }
      },
      {
        "id": 4,
        "title": "Réplications actives",
        "type": "stat",
        "gridPos": {"x": 0, "y": 8, "w": 4, "h": 4},
        "targets": [{
          "expr": "esxi_replications_active",
          "refId": "A"
        }],
        "options": {
          "colorMode": "background"
        },
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 1, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Vérifications SureBackup réussies",
        "type": "stat",
        "gridPos": {"x": 4, "y": 8, "w": 4, "h": 4},
        "targets": [{
          "expr": "esxi_verifications_passed",
          "refId": "A"
        }],
        "options": {
          "colorMode": "value"
        }
      },
      {
        "id": 6,
        "title": "Espace libre datastores (GB)",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 12, "w": 24, "h": 8},
        "targets": [{
          "expr": "esxi_datastore_free_gb",
          "refId": "A"
        }]
      }
    ],
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

Pour importer ce dashboard :
1. Copiez le JSON ci-dessus
2. Dans Grafana : **Dashboards → Import**
3. Collez le JSON et cliquez **Load**

---

## Alertes Grafana

### Exemple : Alerte sur échec de backup

1. Dans un panel, cliquez sur **Alert**
2. Configurez :
   - **Name :** Backups échoués
   - **Condition :** `WHEN last() OF query(A) IS ABOVE 5`
   - **Frequency :** Evaluate every 1m for 5m

### Exemple : Alerte sur utilisation datastore

1. Créez un panel avec la requête : `esxi_datastore_used_percent`
2. Ajoutez une alerte :
   - **Condition :** `WHEN max() OF query(A) IS ABOVE 85`
   - **Message :** "Datastore presque plein : {{$labels.datastore}} à {{$value}}%"

---

## Dépannage

### Prometheus ne récupère pas les métriques

1. Vérifiez que le backend Django est accessible :
   ```bash
   curl http://localhost:8000/api/metrics
   ```

2. Vérifiez les targets Prometheus :
   - Ouvrez http://localhost:9090/targets
   - Le job `esxi_backup_manager` doit être **UP**

3. Si le statut est DOWN :
   - Vérifiez la configuration dans `prometheus.yml`
   - Sur Linux avec Docker, utilisez l'IP de la machine hôte au lieu de `host.docker.internal`

### Grafana ne se connecte pas à Prometheus

1. Vérifiez la configuration de la data source
2. Testez la connectivité :
   ```bash
   # Depuis le container Grafana
   docker exec -it esxi-grafana curl http://prometheus:9090/api/v1/status/config
   ```

### Les métriques sont vides

1. Assurez-vous que des données existent dans Django :
   ```bash
   python manage.py shell
   >>> from backups.models import BackupJob
   >>> BackupJob.objects.count()
   ```

2. Forcez un scrape dans Prometheus :
   - Prometheus UI → Status → Targets
   - Cliquez sur le job et forcez un scrape manuel

---

## Optimisation et bonnes pratiques

### Rétention des données Prometheus

Modifiez `docker-compose.monitoring.yml` :

```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=90d'  # Conserver 90 jours
    - '--storage.tsdb.retention.size=50GB' # Max 50GB
```

### Sécurisation

1. **Authentification Prometheus :**
   Ajoutez un reverse proxy Nginx avec authentification basic

2. **Authentification Grafana :**
   ```yaml
   grafana:
     environment:
       - GF_SECURITY_ADMIN_PASSWORD=VotreMotDePasseSecurise
       - GF_AUTH_ANONYMOUS_ENABLED=false
   ```

3. **HTTPS :**
   Configurez un reverse proxy avec certificat SSL

### Performance

- Ajustez `scrape_interval` selon vos besoins (15s à 1m)
- Utilisez des recording rules pour pré-calculer les métriques complexes
- Activez la compression dans Prometheus

---

## Ressources

- [Documentation Prometheus](https://prometheus.io/docs/)
- [Documentation Grafana](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)

---

## Support

Pour toute question ou problème, consultez :
- La documentation principale du projet
- Les logs Prometheus : `docker logs esxi-prometheus`
- Les logs Grafana : `docker logs esxi-grafana`
