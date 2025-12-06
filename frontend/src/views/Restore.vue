<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">🔄 Restauration</h1>
        <p class="mt-1 text-sm text-gray-500">Restaurer une VM depuis une sauvegarde OVF/OVA</p>
      </div>
    </div>

    <!-- Formulaire de Restauration -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-6">Restaurer une Sauvegarde</h2>

      <form @submit.prevent="handleRestore" class="space-y-6">
        <!-- Fichier OVF/OVA -->
        <div>
          <label class="label">Fichier de sauvegarde (OVF ou OVA)</label>

          <!-- Affichage du fichier sélectionné ou bouton de sélection -->
          <div v-if="form.ovf_path" class="mb-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <div>
                  <p class="font-medium text-gray-900">{{ selectedBackupName }}</p>
                  <p class="text-sm text-gray-600">{{ form.ovf_path }}</p>
                </div>
              </div>
              <button
                type="button"
                @click="clearSelection"
                class="text-gray-400 hover:text-gray-600"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <button
            type="button"
            @click="openFileBrowser"
            class="btn-secondary w-full flex items-center justify-center gap-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            {{ form.ovf_path ? 'Changer de sauvegarde' : 'Choisir la sauvegarde' }}
          </button>

          <p class="mt-2 text-sm text-gray-500">
            Cliquez pour parcourir toutes les sauvegardes disponibles
          </p>
        </div>

        <!-- Serveur ESXi de destination -->
        <div>
          <label class="label">Serveur ESXi de destination</label>
          <select v-model="form.esxi_server_id" @change="loadDatastores" required class="input-field">
            <option value="">Sélectionnez un serveur ESXi</option>
            <option v-for="server in servers" :key="server.id" :value="server.id">
              {{ server.name || server.hostname }} ({{ server.hostname }})
            </option>
          </select>
          <p class="mt-1 text-sm text-gray-500">
            Serveur où la VM sera restaurée
          </p>
        </div>

        <!-- Nom de la VM restaurée -->
        <div>
          <label class="label">Nom de la VM restaurée</label>
          <input
            v-model="form.vm_name"
            type="text"
            required
            class="input-field"
            placeholder="Ma-VM-Restaurée"
          />
          <p class="mt-1 text-sm text-gray-500">
            Nom que portera la VM restaurée
          </p>
        </div>

        <!-- Datastore -->
        <div>
          <label class="label">Datastore de destination</label>
          <select v-model="form.datastore_name" :disabled="!form.esxi_server_id" required class="input-field">
            <option value="">{{ form.esxi_server_id ? 'Sélectionnez un datastore' : 'Sélectionnez d\'abord un serveur' }}</option>
            <option v-for="ds in datastores" :key="ds.name" :value="ds.name">
              {{ ds.name }} ({{ ds.free_space }} GB libre / {{ ds.capacity }} GB total)
            </option>
          </select>
          <p class="mt-1 text-sm text-gray-500">
            Emplacement de stockage sur le serveur ESXi
          </p>
        </div>

        <!-- Réseau -->
        <div>
          <label class="label">Réseau (optionnel)</label>
          <select v-model="form.network_name" :disabled="!form.esxi_server_id" class="input-field">
            <option value="VM Network">{{ form.esxi_server_id ? 'VM Network (défaut)' : 'Sélectionnez d\'abord un serveur' }}</option>
            <option v-for="net in networks" :key="net.name" :value="net.name">
              {{ net.name }}
            </option>
          </select>
          <p class="mt-1 text-sm text-gray-500">
            Réseau auquel connecter la VM (défaut: VM Network)
          </p>
        </div>

        <!-- Power ON -->
        <div class="flex items-center">
          <input
            v-model="form.power_on"
            type="checkbox"
            id="power_on"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label for="power_on" class="ml-2 block text-sm text-gray-900">
            Démarrer la VM après restauration
          </label>
        </div>

        <!-- Info Box -->
        <div class="flex items-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <svg class="w-5 h-5 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
          <div class="text-sm text-blue-800">
            <p class="font-medium">La restauration peut prendre plusieurs minutes</p>
            <p class="mt-1">Les fichiers OVF/OVA seront déployés sur le serveur ESXi sélectionné.</p>
          </div>
        </div>

        <!-- Error Display -->
        <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-sm text-red-800">{{ error }}</p>
        </div>

        <!-- Success Display -->
        <div v-if="success" class="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p class="text-sm text-green-800">{{ success }}</p>
        </div>

        <!-- Progress Display -->
        <div v-if="isRestoring" class="p-6 bg-blue-50 border border-blue-200 rounded-lg space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <svg class="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <div>
                <p class="text-sm font-medium text-blue-900">Restauration en cours...</p>
                <p class="text-xs text-blue-700 mt-1">{{ restoreMessage }}</p>
              </div>
            </div>
            <span class="text-2xl font-bold text-blue-600">{{ restoreProgress }}%</span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
            <div
              class="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
              :style="{ width: restoreProgress + '%' }"
            ></div>
          </div>

          <!-- Progress Details -->
          <div class="flex items-center justify-between text-xs text-blue-700">
            <span>{{ form.vm_name }}</span>
            <span>{{ restoreStatus }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-4">
          <button
            type="submit"
            :disabled="loading"
            class="btn-primary flex items-center gap-2"
            :class="{ 'opacity-50 cursor-not-allowed': loading }"
          >
            <svg v-if="loading" class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>{{ loading ? 'Restauration en cours...' : '🔄 Restaurer la VM' }}</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Guide Rapide -->
    <div class="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
      <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <svg class="w-5 h-5 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Guide Rapide
      </h3>
      <div class="space-y-3 text-sm text-gray-700">
        <div class="flex items-start">
          <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-blue-600 text-white rounded-full text-xs font-bold mr-3">1</span>
          <div>
            <p class="font-medium">Trouvez votre fichier de sauvegarde</p>
            <p class="text-gray-600">Fichier .ova (archive unique) ou .ovf (dans un dossier)</p>
          </div>
        </div>
        <div class="flex items-start">
          <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-blue-600 text-white rounded-full text-xs font-bold mr-3">2</span>
          <div>
            <p class="font-medium">Sélectionnez le serveur ESXi de destination</p>
            <p class="text-gray-600">Choisissez où restaurer la VM</p>
          </div>
        </div>
        <div class="flex items-start">
          <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-blue-600 text-white rounded-full text-xs font-bold mr-3">3</span>
          <div>
            <p class="font-medium">Configurez et restaurez</p>
            <p class="text-gray-600">Donnez un nom, choisissez le datastore et lancez la restauration</p>
          </div>
        </div>
      </div>
    </div>

    <!-- File Browser Modal -->
    <div v-if="showFileBrowser" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] flex flex-col">
        <!-- Header -->
        <div class="p-6 border-b space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900">📁 Parcourir les sauvegardes</h3>
            <button
              @click="closeFileBrowser"
              class="text-gray-400 hover:text-gray-600"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Search Field -->
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Rechercher une sauvegarde par nom..."
              class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="loadingFiles" class="flex items-center justify-center py-12">
            <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="ml-3 text-gray-600">Chargement des fichiers...</span>
          </div>

          <div v-else-if="filteredBackupFiles.length === 0" class="text-center py-12">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="mt-4 text-gray-500">
              {{ searchQuery ? 'Aucun résultat trouvé' : 'Aucun fichier de sauvegarde trouvé' }}
            </p>
            <p class="mt-2 text-sm text-gray-400">
              {{ searchQuery ? 'Essayez avec un autre terme de recherche' : 'Vérifiez que les chemins de stockage sont configurés' }}
            </p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="file in filteredBackupFiles"
              :key="file.path"
              @click="selectBackupFile(file)"
              class="flex items-center justify-between p-4 border rounded-lg hover:bg-blue-50 hover:border-blue-300 cursor-pointer transition"
              :class="{ 'bg-blue-50 border-blue-300': form.ovf_path === file.path }"
            >
              <div class="flex items-center flex-1">
                <div class="flex-shrink-0">
                  <svg class="w-8 h-8" :class="file.type === 'ova' ? 'text-blue-600' : 'text-green-600'" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-4 flex-1">
                  <p class="text-sm font-medium text-gray-900">{{ file.name }}</p>
                  <p class="text-xs text-gray-500 mt-1">{{ file.path }}</p>
                  <div class="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span class="flex items-center">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mr-2"
                        :class="file.type === 'ova' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'">
                        {{ file.type.toUpperCase() }}
                      </span>
                    </span>
                    <span>{{ file.size_mb.toFixed(2) }} MB</span>
                    <span>{{ formatDate(file.modified) }}</span>
                  </div>
                </div>
              </div>
              <div v-if="form.ovf_path === file.path" class="flex-shrink-0 ml-4">
                <svg class="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between p-6 border-t bg-gray-50">
          <p class="text-sm text-gray-600">
            {{ filteredBackupFiles.length }} fichier(s) trouvé(s)
            <span v-if="searchQuery && filteredBackupFiles.length < backupFiles.length" class="text-gray-400">
              sur {{ backupFiles.length }} au total
            </span>
          </p>
          <div class="flex gap-3">
            <button
              type="button"
              @click="closeFileBrowser"
              class="btn-secondary"
            >
              Annuler
            </button>
            <button
              type="button"
              @click="confirmFileSelection"
              :disabled="!form.ovf_path"
              class="btn-primary"
              :class="{ 'opacity-50 cursor-not-allowed': !form.ovf_path }"
            >
              Sélectionner
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import { restoreAPI, storagePathsAPI, esxiServersAPI } from '@/services/api'

