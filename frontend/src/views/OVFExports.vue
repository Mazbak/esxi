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
          <label class="label">Machine virtuelle <span class="text-red-500">*</span></label>
          <select v-model="form.virtual_machine" @change="onVMChange" required class="input-field" :disabled="creating">
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
            Format de sauvegarde <span class="text-red-500 ml-1">*</span>
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
          <label class="label">Emplacement de sauvegarde <span class="text-red-500">*</span></label>

          <!-- Sélecteur de chemins prédéfinis -->
          <div v-if="storagePaths.length > 0" class="mb-2">
            <select
              @change="selectStoragePath"
              class="input-field text-sm"
              :disabled="creating"
            >
              <option value="">📁 Choisir un chemin prédéfini...</option>
              <option
                v-for="path in storagePaths"
                :key="path.id"
                :value="path.path"
              >
                {{ path.name }} - {{ path.path }}
              </option>
            </select>
          </div>

          <!-- Champ manuel -->
          <input
            v-model="form.export_location"
            type="text"
            required
            class="input-field"
            :disabled="creating"
            placeholder="/mnt/backups ou /mnt/smb-share ou \\serveur\partage"
          />
          <p class="mt-1 text-sm text-gray-500">
            <span v-if="storagePaths.length > 0">Sélectionnez un chemin prédéfini ou saisissez manuellement. </span>
            Disque monté, partage SMB, disque iSCSI, NFS, ou tout chemin accessible
          </p>
        </div>

        <div class="flex items-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <svg class="w-5 h-5 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-blue-800">
            La sauvegarde sera exécutée en arrière-plan. Format OVF standard VMware pour migration.
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

    <!-- Power Warning Modal -->
    <div v-if="showPowerWarning" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="closePowerWarning">
      <div class="bg-white rounded-lg shadow-2xl max-w-lg w-full mx-4">
        <div class="p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="flex-shrink-0 w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
              <svg class="w-6 h-6 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900">⚠️ VM en fonctionnement</h3>
          </div>

          <div class="space-y-4 mb-6">
            <p class="text-gray-700">
              La machine virtuelle <strong>{{ selectedVMName }}</strong> est actuellement <strong class="text-green-600">allumée</strong>.
            </p>

            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p class="text-sm text-blue-900 font-medium mb-2">💡 Recommandation :</p>
              <p class="text-sm text-blue-800">
                Pour garantir l'intégrité et la cohérence de la sauvegarde, il est fortement recommandé d'éteindre la VM avant de procéder.
              </p>
            </div>

            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p class="text-sm text-yellow-900 font-medium mb-2">⚠️ Risques si vous continuez sans éteindre :</p>
              <ul class="text-sm text-yellow-800 list-disc list-inside space-y-1">
                <li>Incohérence des données en cours d'écriture</li>
                <li>Corruption potentielle de la sauvegarde</li>
                <li>Restauration incomplète possible</li>
              </ul>
            </div>
          </div>

          <div class="space-y-3">
            <button
              @click="powerOffAndExport"
              :disabled="poweringOff"
              class="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-lg transition-colors"
            >
              <svg v-if="poweringOff" class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>{{ poweringOff ? 'Extinction en cours...' : '✅ Éteindre la VM puis sauvegarder' }}</span>
            </button>

            <button
              @click="closePowerWarning"
              :disabled="poweringOff"
              class="w-full px-4 py-3 bg-gray-200 hover:bg-gray-300 disabled:bg-gray-100 text-gray-700 font-semibold rounded-lg transition-colors"
            >
              Annuler
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useVMOperationsStore } from '@/stores/vmOperations'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import { storagePathsAPI } from '@/services/api'
import Modal from '@/components/common/Modal.vue'

const vmOpsStore = useVMOperationsStore()
const esxiStore = useEsxiStore()
const toast = useToastStore()

const showCreateModal = ref(false)
const creating = ref(false)  // Local loading state for modal
const storagePaths = ref([])  // Chemins de sauvegarde prédéfinis
const showPowerWarning = ref(false)
const poweringOff = ref(false)
const selectedVM = ref(null)
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

const selectedVMName = computed(() => selectedVM.value?.name || '')

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
  await loadStoragePaths()  // Charger les chemins de sauvegarde prédéfinis

  // Démarrer le polling de progression réelle si il y a des exports actifs
  if (hasActiveExports.value) {
    startStatusCheck()
  }
})

onUnmounted(() => {
  stopStatusCheck()
})

