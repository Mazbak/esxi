import { ref, onMounted, onUnmounted } from 'vue'
import { useOperationsStore } from '@/stores/operations'

/**
 * Composable pour tracker une opération avec persistence
 * @param {string} operationType - Type d'opération (replication, backup, export, restore)
 * @param {Function} getProgressFn - Fonction pour obtenir la progression (reçoit l'ID)
 * @param {Object} options - Options (pollInterval, onComplete, onError)
 */
export function useOperationTracking(operationType, getProgressFn, options = {}) {
  const operationsStore = useOperationsStore()
  const pollInterval = ref(null)
  const currentOperationId = ref(null)

  const {
    pollInterval: pollMs = 500,
    onComplete = null,
    onError = null,
    onProgress = null
  } = options

  /**
   * Démarrer le tracking d'une opération
   */
  const startTracking = (operationId, initialData = {}) => {
    currentOperationId.value = operationId

    // Enregistrer l'opération dans le store
    operationsStore.setOperation(operationType, operationId, {
      progress: 0,
      status: 'starting',
      message: 'Démarrage...',
      ...initialData
    })

    // Démarrer le polling
    startPolling(operationId)
  }

  /**
   * Démarrer le polling de la progression
   */
  const startPolling = (operationId) => {
    // Arrêter le polling précédent s'il existe
    stopPolling()

    pollInterval.value = setInterval(async () => {
      try {
        const progressData = await getProgressFn(operationId)

        // Mettre à jour le store
        operationsStore.updateProgress(
          operationType,
          operationId,
          progressData.progress || 0,
          progressData.status,
          progressData.message || ''
        )

        // Callback de progression
        if (onProgress) {
          onProgress(progressData)
        }

        // Arrêter le polling si terminé
        if (progressData.status === 'completed' || progressData.status === 'error' || progressData.status === 'cancelled') {
          stopPolling()
          currentOperationId.value = null

          // Callbacks
          if (progressData.status === 'completed' && onComplete) {
            onComplete(progressData)
          } else if (progressData.status === 'error' && onError) {
            onError(progressData)
          }

          // Retirer l'opération après un délai (pour voir le statut final)
          setTimeout(() => {
            // Ne retirer que si toujours dans le même état (pas relancée)
            const op = operationsStore.getOperation(operationType, operationId)
            if (op && (op.status === 'completed' || op.status === 'error' || op.status === 'cancelled')) {
              operationsStore.removeOperation(operationType, operationId)
            }
          }, 10000) // 10 secondes
        }
      } catch (error) {
        console.error(`Erreur polling ${operationType}:`, error)
        // Ne pas arrêter le polling en cas d'erreur réseau temporaire
      }
    }, pollMs)
  }

  /**
   * Arrêter le polling
   */
  const stopPolling = () => {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      pollInterval.value = null
    }
  }

  /**
   * Reprendre le tracking des opérations en cours (après rechargement de page)
   */
  const resumeTracking = () => {
    // Chercher les opérations en cours pour ce type
    const activeOps = operationsStore.getOperationsByType(operationType)

    activeOps.forEach(op => {
      if (op.status === 'running' || op.status === 'starting' || op.status === 'in_progress') {
        console.log(`Reprise du tracking: ${operationType} ${op.id}`)
        currentOperationId.value = op.id
        startPolling(op.id)
      }
    })
  }

  /**
   * Annuler l'opération en cours
   */
  const cancelCurrent = () => {
    if (currentOperationId.value) {
      stopPolling()
      operationsStore.updateProgress(
        operationType,
        currentOperationId.value,
        0,
        'cancelled',
        'Opération annulée'
      )
      currentOperationId.value = null
    }
  }

  /**
   * Vérifier si une opération est en cours
   */
  const hasActiveOperation = (operationId) => {
    return operationsStore.hasActiveOperation(operationType, operationId)
  }

  /**
   * Obtenir une opération
   */
  const getOperation = (operationId) => {
    return operationsStore.getOperation(operationType, operationId)
  }

  // Reprendre le tracking au montage du composant
  onMounted(() => {
    resumeTracking()
  })

  // Nettoyer au démontage
  onUnmounted(() => {
    stopPolling()
  })

  return {
    startTracking,
    stopPolling,
    resumeTracking,
    cancelCurrent,
    hasActiveOperation,
    getOperation,
    currentOperationId
  }
}