const esxiStore = useEsxiStore()
const toast = useToastStore()

const loading = ref(false)
const error = ref(null)
const success = ref(null)
const datastores = ref([])
const networks = ref([])
const storagePaths = ref([])  // Chemins de sauvegarde prédéfinis
const showFileBrowser = ref(false)
const loadingFiles = ref(false)
const backupFiles = ref([])
const searchQuery = ref('')
const restoreProgress = ref(0)
const restoreStatus = ref('')
const restoreMessage = ref('')
const isRestoring = ref(false)

const form = reactive({
  ovf_path: '',
  esxi_server_id: '',
  vm_name: '',
  datastore_name: '',
  network_name: 'VM Network',
  power_on: false
})

const servers = computed(() => esxiStore.servers)

// Computed property pour filtrer les sauvegardes selon la recherche
const filteredBackupFiles = computed(() => {
  if (!searchQuery.value.trim()) {
    return backupFiles.value
  }

  const query = searchQuery.value.toLowerCase()
  return backupFiles.value.filter(file =>
    file.name.toLowerCase().includes(query) ||
    file.path.toLowerCase().includes(query)
  )
})

// Computed property pour le nom du fichier sélectionné
const selectedBackupName = computed(() => {
  if (!form.ovf_path) return ''
  const file = backupFiles.value.find(f => f.path === form.ovf_path)
  return file ? file.name : form.ovf_path.split('/').pop()
})

