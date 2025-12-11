<template>
  <Modal :show="show" title="Créer une nouvelle sauvegarde" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label class="label">Machine virtuelle</label>
        <select v-model="form.virtual_machine" @change="onVMChange" required class="input-field" :disabled="loading">
          <option value="">Sélectionnez une VM</option>
          <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">
            {{ vm.name }} ({{ vm.guest_os }})
          </option>
        </select>
      </div>

      <div>
        <label class="label">Type de sauvegarde</label>
        <select v-model="form.backup_type" required class="input-field" :disabled="loading">
          <option value="full">Complète</option>
          <option value="incremental">Incrémentale</option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          <span v-if="form.backup_type === 'full'">
            Sauvegarde complète avec snapshot + copie des VMDKs
          </span>
          <span v-else>
            Sauvegarde incrémentale basée sur une sauvegarde complète existante
          </span>
        </p>
      </div>

      <div v-if="form.backup_type === 'incremental'">
        <label class="label">Sauvegarde de base</label>
        <select v-model="form.base_backup" required class="input-field" :disabled="!form.virtual_machine || loadingBaseBackups">
          <option value="">{{ loadingBaseBackups ? 'Chargement...' : 'Sélectionnez une sauvegarde de base' }}</option>
          <option v-for="backup in availableBaseBackups" :key="backup.id" :value="backup.id">
            {{ formatDate(backup.created_at) }} - {{ formatSize(backup.backup_size_mb) }}
          </option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          Choisissez la sauvegarde complète sur laquelle baser cette sauvegarde incrémentale
        </p>
        <p v-if="form.virtual_machine && availableBaseBackups.length === 0 && !loadingBaseBackups" class="mt-1 text-sm text-red-600">
          ⚠️ Aucune sauvegarde complète disponible pour cette VM. Créez d'abord une sauvegarde complète.
        </p>
      </div>

      <div>
        <label class="label">Répertoire de sauvegarde</label>
        <div class="flex gap-2">
          <select
            v-if="favoriteLocations.length > 0"
            v-model="form.backup_location"
            required
            class="input-field flex-1"
          >
            <option v-for="location in favoriteLocations" :key="location" :value="location">
              {{ location }}
            </option>
            <option value="">➕ Autre chemin personnalisé...</option>
          </select>
          <input
            v-else
            v-model="form.backup_location"
            type="text"
            required
            class="input-field flex-1"
            placeholder="D:\backup ou /mnt/backup_esxi"
          >
          <button
            type="button"
            @click="showLocationManager = true"
            class="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            title="Gérer les répertoires favoris"
          >
            ⚙️
          </button>
        </div>
        <input
          v-if="favoriteLocations.length > 0 && form.backup_location === ''"
          v-model="customLocation"
          type="text"
          class="input-field mt-2"
          placeholder="Entrez un chemin personnalisé"
          @input="form.backup_location = customLocation"
        >
        <p class="mt-1 text-sm text-gray-500">
          Chemin local (D:\backup) ou distant (\\NAS\Backups, /mnt/nfs)
        </p>
      </div>

      <!-- Modal de gestion des répertoires favoris -->
      <div v-if="showLocationManager" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="showLocationManager = false">
        <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
          <h3 class="text-xl font-bold mb-4">Gérer les répertoires de sauvegarde</h3>

          <!-- Liste des répertoires favoris -->
          <div class="space-y-2 mb-4">
            <div v-for="(location, index) in favoriteLocations" :key="index"
                 class="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
              <span class="flex-1 font-mono text-sm">{{ location }}</span>
              <button
                type="button"
                @click="removeFavoriteLocation(index)"
                class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded transition-colors"
              >
                🗑️ Supprimer
              </button>
            </div>
            <p v-if="favoriteLocations.length === 0" class="text-gray-500 text-center py-4">
              Aucun répertoire favori. Ajoutez-en un ci-dessous.
            </p>
          </div>

          <!-- Ajouter un nouveau répertoire -->
          <div class="border-t pt-4">
            <label class="label">Ajouter un répertoire</label>
            <div class="flex gap-2">
              <input
                v-model="newLocation"
                type="text"
                class="input-field flex-1"
                placeholder="D:\backup ou /mnt/backup_esxi"
                @keyup.enter="addFavoriteLocation"
              >
              <button
                type="button"
                @click="addFavoriteLocation"
                class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
              >
                ➕ Ajouter
              </button>
            </div>
          </div>

          <!-- Bouton fermer -->
          <div class="mt-6 flex justify-end">
            <button
              type="button"
              @click="showLocationManager = false"
              class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>

      <div v-if="form.backup_type === 'incremental'" class="flex items-center p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <svg class="w-5 h-5 text-yellow-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <div class="text-sm text-yellow-800">
          <p><strong>Important:</strong> La sauvegarde incrémentale nécessite qu'une sauvegarde complète existe déjà pour cette VM.</p>
          <p class="mt-1">Système snapshot + copie VMDK incrémentale pour une restauration complète.</p>
        </div>
      </div>

      <div class="flex items-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <svg class="w-5 h-5 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
        </svg>
        <p class="text-sm text-blue-800">
          La sauvegarde sera exécutée en arrière-plan. Vous pouvez suivre sa progression dans la liste des sauvegardes.
        </p>
      </div>

      <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>
    </form>

    <!-- Modal d'avertissement VM allumée -->
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
              La machine virtuelle <strong class="text-gray-900">{{ selectedVMName }}</strong> est actuellement <strong class="text-green-600">allumée</strong>.
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
              type="button"
              @click="powerOffAndBackup"
              :disabled="poweringOff"
              class="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
              :class="{ 'opacity-50 cursor-not-allowed': poweringOff }"
            >
              <svg v-if="poweringOff" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>{{ poweringOff ? 'Extinction en cours...' : '✅ Éteindre la VM puis sauvegarder' }}</span>
            </button>

            <button
              type="button"
              @click="continueWithoutPowerOff"
              class="w-full px-4 py-3 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold rounded-lg transition-colors"
            >
              ⚠️ Continuer sans éteindre (non recommandé)
            </button>

            <button
              type="button"
              @click="closePowerWarning"
              class="w-full px-4 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors"
            >
              Annuler
            </button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <button type="button" @click="$emit('close')" class="btn-secondary" :disabled="loading">
        Annuler
      </button>
      <button
        type="button"
        @click="handleSubmit"
        :disabled="loading"
        class="btn-primary flex items-center gap-2"
        :class="{ 'opacity-50 cursor-not-allowed': loading }"
      >
        <svg v-if="loading" class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ loading ? 'Création en cours...' : 'Créer et démarrer' }}</span>
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useVMOperationsStore } from '@/stores/vmOperations'
import Modal from '@/components/common/Modal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

