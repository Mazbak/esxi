<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Sauvegardes</h1>
        <p class="mt-1 text-sm text-gray-500">Gérez vos jobs de sauvegarde</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvelle sauvegarde
      </button>
    </div>

    <!-- Statistics -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Total</p>
            <p class="mt-1 text-2xl font-bold">{{ statistics?.total_backups || 0 }}</p>
          </div>
          <div class="p-3 bg-blue-100 rounded-lg">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Réussies</p>
            <p class="mt-1 text-2xl font-bold text-green-600">{{ statistics?.completed || 0 }}</p>
          </div>
          <div class="p-3 bg-green-100 rounded-lg">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Échouées</p>
            <p class="mt-1 text-2xl font-bold text-red-600">{{ statistics?.failed || 0 }}</p>
          </div>
          <div class="p-3 bg-red-100 rounded-lg">
            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Taille totale</p>
            <p class="mt-1 text-2xl font-bold text-purple-600">{{ statistics?.total_size_gb || 0 }} GB</p>
          </div>
          <div class="p-3 bg-purple-100 rounded-lg">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="flex items-center space-x-4">
        <div class="flex-1">
          <label class="text-sm font-medium text-gray-700 mr-2">Statut:</label>
          <select v-model="statusFilter" class="input-field inline-block w-auto">
            <option value="">Tous</option>
            <option value="pending">En attente</option>
            <option value="running">En cours</option>
            <option value="completed">Terminé</option>
            <option value="failed">Échoué</option>
            <option value="cancelled">Annulé</option>
          </select>
        </div>
        <div class="flex-1">
          <label class="text-sm font-medium text-gray-700 mr-2">Type:</label>
          <select v-model="typeFilter" class="input-field inline-block w-auto">
            <option value="">Tous</option>
            <option value="full">Complète</option>
            <option value="incremental">Incrémentale</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <Loading v-if="loading && jobs.length === 0" text="Chargement des sauvegardes..." />

    <!-- Backups List -->
    <div v-else-if="filteredJobs.length > 0" class="space-y-4">
      <div
        v-for="job in filteredJobs"
        :key="job.id"
        class="card hover:shadow-lg transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-start space-x-4 flex-1">
            <div :class="getStatusColor(job.status)" class="p-3 rounded-lg">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div class="flex-1">
              <div class="flex items-center space-x-3">
                <h3 class="text-lg font-semibold text-gray-900">{{ getVMName(job.virtual_machine) }}</h3>
                <span :class="getStatusBadgeClass(job.status)" class="badge">
                  {{ getStatusLabel(job.status) }}
                </span>
                <span :class="getTypeBadgeClass(job.backup_type)" class="badge">
                  {{ getTypeLabel(job.backup_type) }}
                </span>
              </div>
              <div class="mt-2 space-y-1 text-sm text-gray-600">
                <p>
                  <span class="font-medium">Créé:</span> {{ formatDate(job.created_at) }}
                </p>
                <p v-if="job.started_at">
                  <span class="font-medium">Démarré:</span> {{ formatDate(job.started_at) }}
                </p>
                <p v-if="job.completed_at">
                  <span class="font-medium">Terminé:</span> {{ formatDate(job.completed_at) }}
                </p>
                <p v-if="job.duration_seconds">
                  <span class="font-medium">Durée:</span> {{ formatDuration(job.duration_seconds) }}
                </p>
                <p v-if="job.backup_size_mb">
                  <span class="font-medium">Taille:</span> {{ formatSize(job.backup_size_mb) }}
                </p>
                <p v-if="job.backup_location">
                  <span class="font-medium">Emplacement:</span>
                  <code class="px-2 py-1 bg-gray-100 rounded text-xs">{{ job.backup_location }}</code>
                </p>
                <p v-if="job.snapshot_name">
                  <span class="font-medium">Snapshot:</span>
                  <code class="px-2 py-1 bg-gray-100 rounded text-xs">{{ job.snapshot_name }}</code>
                </p>
                <p v-if="job.base_backup" class="flex items-center">
                  <span class="font-medium">Basée sur:</span>
                  <span class="ml-2 text-blue-600">Sauvegarde #{{ job.base_backup }}</span>
                  <svg class="w-4 h-4 ml-1 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </p>
                <p v-if="job.vmdk_files && job.vmdk_files.length > 0">
                  <span class="font-medium">VMDKs:</span>
                  <span class="ml-2 text-gray-700">{{ job.vmdk_files.length }} fichier(s)</span>
                </p>
              </div>

              <!-- Progress bar for running jobs -->
              <div v-if="job.status === 'running'" class="mt-4">
                <div class="flex items-center justify-between text-sm mb-1">
                  <span class="text-gray-600">Progression</span>
                  <span class="text-gray-900 font-medium">
                    {{ job.progress_percentage < 20 ? 'Création snapshot...' :
                       job.progress_percentage < 70 ? 'Téléchargement VMDK...' :
                       job.progress_percentage < 90 ? 'Configuration...' : 'Finalisation...' }}
                  </span>
                </div>
                <div class="flex items-center gap-3">
                  <div class="flex-1 bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      class="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-linear"
                      :style="`width: ${job.progress_percentage || 0}%`"
                    ></div>
                  </div>
                  <span class="text-sm font-semibold text-blue-600 min-w-[3rem] text-right">
                    {{ job.progress_percentage || 0 }}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center space-x-2 ml-4">
            <button
              v-if="job.status === 'running' || job.status === 'pending'"
              @click="cancelJob(job)"
              class="btn-danger text-sm"
            >
              <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Annuler
            </button>
            <button
              @click="deleteJob(job)"
              class="p-2 text-red-600 hover:bg-red-50 rounded-lg"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <svg class="w-24 h-24 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Aucune sauvegarde</h3>
      <p class="text-gray-500 mb-4">Créez votre première sauvegarde</p>
      <button @click="showCreateModal = true" class="btn-primary">
        Nouvelle sauvegarde
      </button>
    </div>

    <!-- Create Modal -->
    <BackupJobForm
      :show="showCreateModal"
      @close="showCreateModal = false"
      @submit="handleCreateJob"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useVMOperationsStore } from '@/stores/vmOperations'
