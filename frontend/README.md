# ESXi Backup Manager - Frontend

Application web moderne pour la gestion et l'automatisation des sauvegardes de machines virtuelles VMware ESXi.

## 🚀 Technologies

- **Vue.js 3** - Framework JavaScript progressif
- **Vite** - Build tool rapide
- **Tailwind CSS** - Framework CSS utility-first
- **Pinia** - Gestion d'état
- **Vue Router** - Routage
- **Axios** - Client HTTP
- **date-fns** - Manipulation de dates
- **Chart.js** - Graphiques (optionnel)

## ✨ Fonctionnalités

### 🔐 Authentification
- Connexion sécurisée avec Django REST Framework
- Gestion des tokens
- Protection des routes

### 📊 Dashboard
- Vue d'ensemble des statistiques
- Serveurs ESXi actifs
- Machines virtuelles managées
- Sauvegardes réussies/échouées
- Utilisation du stockage
- Sauvegardes récentes
- Actions rapides

### 🖥️ Gestion des Serveurs ESXi
- Ajout/modification/suppression de serveurs
- Test de connexion
- Synchronisation des VMs
- Statut de connexion en temps réel
- Gestion des datastores

### 💻 Machines Virtuelles
- Liste complète des VMs synchronisées
- Filtrage par état (allumé, éteint, suspendu)
- Filtrage par serveur
- Recherche avancée
- Informations détaillées (CPU, RAM, stockage, OS, IP)
- Accès direct à la sauvegarde

### 💾 Sauvegardes
- Création de sauvegardes manuelles
- Sauvegardes complètes ou incrémentales
- Configuration du répertoire de sauvegarde
- Démarrage/annulation des jobs
- Suivi en temps réel de la progression
- Statistiques détaillées
- Historique complet
- Filtrage par statut et type

### 📅 Planifications
- Création de sauvegardes automatiques
- Fréquence : quotidienne, hebdomadaire, mensuelle
- Activation/désactivation facile
- Gestion par VM
- Vue d'ensemble des planifications actives

### ⚙️ Paramètres
- Configuration globale
- Répertoire de sauvegarde par défaut
- Rétention des sauvegardes
- Notifications (à venir)
- Informations système

## 📦 Installation

### Prérequis
- Node.js 18+
- npm ou yarn

### Étapes d'installation

1. **Installation des dépendances**
```bash
cd frontend
npm install
```

2. **Configuration de l'environnement**
```bash
cp .env.example .env
```

Éditez `.env` et configurez l'URL de votre backend :
```env
VITE_API_URL=http://localhost:8000/api
```

3. **Démarrage en développement**
```bash
npm run dev
```

L'application sera disponible sur `http://localhost:3000`

4. **Build pour la production**
```bash
npm run build
```

Les fichiers de production seront générés dans le dossier `dist/`

5. **Prévisualisation du build de production**
```bash
npm run preview
```

## 🏗️ Structure du projet

```
frontend/
├── public/              # Fichiers statiques
├── src/
│   ├── assets/          # Assets (CSS, images)
│   │   └── css/
│   │       └── main.css # Styles Tailwind
│   ├── components/      # Composants Vue
│   │   ├── common/      # Composants réutilisables
│   │   │   ├── Layout.vue
│   │   │   ├── Sidebar.vue
│   │   │   ├── Header.vue
│   │   │   ├── Loading.vue
│   │   │   └── Modal.vue
│   │   ├── dashboard/   # Composants du dashboard
│   │   │   ├── StatsCard.vue
│   │   │   └── RecentBackups.vue
│   │   ├── esxi/        # Composants ESXi
│   │   │   └── ServerForm.vue
│   │   ├── backups/     # Composants de sauvegarde
│   │   │   └── BackupJobForm.vue
│   │   └── schedules/   # Composants de planification
│   │       └── ScheduleForm.vue
│   ├── views/           # Pages/Vues
│   │   ├── Login.vue
│   │   ├── Dashboard.vue
│   │   ├── ESXiServers.vue
│   │   ├── VirtualMachines.vue
│   │   ├── Backups.vue
│   │   ├── Schedules.vue
│   │   └── Settings.vue
│   ├── stores/          # Stores Pinia
│   │   ├── auth.js      # Authentification
│   │   ├── esxi.js      # Serveurs et VMs
│   │   ├── backups.js   # Sauvegardes et planifications
│   │   └── dashboard.js # Statistiques
│   ├── services/        # Services
│   │   └── api.js       # Client API
│   ├── router/          # Configuration du routeur
│   │   └── index.js
│   ├── App.vue          # Composant racine
│   └── main.js          # Point d'entrée
├── index.html
├── package.json
├── vite.config.js       # Configuration Vite
├── tailwind.config.js   # Configuration Tailwind
├── postcss.config.js    # Configuration PostCSS
└── README.md
```