const esxiStore = useEsxiStore()
const vmOpsStore = useVMOperationsStore()

const loading = ref(false)
const error = ref(null)
const showLocationManager = ref(false)
const newLocation = ref('')
const customLocation = ref('')
const favoriteLocations = ref([])
const availableBaseBackups = ref([])
const loadingBaseBackups = ref(false)
const showPowerWarning = ref(false)
const poweringOff = ref(false)
const selectedVM = ref(null)
const selectedVMName = computed(() => selectedVM.value?.name || '')

const form = reactive({
  virtual_machine: '',
  backup_type: 'full',
  base_backup: '',
  backup_location: ''
})

const virtualMachines = computed(() => esxiStore.virtualMachines)

// Charger les répertoires favoris depuis localStorage
function loadFavoriteLocations() {
  const saved = localStorage.getItem('backup_favorite_locations')
  if (saved) {
    try {
      favoriteLocations.value = JSON.parse(saved)
      // Définir le premier comme valeur par défaut si disponible
      if (favoriteLocations.value.length > 0 && !form.backup_location) {
        form.backup_location = favoriteLocations.value[0]
      }
    } catch (e) {
      console.error('Erreur lors du chargement des répertoires favoris:', e)
      favoriteLocations.value = []
    }
  }
  // Valeur par défaut si aucun favori
  if (favoriteLocations.value.length === 0 && !form.backup_location) {
    form.backup_location = '/mnt/backup_esxi'
  }
}

// Sauvegarder les répertoires favoris dans localStorage
function saveFavoriteLocations() {
  localStorage.setItem('backup_favorite_locations', JSON.stringify(favoriteLocations.value))
}

// Ajouter un répertoire favori
function addFavoriteLocation() {
  if (newLocation.value.trim() && !favoriteLocations.value.includes(newLocation.value.trim())) {
    favoriteLocations.value.push(newLocation.value.trim())
    saveFavoriteLocations()
    // Si c'est le premier, le définir comme valeur par défaut
    if (favoriteLocations.value.length === 1) {
      form.backup_location = newLocation.value.trim()
    }
    newLocation.value = ''
  }
}

// Supprimer un répertoire favori
function removeFavoriteLocation(index) {
  const removed = favoriteLocations.value[index]
  favoriteLocations.value.splice(index, 1)
  saveFavoriteLocations()
  // Si c'était celui sélectionné, choisir le premier disponible
  if (form.backup_location === removed) {
    form.backup_location = favoriteLocations.value.length > 0 ? favoriteLocations.value[0] : '/mnt/backup_esxi'
  }
}

