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
          <input
            v-model="form.ovf_path"
            type="text"
            required
            class="input-field"
            placeholder="/backups/ma-vm.ova ou /backups/ma-vm/ma-vm.ovf"
          />
          <p class="mt-1 text-sm text-gray-500">
            Chemin complet vers le fichier .ova ou .ovf à restaurer
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
              {{ ds.name }} ({{ formatSize(ds.free_space) }} libre / {{ formatSize(ds.capacity) }} total)
            </option>
          </select>
          <p class="mt-1 text-sm text-gray-500">
            Emplacement de stockage sur le serveur ESXi
          </p>
        </div>

        <!-- Réseau -->
        <div>
          <label class="label">Réseau (optionnel)</label>
          <input
            v-model="form.network_name"
            type="text"
            class="input-field"
            placeholder="VM Network"
          />
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

          <button
            type="button"
            @click="resetForm"
            class="btn-secondary"
            :disabled="loading"
          >
            Réinitialiser
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import { restoreAPI } from '@/services/api'

const esxiStore = useEsxiStore()
const toast = useToastStore()

const loading = ref(false)
const error = ref(null)
const success = ref(null)
const datastores = ref([])

const form = reactive({
  ovf_path: '',
  esxi_server_id: '',
  vm_name: '',
  datastore_name: '',
  network_name: 'VM Network',
  power_on: false
})

const servers = computed(() => esxiStore.servers)

onMounted(async () => {
  // Charger les serveurs ESXi
  if (servers.value.length === 0) {
    await esxiStore.fetchServers()
  }
})

async function loadDatastores() {
  if (!form.esxi_server_id) return

  try {
    const selectedServer = servers.value.find(s => s.id === form.esxi_server_id)
    if (selectedServer) {
      // Charger les datastores du serveur sélectionné
      await esxiStore.fetchDatastores({ server: selectedServer.id })
      // Filtrer pour ne garder QUE les datastores du serveur sélectionné
      datastores.value = (esxiStore.datastores || []).filter(ds => ds.server === selectedServer.id)
    }
  } catch (err) {
    console.error('Erreur chargement datastores:', err)
    toast.error('Erreur lors du chargement des datastores')
  }
}

async function handleRestore() {
  error.value = null
  success.value = null
  loading.value = true

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

    // Appeler l'API (à adapter selon votre backend)
    const response = await restoreAPI.restoreOVF(selectedServer.id, payload)

    success.value = `✅ Restauration réussie ! VM "${form.vm_name}" déployée avec succès.`
    toast.success(`VM "${form.vm_name}" restaurée avec succès !`, 5000)

    // Réinitialiser le formulaire après succès
    setTimeout(() => {
      resetForm()
    }, 2000)

  } catch (err) {
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
}

function formatSize(bytes) {
  if (!bytes) return '0 GB'
  const gb = bytes / (1024 ** 3)
  return `${gb.toFixed(2)} GB`
}
</script>