onMounted(async () => {
  // Charger les serveurs ESXi
  if (servers.value.length === 0) {
    await esxiStore.fetchServers()
  }
  // Charger les chemins de sauvegarde prédéfinis
  await loadStoragePaths()
})

async function loadDatastores() {
  if (!form.esxi_server_id) return

  try {
    // Charger les datastores directement depuis l'API ESXi
    const response = await esxiServersAPI.getDatastores(form.esxi_server_id)
    datastores.value = response.data.datastores.map(ds => ({
      name: ds.name,
      capacity: ds.capacity_gb,
      free_space: ds.free_space_gb
    }))

    // Charger également les réseaux
    await loadNetworks()
  } catch (err) {
    console.error('Erreur chargement datastores:', err)
    toast.error('Erreur lors du chargement des datastores')
  }
}

async function loadNetworks() {
  if (!form.esxi_server_id) return

  try {
    // Charger les réseaux directement depuis l'API ESXi
    const response = await esxiServersAPI.getNetworks(form.esxi_server_id)
    networks.value = response.data.networks || []
  } catch (err) {
    console.error('Erreur chargement réseaux:', err)
    toast.error('Erreur lors du chargement des réseaux')
  }
}

async function handleRestore() {
  error.value = null
  success.value = null
  loading.value = true
  isRestoring.value = true
  restoreProgress.value = 0
  restoreStatus.value = 'starting'
  restoreMessage.value = 'Démarrage de la restauration...'

  let pollInterval = null

  try {
    // Appeler l'API de restauration
    const payload = {
      ovf_path: form.ovf_path,
      vm_name: form.vm_name,
      datastore_name: form.datastore_name,
      network_name: form.network_name || 'VM Network',
      power_on: form.power_on
    }

    // Trouver le serveur sélectionné
    const selectedServer = servers.value.find(s => s.id === form.esxi_server_id)
    if (!selectedServer) {
      throw new Error('Serveur ESXi introuvable')
    }

    // Appeler l'API de restauration OVF sur le serveur ESXi
    const response = await esxiServersAPI.restoreOVF(selectedServer.id, payload)

    // Si on a un restore_id, démarrer le polling de la progression
    if (response.data.restore_id) {
      const restoreId = response.data.restore_id

      // Polling toutes les 500ms pour récupérer la progression
      pollInterval = setInterval(async () => {
        try {
          const progressResponse = await esxiServersAPI.getRestoreProgress(restoreId)
          const progressData = progressResponse.data

          restoreProgress.value = progressData.progress
          restoreStatus.value = progressData.status
          restoreMessage.value = progressData.message

          // Arrêter le polling si terminé ou en erreur
          if (progressData.status === 'completed' || progressData.status === 'error') {
            clearInterval(pollInterval)
            isRestoring.value = false

            if (progressData.status === 'completed') {
              success.value = `✅ Restauration réussie ! VM "${form.vm_name}" déployée avec succès.`
              toast.success(`VM "${form.vm_name}" restaurée avec succès !`, 5000)

              // Réinitialiser le formulaire après succès
              setTimeout(() => {
                resetForm()
              }, 2000)
            } else if (progressData.status === 'error') {
              throw new Error(progressData.message)
            }
          }
        } catch (pollErr) {
          console.error('Erreur polling progression:', pollErr)
          clearInterval(pollInterval)
          isRestoring.value = false
        }
      }, 500)
    } else {
      // Pas de restore_id, succès immédiat (ancien comportement)
      success.value = `✅ Restauration réussie ! VM "${form.vm_name}" déployée avec succès.`
      toast.success(`VM "${form.vm_name}" restaurée avec succès !`, 5000)
      isRestoring.value = false

      setTimeout(() => {
        resetForm()
      }, 2000)
    }

  } catch (err) {
    if (pollInterval) clearInterval(pollInterval)
    isRestoring.value = false
    error.value = err.response?.data?.error || err.message || 'Erreur lors de la restauration'
    toast.error(`Erreur: ${error.value}`)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.ovf_path = ''
  form.esxi_server_id = ''
  form.vm_name = ''
  form.datastore_name = ''
  form.network_name = 'VM Network'
  form.power_on = false
  error.value = null
  success.value = null
  datastores.value = []
  restoreProgress.value = 0
  restoreStatus.value = ''
  restoreMessage.value = ''
  isRestoring.value = false
}

// Charger les chemins de sauvegarde prédéfinis (actifs uniquement)
async function loadStoragePaths() {
  try {
    const response = await storagePathsAPI.getActive()
    storagePaths.value = response.data

    // Si un chemin par défaut existe, le pré-remplir
    const defaultPath = storagePaths.value.find(p => p.is_default)
    if (defaultPath) {
      form.ovf_path = defaultPath.path + '/'
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
    // Ajouter un slash à la fin si pas déjà présent
    form.ovf_path = selectedPath.endsWith('/') ? selectedPath : selectedPath + '/'
  }
  // Reset le select après sélection
  event.target.value = ''
}

function formatSize(bytes) {
  if (!bytes) return '0 GB'
  const gb = bytes / (1024 ** 3)
  return `${gb.toFixed(2)} GB`
}

// Navigateur de fichiers
async function openFileBrowser() {
  showFileBrowser.value = true
  loadingFiles.value = true
  backupFiles.value = []
  searchQuery.value = ''  // Reset search query

  try {
    const response = await restoreAPI.listBackupFiles()
    backupFiles.value = response.data.files || []
  } catch (err) {
    console.error('Erreur chargement fichiers:', err)
    toast.error('Erreur lors du chargement des fichiers de sauvegarde')
  } finally {
    loadingFiles.value = false
  }
}

function closeFileBrowser() {
  showFileBrowser.value = false
  searchQuery.value = ''  // Reset search query on close
}

function clearSelection() {
  form.ovf_path = ''
}

function selectBackupFile(file) {
  form.ovf_path = file.path
  // Extraire le nom de la VM du nom du fichier (sans l'extension)
  if (!form.vm_name) {
    const nameWithoutExt = file.name.replace(/\.(ova|ovf)$/, '')
    form.vm_name = nameWithoutExt
  }
}

function confirmFileSelection() {
  closeFileBrowser()
  toast.success('Fichier sélectionné avec succès')
}

function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>
