<template>
  <!-- Conteneur global des opérations en cours -->
  <div v-if="activeOperations.length > 0" class="fixed bottom-4 right-4 z-50 space-y-3 max-w-md w-full">
    <!-- Carte pour chaque opération -->
    <transition-group
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0 translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-4"
    >
      <div
        v-for="op in activeOperations"
        :key="`${op.type}_${op.id}`"
        class="bg-white/95 backdrop-blur-xl rounded-2xl shadow-2xl p-5 border border-gray-200/50 animate-slide-up"
      >
        <!-- Header avec type d'opération et bouton fermer -->
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center space-x-3">
            <!-- Icône selon le type -->
            <div :class="getIconBg(op.type)" class="p-2.5 rounded-xl shadow-lg">
              <component :is="getIcon(op.type)" class="w-5 h-5 text-white" />
            </div>
            <div>
              <p class="text-sm font-bold text-gray-900">{{ getOperationTitle(op) }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ op.vmName || 'VM' }}</p>
            </div>
          </div>

          <!-- Bouton fermer (si terminé) -->
          <button
            v-if="op.status === 'completed' || op.status === 'error' || op.status === 'cancelled'"
            @click="removeOperation(op.type, op.id)"
            class="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Message -->
        <p class="text-xs text-gray-600 mb-3 line-clamp-2">{{ op.message || 'En cours...' }}</p>

        <!-- Barre de progression -->
        <div class="space-y-2">
          <!-- Progress bar -->
          <div class="relative h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              :class="getProgressBarClass(op.status)"
              class="h-full rounded-full transition-all duration-500 ease-out relative"
              :style="{ width: `${op.progress || 0}%` }"
            >
              <!-- Shimmer effect -->
              <div v-if="op.status === 'running' || op.status === 'in_progress'" class="absolute inset-0 shimmer"></div>
            </div>
          </div>

          <!-- Pourcentage et statut -->
          <div class="flex items-center justify-between text-xs">
            <span class="font-semibold" :class="getStatusColor(op.status)">
              {{ getStatusText(op.status) }}
            </span>
            <span class="text-gray-500 font-medium">{{ Math.round(op.progress || 0) }}%</span>
          </div>
        </div>

        <!-- Actions selon le statut -->
        <div v-if="op.status === 'running' || op.status === 'in_progress'" class="mt-3 pt-3 border-t border-gray-100">
          <button
            @click="cancelOperation(op.type, op.id)"
            class="text-xs font-semibold text-red-600 hover:text-red-700 transition-colors"
          >
            Annuler l'opération
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { vmReplicationsAPI, ovfExportsAPI, vmBackupsAPI } from '@/services/api'
import { useToastStore } from '@/stores/toast'

const operationsStore = useOperationsStore()
const toast = useToastStore()

const activeOperations = computed(() => operationsStore.getActiveOperations)

const getIcon = (type) => {
  const icons = {
    replication: IconReplication,
    backup: IconBackup,
    export: IconExport,
    restore: IconRestore
  }
  return icons[type] || IconDefault
}

const getIconBg = (type) => {
  const colors = {
    replication: 'bg-gradient-to-br from-blue-500 to-indigo-600',
    backup: 'bg-gradient-to-br from-green-500 to-emerald-600',
    export: 'bg-gradient-to-br from-purple-500 to-violet-600',
    restore: 'bg-gradient-to-br from-orange-500 to-red-600'
  }
  return colors[type] || 'bg-gradient-to-br from-gray-500 to-gray-600'
}

const getOperationTitle = (op) => {
  const titles = {
    replication: 'Réplication en cours',
    backup: 'Sauvegarde en cours',
    export: 'Export en cours',
    restore: 'Restauration en cours'
  }
  return titles[op.type] || 'Opération en cours'
}

const getProgressBarClass = (status) => {
  if (status === 'completed') {
    return 'bg-gradient-to-r from-green-500 to-emerald-600'
  } else if (status === 'error' || status === 'cancelled') {
    return 'bg-gradient-to-r from-red-500 to-pink-600'
  } else {
    return 'bg-gradient-to-r from-blue-500 to-indigo-600'
  }
}

const getStatusColor = (status) => {
  if (status === 'completed') return 'text-green-600'
  if (status === 'error') return 'text-red-600'
  if (status === 'cancelled') return 'text-gray-600'
  return 'text-blue-600'
}

const getStatusText = (status) => {
  const texts = {
    starting: 'Démarrage...',
    running: 'En cours',
    in_progress: 'En cours',
    completed: 'Terminé',
    error: 'Erreur',
    cancelled: 'Annulé'
  }
  return texts[status] || 'En cours'
}

const removeOperation = (type, id) => {
  operationsStore.removeOperation(type, id)
}

const cancelOperation = async (type, id) => {
  if (!confirm('Voulez-vous vraiment annuler cette opération ?')) return

  try {
    // Appeler l'API d'annulation selon le type
    if (type === 'replication') {
      await vmReplicationsAPI.cancelReplication(id)
    } else if (type === 'export') {
      await ovfExportsAPI.cancel(id)
    } else if (type === 'backup') {
      await vmBackupsAPI.cancel(id)
    }

    toast.success('Opération annulée')
    operationsStore.updateProgress(type, id, 0, 'cancelled', 'Opération annulée par l\'utilisateur')
  } catch (error) {
    console.error('Erreur annulation:', error)
    toast.error('Impossible d\'annuler l\'opération')
  }
}

// Icon components
const IconReplication = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z' })
  ])
}

const IconBackup = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' })
  ])
}

const IconExport = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12' })
  ])
}

const IconRestore = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' })
  ])
}

const IconDefault = {
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', 'stroke-width': '2' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M13 10V3L4 14h7v7l9-11h-7z' })
  ])
}
</script>
