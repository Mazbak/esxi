<template>
  <div class="card">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Sauvegardes récentes</h3>

    <div v-if="loading" class="text-center py-8">
      <Loading text="Chargement..." />
    </div>

    <div v-else-if="backups.length === 0" class="text-center py-8 text-gray-500">
      <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
      <p>Aucune sauvegarde récente</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="backup in backups"
        :key="backup.id"
        class="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <div class="flex items-center space-x-4 flex-1">
          <div :class="getStatusColor(backup.status)" class="p-2 rounded-lg">
            <component :is="getStatusIcon(backup.status)" class="w-5 h-5 text-white" />
          </div>
          <div class="flex-1">
            <p class="font-medium text-gray-900">{{ getVMName(backup) }}</p>
            <p class="text-sm text-gray-500">{{ formatDate(backup.created_at) }}</p>
          </div>
        </div>
        <div class="text-right">
          <span :class="getStatusBadgeClass(backup.status)" class="badge">
            {{ getStatusLabel(backup.status) }}
          </span>
          <p v-if="backup.backup_size_mb" class="text-sm text-gray-500 mt-1">
            {{ formatSize(backup.backup_size_mb) }}
          </p>
        </div>
      </div>
    </div>

    <div v-if="backups.length > 0" class="mt-4 text-center">
      <router-link to="/ovf-exports" class="text-primary-600 hover:text-primary-700 text-sm font-medium">
        Voir toutes les sauvegardes →
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import Loading from '@/components/common/Loading.vue'

const props = defineProps({
  backups: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

function getVMName(backup) {
  return backup.virtual_machine?.name || `VM #${backup.virtual_machine}`
}

function formatDate(date) {
  if (!date) return '-'
  return format(new Date(date), 'dd MMM yyyy HH:mm', { locale: fr })
}

function formatSize(sizeInMB) {
  if (sizeInMB >= 1024) {
    return `${(sizeInMB / 1024).toFixed(2)} GB`
  }
  return `${sizeInMB.toFixed(2)} MB`
}

function getStatusColor(status) {
  const colors = {
    completed: 'bg-green-500',
    running: 'bg-blue-500',
    failed: 'bg-red-500',
    pending: 'bg-yellow-500',
    cancelled: 'bg-gray-500'
  }
  return colors[status] || 'bg-gray-500'
}

function getStatusBadgeClass(status) {
  const classes = {
    completed: 'badge-success',
    running: 'badge-info',
    failed: 'badge-danger',
    pending: 'badge-warning',
    cancelled: 'badge-gray'
  }
  return classes[status] || 'badge-gray'
}

function getStatusLabel(status) {
  const labels = {
    completed: 'Terminée',
    running: 'En cours',
    failed: 'Échec',
    pending: 'En attente',
    cancelled: 'Annulée'
  }
  return labels[status] || status
}

function getStatusIcon(status) {
  if (status === 'completed') return IconCheck
  if (status === 'running') return IconClock
  if (status === 'failed') return IconError
  return IconClock
}

const IconCheck = {
  template: `<svg fill="currentColor" viewBox="0 0 20 20">
    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
  </svg>`
}

const IconClock = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>`
}

const IconError = {
  template: `<svg fill="currentColor" viewBox="0 0 20 20">
    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
  </svg>`
}
</script>
