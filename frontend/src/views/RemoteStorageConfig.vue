<template>
  <div class="remote-storage-config p-6">
    <div class="header mb-6">
      <h1 class="text-3xl font-bold text-gray-800 mb-2">
        Configuration Stockage Distant
      </h1>
      <p class="text-gray-600">
        Gérez vos configurations de stockage réseau (SMB/CIFS, NFS) pour les sauvegardes ESXi
      </p>
    </div>

    <!-- Actions principales -->
    <div class="actions mb-6 flex gap-3">
      <button
        @click="showCreateModal = true"
        class="btn-primary flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvelle Configuration
      </button>

      <button
        @click="loadConfigurations"
        class="btn-secondary flex items-center gap-2"
        :disabled="loading"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Actualiser
      </button>
    </div>

    <!-- Liste des configurations -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      <p class="mt-4 text-gray-600">Chargement des configurations...</p>
    </div>

    <div v-else-if="configurations.length === 0" class="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
      </svg>
      <h3 class="mt-2 text-lg font-medium text-gray-900">Aucune configuration</h3>
      <p class="mt-1 text-gray-500">Commencez par créer votre première configuration de stockage distant.</p>
      <button @click="showCreateModal = true" class="mt-4 btn-primary">
        Créer une configuration
      </button>
    </div>

    <div v-else class="grid gap-4">
      <div
        v-for="config in configurations"
        :key="config.id"
        class="config-card bg-white rounded-lg shadow-md border-l-4 p-6 hover:shadow-lg transition-shadow"
        :class="{
          'border-green-500': config.is_default && config.is_active,
          'border-blue-500': !config.is_default && config.is_active,
          'border-gray-300': !config.is_active
        }"
      >
        <div class="flex items-start justify-between">
          <!-- Informations principales -->
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-xl font-bold text-gray-800">
                {{ config.name }}
              </h3>

              <span
                v-if="config.is_default"
                class="px-2 py-1 text-xs font-semibold bg-green-100 text-green-800 rounded"
              >
                PAR DÉFAUT
              </span>

              <span
                v-if="!config.is_active"
                class="px-2 py-1 text-xs font-semibold bg-gray-100 text-gray-600 rounded"
              >
                INACTIF
              </span>

              <span
                v-if="config.last_test_success && config.is_active"
                class="px-2 py-1 text-xs font-semibold bg-green-50 text-green-700 rounded flex items-center gap-1"
              >
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                TESTÉ
              </span>

              <span
                v-else-if="config.last_test_at && !config.last_test_success"
                class="px-2 py-1 text-xs font-semibold bg-red-50 text-red-700 rounded flex items-center gap-1"
              >
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
                ÉCHEC TEST
              </span>
            </div>

            <!-- Détails de connexion -->
            <div class="grid grid-cols-2 gap-4 mt-4 text-sm">
              <div>
                <span class="text-gray-500">Protocole:</span>
                <span class="ml-2 font-medium text-gray-700">{{ config.protocol.toUpperCase() }}</span>
              </div>

              <div>
                <span class="text-gray-500">Hôte:</span>
                <span class="ml-2 font-medium text-gray-700">{{ config.host }}:{{ config.port }}</span>
              </div>

              <div v-if="config.share_name">
                <span class="text-gray-500">Partage:</span>
                <span class="ml-2 font-medium text-gray-700">{{ config.share_name }}</span>
              </div>

              <div v-if="config.username">
                <span class="text-gray-500">Utilisateur:</span>
                <span class="ml-2 font-medium text-gray-700">
                  {{ config.domain ? `${config.domain}\\` : '' }}{{ config.username }}
                </span>
              </div>
            </div>

            <!-- Chemin complet -->
            <div class="mt-3 p-3 bg-gray-50 rounded border border-gray-200">
              <p class="text-xs text-gray-500 mb-1">Chemin complet:</p>
              <code class="text-sm font-mono text-gray-800">{{ config.full_path }}</code>
            </div>

            <!-- Dernier test -->
            <div v-if="config.last_test_at" class="mt-3 text-xs text-gray-500">
              Dernier test: {{ formatDate(config.last_test_at) }}
              <span v-if="config.last_test_message" class="ml-2 text-gray-600">
                - {{ config.last_test_message }}
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex flex-col gap-2 ml-4">
            <button
              @click="testConfiguration(config)"
              class="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded transition-colors flex items-center gap-2"
              :disabled="testing === config.id"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ testing === config.id ? 'Test...' : 'Tester' }}
            </button>

            <button
              @click="editConfiguration(config)"
              class="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded transition-colors flex items-center gap-2"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Modifier
            </button>

            <button
              @click="deleteConfiguration(config)"
              class="px-3 py-2 bg-red-500 hover:bg-red-600 text-white text-sm rounded transition-colors flex items-center gap-2"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Supprimer
            </button>
          </div>
        </div>

        <!-- Résultat du test en cours -->
        <div
          v-if="testResults[config.id]"
          class="mt-4 p-4 rounded border"
          :class="{
            'bg-green-50 border-green-200': testResults[config.id].success,
            'bg-red-50 border-red-200': !testResults[config.id].success
          }"
        >
          <p class="font-medium" :class="{
            'text-green-800': testResults[config.id].success,
            'text-red-800': !testResults[config.id].success
          }">
            {{ testResults[config.id].message }}
          </p>

          <div v-if="testResults[config.id].success" class="mt-2 text-sm text-green-700">
            <p>✓ Connectivité réseau: OK</p>
            <p>✓ Authentification: {{ testResults[config.id].authentication ? 'OK' : 'N/A' }}</p>
            <p>✓ Permissions d'écriture: OK</p>
            <p>✓ Espace disponible: {{ testResults[config.id].available_space_gb }} GB</p>
          </div>

          <div v-if="!testResults[config.id].success && testResults[config.id].errors.length > 0" class="mt-2 text-sm text-red-700">
            <p v-for="(error, idx) in testResults[config.id].errors" :key="idx">
              ✗ {{ error }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Création/Édition -->
    <div
      v-if="showCreateModal || editingConfig"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
          <h2 class="text-2xl font-bold text-gray-800">
            {{ editingConfig ? 'Modifier la Configuration' : 'Nouvelle Configuration' }}
          </h2>
        </div>

        <form @submit.prevent="saveConfiguration" class="p-6 space-y-4">
          <!-- Nom -->
          <div>
            <label class="label">Nom de la configuration *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="input-field"
              placeholder="NAS Principal"
            >
            <p class="mt-1 text-xs text-gray-500">Nom descriptif pour identifier cette configuration</p>
          </div>

          <!-- Protocole -->
          <div>
            <label class="label">Protocole *</label>
            <select v-model="form.protocol" required class="input-field">
              <option value="smb">SMB/CIFS (Windows Share, Samba)</option>
              <option value="nfs">NFS (Network File System)</option>
              <option value="local">Local (Développement uniquement)</option>
            </select>
          </div>

          <!-- Hôte -->
          <div>
            <label class="label">Hôte (IP ou nom) *</label>
            <input
              v-model="form.host"
              type="text"
              required
              class="input-field"
              placeholder="192.168.1.100 ou nas.local"
            >
          </div>

          <!-- Port -->
          <div>
            <label class="label">Port</label>
            <input
              v-model.number="form.port"
              type="number"
              class="input-field"
              placeholder="445 pour SMB, 2049 pour NFS"
            >
            <p class="mt-1 text-xs text-gray-500">Par défaut: 445 (SMB) ou 2049 (NFS)</p>
          </div>

          <!-- Nom du partage (SMB uniquement) -->
          <div v-if="form.protocol === 'smb'">
            <label class="label">Nom du partage *</label>
            <input
              v-model="form.share_name"
              type="text"
              :required="form.protocol === 'smb'"
              class="input-field"
              placeholder="backups"
            >
          </div>

          <!-- Chemin de base -->
          <div>
            <label class="label">Sous-dossier (optionnel)</label>
            <input
              v-model="form.base_path"
              type="text"
              class="input-field"
              placeholder="esxi_backups"
            >
            <p class="mt-1 text-xs text-gray-500">Sous-dossier dans le partage</p>
          </div>

          <!-- Credentials (SMB) -->
          <div v-if="form.protocol === 'smb'" class="border-t pt-4">
            <h3 class="text-lg font-semibold text-gray-700 mb-3">Authentification</h3>

            <div class="space-y-4">
              <div>
                <label class="label">Nom d'utilisateur</label>
                <input
                  v-model="form.username"
                  type="text"
                  class="input-field"
                  placeholder="admin"
                >
              </div>

              <div>
                <label class="label">Mot de passe</label>
                <input
                  v-model="form.password"
                  type="password"
                  class="input-field"
                  :placeholder="editingConfig ? 'Laisser vide pour ne pas changer' : 'Mot de passe'"
                >
                <p class="mt-1 text-xs text-gray-500">
                  {{ editingConfig ? 'Laisser vide pour conserver le mot de passe actuel' : 'Sera chiffré de manière sécurisée' }}
                </p>
              </div>

              <div>
                <label class="label">Domaine Windows</label>
                <input
                  v-model="form.domain"
                  type="text"
                  class="input-field"
                  placeholder="WORKGROUP"
                >
              </div>
            </div>
          </div>

          <!-- Options -->
          <div class="border-t pt-4 space-y-3">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="form.is_active"
                type="checkbox"
                class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              >
              <span class="text-sm font-medium text-gray-700">Configuration active</span>
            </label>

            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="form.is_default"
                type="checkbox"
                class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              >
              <span class="text-sm font-medium text-gray-700">Définir comme configuration par défaut</span>
            </label>
          </div>

          <!-- Résultat du test de connexion dans le modal -->
          <div
            v-if="modalTestResult"
            class="p-4 rounded border"
            :class="{
              'bg-green-50 border-green-200 text-green-800': modalTestResult.success,
              'bg-red-50 border-red-200 text-red-800': !modalTestResult.success
            }"
          >
            <p class="font-medium">{{ modalTestResult.message }}</p>
            <ul v-if="modalTestResult.errors.length > 0" class="mt-2 text-sm list-disc list-inside">
              <li v-for="(error, idx) in modalTestResult.errors" :key="idx">{{ error }}</li>
            </ul>
          </div>

          <!-- Actions -->
          <div class="flex justify-between items-center pt-4 border-t">
            <button
              type="button"
              @click="testConnectionInModal"
              class="btn-secondary"
              :disabled="testingModal"
            >
              {{ testingModal ? 'Test en cours...' : 'Tester la connexion' }}
            </button>

            <div class="flex gap-2">
              <button
                type="button"
                @click="closeModal"
                class="btn-secondary"
              >
                Annuler
              </button>

              <button
                type="submit"
                class="btn-primary"
                :disabled="saving"
              >
                {{ saving ? 'Enregistrement...' : (editingConfig ? 'Modifier' : 'Créer') }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

// State
const configurations = ref([])
const loading = ref(false)
const showCreateModal = ref(false)
const editingConfig = ref(null)
const saving = ref(false)
const testing = ref(null)
const testResults = ref({})
const testingModal = ref(false)
const modalTestResult = ref(null)

// Form
const form = reactive({
  name: '',
  protocol: 'smb',
  host: '',
  port: 445,
  share_name: '',
  base_path: '',
  username: '',
  password: '',
  domain: 'WORKGROUP',
  is_active: true,
  is_default: false
})

// Charger les configurations
async function loadConfigurations() {
  loading.value = true
  try {
    const response = await axios.get(`${API_BASE}/remote-storage/`)
    configurations.value = response.data
  } catch (error) {
    console.error('Erreur chargement configurations:', error)
    alert('Erreur lors du chargement des configurations')
  } finally {
    loading.value = false
  }
}

// Tester une configuration existante
async function testConfiguration(config) {
  testing.value = config.id
  testResults.value[config.id] = null

  try {
    const response = await axios.post(`${API_BASE}/remote-storage/${config.id}/test/`)
    testResults.value[config.id] = response.data

    // Recharger la config pour avoir les infos de test à jour
    await loadConfigurations()
  } catch (error) {
    console.error('Erreur test:', error)
    testResults.value[config.id] = {
      success: false,
      message: 'Erreur lors du test',
      errors: [error.response?.data?.detail || error.message]
    }
  } finally {
    testing.value = null
  }
}

// Tester la connexion dans le modal
async function testConnectionInModal() {
  testingModal.value = true
  modalTestResult.value = null

  try {
    const testData = { ...form }
    if (!testData.password && editingConfig.value) {
      delete testData.password  // Ne pas envoyer si vide en édition
    }

    const response = await axios.post(`${API_BASE}/remote-storage/test_connection/`, testData)
    modalTestResult.value = response.data
  } catch (error) {
    console.error('Erreur test connexion:', error)
    modalTestResult.value = {
      success: false,
      message: 'Erreur lors du test',
      errors: [error.response?.data?.detail || error.message],
      authentication: false,
      write_permissions: false,
      available_space_gb: 0
    }
  } finally {
    testingModal.value = false
  }
}

// Sauvegarder la configuration
async function saveConfiguration() {
  saving.value = true

  try {
    const data = { ...form }

    // Ne pas envoyer le mot de passe vide en édition
    if (editingConfig.value && !data.password) {
      delete data.password
    }

    if (editingConfig.value) {
      await axios.put(`${API_BASE}/remote-storage/${editingConfig.value.id}/`, data)
    } else {
      await axios.post(`${API_BASE}/remote-storage/`, data)
    }

    alert(editingConfig.value ? 'Configuration modifiée avec succès' : 'Configuration créée avec succès')
    closeModal()
    await loadConfigurations()
  } catch (error) {
    console.error('Erreur sauvegarde:', error)
    const errorMsg = error.response?.data?.detail || JSON.stringify(error.response?.data) || error.message
    alert(`Erreur lors de la sauvegarde: ${errorMsg}`)
  } finally {
    saving.value = false
  }
}

// Éditer une configuration
function editConfiguration(config) {
  editingConfig.value = config

  form.name = config.name
  form.protocol = config.protocol
  form.host = config.host
  form.port = config.port
  form.share_name = config.share_name || ''
  form.base_path = config.base_path || ''
  form.username = config.username || ''
  form.password = ''  // Ne pas pré-remplir le mot de passe
  form.domain = config.domain || 'WORKGROUP'
  form.is_active = config.is_active
  form.is_default = config.is_default
}

// Supprimer une configuration
async function deleteConfiguration(config) {
  if (!confirm(`Êtes-vous sûr de vouloir supprimer la configuration "${config.name}" ?`)) {
    return
  }

  try {
    await axios.delete(`${API_BASE}/remote-storage/${config.id}/`)
    alert('Configuration supprimée avec succès')
    await loadConfigurations()
  } catch (error) {
    console.error('Erreur suppression:', error)
    alert('Erreur lors de la suppression: ' + (error.response?.data?.detail || error.message))
  }
}

// Fermer le modal
function closeModal() {
  showCreateModal.value = false
  editingConfig.value = null
  modalTestResult.value = null

  // Reset form
  form.name = ''
  form.protocol = 'smb'
  form.host = ''
  form.port = 445
  form.share_name = ''
  form.base_path = ''
  form.username = ''
  form.password = ''
  form.domain = 'WORKGROUP'
  form.is_active = true
  form.is_default = false
}

// Formater la date
function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString('fr-FR')
}

// Charger au montage
onMounted(() => {
  loadConfigurations()
})
</script>

<style scoped>
.config-card {
  transition: all 0.3s ease;
}

.config-card:hover {
  transform: translateY(-2px);
}
</style>
