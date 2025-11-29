<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">💾 Sauvegardes</h1>
        <p class="mt-1 text-sm text-gray-500">Sauvegarder vos VMs (espace occupé uniquement + configuration complète)</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
      >
        ➕ Nouvelle Sauvegarde
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Total Sauvegardes</p>
            <p class="text-2xl font-bold text-gray-900">{{ stats.total }}</p>
          </div>
          <div class="p-3 bg-blue-100 rounded-full">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Réussis</p>
            <p class="text-2xl font-bold text-green-600">{{ stats.completed }}</p>
          </div>
          <div class="p-3 bg-green-100 rounded-full">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">En cours</p>
            <p class="text-2xl font-bold text-blue-600">{{ stats.running }}</p>
          </div>
          <div class="p-3 bg-blue-100 rounded-full">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Échoués</p>
            <p class="text-2xl font-bold text-red-600">{{ stats.failed }}</p>
          </div>
          <div class="p-3 bg-red-100 rounded-full">
            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Exports List -->
    <div class="bg-white shadow rounded-lg overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Sauvegardes</h3>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">VM</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Emplacement</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taille</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progression</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-if="loading" class="text-center">
              <td colspan="7" class="px-6 py-4">
                <div class="flex justify-center">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              </td>
            </tr>
            <tr v-else-if="exportsWithProgress.length === 0">
              <td colspan="7" class="px-6 py-4 text-center text-gray-500">
                Aucune sauvegarde
              </td>
            </tr>
            <tr v-else v-for="exportJob in exportsWithProgress" :key="exportJob.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ exportJob.vm_name }}</div>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-500 max-w-xs truncate">{{ exportJob.export_location }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500">{{ formatSize(exportJob.export_size_mb) }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getStatusClass(exportJob.status)" class="px-2 py-1 text-xs font-semibold rounded-full">
                  {{ getStatusLabel(exportJob.status) }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="space-y-1">
                  <div class="flex items-center justify-between text-xs">
                    <span class="text-gray-600">
                      {{ exportJob.status === 'running' ?
                         (exportJob.progress_percentage < 10 ? 'Initialisation...' :
                          exportJob.progress_percentage < 85 ? 'Téléchargement...' :
                          exportJob.progress_percentage < 95 ? 'Finalisation...' : 'Vérification...')
                         : '' }}
                    </span>
                    <span class="font-medium text-gray-800">{{ exportJob.progress_percentage || 0 }}%</span>
                  </div>

                  <!-- Barre de progression -->
                  <div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      :class="getProgressBarClass(exportJob.status)"
                      class="h-2.5 rounded-full transition-all duration-300 ease-linear"
                      :style="{ width: exportJob.progress_percentage + '%' }"
                    ></div>
                  </div>

                  <!-- Détails de téléchargement (poids et vitesse) -->
                  <div v-if="exportJob.status === 'running' && exportJob.total_bytes > 0" class="text-xs text-gray-500 mt-1">
                    <div class="flex items-center justify-between">
                      <span>
                        📦 {{ formatBytes(exportJob.downloaded_bytes) }} / {{ formatBytes(exportJob.total_bytes) }}
                      </span>
                      <span v-if="exportJob.download_speed_mbps > 0" class="text-blue-600">
                        ⚡ {{ exportJob.download_speed_mbps }} MB/s
                      </span>
                    </div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(exportJob.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button
                  v-if="exportJob.status === 'running' || exportJob.status === 'pending'"
                  @click="cancelExport(exportJob.id)"
                  class="text-red-600 hover:text-red-900 mr-3"
                >
                  ✖ Annuler
                </button>
                <button
                  @click="deleteExport(exportJob.id)"
                  class="text-red-600 hover:text-red-900"
                >
                  🗑️ Supprimer
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create Export Modal -->
    <Modal :show="showCreateModal" title="Créer une Sauvegarde" @close="showCreateModal = false">
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div>
          <label class="label">Machine virtuelle</label>
          <select v-model="form.virtual_machine" required class="input-field" :disabled="creating">
            <option value="">Sélectionnez une VM</option>
            <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">
              {{ vm.name }} ({{ vm.guest_os }})
            </option>
          </select>
        </div>

        <!-- Format d'export (OVF ou OVA) -->
        <div class="border-2 rounded-lg p-4" :class="form.export_format === 'ova' ? 'border-green-500 bg-green-50' : 'border-gray-300'">
          <label class="label flex items-center">
            <svg class="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            Format de sauvegarde
          </label>
          <select v-model="form.export_format" required class="input-field mt-2" :disabled="creating">
            <option value="ova">✅ OVA - Archive unique (Recommandé)</option>
            <option value="ovf">📁 OVF - Multi-fichiers</option>
          </select>
          <div v-if="form.export_format === 'ova'" class="mt-2 p-3 bg-green-100 rounded-lg">
            <p class="text-sm text-green-800 font-medium">✅ Format OVA (Recommandé)</p>
            <ul class="mt-1 text-xs text-green-700 list-disc list-inside space-y-1">
              <li>Fichier unique (.ova) - facile à transférer</li>
              <li>Plus compact (archive TAR)</li>
              <li>Compatible tous outils VMware</li>
              <li>Idéal pour archivage et migration</li>
            </ul>
          </div>
          <div v-else class="mt-2 p-3 bg-blue-100 rounded-lg">
            <p class="text-sm text-blue-800 font-medium">📁 Format OVF</p>
            <ul class="mt-1 text-xs text-blue-700 list-disc list-inside space-y-1">
              <li>Plusieurs fichiers (.ovf, .vmdk, .mf)</li>
              <li>Permet modification avant import</li>
              <li>Utile pour personnalisation avancée</li>
            </ul>
          </div>
        </div>

        <div>
          <label class="label">Emplacement d'export</label>
          <input
            v-model="form.export_location"
            type="text"
            required
            class="input-field"
            :disabled="creating"
            placeholder="/mnt/exports ou D:\exports"
          />
          <p class="mt-1 text-sm text-gray-500">
            Chemin où la sauvegarde sera stockée
          </p>
        </div>

        <div class="flex items-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <svg class="w-5 h-5 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-blue-800">
            L'export sera exécuté en arrière-plan. Format OVF standard VMware pour migration.
          </p>
        </div>
      </form>

      <template #footer>
        <button type="button" @click="showCreateModal = false" class="btn-secondary" :disabled="creating">
          Annuler
        </button>
        <button
          type="button"
          @click="handleCreate"
          :disabled="creating"
          class="btn-primary flex items-center gap-2"
          :class="{ 'opacity-50 cursor-not-allowed': creating }"
        >
          <svg v-if="creating" class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>{{ creating ? 'Création en cours...' : 'Créer et démarrer' }}</span>
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useVMOperationsStore } from '@/stores/vmOperations'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import Modal from '@/components/common/Modal.vue'

const vmOpsStore = useVMOperationsStore()
const esxiStore = useEsxiStore()
const toast = useToastStore()

const showCreateModal = ref(false)
const creating = ref(false)  // Local loading state for modal
const form = ref({
  virtual_machine: '',
  export_format: 'ova',  // OVA par défaut (recommandé)
  export_location: '/mnt/exports'
})

// Progression réelle basée sur le téléchargement (règle de trois)
let statusCheckInterval = null

const exports = computed(() => vmOpsStore.ovfExports)
const loading = computed(() => vmOpsStore.loading)
const virtualMachines = computed(() => esxiStore.virtualMachines)

const stats = computed(() => {
  return {
    total: exports.value.length,
    completed: exports.value.filter(e => e.status === 'completed').length,
    running: exports.value.filter(e => e.status === 'running').length,
    failed: exports.value.filter(e => e.status === 'failed').length,
  }
})

// Exports avec progression réelle du backend (arrondis à l'entier)
const exportsWithProgress = computed(() => {
  return exports.value.map(exp => {
    return {
      ...exp,
      progress_percentage: Math.round(exp.progress_percentage || 0)
    }
  })
})

// Vérifie s'il y a des exports actifs
const hasActiveExports = computed(() => {
  return exports.value.some(e => e.status === 'running' || e.status === 'pending')
})

// Vérifier le statut réel périodiquement (progression réelle du backend)
function startStatusCheck() {
  if (statusCheckInterval) return

  statusCheckInterval = setInterval(async () => {
    if (hasActiveExports.value) {
      try {
        const { ovfExportsAPI } = await import('@/services/api')
        const response = await ovfExportsAPI.getAll()
        vmOpsStore.ovfExports = response.data
      } catch (error) {
        console.error('Erreur vérification statut:', error)
      }
    } else {
      stopStatusCheck()
    }
  }, 1000) // Vérifier toutes les secondes pour une progression fluide
}

function stopStatusCheck() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
    statusCheckInterval = null
  }
}

