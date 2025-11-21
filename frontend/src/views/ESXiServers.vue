<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Serveurs ESXi</h1>
        <p class="mt-1 text-sm text-gray-500">Gérez vos serveurs VMware ESXi</p>
      </div>
      <button @click="showAddModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Ajouter un serveur
      </button>
    </div>

    <!-- Loading State -->
    <Loading v-if="loading && servers.length === 0" text="Chargement des serveurs..." />

    <!-- Servers List -->
    <div v-else-if="servers.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div
        v-for="server in servers"
        :key="server.id"
        class="card hover:shadow-lg transition-all"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center space-x-3">
            <div :class="getStatusColor(server.connection_status)" class="p-3 rounded-lg">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{{ server.hostname }}</h3>
              <p class="text-sm text-gray-500">Port: {{ server.port }}</p>
            </div>
          </div>
          <span
            :class="getStatusBadgeClass(server.connection_status)"
            class="badge"
          >
            {{ getStatusLabel(server.connection_status) }}
          </span>
        </div>

        <!-- Info -->
        <div class="space-y-2 mb-4">
          <div class="flex items-center text-sm">
            <svg class="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span class="text-gray-600">Utilisateur:</span>
            <span class="ml-2 font-medium text-gray-900">{{ server.username }}</span>
          </div>
          <div v-if="server.last_connection" class="flex items-center text-sm">
            <svg class="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-600">Dernière connexion:</span>
            <span class="ml-2 text-gray-900">{{ formatDate(server.last_connection) }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center space-x-2 pt-4 border-t border-gray-200">
          <button
            @click="testConnection(server)"
            :disabled="testingConnection[server.id]"
            class="flex-1 btn-primary text-sm"
          >
            <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {{ testingConnection[server.id] ? 'Test...' : 'Tester' }}
          </button>
          <button
            @click="syncVMs(server)"
            :disabled="syncingVMs[server.id]"
            class="flex-1 btn-success text-sm"
          >
            <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {{ syncingVMs[server.id] ? 'Sync...' : 'Sync VMs' }}
          </button>
          <button
            @click="editServer(server)"
            class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            @click="confirmDelete(server)"
            class="p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded-lg"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <svg class="w-24 h-24 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Aucun serveur ESXi</h3>
      <p class="text-gray-500 mb-4">Commencez par ajouter votre premier serveur ESXi</p>
      <button @click="showAddModal = true" class="btn-primary">
        Ajouter un serveur
      </button>
    </div>

    <!-- Add/Edit Modal -->
    <ServerForm
      :show="showAddModal || showEditModal"
      :server="selectedServer"
      :is-edit="showEditModal"
      @close="closeModal"
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import Loading from '@/components/common/Loading.vue'
import ServerForm from '@/components/esxi/ServerForm.vue'

const esxiStore = useEsxiStore()
const toast = useToastStore()

const showAddModal = ref(false)
const showEditModal = ref(false)
const selectedServer = ref(null)
const testingConnection = reactive({})
const syncingVMs = reactive({})

const servers = computed(() => esxiStore.servers)
const loading = computed(() => esxiStore.loading)

onMounted(() => {
  esxiStore.fetchServers()
})

function formatDate(date) {
  if (!date) return '-'
  return format(new Date(date), 'dd MMM yyyy HH:mm', { locale: fr })
}

function getStatusColor(status) {
  const colors = {
    connected: 'bg-green-500',
    disconnected: 'bg-gray-400',
    error: 'bg-red-500'
  }
  return colors[status] || 'bg-gray-400'
}

function getStatusBadgeClass(status) {
  const classes = {
    connected: 'badge-success',
    disconnected: 'badge-gray',
    error: 'badge-danger'
  }
  return classes[status] || 'badge-gray'
}

function getStatusLabel(status) {
  const labels = {
    connected: 'Connecté',
    disconnected: 'Déconnecté',
    error: 'Erreur'
  }
  return labels[status] || status
}

async function testConnection(server) {
  testingConnection[server.id] = true
  try {
    await esxiStore.testConnection(server.id)
    toast.success(`Connexion au serveur ${server.hostname} réussie!`)
  } catch (err) {
    toast.error(`Échec de la connexion à ${server.hostname}: ${err.message}`)
  } finally {
    testingConnection[server.id] = false
  }
}

async function syncVMs(server) {
  syncingVMs[server.id] = true
  try {
    toast.info('Synchronisation des VMs en cours...')
    const result = await esxiStore.syncVMs(server.id)
    toast.success(`${result.vms_count} VM(s) synchronisée(s) depuis ${server.hostname}`)
  } catch (err) {
    toast.error(`Erreur lors de la synchronisation: ${err.message}`)
  } finally {
    syncingVMs[server.id] = false
  }
}

function editServer(server) {
  selectedServer.value = server
  showEditModal.value = true
}

function confirmDelete(server) {
  if (confirm(`Êtes-vous sûr de vouloir supprimer le serveur ${server.hostname}?`)) {
    deleteServer(server)
  }
}

async function deleteServer(server) {
  try {
    await esxiStore.deleteServer(server.id)
    toast.success(`Serveur ${server.hostname} supprimé avec succès`)
  } catch (err) {
    toast.error(`Erreur lors de la suppression: ${err.message}`)
  }
}

async function handleSubmit(formData) {
  try {
    if (showEditModal.value && selectedServer.value) {
      await esxiStore.updateServer(selectedServer.value.id, formData)
      toast.success('Serveur ESXi mis à jour avec succès')
    } else {
      await esxiStore.createServer(formData)
      toast.success(`Serveur ${formData.hostname} ajouté avec succès`)
    }
    closeModal()
  } catch (err) {
    toast.error(`Erreur: ${err.message || 'Une erreur est survenue'}`)
    throw err
  }
}

function closeModal() {
  showAddModal.value = false
  showEditModal.value = false
  selectedServer.value = null
}
</script>