import { useOperationsStore } from '@/stores/operations'  // Store de persistance
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import Loading from '@/components/common/Loading.vue'
import BackupJobForm from '@/components/backups/BackupJobForm.vue'

const vmOpsStore = useVMOperationsStore()
const operationsStore = useOperationsStore()  // Store de persistance
const esxiStore = useEsxiStore()
const toast = useToastStore()

const showCreateModal = ref(false)
const statusFilter = ref('')
const typeFilter = ref('')

// Tracker pour les jobs déjà notifiés
const notifiedFailedJobs = ref(new Set())

const jobs = computed(() => vmOpsStore.vmBackups)
const loading = computed(() => vmOpsStore.loading)
const virtualMachines = computed(() => esxiStore.virtualMachines)

const statistics = computed(() => {
  const backups = jobs.value
  return {
    total_backups: backups.length,
    completed: backups.filter(b => b.status === 'completed').length,
    failed: backups.filter(b => b.status === 'failed').length,
    total_size_gb: (backups.reduce((sum, b) => sum + (b.backup_size_mb || 0), 0) / 1024).toFixed(2)
  }
})

const filteredJobs = computed(() => {
  let filtered = jobs.value

  if (statusFilter.value) {
    filtered = filtered.filter(j => j.status === statusFilter.value)
  }

  if (typeFilter.value) {
    filtered = filtered.filter(j => j.backup_type === typeFilter.value)
  }

  return filtered
})

let refreshInterval = null

onMounted(async () => {
  // Charger les données initiales
  await Promise.all([
    vmOpsStore.fetchVMBackups(),
    esxiStore.fetchVirtualMachines()
  ])

  // Restaurer les backups en cours depuis le store de persistance
  setTimeout(() => {
    const activeBackups = operationsStore.getOperationsByType('backup')
    console.log('[BACKUP-RESTORE] Backups actifs trouvés dans le store:', activeBackups.length)

    if (activeBackups.length > 0) {
      activeBackups.forEach(op => {
        console.log('[BACKUP-RESTORE] Backup actif:', op.id, 'Status:', op.status, 'Progress:', op.progress)

        // Vérifier si le job existe encore dans la liste
        const job = jobs.value.find(j => j.id === op.id)
        if (!job) {
          console.log('[BACKUP-RESTORE] Job introuvable, suppression du store')
          operationsStore.removeOperation('backup', op.id)
        } else if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
          console.log('[BACKUP-RESTORE] Job terminé, suppression du store')
          operationsStore.removeOperation('backup', op.id)
        } else {
          console.log('[BACKUP-RESTORE] ✓ Job toujours actif, barre de progression restaurée')
        }
      })
    }
  }, 500)

  // Auto-refresh pour les jobs en cours ou en attente
  refreshInterval = setInterval(async () => {
    const hasActiveJobs = jobs.value.some(j => j.status === 'running' || j.status === 'pending')
    if (hasActiveJobs) {
      // Rafraîchir silencieusement (sans spinner) pour une progression fluide
      try {
        // Utiliser l'API configurée avec authentification
        const { vmBackupsAPI } = await import('@/services/api')
        const response = await vmBackupsAPI.getAll()
        vmOpsStore.vmBackups = response.data
      } catch (error) {
        console.error('Erreur rafraîchissement:', error)
      }
    }
  }, 250) // Rafraîchir toutes les 250ms pour une progression ultra-fluide (1%, 2%, 3%...)
})

