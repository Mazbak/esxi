# Correctifs Réplication - Implémentation Complète

## ✅ Déjà Fait

### Backend
1. ✅ Endpoint API `check_replica_exists` créé dans `backend/api/views.py:3050-3096`
   - Vérifie si une VM replica existe sur le serveur de destination
   - Retourne `{exists: true/false, replica_name, message}`

### Frontend
1. ✅ Méthode `checkReplicaExists` ajoutée dans `frontend/src/services/api.js:280`
2. ✅ Store `operationsStore` importé dans `Replication.vue:864,867`
3. ✅ Modal "Replica Existante" ajouté dans `Replication.vue:858-983`
4. ✅ Variables d'état ajoutées dans `Replication.vue:1034-1040`

---

## 🔧 Reste à Faire

### 1. Fonction `deleteReplicaAndRetry` (à ajouter après la ligne ~1350 de Replication.vue)

```javascript
async function deleteReplicaAndRetry() {
  replicaExistsModalData.value.deleting = true

  try {
    const replication = replications.value.find(r => r.id === replicaExistsModalData.value.replicationId)
    if (!replication) {
      toast.error('Réplication introuvable')
      return
    }

    // Supprimer la réplication qui va supprimer automatiquement la replica
    await vmReplicationsAPI.delete(replication.id)

    // Recréer la réplication
    const newReplication = await vmReplicationsAPI.create({
      name: replication.name,
      virtual_machine: replication.virtual_machine,
      destination_server: replication.destination_server,
      destination_datastore: replication.destination_datastore,
      replication_interval_minutes: replication.replication_interval_minutes,
      failover_mode: replication.failover_mode,
      auto_failover_threshold_minutes: replication.auto_failover_threshold_minutes,
      is_active: replication.is_active
    })

    toast.success('Ancienne replica supprimée, nouvelle réplication créée')

    // Fermer le modal
    showReplicaExistsModal.value = false

    // Rafraîchir la liste
    await fetchData()

    // Lancer la nouvelle réplication
    const newReplData = newReplication.data
    await startReplicationWithoutCheck(newReplData)

  } catch (error) {
    console.error('Erreur suppression replica:', error)
    toast.error(error.response?.data?.error || 'Erreur lors de la suppression de la replica')
  } finally {
    replicaExistsModalData.value.deleting = false
  }
}
```

### 2. Modifier `startReplication` pour vérifier la replica (remplacer ligne ~1114)

```javascript
async function startReplication(replication) {
  if (!confirm(`Voulez-vous démarrer la réplication de ${replication.vm_name} ?`)) return

  try {
    // Vérifier si une replica existe déjà
    const checkResponse = await vmReplicationsAPI.checkReplicaExists(replication.id)

    if (checkResponse.data.exists) {
      // Afficher le modal de confirmation
      replicaExistsModalData.value = {
        replicationId: replication.id,
        replicaName: checkResponse.data.replica_name,
        deleting: false
      }
      showReplicaExistsModal.value = true
      return
    }

    // Pas de replica existante, continuer normalement
    await startReplicationWithoutCheck(replication)

  } catch (error) {
    console.error('Erreur vérification replica:', error)
    // En cas d'erreur de vérification, continuer quand même
    await startReplicationWithoutCheck(replication)
  }
}
```

### 3. Renommer l'ancienne fonction `startReplication` en `startReplicationWithoutCheck`

```javascript
async function startReplicationWithoutCheck(replication) {
  // Le contenu actuel de startReplication (lignes 1117-1230)
  replicatingId.value = replication.id
  replicationProgress.value = 0
  replicationStatus.value = 'starting'
  replicationMessage.value = 'Démarrage de la réplication...'

  try {
    const response = await vmReplicationsAPI.startReplication(replication.id)
    const replicationId = response.data.replication_id

    // ... reste du code actuel ...
  } catch (error) {
    // ... gestion erreurs ...
  }
}
```

---

## 🎯 Problème #2 : Persistence de la Barre de Progression

### Intégrer `operationsStore` dans startReplicationWithoutCheck

