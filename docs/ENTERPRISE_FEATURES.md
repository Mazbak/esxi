# Fonctionnalités Enterprise - ESXi Backup Manager

## Vue d'ensemble

Ce document décrit les trois fonctionnalités enterprise récemment implémentées dans ESXi Backup Manager :

1. **Dashboard Grafana avancé** - Monitoring en temps réel via Prometheus
2. **Réplication VM + Failover** - Haute disponibilité avec basculement automatique/manuel
3. **Vérification Automatique Backups (SureBackup)** - Validation de la restaurabilité des sauvegardes

Ces fonctionnalités apportent des capacités de niveau professionnel comparables à des solutions comme Veeam Backup & Replication.

---

## Table des matières

- [1. Dashboard Grafana](#1-dashboard-grafana)
- [2. Réplication VM + Failover](#2-réplication-vm--failover)
- [3. SureBackup (Vérification Backups)](#3-surebackup-vérification-backups)
- [4. API Endpoints](#4-api-endpoints)
- [5. Modèles de données](#5-modèles-de-données)
- [6. Guide de déploiement](#6-guide-de-déploiement)
- [7. Cas d'usage](#7-cas-dusage)

---

## 1. Dashboard Grafana

### Description

Un endpoint Prometheus expose plus de 40 métriques pour une visualisation avancée dans Grafana.

### Endpoint Metrics

**URL :** `GET /api/metrics`

**Format :** Prometheus text format (text/plain; version=0.0.4)

**Authentification :** Aucune (pour permettre le scraping Prometheus)

### Catégories de métriques

#### Backups
- `esxi_backups_total` - Nombre total de jobs
- `esxi_backups_completed_total` - Jobs complétés
- `esxi_backups_failed_total` - Jobs échoués
- `esxi_backups_pending_total` - Jobs en attente
- `esxi_backups_running_total` - Jobs en cours
- `esxi_backups_success_rate` - Taux de réussite (%)

#### Réplication
- `esxi_replications_total` - Réplications totales
- `esxi_replications_active` - Réplications actives
- `esxi_replications_paused` - Réplications en pause
- `esxi_replications_error` - Réplications en erreur
- `esxi_replications_syncing` - Synchronisations en cours
- `esxi_failover_events_total` - Événements de failover
- `esxi_failover_events_completed` - Failovers réussis
- `esxi_failover_events_failed` - Failovers échoués

#### SureBackup
- `esxi_verifications_total` - Vérifications totales
- `esxi_verifications_passed` - Vérifications réussies
- `esxi_verifications_failed` - Vérifications échouées
- `esxi_verifications_pending` - En attente
- `esxi_verifications_running` - En cours
- `esxi_verifications_success_rate` - Taux de succès (%)

#### Datastores (avec labels)
- `esxi_datastore_used_percent{datastore="name"}` - Utilisation (%)
- `esxi_datastore_capacity_gb{datastore="name"}` - Capacité totale
- `esxi_datastore_free_gb{datastore="name"}` - Espace libre

#### Infrastructure
- `esxi_servers_total` - Serveurs totaux
- `esxi_servers_active` - Serveurs actifs
- `esxi_snapshots_total` - Snapshots totaux
- `esxi_snapshot_schedules_active` - Planifications actives
- `esxi_storage_paths_total` - Chemins de stockage
- `esxi_storage_paths_active` - Chemins actifs

### Configuration

Voir le guide détaillé : [GRAFANA_SETUP.md](./GRAFANA_SETUP.md)

**Démarrage rapide :**

```bash
# Lancer Prometheus + Grafana avec Docker
docker-compose -f docker-compose.monitoring.yml up -d

# Accéder à Grafana
open http://localhost:3001
# Identifiants: admin / admin
```

### Dashboards pré-configurés

Un dashboard complet est fourni dans `monitoring/grafana/dashboards/esxi-overview.json` incluant :

- Gauge du taux de succès des backups
- Pie chart des statuts de backup
- Bar gauge de l'utilisation des datastores
- Stats des réplications actives
- Graphiques temporels des tendances
- Alertes configurables

---

## 2. Réplication VM + Failover

### Description

Système de réplication continue des VMs entre serveurs ESXi avec capacité de failover automatique ou manuel en cas de panne.

### Architecture

```
┌─────────────────────┐                      ┌─────────────────────┐
│  Serveur ESXi       │                      │  Serveur ESXi       │
│  Source             │   Réplication        │  Destination        │
│                     │───────────────────▶  │                     │
│  VM Production      │   (15min par défaut) │  VM Répliquée       │
│  (Active)           │                      │  (Standby)          │
└─────────────────────┘                      └─────────────────────┘
           │                                            │
           │                                            │
           ▼                                            ▼
    Détection panne                            Failover déclenché
           │                                            │
           └────────────────────────────────────────────┘
                        Bascule automatique
```

### Modèle de données : VMReplication

```python
class VMReplication:
    name: str                               # Nom de la réplication
    virtual_machine: FK(VirtualMachine)     # VM source
    source_server: FK(ESXiServer)           # Serveur source
    destination_server: FK(ESXiServer)      # Serveur destination
    destination_datastore: str              # Datastore cible
    replication_interval_minutes: int       # Intervalle (défaut: 15)
    status: str                             # active/paused/error/syncing
    failover_mode: str                      # manual/automatic/test
    auto_failover_threshold_minutes: int    # Délai avant failover auto
    last_replication_at: datetime           # Dernière réplication
    last_replication_duration_seconds: int  # Durée dernière réplication
    total_replicated_size_mb: float         # Taille totale répliquée
    is_active: bool                         # Réplication active
```

**Contraintes :**
- `unique_together`: (virtual_machine, destination_server) - Une VM ne peut avoir qu'une seule réplication vers un serveur donné

### Modes de failover

#### 1. Manuel (`manual`)
- Failover déclenché uniquement par l'utilisateur
- Contrôle total sur le moment du basculement
- Recommandé pour les environnements critiques

#### 2. Automatique (`automatic`)
- Détection automatique de panne du serveur source
- Basculement automatique après le délai de seuil
- Surveillance continue de l'état du serveur source
- Idéal pour la haute disponibilité 24/7

#### 3. Test (`test`)
- Mode de test sans impact sur la production
- Valide le processus de failover sans arrêter la VM source
- Utile pour les exercices de DR (Disaster Recovery)

### API Endpoints

#### Lister les réplications
```http
GET /api/vm-replications/
```

**Réponse :**
```json
[
  {
    "id": 1,
    "name": "Réplication VM Web Server",
    "virtual_machine": 5,
    "vm_name": "web-server-01",
    "source_server": 1,
    "source_server_name": "esxi-prod-01",
    "destination_server": 2,
    "destination_server_name": "esxi-prod-02",
    "destination_datastore": "datastore-replica",
    "replication_interval_minutes": 15,
    "status": "active",
    "status_display": "Active",
    "failover_mode": "automatic",
    "auto_failover_threshold_minutes": 5,
    "last_replication_at": "2025-11-29T10:30:00Z",
    "last_replication_duration_seconds": 120,
    "total_replicated_size_mb": 51200.0,
    "is_active": true,
    "created_at": "2025-11-20T08:00:00Z",
    "updated_at": "2025-11-29T10:30:00Z"
  }
]
```

#### Créer une réplication
```http
POST /api/vm-replications/
Content-Type: application/json

{
  "name": "Réplication DB Server",
  "virtual_machine": 12,
  "source_server": 1,
  "destination_server": 3,
  "destination_datastore": "datastore-dr",
  "replication_interval_minutes": 30,
  "failover_mode": "manual",
  "auto_failover_threshold_minutes": 10,
  "is_active": true
}
```

#### Démarrer la réplication
```http
POST /api/vm-replications/{id}/start_replication/
```

**Réponse :**
```json
{
  "status": "started",
  "message": "Réplication démarrée avec succès"
}
```

#### Mettre en pause
```http
POST /api/vm-replications/{id}/pause/
```

#### Reprendre
```http
POST /api/vm-replications/{id}/resume/
```

#### Déclencher un failover manuel
```http
POST /api/vm-replications/{id}/trigger_failover/
Content-Type: application/json

{
  "reason": "Maintenance planifiée du serveur source",
  "test_mode": false
}
```

**Réponse :**
```json
{
  "id": 42,
  "replication": 1,
  "failover_type": "manual",
  "status": "initiated",
  "reason": "Maintenance planifiée du serveur source",
  "source_vm_powered_off": false,
  "destination_vm_powered_on": false,
  "triggered_by": 1,
  "started_at": "2025-11-29T14:00:00Z",
  "completed_at": null
}
```

### Modèle de données : FailoverEvent

```python
class FailoverEvent:
    replication: FK(VMReplication)          # Réplication concernée
    failover_type: str                      # manual/automatic/test
    status: str                             # initiated/in_progress/completed/failed/rolled_back
    reason: str                             # Raison du failover
    source_vm_powered_off: bool             # VM source arrêtée
    destination_vm_powered_on: bool         # VM destination démarrée
    error_message: str                      # Message d'erreur
    triggered_by: FK(User)                  # Utilisateur (si manuel)
    started_at: datetime
    completed_at: datetime
```

### Processus de failover

1. **Initiation** - Création de l'événement FailoverEvent
2. **Validation** - Vérification de l'état des serveurs et de la VM
3. **Arrêt source** - Extinction de la VM sur le serveur source (si pas en mode test)
4. **Démarrage destination** - Démarrage de la VM répliquée
5. **Vérification** - Validation du démarrage
6. **Finalisation** - Mise à jour du statut

### Surveillance et alertes

**Métriques Grafana :**
- Nombre de réplications par statut
- Durée moyenne de réplication
- Taille totale répliquée
- Événements de failover (succès/échecs)
- Temps de basculement

**Alertes recommandées :**
- Réplication en erreur depuis plus de 1h
- Failover automatique échoué
- Écart de réplication > seuil défini

---

## 3. SureBackup (Vérification Backups)

### Description

Système de vérification automatique de la restaurabilité des backups en les montant et en démarrant les VMs dans un environnement isolé.

**Inspiré de Veeam SureBackup**, cette fonctionnalité garantit que vos backups sont effectivement restaurables en cas de besoin.

### Principe de fonctionnement

```
┌─────────────────┐
│   Backup OVF    │
│   ou VMDK       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Environnement de test isolé            │
│                                         │
│  1. Restaurer VM depuis backup          │
│  2. Démarrer VM (test boot)             │
│  3. Vérifier ping réseau (optionnel)    │
│  4. Vérifier services (optionnel)       │
│  5. Logger résultats                    │
│  6. Nettoyer (supprimer VM de test)     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Rapport de     │
│  vérification   │
│  (passé/échoué) │
└─────────────────┘
```

### Modèle de données : BackupVerification

```python
class BackupVerification:
    # Source de backup (l'un ou l'autre, pas les deux)
    ovf_export: FK(OVFExportJob) | None
    vm_backup: FK(VMBackupJob) | None

    esxi_server: FK(ESXiServer)             # Serveur pour le test
    test_type: str                          # boot/boot_ping/boot_ping_services/full
    status: str                             # pending/running/passed/failed/warning

    # Résultats des tests
    vm_restored: bool                       # VM restaurée avec succès
    vm_booted: bool                         # VM a démarré
    boot_time_seconds: int                  # Temps de démarrage
    ping_successful: bool                   # Ping réseau réussi
    services_checked: JSONField             # Services vérifiés {"ssh": true, "http": false}

    # Configuration du test
    test_network: str                       # Réseau isolé (défaut: "VM Network Isolated")
    test_datastore: str                     # Datastore pour le test
    vm_cleanup_done: bool                   # VM de test supprimée

    # Logs et diagnostic
    detailed_log: str                       # Log détaillé
    error_message: str                      # Message d'erreur
    total_duration_seconds: int             # Durée totale

    started_at: datetime
    completed_at: datetime
    created_at: datetime
```

**Validation :** Une vérification doit avoir soit `ovf_export` soit `vm_backup`, mais pas les deux.

### Types de tests

#### 1. Boot (`boot`)
- Test le plus rapide
- Vérifie uniquement que la VM démarre
- Durée estimée : 2-5 minutes

#### 2. Boot + Ping (`boot_ping`)
- Vérifie le démarrage + connectivité réseau
- Recommandé pour la plupart des VMs
- Durée estimée : 5-10 minutes

#### 3. Boot + Ping + Services (`boot_ping_services`)
- Vérifie démarrage, réseau et services applicatifs
- Services personnalisables (SSH, HTTP, HTTPS, SQL, etc.)
- Durée estimée : 10-20 minutes

#### 4. Full (`full`)
- Test complet personnalisé
- Scripts de validation spécifiques
- Durée variable selon les tests

### Modèle de données : BackupVerificationSchedule

```python
class BackupVerificationSchedule:
    name: str                               # Nom de la planification
    virtual_machine: FK(VirtualMachine) | None  # VM spécifique (null = toutes)
    esxi_server: FK(ESXiServer)             # Serveur pour les tests
    frequency: str                          # daily/weekly/monthly/after_backup
    test_type: str                          # boot/boot_ping/boot_ping_services/full
    is_active: bool                         # Planification active
    last_run_at: datetime
    next_run_at: datetime
```

### API Endpoints

#### Lister les vérifications
```http
GET /api/backup-verifications/
```

**Filtres disponibles :**
- `?status=passed` - Vérifications réussies
- `?ovf_export=5` - Pour un export OVF spécifique
- `?vm_backup=12` - Pour un backup VMDK spécifique
- `?test_type=boot_ping` - Par type de test

**Réponse :**
```json
[
  {
    "id": 1,
    "backup_name": "web-server-01",
    "ovf_export": 42,
    "vm_backup": null,
    "esxi_server": 1,
    "test_type": "boot_ping",
    "status": "passed",
    "vm_restored": true,
    "vm_booted": true,
    "boot_time_seconds": 180,
    "ping_successful": true,
    "services_checked": {"ssh": true, "http": true},
    "test_network": "VM Network Isolated",
    "test_datastore": "datastore-test",
    "vm_cleanup_done": true,
    "detailed_log": "2025-11-29 10:00:00 - Démarrage restauration...\n...",
    "total_duration_seconds": 420,
    "started_at": "2025-11-29T10:00:00Z",
    "completed_at": "2025-11-29T10:07:00Z",
    "created_at": "2025-11-29T09:55:00Z"
  }
]
```

#### Créer une vérification manuelle
```http
POST /api/backup-verifications/
Content-Type: application/json

{
  "ovf_export": 42,
  "esxi_server": 1,
  "test_type": "boot_ping",
  "test_network": "VM Network Isolated",
  "test_datastore": "datastore-test"
}
```

#### Obtenir les statistiques
```http
GET /api/backup-verifications/statistics/
```

**Réponse :**
```json
{
  "total_verifications": 150,
  "passed": 142,
  "failed": 8,
  "success_rate": 94.67,
  "average_duration_seconds": 380,
  "last_verification": "2025-11-29T10:07:00Z",
  "by_test_type": {
    "boot": 50,
    "boot_ping": 80,
    "boot_ping_services": 20
  }
}
```

#### Planifications de vérification

##### Lister les planifications
```http
GET /api/verification-schedules/
```

##### Créer une planification
```http
POST /api/verification-schedules/
Content-Type: application/json

{
  "name": "Vérification hebdomadaire DB",
  "virtual_machine": 12,
  "esxi_server": 1,
  "frequency": "weekly",
  "test_type": "boot_ping_services",
  "is_active": true
}
```

**Fréquences disponibles :**
- `daily` - Quotidienne
- `weekly` - Hebdomadaire
- `monthly` - Mensuelle
- `after_backup` - Après chaque backup (recommandé)

### Réseau isolé

⚠️ **Important :** Les vérifications doivent se faire dans un réseau isolé pour éviter :
- Conflits d'adresses IP
- Connexions involontaires à des systèmes de production
- Impact sur les services réels

**Configuration réseau recommandée :**
```
VM Network Isolated
├── VLAN dédié (ex: VLAN 999)
├── Pas de routage vers production
├── DHCP isolé (optionnel)
└── Internet bloqué (optionnel)
```

### Services vérifiables

Le champ `services_checked` peut contenir différents tests :

```json
{
  "ssh": true,           // Port 22 accessible
  "http": true,          // Port 80 accessible
  "https": false,        // Port 443 non accessible
  "mysql": true,         // Port 3306 accessible
  "postgresql": true,    // Port 5432 accessible
  "rdp": false,          // Port 3389 non accessible
  "custom_8080": true    // Port custom
}
```

### Cas d'usage

#### Cas 1 : Vérification après chaque backup
```python
# Configuration automatique
{
  "name": "Auto-vérification VMs critiques",
  "virtual_machine": null,  # Toutes les VMs
  "frequency": "after_backup",
  "test_type": "boot_ping",
  "is_active": true
}
```

#### Cas 2 : Test mensuel complet
```python
{
  "name": "Test DR mensuel",
  "frequency": "monthly",
  "test_type": "boot_ping_services",
  "is_active": true
}
```

#### Cas 3 : Vérification rapide quotidienne
```python
{
  "name": "Vérification quotidienne rapide",
  "frequency": "daily",
  "test_type": "boot",  # Test le plus rapide
  "is_active": true
}
```

### Métriques Grafana

- Taux de succès des vérifications
- Durée moyenne des tests
- Nombre de vérifications par type
- Backups non vérifiés depuis X jours
- Tendance des échecs de vérification

---

## 4. API Endpoints

### Résumé des endpoints disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/metrics` | GET | Métriques Prometheus |
| `/api/vm-replications/` | GET, POST | Gérer réplications |
| `/api/vm-replications/{id}/` | GET, PUT, PATCH, DELETE | Détail réplication |
| `/api/vm-replications/{id}/start_replication/` | POST | Démarrer réplication |
| `/api/vm-replications/{id}/pause/` | POST | Mettre en pause |
| `/api/vm-replications/{id}/resume/` | POST | Reprendre |
| `/api/vm-replications/{id}/trigger_failover/` | POST | Déclencher failover |
| `/api/failover-events/` | GET | Historique failovers |
| `/api/failover-events/{id}/` | GET | Détail failover |
| `/api/backup-verifications/` | GET, POST | Gérer vérifications |
| `/api/backup-verifications/{id}/` | GET, PUT, PATCH, DELETE | Détail vérification |
| `/api/backup-verifications/statistics/` | GET | Statistiques |
| `/api/verification-schedules/` | GET, POST | Gérer planifications |
| `/api/verification-schedules/{id}/` | GET, PUT, PATCH, DELETE | Détail planification |

### Authentification

Tous les endpoints (sauf `/api/metrics`) requièrent une authentification :

```http
GET /api/vm-replications/
Authorization: Token your-api-token-here
```

---

## 5. Modèles de données

### Schéma relationnel

```
┌─────────────────────┐
│  VirtualMachine     │
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  VMReplication      │ 1:N │  FailoverEvent      │
│                     │────▶│                     │
│  - source_server    │     │  - failover_type    │
│  - dest_server      │     │  - status           │
│  - failover_mode    │     │  - triggered_by     │
└─────────────────────┘     └─────────────────────┘

┌─────────────────────┐
│  OVFExportJob       │
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│ BackupVerification  │
│                     │
│  - test_type        │
│  - status           │
│  - services_checked │
└──────────┬──────────┘
           │
           │ N:1
           ▼
┌─────────────────────┐
│ BackupVerification  │
│ Schedule            │
│                     │
│  - frequency        │
│  - next_run_at      │
└─────────────────────┘

┌─────────────────────┐
│  VMBackupJob        │
└──────────┬──────────┘
           │
           │ 1:N
           └─────────────────────┘
```

### Contraintes et validations

#### VMReplication
- **unique_together**: (virtual_machine, destination_server)
- **Validation** : source_server ≠ destination_server

#### BackupVerification
- **Validation** : (ovf_export XOR vm_backup) - Un seul des deux requis
- **Validation** : test_datastore doit exister sur esxi_server

---

## 6. Guide de déploiement

### Étape 1 : Appliquer les migrations

```bash
cd /home/user/esxi/backend
python manage.py migrate
```

**Sortie attendue :**
```
Running migrations:
  Applying backups.0019_add_replication_and_surebackup... OK
```

### Étape 2 : Configurer Grafana

```bash
# Démarrer Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.monitoring.yml logs -f

# Accéder à Grafana
open http://localhost:3001
```

Voir [GRAFANA_SETUP.md](./GRAFANA_SETUP.md) pour les détails.

### Étape 3 : Tester l'endpoint metrics

```bash
curl http://localhost:8000/api/metrics

# Sortie attendue :
# esxi_backups_total 42
# esxi_backups_completed_total 38
# esxi_backups_success_rate 90.48
# ...
```

### Étape 4 : Créer une réplication de test

```bash
curl -X POST http://localhost:8000/api/vm-replications/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Replication",
    "virtual_machine": 1,
    "source_server": 1,
    "destination_server": 2,
    "destination_datastore": "datastore1",
    "failover_mode": "manual"
  }'
```

### Étape 5 : Créer une vérification de test

```bash
curl -X POST http://localhost:8000/api/backup-verifications/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ovf_export": 1,
    "esxi_server": 1,
    "test_type": "boot",
    "test_datastore": "datastore-test"
  }'
```

### Étape 6 : Implémenter les services (TODO)

Les ViewSets incluent des TODO pour les implémentations réelles :

1. **Replication Service** (`backend/backups/replication_service.py`)
   - Logique de réplication via pyVmomi
   - Gestion du failover
   - Monitoring des serveurs sources

2. **SureBackup Service** (`backend/backups/surebackup_service.py`)
   - Restauration de backups
   - Démarrage de VMs de test
   - Vérification de services
   - Nettoyage automatique

### Étape 7 : Créer les interfaces frontend (TODO)

Pages à créer :
- `frontend/src/views/Replication.vue`
- `frontend/src/views/Failover.vue`
- `frontend/src/views/SureBackup.vue`

---

## 7. Cas d'usage

### Cas 1 : Haute disponibilité pour application critique

**Contexte :** Application web critique qui doit être disponible 24/7

**Solution :**
```json
{
  "name": "HA Web Application",
  "virtual_machine": "web-app-prod",
  "source_server": "esxi-dc1",
  "destination_server": "esxi-dc2",
  "replication_interval_minutes": 5,
  "failover_mode": "automatic",
  "auto_failover_threshold_minutes": 2
}
```

**Résultat :**
- VM répliquée toutes les 5 minutes
- En cas de panne de esxi-dc1, failover automatique en 2 minutes
- Downtime total : ~2 minutes max

### Cas 2 : Plan de reprise d'activité (DR)

**Contexte :** Besoin de vérifier régulièrement que les backups sont restaurables

**Solution :**
```json
{
  "name": "DR Test Mensuel",
  "frequency": "monthly",
  "test_type": "boot_ping_services",
  "is_active": true
}
```

**Résultat :**
- Test automatique mensuel de tous les backups
- Vérification du boot + réseau + services
- Rapport détaillé de restaurabilité
- Conformité audit (preuve que les backups fonctionnent)

### Cas 3 : Migration planifiée

**Contexte :** Migration d'infrastructure vers nouveau datacenter

**Solution :**
1. Créer réplications vers nouveau datacenter
2. Laisser synchroniser plusieurs jours
3. Planifier fenêtre de maintenance
4. Déclencher failover manuel pendant la fenêtre
5. Valider et basculer définitivement

```bash
# Étape 1 : Créer réplication
POST /api/vm-replications/ {
  "failover_mode": "manual",
  "replication_interval_minutes": 15
}

# Étape 2 : Attendre synchronisation complète

# Étape 3 : Déclencher failover pendant fenêtre
POST /api/vm-replications/{id}/trigger_failover/ {
  "reason": "Migration vers nouveau datacenter",
  "test_mode": false
}
```

### Cas 4 : Validation continue des backups

**Contexte :** S'assurer que chaque nouveau backup est restaurable

**Solution :**
```json
{
  "name": "Validation post-backup",
  "frequency": "after_backup",
  "test_type": "boot_ping",
  "is_active": true
}
```

**Résultat :**
- Chaque backup est testé automatiquement après création
- Détection immédiate de problèmes de backup
- Confiance totale dans les sauvegardes

---

## Prochaines étapes

### Court terme (Sprint actuel)
- [ ] Implémenter `replication_service.py`
- [ ] Implémenter `surebackup_service.py`
- [ ] Créer interfaces frontend pour réplication
- [ ] Créer interfaces frontend pour SureBackup

### Moyen terme
- [ ] Scheduler automatique pour réplications
- [ ] Scheduler automatique pour vérifications
- [ ] Notifications par email pour événements critiques
- [ ] Rapports PDF de vérification

### Long terme
- [ ] Support multi-site (réplication sur 3+ sites)
- [ ] Orchestration de DR (basculement de plusieurs VMs)
- [ ] Tests de charge sur VMs restaurées
- [ ] Intégration avec systèmes de ticketing

---

## Support et documentation

- **Guide Grafana** : [GRAFANA_SETUP.md](./GRAFANA_SETUP.md)
- **API Reference** : `/api/schema/swagger-ui/`
- **Code source** :
  - Models : `backend/backups/models.py` (lignes 1151-1548)
  - Serializers : `backend/api/serializers.py`
  - Views : `backend/api/views.py`
  - URLs : `backend/api/urls.py`

---

## Glossaire

- **Failover** : Basculement automatique ou manuel vers un système de secours
- **Réplication** : Copie continue des données vers un système distant
- **SureBackup** : Vérification de restaurabilité en démarrant la VM depuis le backup
- **Prometheus** : Système de monitoring et base de données time-series
- **Grafana** : Plateforme de visualisation de métriques
- **DR** : Disaster Recovery - Plan de reprise après sinistre
- **HA** : High Availability - Haute disponibilité
- **RTO** : Recovery Time Objective - Temps de récupération cible
- **RPO** : Recovery Point Objective - Perte de données maximale acceptable
