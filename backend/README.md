# ESXi Backup Manager

Système complet de gestion et d'automatisation des sauvegardes de machines virtuelles VMware ESXi.

## 🎯 Vue d'ensemble

Cette solution complète permet de :
- Gérer plusieurs serveurs VMware ESXi
- Sauvegarder automatiquement ou manuellement des machines virtuelles
- Planifier des sauvegardes récurrentes (quotidiennes, hebdomadaires, mensuelles)
- Suivre l'état et la progression des sauvegardes
- Gérer l'espace de stockage et la rétention des données

## 🏗️ Architecture

### Backend - Django REST Framework
- **Framework** : Django 4.x avec Django REST Framework
- **Base de données** : SQLite (production: PostgreSQL recommandé)
- **Authentification** : Token-based avec DRF
- **API VMware** : pyVmomi pour la communication avec ESXi
- **Tâches asynchrones** : Celery (optionnel)
- **Scheduler** : APScheduler pour les planifications

### Frontend - Vue.js
- **Framework** : Vue.js 3 avec Composition API
- **Build Tool** : Vite
- **UI Framework** : Tailwind CSS
- **State Management** : Pinia
- **Routing** : Vue Router
- **HTTP Client** : Axios

## 📦 Installation

### Prérequis
- Python 3.8+
- Node.js 18+
- VMware ESXi 6.x ou supérieur
- Accès administrateur aux serveurs ESXi

### 1. Installation du Backend

```bash
# Créer et activer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Migrations de la base de données
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur de développement
python manage.py runserver
```

Le backend sera accessible sur `http://localhost:8000`

### 2. Installation du Frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Configurer l'environnement
cp .env.example .env

# Lancer le serveur de développement
npm run dev
```

Le frontend sera accessible sur `http://localhost:3000`

## 🚀 Démarrage rapide

### 1. Configuration initiale

1. Accédez à l'interface web : `http://localhost:3000`
2. Connectez-vous avec vos identifiants admin
3. Ajoutez votre premier serveur ESXi :
   - Allez dans "Serveurs ESXi"
   - Cliquez sur "Ajouter un serveur"
   - Remplissez les informations de connexion
   - Testez la connexion
   - Synchronisez les VMs

### 2. Créer une sauvegarde manuelle

1. Allez dans "Sauvegardes"
2. Cliquez sur "Nouvelle sauvegarde"
3. Sélectionnez une VM
4. Choisissez le type (complète/incrémentale)
5. Définissez le répertoire de sauvegarde
6. La sauvegarde démarre automatiquement

### 3. Planifier une sauvegarde automatique

1. Allez dans "Planifications"
2. Cliquez sur "Nouvelle planification"
3. Sélectionnez une VM
4. Choisissez la fréquence
5. Activez la planification

## 📁 Structure du projet