onMounted(async () => {
  await vmOpsStore.fetchOVFExports()
  await esxiStore.fetchVirtualMachines()

  // Démarrer le polling de progression réelle si il y a des exports actifs
  if (hasActiveExports.value) {
    startStatusCheck()
  }
})

onUnmounted(() => {
  stopStatusCheck()
})

async function handleCreate() {
  creating.value = true
  try {
    await vmOpsStore.createOVFExport(form.value)

    // Fermer le modal IMMÉDIATEMENT (l'export s'exécute en arrière-plan)
    showCreateModal.value = false
    creating.value = false

    // Notification de succès
    const selectedVM = virtualMachines.value.find(vm => vm.id === form.value.virtual_machine)
    const vmName = selectedVM ? selectedVM.name : 'VM'
    toast.success(`💾 Sauvegarde de "${vmName}" démarrée avec succès ! Suivez la progression ci-dessous.`, 5000)

    // Reset form
    form.value = { virtual_machine: '', export_format: 'ova', export_location: '/mnt/exports' }

    // Rafraîchir la liste pour obtenir le nouvel export
    await vmOpsStore.fetchOVFExports()

    // Démarrer le polling de progression réelle si pas déjà démarré
    if (!statusCheckInterval) {
      startStatusCheck()
    }
  } catch (error) {
    console.error('Erreur création export:', error)
    creating.value = false
    // Error toast is already shown by the store
    // Keep modal open to let user fix the issue or close manually
  }
}

