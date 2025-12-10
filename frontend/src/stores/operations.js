import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * Store pour gérer toutes les opérations en cours avec persistence
 * (sauvegardes, exports, réplications, restaurations, etc.)
 */
export const useOperationsStore = defineStore('operations', () => {
  // État des opérations en cours
  const operations = ref({})

  // Charger les opérations depuis localStorage au démarrage
  const loadFromStorage = () => {
    try {
      const stored = localStorage.getItem('esxi_operations')
      if (stored) {
        operations.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Erreur chargement opérations:', error)
    }
  }

  // Sauvegarder dans localStorage
  const saveToStorage = () => {
    try {
      localStorage.setItem('esxi_operations', JSON.stringify(operations.value))
    } catch (error) {
      console.error('Erreur sauvegarde opérations:', error)
    }
  }

  /**
   * Ajouter ou mettre à jour une opération
   * @param {string} type - Type d'opération (replication, backup, export, restore)
   * @param {string} id - ID unique de l'opération
   * @param {object} data - Données de l'opération
   */
  const setOperation = (type, id, data) => {
    const key = `${type}_${id}`
    operations.value[key] = {
      type,
      id,
      ...data,
      lastUpdate: Date.now()
    }
    saveToStorage()
  }

  /**
   * Mettre à jour la progression d'une opération
   */
  const updateProgress = (type, id, progress, status, message) => {
    const key = `${type}_${id}`
    if (operations.value[key]) {
      operations.value[key] = {
        ...operations.value[key],
        progress,
        status,
        message,
        lastUpdate: Date.now()
      }
      saveToStorage()
    }
  }

  /**
   * Supprimer une opération terminée
   */
  const removeOperation = (type, id) => {
    const key = `${type}_${id}`
    delete operations.value[key]
    saveToStorage()
  }

  /**
   * Nettoyer les opérations obsolètes (>24h)
   */
  const cleanupOldOperations = () => {
    const now = Date.now()
    const maxAge = 24 * 60 * 60 * 1000 // 24 heures

    Object.keys(operations.value).forEach(key => {
      const op = operations.value[key]
      if (now - op.lastUpdate > maxAge) {
        delete operations.value[key]
      }
    })
    saveToStorage()
  }

  /**
   * Obtenir une opération spécifique
   */
  const getOperation = (type, id) => {
    const key = `${type}_${id}`
    return operations.value[key]
  }

  /**
   * Obtenir toutes les opérations d'un type
   */
  const getOperationsByType = (type) => {
    return Object.values(operations.value).filter(op => op.type === type)
  }

  /**
   * Obtenir toutes les opérations en cours
   */
  const getActiveOperations = computed(() => {
    return Object.values(operations.value).filter(op =>
      op.status === 'running' || op.status === 'starting' || op.status === 'in_progress'
    )
  })

  /**
   * Vérifier si une opération est en cours
   */
  const hasActiveOperation = (type, id) => {
    const key = `${type}_${id}`
    const op = operations.value[key]
    return op && (op.status === 'running' || op.status === 'starting' || op.status === 'in_progress')
  }

  /**
   * Obtenir le nombre d'opérations actives
   */
  const activeCount = computed(() => {
    return getActiveOperations.value.length
  })

  // Charger au démarrage
  loadFromStorage()

  // Nettoyer les opérations obsolètes au démarrage
  cleanupOldOperations()

  return {
    operations,
    setOperation,
    updateProgress,
    removeOperation,
    cleanupOldOperations,
    getOperation,
    getOperationsByType,
    getActiveOperations,
    hasActiveOperation,
    activeCount,
    loadFromStorage,
  }
})