```
esxi_backend/
├── api/                    # API REST
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── esxi_client.py     # Client pyVmomi
├── backups/               # Gestion des sauvegardes
│   ├── models.py
│   ├── backup_service.py  # Service de sauvegarde
│   └── tasks.py           # Tâches Celery
├── esxi/                  # Modèles ESXi
│   ├── models.py
│   └── vmware_service.py  # Service VMware
├── sauvegarde/            # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── frontend/              # Application Vue.js
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── services/
│   │   └── router/
│   ├── public/
│   └── package.json
├── manage.py
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Authentification
```
POST   /api/auth/login/              # Connexion
POST   /api/auth/logout/             # Déconnexion
GET    /api/auth/user/               # Utilisateur actuel
```

### Serveurs ESXi
```
GET    /api/esxi-servers/            # Liste des serveurs
POST   /api/esxi-servers/            # Créer un serveur
PUT    /api/esxi-servers/{id}/       # Modifier
DELETE /api/esxi-servers/{id}/       # Supprimer
POST   /api/esxi-servers/{id}/test_connection/  # Tester
POST   /api/esxi-servers/{id}/sync_vms/         # Synchroniser
```

### Machines Virtuelles
```
GET    /api/virtual-machines/        # Liste des VMs
GET    /api/virtual-machines/{id}/   # Détails d'une VM
```

### Sauvegardes
```
GET    /api/backup-jobs/             # Liste des jobs
POST   /api/backup-jobs/             # Créer un job
POST   /api/backup-jobs/{id}/start/  # Démarrer
POST   /api/backup-jobs/{id}/cancel/ # Annuler
GET    /api/backup-jobs/statistics/  # Statistiques
```

### Planifications
```
GET    /api/backup-schedules/        # Liste
POST   /api/backup-schedules/        # Créer
PUT    /api/backup-schedules/{id}/   # Modifier
POST   /api/backup-schedules/{id}/toggle_active/  # Activer/Désactiver
```

### Dashboard
```
GET    /api/dashboard/stats/         # Statistiques
GET    /api/dashboard/recent_backups/  # Sauvegardes récentes
```

## ⚙️ Configuration

### Backend (settings.py)

```python
# Configuration CORS pour le frontend
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# Configuration Celery (optionnel)
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api
```

## 🔐 Sécurité

### Bonnes pratiques

1. **Ne jamais commiter** :
   - Mots de passe ESXi
   - Clés secrètes Django
   - Tokens d'authentification

2. **En production** :
   - Utilisez PostgreSQL au lieu de SQLite
   - Activez HTTPS
   - Configurez un pare-feu
   - Utilisez des mots de passe forts
   - Activez les logs d'audit

3. **Gestion des credentials** :
   - Stockez les mots de passe ESXi de manière sécurisée
   - Envisagez d'utiliser Django's `cryptography` pour chiffrer les mots de passe
   - Utilisez des variables d'environnement pour les secrets

## 📊 Fonctionnalités détaillées

### Types de sauvegarde

1. **Sauvegarde complète** :
   - Export complet de la VM (OVF/OVA)
   - Inclut tous les disques virtuels (.vmdk)
   - Fichiers de configuration (.vmx)
   - Recommandée pour les sauvegardes initiales

2. **Sauvegarde incrémentale** :
   - Sauvegarde uniquement les modifications
   - Plus rapide et moins gourmande en espace
   - Nécessite une sauvegarde complète préalable

### Planification

- **Quotidienne** : Exécution tous les jours à minuit
- **Hebdomadaire** : Tous les lundis à minuit
- **Mensuelle** : Le 1er de chaque mois à minuit

Personnalisable via APScheduler pour des horaires spécifiques.

### Monitoring

- Suivi en temps réel des sauvegardes en cours
- Historique complet des sauvegardes
- Statistiques de réussite/échec
- Utilisation de l'espace de stockage
- Logs détaillés pour chaque opération

## 🛠️ Dépannage

### Erreurs courantes

1. **Impossible de se connecter à ESXi** :
   - Vérifiez les credentials
   - Vérifiez que le port 443 est accessible
   - Désactivez temporairement le pare-feu pour tester

2. **Erreur de synchronisation des VMs** :
   - Vérifiez les permissions de l'utilisateur ESXi
   - Assurez-vous que pyVmomi est correctement installé

3. **Sauvegarde échoue** :
   - Vérifiez l'espace disque disponible
   - Vérifiez les permissions du répertoire de sauvegarde
   - Consultez les logs Django

### Logs

```bash
# Logs Django
python manage.py runserver --verbosity 3

# Logs Celery (si utilisé)
celery -A sauvegarde worker --loglevel=info
```

## 🚀 Déploiement en production

### Backend

```bash
# Installer gunicorn
pip install gunicorn

# Lancer avec gunicorn
gunicorn sauvegarde.wsgi:application --bind 0.0.0.0:8000
```

### Frontend

```bash
cd frontend
npm run build

# Les fichiers sont dans dist/
# Servez-les avec nginx ou Apache
```

### Nginx (exemple)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📝 TODO / Améliorations futures

- [ ] Support multi-utilisateurs avec permissions
- [ ] Notifications par email
- [ ] Dashboard avec graphiques avancés (Chart.js)
- [ ] Support des snapshots ESXi
- [ ] Restauration de sauvegardes
- [ ] Compression des sauvegardes
- [ ] Chiffrement des sauvegardes
- [ ] Support S3/Cloud Storage
- [ ] API webhooks
- [ ] Logs d'audit détaillés
- [ ] Interface CLI
- [ ] Tests automatisés

## 👥 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir des issues ou des pull requests.

## 📄 Licence

Ce projet est sous licence [à définir].

## 🆘 Support

Pour toute question ou problème :
- Consultez la documentation
- Ouvrez une issue sur GitHub
- Contactez l'équipe de développement

---

**Note** : Ce projet est conçu pour des environnements de test et de développement. Pour une utilisation en production, assurez-vous de suivre les meilleures pratiques de sécurité et de performance.