// Vérifier l'état de la VM sélectionnée
async function onVMChange() {
  if (form.value.virtual_machine) {
    selectedVM.value = virtualMachines.value.find(vm => vm.id === form.value.virtual_machine)
    console.log('🔄 OVFExport - VM sélectionnée (cache):', selectedVM.value)

    // Récupérer l'état en temps réel depuis ESXi
    try {
      const { virtualMachinesAPI } = await import('@/services/api')
      const response = await virtualMachinesAPI.getById(form.value.virtual_machine)
      const vmRealTime = response.data

      console.log('🔄 OVFExport - VM état temps réel:', vmRealTime)
      console.log('🔄 OVFExport - power_state temps réel:', vmRealTime.power_state)

      // Mettre à jour avec les données temps réel
      selectedVM.value = vmRealTime
    } catch (error) {
      console.error('❌ Erreur récupération état VM:', error)
      // Utiliser les données du cache si erreur
    }
  } else {
    selectedVM.value = null
  }
}

async function handleCreate() {
  // Valider tous les champs obligatoires
  if (!form.value.virtual_machine) {
    toast.error('Veuillez sélectionner une machine virtuelle')
    return
  }
  if (!form.value.export_format) {
    toast.error('Veuillez sélectionner un format de sauvegarde')
    return
  }
  if (!form.value.export_location || form.value.export_location.trim() === '') {
    toast.error('Veuillez saisir un emplacement de sauvegarde')
    return
  }

  // Vérifier si la VM est allumée
  if (selectedVM.value && selectedVM.value.power_state === 'poweredOn') {
    console.log('⚠️ VM allumée détectée, affichage du modal d\'avertissement')

    // Fermer le modal de création AVANT d'afficher le modal d'avertissement
    showCreateModal.value = false

    // Attendre un peu pour que l'animation de fermeture se termine
    await new Promise(resolve => setTimeout(resolve, 100))

    // Afficher le modal d'avertissement
    showPowerWarning.value = true
    return
  }

  console.log('✅ VM éteinte ou état inconnu, démarrage de l\'export')
  await executeExport()
}

async function executeExport() {
  creating.value = true
  try {
    await vmOpsStore.createOVFExport(form.value)

    // Fermer le modal IMMÉDIATEMENT (l'export s'exécute en arrière-plan)
    showCreateModal.value = false
    creating.value = false

    // Notification de succès
    const selectedVMData = virtualMachines.value.find(vm => vm.id === form.value.virtual_machine)
    const vmName = selectedVMData ? selectedVMData.name : 'VM'
    toast.success(`💾 Sauvegarde de "${vmName}" démarrée avec succès ! Suivez la progression ci-dessous.`, 5000)

    // Reset form
    form.value = { virtual_machine: '', export_format: 'ova', export_location: '/mnt/exports' }
    selectedVM.value = null

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

// Éteindre la VM puis lancer l'export
async function powerOffAndExport() {
  poweringOff.value = true

  try {
    console.log('🔌 Extinction de la VM:', selectedVM.value.id)
    const response = await esxiStore.powerOffVM(selectedVM.value.id)

    if (response.success) {
      toast.success(`✅ VM "${selectedVM.value.name}" éteinte avec succès`, 3000)

      // Attendre 3 secondes pour que l'extinction soit effective
      await new Promise(resolve => setTimeout(resolve, 3000))

      // Fermer le modal d'avertissement
      showPowerWarning.value = false
      poweringOff.value = false

      // Lancer l'export
      await executeExport()
    } else {
      throw new Error(response.message || 'Échec de l\'extinction de la VM')
    }
  } catch (error) {
    console.error('❌ Erreur extinction VM:', error)
    toast.error(error.response?.data?.error || error.message || 'Erreur lors de l\'extinction de la VM')
    poweringOff.value = false
  }
}

// Fermer le modal d'avertissement et rouvrir le modal de création
function closePowerWarning() {
  console.log('❌ Utilisateur annule l\'export')
  showPowerWarning.value = false
  poweringOff.value = false

  // Rouvrir le modal de création
  setTimeout(() => {
    showCreateModal.value = true
  }, 100)
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

// Charger les chemins de sauvegarde prédéfinis (actifs uniquement)
async function loadStoragePaths() {
  try {
    const response = await storagePathsAPI.getActive()
    storagePaths.value = response.data

    // Si un chemin par défaut existe, le pré-sélectionner
    const defaultPath = storagePaths.value.find(p => p.is_default)
    if (defaultPath) {
      form.value.export_location = defaultPath.path
    }
  } catch (err) {
    console.error('Erreur chargement chemins:', err)
    // Pas d'erreur toast, c'est optionnel
  }
}

// Sélectionner un chemin prédéfini
function selectStoragePath(event) {
  const selectedPath = event.target.value
  if (selectedPath) {
    form.value.export_location = selectedPath
  }
  // Reset le select après sélection
  event.target.value = ''
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
