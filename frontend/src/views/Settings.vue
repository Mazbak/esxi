<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Paramètres</h1>
      <p class="mt-1 text-sm text-gray-500">Configuration de l'application</p>
    </div>

    <!-- General Settings -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Paramètres généraux</h2>
      <div class="space-y-4">
        <div>
          <label class="label">Répertoire de sauvegarde par défaut</label>
          <input
            v-model="settings.defaultBackupLocation"
            type="text"
            class="input-field"
            placeholder="/mnt/backup_esxi"
          >
          <p class="mt-1 text-sm text-gray-500">
            Emplacement par défaut pour les nouvelles sauvegardes
          </p>
        </div>

        <div>
          <label class="label">Rétention des sauvegardes (jours)</label>
          <input
            v-model.number="settings.retentionDays"
            type="number"
            class="input-field"
            placeholder="30"
          >
          <p class="mt-1 text-sm text-gray-500">
            Nombre de jours de conservation des sauvegardes
          </p>
        </div>

        <div class="flex items-center">
          <input
            v-model="settings.autoStartBackups"
            type="checkbox"
            id="autoStart"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          >
          <label for="autoStart" class="ml-2 block text-sm text-gray-700">
            Démarrer automatiquement les nouvelles sauvegardes
          </label>
        </div>

        <div class="flex items-center">
          <input
            v-model="settings.emailNotifications"
            type="checkbox"
            id="emailNotif"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          >
          <label for="emailNotif" class="ml-2 block text-sm text-gray-700">
            Activer les notifications par email
          </label>
        </div>
      </div>

      <div class="mt-6">
        <button @click="saveSettings" class="btn-primary">
          Enregistrer les paramètres
        </button>
      </div>
    </div>

    <!-- Storage Paths Management -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">📁 Chemins de sauvegarde</h2>
        <button @click="showCreateModal = true" class="btn-primary text-sm">
          ➕ Nouveau chemin
        </button>
      </div>

      <div v-if="loadingPaths" class="text-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-2 text-sm text-gray-500">Chargement...</p>
      </div>

      <div v-else-if="storagePaths.length === 0" class="text-center py-8 bg-gray-50 rounded-lg">
        <p class="text-gray-500">Aucun chemin de sauvegarde configuré</p>
        <button @click="showCreateModal = true" class="btn-primary mt-3 text-sm">
          ➕ Créer le premier chemin
        </button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="path in storagePaths"
          :key="path.id"
          class="border rounded-lg p-3 hover:border-blue-400 transition-colors"
          :class="{ 'border-green-500 bg-green-50': path.is_default }"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <h3 class="font-semibold text-gray-900">{{ path.name }}</h3>
                <span v-if="path.is_default" class="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded">
                  Par défaut
                </span>
                <span v-if="!path.is_active" class="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                  Inactif
                </span>
                <span class="px-2 py-0.5 text-xs font-medium rounded" :class="{
                  'bg-blue-100 text-blue-800': path.storage_type === 'local',
                  'bg-purple-100 text-purple-800': path.storage_type === 'smb',
                  'bg-orange-100 text-orange-800': path.storage_type === 'nfs',
                  'bg-indigo-100 text-indigo-800': path.storage_type === 'iscsi',
                  'bg-gray-100 text-gray-800': path.storage_type === 'other'
                }">
                  {{ path.storage_type_display }}
                </span>
              </div>
              <p class="mt-1 text-sm text-gray-600 font-mono">{{ path.path }}</p>
              <p v-if="path.description" class="mt-1 text-xs text-gray-500">{{ path.description }}</p>
            </div>

            <div class="flex items-center gap-1.5 ml-4">
              <button v-if="!path.is_default" @click="setAsDefault(path.id)" class="btn-secondary text-xs px-2 py-1" title="Définir comme défaut">
                ⭐
              </button>
              <button @click="editPath(path)" class="btn-secondary text-xs px-2 py-1" title="Modifier">
                ✏️
              </button>
              <button @click="deletePath(path)" class="btn-danger text-xs px-2 py-1" title="Supprimer">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- About -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">À propos</h2>
      <div class="space-y-3 text-sm">
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Application</span>
          <span class="font-medium text-gray-900">ESXi Backup Manager</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Version</span>
          <span class="font-medium text-gray-900">1.0.0</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Backend</span>
          <span class="font-medium text-gray-900">Django + Django REST Framework</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Frontend</span>
          <span class="font-medium text-gray-900">Vue.js 3 + Tailwind CSS</span>
        </div>
      </div>
    </div>

    <!-- Danger Zone -->
    <div class="card border-2 border-red-200">
      <h2 class="text-lg font-semibold text-red-900 mb-4">Zone dangereuse</h2>
      <p class="text-sm text-gray-600 mb-4">
        Actions irréversibles qui nécessitent une confirmation
      </p>
      <button class="btn-danger">
        Réinitialiser toutes les données
      </button>
    </div>

    <!-- Modal Créer/Modifier chemin -->
    <Modal
      :show="showCreateModal || showEditModal"
      @close="closeModal"
      :title="editingPath ? 'Modifier le chemin' : 'Créer un chemin de sauvegarde'"
    >
      <form @submit.prevent="savePath" class="space-y-4">
        <div>
          <label class="label">Nom du chemin</label>
          <input v-model="pathForm.name" type="text" required class="input-field" placeholder="NAS Principal, Backup Mensuel..." />
        </div>

        <div>
          <label class="label">Chemin complet</label>
          <input v-model="pathForm.path" type="text" required class="input-field" placeholder="/mnt/backups, \\serveur\partage, /mnt/nfs-share..." />
        </div>

        <div>
          <label class="label">Type de stockage</label>
          <select v-model="pathForm.storage_type" class="input-field" required>
            <option value="local">Disque local</option>
            <option value="smb">Partage SMB/CIFS</option>
            <option value="nfs">Partage NFS</option>
            <option value="iscsi">Disque iSCSI</option>
            <option value="other">Autre</option>
          </select>
        </div>

        <div>
          <label class="label">Description (optionnel)</label>
          <textarea v-model="pathForm.description" class="input-field" rows="2" placeholder="Description du chemin de sauvegarde..."></textarea>
        </div>

        <div class="flex items-center gap-4">
          <label class="flex items-center">
            <input type="checkbox" v-model="pathForm.is_active" class="mr-2" />
            <span class="text-sm text-gray-700">Chemin actif</span>
          </label>

          <label class="flex items-center">
            <input type="checkbox" v-model="pathForm.is_default" class="mr-2" />
            <span class="text-sm text-gray-700">Définir comme défaut</span>
          </label>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button type="button" @click="closeModal" class="btn-secondary">Annuler</button>
          <button type="submit" class="btn-primary" :disabled="savingPath">
            {{ savingPath ? 'Enregistrement...' : (editingPath ? 'Modifier' : 'Créer') }}
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useToastStore } from '@/stores/toast'
import { storagePathsAPI } from '@/services/api'
import Modal from '@/components/common/Modal.vue'

