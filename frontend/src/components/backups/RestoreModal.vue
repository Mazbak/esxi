<template>
  <Modal :show="show" title="Restaurer une sauvegarde OVF" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg mb-4">
        <div class="flex items-center">
          <svg class="w-5 h-5 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
          <div class="text-sm text-blue-800">
            <p class="font-medium">Sauvegarde à restaurer:</p>
            <p class="mt-1">{{ backupJob?.backup_location }}</p>
          </div>
        </div>
      </div>

      <div>
        <label class="label">Serveur ESXi de destination</label>
        <select v-model="form.esxi_server_id" required class="input-field">
          <option value="">Sélectionnez un serveur ESXi</option>
          <option v-for="server in esxiServers" :key="server.id" :value="server.id">
            {{ server.name }} ({{ server.hostname }})
          </option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          Serveur ESXi où déployer la VM restaurée
        </p>
      </div>

      <div>
        <label class="label">Nom de la VM restaurée</label>
        <input
          v-model="form.vm_name"
          type="text"
          required
          class="input-field"
          placeholder="Ex: VM-Restored-2024"
        >
        <p class="mt-1 text-sm text-gray-500">
          Nom de la nouvelle machine virtuelle
        </p>
      </div>

      <div>
        <label class="label">Datastore</label>
        <select v-model="form.datastore_name" required class="input-field">
          <option value="">Sélectionnez un datastore</option>
          <option v-for="ds in datastores" :key="ds.name" :value="ds.name">
            {{ ds.name }} ({{ ds.free_space_gb }} GB libre / {{ ds.capacity_gb }} GB)
          </option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          Emplacement de stockage pour la VM
        </p>
      </div>

      <div>
        <label class="label">Réseau</label>
        <input
          v-model="form.network_name"
          type="text"
          required
          class="input-field"
          placeholder="VM Network"
        >
        <p class="mt-1 text-sm text-gray-500">
          Réseau à connecter à la VM (par défaut: VM Network)
        </p>
      </div>

      <div class="flex items-center">
        <input
          v-model="form.power_on"
          type="checkbox"
          id="power_on"
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        >
        <label for="power_on" class="ml-2 block text-sm text-gray-900">
          Démarrer la VM après restauration
        </label>
      </div>

      <div class="flex items-center p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <svg class="w-5 h-5 text-yellow-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-sm text-yellow-800">
          La restauration peut prendre plusieurs minutes selon la taille de la sauvegarde.
        </p>
      </div>

      <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>
    </form>

    <template #footer>
      <button type="button" @click="$emit('close')" class="btn-secondary">
        Annuler
      </button>
      <button
        type="button"
        @click="handleSubmit"
        :disabled="loading"
        class="btn-primary"
        :class="{ 'opacity-50 cursor-not-allowed': loading }"
      >
        {{ loading ? 'Restauration...' : 'Démarrer la restauration' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import Modal from '@/components/common/Modal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  backupJob: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'submit'])

const esxiStore = useEsxiStore()
const toast = useToastStore()

const loading = ref(false)
const error = ref(null)

const form = reactive({
  esxi_server_id: '',
  vm_name: '',
  datastore_name: '',
  network_name: 'VM Network',
  power_on: false
})

const esxiServers = computed(() => esxiStore.servers)
const datastores = computed(() => esxiStore.datastores)

// Watch for server selection to load datastores
watch(() => form.esxi_server_id, async (newServerId) => {
  if (newServerId) {
    try {
      await esxiStore.fetchDatastores({ esxi_server_id: newServerId })
    } catch (err) {
      console.error('Error fetching datastores:', err)
      toast.error('Impossible de charger les datastores du serveur')
    }
  }
})

onMounted(async () => {
  if (esxiServers.value.length === 0) {
    await esxiStore.fetchServers()
  }

  // Auto-populate VM name if backup job is available
  if (props.backupJob && props.backupJob.virtual_machine_name) {
    form.vm_name = `${props.backupJob.virtual_machine_name}-restored-${new Date().getTime()}`
  }
})

async function handleSubmit() {
  error.value = null
  loading.value = true

  try {
    await emit('submit', { ...form })
    resetForm()
  } catch (err) {
    error.value = err.message || 'Une erreur est survenue'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.esxi_server_id = ''
  form.vm_name = ''
  form.datastore_name = ''
  form.network_name = 'VM Network'
  form.power_on = false
}
</script>