// Charger les sauvegardes de base disponibles quand la VM change
async function onVMChange() {
  // Récupérer les informations de la VM sélectionnée
  if (form.virtual_machine) {
    selectedVM.value = virtualMachines.value.find(vm => vm.id === form.virtual_machine)
    console.log('🔄 onVMChange - VM sélectionnée:', selectedVM.value)
    console.log('🔄 onVMChange - power_state:', selectedVM.value?.power_state)
  } else {
    selectedVM.value = null
  }

  if (form.virtual_machine && form.backup_type === 'incremental') {
    await loadAvailableBaseBackups()
  }
}

// Charger les sauvegardes complètes disponibles pour la VM sélectionnée
async function loadAvailableBaseBackups() {
  if (!form.virtual_machine) {
    availableBaseBackups.value = []
    return
  }

  loadingBaseBackups.value = true
  try {
    availableBaseBackups.value = await vmOpsStore.getAvailableBaseBackups(form.virtual_machine)
  } catch (err) {
    console.error('Erreur chargement backups de base:', err)
    availableBaseBackups.value = []
  } finally {
    loadingBaseBackups.value = false
  }
}

// Reset form when modal closes
watch(() => props.show, (newValue) => {
  if (!newValue) {
    resetForm()
    error.value = null
    loading.value = false
  }
})

// Charger les backups de base quand on passe en mode incrémental
watch(() => form.backup_type, async (newValue) => {
  if (newValue === 'incremental' && form.virtual_machine) {
    await loadAvailableBaseBackups()
  } else {
    form.base_backup = ''
    availableBaseBackups.value = []
  }
})

onMounted(() => {
  if (virtualMachines.value.length === 0) {
    esxiStore.fetchVirtualMachines()
  }
  // Charger les répertoires favoris au démarrage
  loadFavoriteLocations()
})

function handleSubmit() {
  error.value = null

  // Debug logs
  console.log('🔍 handleSubmit - selectedVM:', selectedVM.value)
  console.log('🔍 handleSubmit - power_state:', selectedVM.value?.power_state)

  // Vérifier si la VM est allumée
  if (selectedVM.value && selectedVM.value.power_state === 'poweredOn') {
    console.log('⚠️ VM est allumée, affichage du modal')
    // Afficher le modal d'avertissement
    showPowerWarning.value = true
    return
  }

  console.log('✅ VM est éteinte ou état inconnu, soumission normale')
  // Si la VM est éteinte ou si on ne peut pas déterminer son état, continuer normalement
  submitBackup()
}

function submitBackup() {
  loading.value = true
  // Emit the submit event with form data
  emit('submit', { ...form })
  // Note: Parent will close modal on success, which will reset loading via watch
}

// Éteindre la VM puis lancer la sauvegarde
async function powerOffAndBackup() {
  poweringOff.value = true
  error.value = null

  try {
    // Appeler l'API pour éteindre la VM
    const response = await esxiStore.powerOffVM(selectedVM.value.id)

    if (response.success) {
      // Attendre quelques secondes pour que l'extinction soit effective
      await new Promise(resolve => setTimeout(resolve, 3000))

      // Fermer le modal d'avertissement
      showPowerWarning.value = false
      poweringOff.value = false

      // Lancer la sauvegarde
      submitBackup()
    } else {
      throw new Error(response.message || 'Échec de l\'extinction de la VM')
    }
  } catch (err) {
    console.error('Erreur extinction VM:', err)
    error.value = err.response?.data?.error || err.message || 'Erreur lors de l\'extinction de la VM'
    poweringOff.value = false
  }
}

// Continuer sans éteindre la VM (non recommandé)
function continueWithoutPowerOff() {
  showPowerWarning.value = false
  submitBackup()
}

// Fermer le modal d'avertissement
function closePowerWarning() {
  showPowerWarning.value = false
  poweringOff.value = false
}

function resetForm() {
  form.virtual_machine = ''
  form.backup_type = 'full'
  form.base_backup = ''
  // Réinitialiser au premier favori ou valeur par défaut
  form.backup_location = favoriteLocations.value.length > 0 ? favoriteLocations.value[0] : '/mnt/backup_esxi'
  customLocation.value = ''
  availableBaseBackups.value = []
}

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('fr-FR')
}

function formatSize(sizeMb) {
  if (!sizeMb || sizeMb === 0) return '-'
  if (sizeMb < 1024) return `${sizeMb.toFixed(2)} MB`
  return `${(sizeMb / 1024).toFixed(2)} GB`
}
</script>