const toast = useToastStore()

const settings = reactive({
  defaultBackupLocation: '/mnt/backup_esxi',
  retentionDays: 30,
  autoStartBackups: true,
  emailNotifications: false
})

// Storage Paths Management
const storagePaths = ref([])
const loadingPaths = ref(false)
const savingPath = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const editingPath = ref(null)

const pathForm = reactive({
  name: '',
  path: '',
  storage_type: 'local',
  description: '',
  is_active: true,
  is_default: false
})

function saveSettings() {
  try {
    // TODO: Implement actual save logic
    // await settingsAPI.save(settings)
    toast.success('Paramètres enregistrés avec succès')
  } catch (err) {
    toast.error(`Erreur lors de l'enregistrement: ${err.message}`)
  }
}

// Charger les chemins de sauvegarde
async function loadStoragePaths() {
  loadingPaths.value = true
  try {
    const response = await storagePathsAPI.getAll()
    storagePaths.value = response.data
  } catch (err) {
    console.error('Erreur chargement chemins:', err)
    toast.error('Erreur lors du chargement des chemins de sauvegarde')
  } finally {
    loadingPaths.value = false
  }
}

// Sauvegarder un chemin (créer ou modifier)
async function savePath() {
  savingPath.value = true
  try {
    if (editingPath.value) {
      await storagePathsAPI.update(editingPath.value.id, pathForm)
      toast.success('Chemin modifié avec succès')
    } else {
      await storagePathsAPI.create(pathForm)
      toast.success('Chemin créé avec succès')
    }

    closeModal()
    await loadStoragePaths()
  } catch (err) {
    console.error('Erreur sauvegarde:', err)
    const message = err.response?.data?.name?.[0] || err.response?.data?.message || 'Erreur lors de la sauvegarde'
    toast.error(message)
  } finally {
    savingPath.value = false
  }
}

// Modifier un chemin
function editPath(path) {
  editingPath.value = path
  pathForm.name = path.name
  pathForm.path = path.path
  pathForm.storage_type = path.storage_type
  pathForm.description = path.description || ''
  pathForm.is_active = path.is_active
  pathForm.is_default = path.is_default
  showEditModal.value = true
}

// Supprimer un chemin
async function deletePath(path) {
  if (!confirm(`Supprimer le chemin "${path.name}" ?`)) return

  try {
    await storagePathsAPI.delete(path.id)
    toast.success('Chemin supprimé')
    await loadStoragePaths()
  } catch (err) {
    console.error('Erreur suppression:', err)
    toast.error('Erreur lors de la suppression')
  }
}

// Définir comme défaut
async function setAsDefault(id) {
  try {
    await storagePathsAPI.setDefault(id)
    toast.success('Chemin défini comme défaut')
    await loadStoragePaths()
  } catch (err) {
    console.error('Erreur définir défaut:', err)
    toast.error('Erreur lors de la définition du défaut')
  }
}

// Fermer modal
function closeModal() {
  showCreateModal.value = false
  showEditModal.value = false
  editingPath.value = null

  // Reset form
  pathForm.name = ''
  pathForm.path = ''
  pathForm.storage_type = 'local'
  pathForm.description = ''
  pathForm.is_active = true
  pathForm.is_default = false
}

onMounted(() => {
  loadStoragePaths()
})
</script>