## 🎨 Design

L'interface utilise Tailwind CSS avec une palette de couleurs personnalisée :

- **Primary** : Bleu (tons de #0ea5e9)
- **Secondary** : Violet (tons de #a855f7)
- **Success** : Vert
- **Danger** : Rouge
- **Warning** : Jaune
- **Info** : Bleu clair

### Composants personnalisés

Classes utilitaires disponibles :
- `.btn-primary` - Bouton principal
- `.btn-secondary` - Bouton secondaire
- `.btn-danger` - Bouton de danger
- `.btn-success` - Bouton de succès
- `.card` - Carte/conteneur
- `.input-field` - Champ de formulaire
- `.label` - Label de formulaire
- `.badge-*` - Badges de statut

## 🔌 API Backend

Le frontend communique avec le backend Django REST Framework via les endpoints suivants :

### Authentification
- `POST /api/auth/login/` - Connexion
- `POST /api/auth/logout/` - Déconnexion
- `GET /api/auth/user/` - Utilisateur actuel

### Serveurs ESXi
- `GET /api/esxi-servers/` - Liste des serveurs
- `POST /api/esxi-servers/` - Créer un serveur
- `PUT /api/esxi-servers/{id}/` - Modifier un serveur
- `DELETE /api/esxi-servers/{id}/` - Supprimer un serveur
- `POST /api/esxi-servers/{id}/test_connection/` - Tester la connexion
- `POST /api/esxi-servers/{id}/sync_vms/` - Synchroniser les VMs

### Machines Virtuelles
- `GET /api/virtual-machines/` - Liste des VMs

### Sauvegardes
- `GET /api/backup-jobs/` - Liste des jobs
- `POST /api/backup-jobs/` - Créer un job
- `POST /api/backup-jobs/{id}/start/` - Démarrer une sauvegarde
- `POST /api/backup-jobs/{id}/cancel/` - Annuler une sauvegarde
- `GET /api/backup-jobs/statistics/` - Statistiques

### Planifications
- `GET /api/backup-schedules/` - Liste des planifications
- `POST /api/backup-schedules/` - Créer une planification
- `PUT /api/backup-schedules/{id}/` - Modifier une planification
- `POST /api/backup-schedules/{id}/toggle_active/` - Activer/désactiver

### Dashboard
- `GET /api/dashboard/stats/` - Statistiques générales
- `GET /api/dashboard/recent_backups/` - Sauvegardes récentes

## 🔒 Sécurité

- Authentification par token (Django REST Framework)
- Protection CSRF
- Routes protégées (navigation guards)
- Validation des formulaires
- Gestion sécurisée des credentials

## 🚧 Développement

### Linting
```bash
npm run lint
```

### Commandes utiles
```bash
npm run dev      # Développement avec hot-reload
npm run build    # Build de production
npm run preview  # Preview du build
```

## 📝 Notes importantes

1. **Proxy de développement** : Vite est configuré pour proxifier `/api` vers `http://localhost:8000` en développement

2. **CORS** : Assurez-vous que le backend Django est configuré pour accepter les requêtes du frontend

3. **Authentification** : Le token est stocké dans `localStorage`. En production, considérez des alternatives plus sécurisées

4. **WebSocket** : Pour un suivi en temps réel des sauvegardes, l'implémentation de WebSocket est recommandée

## 🛠️ Personnalisation

### Modifier les couleurs
Éditez `tailwind.config.js` :

```javascript
theme: {
  extend: {
    colors: {
      primary: { ... },
      secondary: { ... }
    }
  }
}
```

### Ajouter des routes
Modifiez `src/router/index.js`

### Ajouter des API endpoints
Modifiez `src/services/api.js`

## 📄 Licence

Ce projet est développé pour la gestion des sauvegardes ESXi.

## 👨‍💻 Support

Pour toute question ou problème, consultez la documentation ou contactez l'équipe de développement.