```javascript
async function startReplicationWithoutCheck(replication) {
  // Initialiser dans le store
  operationsStore.setOperation('replication', replication.id, {
    vmName: replication.vm_name,
    progress: 0,
    status: 'starting',
    message: 'Démarrage de la réplication...'
  })

  // Variables locales pour UI
  replicatingId.value = replication.id
  replicationProgress.value = 0
  replicationStatus.value = 'starting'
  replicationMessage.value = 'Démarrage de la réplication...'

  try {
    const response = await vmReplicationsAPI.startReplication(replication.id)
    const replicationId = response.data.replication_id

    if (replicationId) {
      currentReplicationId.value = replicationId

      // Polling
      pollInterval = setInterval(async () => {
        try {
          const progressResponse = await vmReplicationsAPI.getReplicationProgress(replicationId)
          const progressData = progressResponse.data

          // Mettre à jour le store ET les variables locales
          operationsStore.updateProgress(
            'replication',
            replication.id,
            progressData.progress,
            progressData.status,
            progressData.message
          )

          replicationProgress.value = progressData.progress
          replicationStatus.value = progressData.status
          replicationMessage.value = progressData.message

          // Si terminé
          if (['completed', 'error', 'cancelled'].includes(progressData.status)) {
            clearInterval(pollInterval)
            pollInterval = null
            replicatingId.value = null
            currentReplicationId.value = null

            // Retirer du store après 10s
            if (progressData.status === 'completed') {
              toast.success('Réplication terminée')
              setTimeout(() => {
                operationsStore.removeOperation('replication', replication.id)
                replicationProgress.value = 0
                replicationStatus.value = ''
                replicationMessage.value = ''
              }, 10000)
            } else if (progressData.status === 'error') {
              // Gestion erreurs (snapshots, powered on, etc.)
              // ... code actuel ...
            }
          }
        } catch (pollErr) {
          console.error('Erreur polling:', pollErr)
        }
      }, 500)
    }
  } catch (error) {
    operationsStore.removeOperation('replication', replication.id)
    // ... gestion erreurs ...
  }
}
```

### Restaurer la progression au chargement

```javascript
onMounted(() => {
  fetchData()

  // Restaurer les réplications en cours depuis le store
  const activeReplications = operationsStore.getOperationsByType('replication')
  if (activeReplications.length > 0) {
    // Reprendre le polling pour chaque réplication active
    activeReplications.forEach(op => {
      if (op.status === 'running' || op.status === 'starting') {
        resumeReplication(op.id, op)
      }
    })
  }
})

function resumeReplication(replicationId, opData) {
  replicatingId.value = replicationId
  replicationProgress.value = opData.progress
  replicationStatus.value = opData.status
  replicationMessage.value = opData.message

  // Relancer le polling
  pollInterval = setInterval(async () => {
    // ... même logique que dans startReplicationWithoutCheck ...
  }, 500)
}
```

---

## 📋 Résumé des Modifications

| Fichier | Ligne | Modification |
|---------|-------|--------------|
| `backend/api/views.py` | 3050-3096 | ✅ Endpoint `check_replica_exists` |
| `frontend/src/services/api.js` | 280 | ✅ Méthode `checkReplicaExists` |
| `Replication.vue` | 864, 867 | ✅ Import store operations |
| `Replication.vue` | 858-983 | ✅ Modal replica existante |
| `Replication.vue` | 1034-1040 | ✅ Variables modal |
| `Replication.vue` | ~1350 | ⏳ Fonction `deleteReplicaAndRetry` |
| `Replication.vue` | ~1114 | ⏳ Modifier `startReplication` |
| `Replication.vue` | ~1117 | ⏳ Créer `startReplicationWithoutCheck` |
| `Replication.vue` | ~1954 | ⏳ Fonction `resumeReplication` |
| `Replication.vue` | onMounted | ⏳ Restaurer progression |

---

## 🧪 Tests à Effectuer

1. **Test Replica Existante**
   - Créer une réplication
   - Lancer la réplication (créer une replica)
   - Relancer la réplication → Modal devrait apparaître
   - Cliquer "Supprimer et Continuer" → Devrait supprimer et relancer

2. **Test Persistence**
   - Lancer une réplication
   - Rafraîchir la page pendant la réplication
   - La barre de progression devrait réapparaître

3. **Test Global OperationsProgress**
   - Lancer une réplication
   - Naviguer vers une autre page
   - La barre devrait être visible en bas à droite de toutes les pages