// Nettoyer l'intervalle lors du démontage du composant
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// Watcher pour détecter les jobs échoués et afficher l'erreur dans un toast
// ET pour sauvegarder les jobs actifs dans le operationsStore
watch(jobs, (newJobs) => {
  newJobs.forEach(job => {
    // Si le job a échoué et qu'on ne l'a pas encore notifié
    if (job.status === 'failed' && !notifiedFailedJobs.value.has(job.id)) {
      notifiedFailedJobs.value.add(job.id)

      // Afficher l'erreur dans un toast
      const errorMsg = job.error_message || 'Une erreur est survenue lors de la sauvegarde'
      toast.error(`❌ Sauvegarde échouée: ${errorMsg}`, 10000) // 10 secondes pour laisser le temps de lire

      // Retirer du store de persistance
      operationsStore.removeOperation('backup', job.id)
    }

    // Sauvegarder dans le store de persistance si job actif
    if (job.status === 'running' || job.status === 'pending') {
      operationsStore.setOperation('backup', job.id, {
        status: job.status,
        progress: job.progress || 0,
        vm_name: job.virtual_machine_name || job.virtual_machine?.name,
        type_display: job.backup_type,
        message: `Sauvegarde ${job.backup_type} en cours...`
      })
    } else if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      // Retirer du store si terminé
      operationsStore.removeOperation('backup', job.id)
    }
  })
}, { deep: true })

async function handleCreateJob(formData) {
  try {
    await vmOpsStore.createVMBackup(formData)

    // Fermer le modal IMMÉDIATEMENT (le backup s'exécute en arrière-plan)
    showCreateModal.value = false

    // RAFRAÎCHIR IMMÉDIATEMENT la liste pour afficher le nouveau backup
    await vmOpsStore.fetchVMBackups()

    // Notification de succès
    const selectedVM = virtualMachines.value.find(vm => vm.id === formData.virtual_machine)
    const vmName = selectedVM ? selectedVM.name : 'VM'
    const backupType = formData.backup_type === 'full' ? 'complète' : 'incrémentale'

    toast.success(`🚀 Sauvegarde ${backupType} de "${vmName}" démarrée avec succès ! Suivez la progression ci-dessous.`, 5000)
  } catch (err) {
    toast.error('Erreur lors de la création: ' + (err.response?.data?.message || err.message))
  }
}

async function cancelJob(job) {
  if (confirm('Voulez-vous vraiment annuler cette sauvegarde?')) {
    try {
      await vmOpsStore.cancelVMBackup(job.id)
      // Rafraîchir immédiatement pour voir le changement de status
      await vmOpsStore.fetchVMBackups()
    } catch (err) {
      toast.error(`Erreur lors de l'annulation: ${err.response?.data?.message || err.message}`)
    }
  }
}

async function deleteJob(job) {
  if (confirm('Voulez-vous vraiment supprimer cette sauvegarde?')) {
    try {
      await vmOpsStore.deleteVMBackup(job.id)
    } catch (err) {
      toast.error(`Erreur lors de la suppression: ${err.response?.data?.message || err.message}`)
    }
  }
}

function getVMName(vmId) {
  const vm = virtualMachines.value.find(v => v.id === vmId)
  return vm ? vm.name : `VM #${vmId}`
}

function formatDate(date) {
  if (!date) return '-'
  return format(new Date(date), 'dd MMM yyyy HH:mm', { locale: fr })
}

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`
  if (minutes > 0) return `${minutes}m ${secs}s`
  return `${secs}s`
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

function getTypeBadgeClass(type) {
  return type === 'full' ? 'badge-info' : 'badge-warning'
}

function getTypeLabel(type) {
  return type === 'full' ? 'Complète' : 'Incrémentale'
}
</script>
