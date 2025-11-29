<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">🔄 Réplication VM</h1>
        <p class="mt-1 text-sm text-gray-500">Configurez la réplication et le failover automatique entre serveurs ESXi</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvelle Réplication
      </button>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-blue-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Total Réplications</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ replications.length }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-green-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Actives</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ activeCount }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-yellow-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">En Cours</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ inProgressCount }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-red-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Total Failovers</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ failoverEvents.length }}</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>

    <!-- Replication List -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Réplications Configurées</h2>

      <div v-if="loading" class="text-center py-8">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p class="mt-2 text-gray-500">Chargement...</p>
      </div>

      <div v-else-if="replications.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">Aucune réplication</h3>
        <p class="mt-1 text-sm text-gray-500">Commencez par créer une nouvelle réplication</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source → Destination</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Intervalle</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dernière Réplication</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="replication in replications" :key="replication.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ replication.vm_name }}</div>
                <div class="text-sm text-gray-500">{{ replication.name }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">
                  {{ replication.source_server_name }} → {{ replication.destination_server_name }}
                </div>
                <div class="text-sm text-gray-500">{{ replication.destination_datastore }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ replication.replication_interval_minutes }} min
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getStatusClass(replication.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ replication.status_display }}
                </span>
                <div v-if="replication.failover_mode === 'automatic'" class="mt-1">
                  <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                    Auto-Failover
                  </span>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <div v-if="replication.last_replication_at">
                  {{ formatDateTime(replication.last_replication_at) }}
                </div>
                <div v-else class="text-gray-400">Jamais</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                <button
                  @click="startReplication(replication)"
                  :disabled="!replication.is_active"
                  class="text-blue-600 hover:text-blue-900 disabled:text-gray-400"
                  title="Démarrer la réplication"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </button>
                <button
                  @click="showFailoverModal(replication)"
                  :disabled="!replication.is_active"
                  class="text-orange-600 hover:text-orange-900 disabled:text-gray-400"
                  title="Failover manuel"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </button>
                <button
                  @click="editReplication(replication)"
                  class="text-indigo-600 hover:text-indigo-900"
                  title="Modifier"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  @click="deleteReplication(replication)"
                  class="text-red-600 hover:text-red-900"
                  title="Supprimer"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Failover Events History -->
    <div class="card" v-if="failoverEvents.length > 0">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Historique des Failovers</h2>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Déclenché par</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="event in failoverEvents.slice(0, 5)" :key="event.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ event.vm_name }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ event.failover_type_display }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getFailoverStatusClass(event.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ event.status_display }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ event.triggered_by_username || 'Système' }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDateTime(event.started_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal || editingReplication" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900">
            {{ editingReplication ? 'Modifier la Réplication' : 'Nouvelle Réplication' }}
          </h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nom</label>
            <input v-model="form.name" type="text" class="input" placeholder="Ex: Réplication WebServer" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Machine Virtuelle</label>
            <select v-model="form.virtual_machine" class="input">
              <option value="">Sélectionner une VM...</option>
              <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">{{ vm.name }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Serveur Source</label>
              <select v-model="form.source_server" class="input">
                <option value="">Sélectionner...</option>
                <option v-for="server in esxiServers" :key="server.id" :value="server.id">{{ server.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Serveur Destination</label>
              <select v-model="form.destination_server" class="input">
                <option value="">Sélectionner...</option>
                <option v-for="server in esxiServers" :key="server.id" :value="server.id">{{ server.name }}</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Datastore Destination</label>
            <input v-model="form.destination_datastore" type="text" class="input" placeholder="Ex: datastore1" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Intervalle de Réplication (minutes)</label>
            <input v-model.number="form.replication_interval_minutes" type="number" class="input" min="15" step="15" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Mode de Failover</label>
            <select v-model="form.failover_mode" class="input">
              <option value="manual">Manuel</option>
              <option value="automatic">Automatique</option>
            </select>
          </div>
          <div v-if="form.failover_mode === 'automatic'">
            <label class="block text-sm font-medium text-gray-700 mb-1">Seuil Auto-Failover (minutes)</label>
            <input v-model.number="form.auto_failover_threshold_minutes" type="number" class="input" min="5" />
            <p class="mt-1 text-xs text-gray-500">Temps d'indisponibilité avant déclenchement auto du failover</p>
          </div>
          <div class="flex items-center">
            <input v-model="form.is_active" type="checkbox" id="is_active" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
            <label for="is_active" class="ml-2 block text-sm text-gray-900">Activer la réplication</label>
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3">
          <button @click="closeModal" class="btn-secondary">Annuler</button>
          <button @click="saveReplication" class="btn-primary" :disabled="saving">
            {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Failover Confirmation Modal -->
    <div v-if="showFailoverConfirmModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900">⚡ Déclencher le Failover</h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <p class="text-sm text-gray-600">
            Vous êtes sur le point de basculer la VM <strong>{{ selectedReplication?.vm_name }}</strong>
            vers le serveur de destination <strong>{{ selectedReplication?.destination_server_name }}</strong>.
          </p>
          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm text-yellow-700">Cette opération va arrêter la VM source et démarrer la VM destination.</p>
              </div>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Raison du failover</label>
            <textarea v-model="failoverReason" rows="3" class="input" placeholder="Décrire la raison du failover..."></textarea>
          </div>
          <div class="flex items-center">
            <input v-model="failoverTestMode" type="checkbox" id="test_mode" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
            <label for="test_mode" class="ml-2 block text-sm text-gray-900">Mode test (ne pas arrêter la VM source)</label>
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3">
          <button @click="showFailoverConfirmModal = false" class="btn-secondary">Annuler</button>
          <button @click="performFailover" class="btn-danger" :disabled="saving">
            {{ saving ? 'Failover en cours...' : 'Confirmer le Failover' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { vmReplicationsAPI, failoverEventsAPI, virtualMachinesAPI, esxiServersAPI } from '../services/api'
import { useToast } from 'vue-toastification'

const toast = useToast()

const replications = ref([])
const failoverEvents = ref([])
const virtualMachines = ref([])
const esxiServers = ref([])
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const showFailoverConfirmModal = ref(false)
const editingReplication = ref(null)
const selectedReplication = ref(null)
const failoverReason = ref('')
const failoverTestMode = ref(false)

const form = ref({
  name: '',
  virtual_machine: '',
  source_server: '',
  destination_server: '',
  destination_datastore: '',
  replication_interval_minutes: 60,
  failover_mode: 'manual',
  auto_failover_threshold_minutes: 15,
  is_active: true
})

const activeCount = computed(() => replications.value.filter(r => r.is_active).length)
const inProgressCount = computed(() => replications.value.filter(r => r.status === 'in_progress').length)

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const [replicationsRes, failoverRes, vmsRes, serversRes] = await Promise.all([
      vmReplicationsAPI.getAll(),
      failoverEventsAPI.getAll(),
      virtualMachinesAPI.getAll(),
      esxiServersAPI.getAll()
    ])
    replications.value = replicationsRes.data.results || replicationsRes.data
    failoverEvents.value = failoverRes.data.results || failoverRes.data
    virtualMachines.value = vmsRes.data.results || vmsRes.data
    esxiServers.value = serversRes.data.results || serversRes.data
  } catch (error) {
    console.error('Erreur chargement données:', error)
    toast.error('Erreur lors du chargement des données')
  } finally {
    loading.value = false
  }
}

async function saveReplication() {
  saving.value = true
  try {
    if (editingReplication.value) {
      await vmReplicationsAPI.update(editingReplication.value.id, form.value)
      toast.success('Réplication mise à jour avec succès')
    } else {
      await vmReplicationsAPI.create(form.value)
      toast.success('Réplication créée avec succès')
    }
    closeModal()
    fetchData()
  } catch (error) {
    console.error('Erreur sauvegarde:', error)
    toast.error('Erreur lors de la sauvegarde')
  } finally {
    saving.value = false
  }
}

function editReplication(replication) {
  editingReplication.value = replication
  form.value = { ...replication }
  showCreateModal.value = true
}

function closeModal() {
  showCreateModal.value = false
  editingReplication.value = null
  form.value = {
    name: '',
    virtual_machine: '',
    source_server: '',
    destination_server: '',
    destination_datastore: '',
    replication_interval_minutes: 60,
    failover_mode: 'manual',
    auto_failover_threshold_minutes: 15,
    is_active: true
  }
}

async function startReplication(replication) {
  if (!confirm(`Démarrer la réplication de ${replication.vm_name} ?`)) return

  try {
    await vmReplicationsAPI.startReplication(replication.id)
    toast.success('Réplication démarrée')
    fetchData()
  } catch (error) {
    console.error('Erreur démarrage réplication:', error)
    toast.error('Erreur lors du démarrage de la réplication')
  }
}

function showFailoverModal(replication) {
  selectedReplication.value = replication
  failoverReason.value = ''
  failoverTestMode.value = false
  showFailoverConfirmModal.value = true
}

async function performFailover() {
  saving.value = true
  try {
    await vmReplicationsAPI.performFailover(selectedReplication.value.id, {
      reason: failoverReason.value,
      test_mode: failoverTestMode.value
    })
    toast.success('Failover déclenché avec succès')
    showFailoverConfirmModal.value = false
    fetchData()
  } catch (error) {
    console.error('Erreur failover:', error)
    toast.error('Erreur lors du failover')
  } finally {
    saving.value = false
  }
}

async function deleteReplication(replication) {
  if (!confirm(`Supprimer la réplication "${replication.name}" ?`)) return

  try {
    await vmReplicationsAPI.delete(replication.id)
    toast.success('Réplication supprimée')
    fetchData()
  } catch (error) {
    console.error('Erreur suppression:', error)
    toast.error('Erreur lors de la suppression')
  }
}

function getStatusClass(status) {
  const classes = {
    idle: 'bg-gray-100 text-gray-800',
    in_progress: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getFailoverStatusClass(status) {
  const classes = {
    initiated: 'bg-yellow-100 text-yellow-800',
    in_progress: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    rolled_back: 'bg-orange-100 text-orange-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function formatDateTime(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>