async function cancelExport(id) {
  if (confirm('Voulez-vous vraiment annuler cet export ?')) {
    try {
      await vmOpsStore.cancelOVFExport(id)
    } catch (error) {
      console.error('Erreur annulation:', error)
    }
  }
}

async function deleteExport(id) {
  if (confirm('Voulez-vous vraiment supprimer cet export ?')) {
    try {
      await vmOpsStore.deleteOVFExport(id)
    } catch (error) {
      console.error('Erreur suppression:', error)
    }
  }
}

function getStatusClass(status) {
  const classes = {
    'pending': 'bg-yellow-100 text-yellow-800',
    'running': 'bg-blue-100 text-blue-800',
    'completed': 'bg-green-100 text-green-800',
    'failed': 'bg-red-100 text-red-800',
    'cancelled': 'bg-gray-100 text-gray-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getStatusLabel(status) {
  const labels = {
    'pending': 'En attente',
    'running': 'En cours',
    'completed': 'Terminé',
    'failed': 'Échoué',
    'cancelled': 'Annulé'
  }
  return labels[status] || status
}

function getProgressBarClass(status) {
  const classes = {
    'pending': 'bg-yellow-500',
    'running': 'bg-blue-500',
    'completed': 'bg-green-500',
    'failed': 'bg-red-500',
    'cancelled': 'bg-gray-500'
  }
  return classes[status] || 'bg-gray-500'
}

function formatSize(sizeMb) {
  if (!sizeMb || sizeMb === 0) return '-'
  if (sizeMb < 1024) return `${sizeMb.toFixed(2)} MB`
  return `${(sizeMb / 1024).toFixed(2)} GB`
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('fr-FR')
}
</script>

<style scoped>
.label {
  @apply block text-sm font-medium text-gray-700 mb-1;
}

.input-field {
  @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500;
}

.btn-primary {
  @apply px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors;
}

.btn-secondary {
  @apply px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors;
}
</style>
