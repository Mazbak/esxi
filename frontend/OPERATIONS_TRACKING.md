# 🎯 Système de Tracking des Opérations avec Persistence

Ce système permet de maintenir les barres de progression visibles même après changement de page ou rafraîchissement.

## 📦 Composants du Système

### 1. Store Pinia (`stores/operations.js`)
Gère l'état global de toutes les opérations en cours avec persistence dans localStorage.

### 2. Composant Global (`components/common/OperationsProgress.vue`)
Affiche les barres de progression en bas à droite de l'écran, visible sur toutes les pages.

### 3. Composable (`composables/useOperationTracking.js`)
Hook réutilisable pour faciliter l'intégration dans les composants.

## 🚀 Utilisation dans un Composant

### Exemple : Replication.vue

```vue
<script setup>
import { ref } from 'vue'
import { vmReplicationsAPI } from '@/services/api'
import { useOperationTracking } from '@/composables/useOperationTracking'

// Créer le tracker pour les réplications
const replicationTracker = useOperationTracking(
  'replication', // Type d'opération
  (id) => vmReplicationsAPI.getReplicationProgress(id), // Fonction pour obtenir la progression
  {
    pollInterval: 500, // Intervalle de polling en ms
    onComplete: (data) => {
      console.log('Réplication terminée!', data)
      toast.success('Réplication terminée avec succès')
      fetchData() // Rafraîchir les données
    },
    onError: (data) => {
      console.error('Erreur réplication:', data)
      toast.error(data.message || 'La réplication a échoué')
    },
    onProgress: (data) => {
      // Callback appelé à chaque mise à jour
      console.log('Progression:', data.progress)
    }
  }
)

// Démarrer une réplication
async function startReplication(replication) {
  if (!confirm(`Voulez-vous démarrer la réplication de ${replication.vm_name} ?`)) return

  try {
    const response = await vmReplicationsAPI.startReplication(replication.id)
    const replicationId = response.data.replication_id

    // Démarrer le tracking avec données initiales
    replicationTracker.startTracking(replicationId, {
      vmName: replication.vm_name,
      progress: 0,
      status: 'starting',
      message: 'Démarrage de la réplication...'
    })

    toast.success('Réplication démarrée')
  } catch (error) {
    console.error('Erreur:', error)
    toast.error('Impossible de démarrer la réplication')
  }
}

// Annuler une réplication
async function cancelReplication(replicationId) {
  if (!confirm('Voulez-vous vraiment arrêter cette réplication ?')) return

  try {
    await vmReplicationsAPI.cancelReplication(replicationId)
    replicationTracker.cancelCurrent()
    toast.info('Réplication annulée')
  } catch (error) {
    console.error('Erreur:', error)
    toast.error('Impossible d\'annuler la réplication')
  }
}
</script>
```

## 🔧 Intégration Step-by-Step

### Étape 1 : Importer le composable
```javascript
import { useOperationTracking } from '@/composables/useOperationTracking'
```

### Étape 2 : Créer le tracker
```javascript
const tracker = useOperationTracking(
  'TYPE_OPERATION', // replication, backup, export, restore
  getFunctionProgress, // Fonction API pour obtenir la progression
  {
    pollInterval: 500,
    onComplete: (data) => { /* ... */ },
    onError: (data) => { /* ... */ }
  }
)
```

### Étape 3 : Démarrer le tracking
```javascript
tracker.startTracking(operationId, {
  vmName: 'Ma VM',
  progress: 0,
  status: 'starting',
  message: 'Démarrage...'
})
```

### Étape 4 : Le système s'occupe du reste !
- ✅ Polling automatique
- ✅ Mise à jour du store
- ✅ Persistence dans localStorage
- ✅ Affichage global
- ✅ Reprise automatique après rechargement

## 📋 Types d'Opérations Supportés

| Type | Description | API Progress Function |
|------|-------------|----------------------|
| `replication` | Réplication de VM | `vmReplicationsAPI.getReplicationProgress(id)` |
| `backup` | Sauvegarde de VM | `vmBackupsAPI.getBackupProgress(id)` |
| `export` | Export OVF | `ovfExportsAPI.getExportProgress(id)` |
| `restore` | Restauration | `restoreAPI.getRestoreProgress(id)` |

## 🎨 Personnalisation

### Modifier les couleurs du composant OperationsProgress
Éditer `components/common/OperationsProgress.vue` :

```javascript
const getIconBg = (type) => {
  const colors = {
    replication: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    backup: 'bg-gradient-to-br from-green-500 to-emerald-600',
    // Ajouter vos couleurs personnalisées
  }
  return colors[type]
}
```

### Modifier l'intervalle de polling par défaut
Modifier `composables/useOperationTracking.js` :

```javascript
const {
  pollInterval: pollMs = 1000, // Changer ici (en ms)
  // ...
} = options
```

## 🧹 Nettoyage Automatique

Le système nettoie automatiquement :
- Les opérations terminées après 10 secondes
- Les opérations obsolètes (>24h) au démarrage

## 💡 Astuces

### Vérifier si une opération est en cours
```javascript
if (tracker.hasActiveOperation(operationId)) {
  console.log('Une opération est déjà en cours')
}
```

### Obtenir les détails d'une opération
```javascript
const operation = tracker.getOperation(operationId)
console.log(operation.progress, operation.status)
```

### Arrêter manuellement le polling
```javascript
tracker.stopPolling()
```

## 🐛 Debugging

Pour voir les opérations stockées :
```javascript
// Dans la console du navigateur
localStorage.getItem('esxi_operations')
```

Pour forcer le nettoyage :
```javascript
import { useOperationsStore } from '@/stores/operations'
const store = useOperationsStore()
store.cleanupOldOperations()
```
