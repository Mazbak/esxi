<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Machines Virtuelles</h1>
        <p class="mt-1 text-sm text-gray-500">Liste de toutes les VMs synchronisées</p>
      </div>
      <div class="flex items-center space-x-3">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher une VM..."
          class="input-field w-64"
        >
        <button @click="refreshVMs" class="btn-primary">
          <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Actualiser
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="flex items-center space-x-4">
        <div class="flex-1">
          <label class="text-sm font-medium text-gray-700 mr-2">État:</label>
          <select v-model="powerStateFilter" class="input-field inline-block w-auto">
            <option value="">Tous</option>
            <option value="poweredOn">Allumé</option>
            <option value="poweredOff">Éteint</option>
            <option value="suspended">Suspendu</option>
          </select>
        </div>
        <div class="flex-1">
          <label class="text-sm font-medium text-gray-700 mr-2">Serveur:</label>
          <select v-model="serverFilter" class="input-field inline-block w-auto">
            <option value="">Tous les serveurs</option>
            <option v-for="server in servers" :key="server.id" :value="server.id">
              {{ server.hostname }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <Loading v-if="loading && virtualMachines.length === 0" text="Chargement des VMs..." />

    <!-- VMs Table -->
    <div v-else-if="filteredVMs.length > 0" class="card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nom
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                État
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Serveur
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                CPU / RAM
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Stockage
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Système
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                IP
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="vm in filteredVMs" :key="vm.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="p-2 bg-purple-100 rounded-lg mr-3">
                    <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                    </svg>
                  </div>
                  <div>
                    <div class="text-sm font-medium text-gray-900">{{ vm.name }}</div>
                    <div class="text-xs text-gray-500">ID: {{ vm.vm_id }}</div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getPowerStateBadgeClass(vm.power_state)" class="badge">
                  {{ getPowerStateLabel(vm.power_state) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ getServerName(vm.server) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ vm.num_cpu }} vCPU / {{ formatMemory(vm.memory_mb) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ vm.disk_gb.toFixed(2) }} GB
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <div class="max-w-xs truncate" :title="vm.guest_os_full">
                  {{ vm.guest_os }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ vm.ip_address || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <router-link
                  :to="`/ovf-exports?vm=${vm.id}`"
                  class="text-primary-600 hover:text-primary-900 mr-3"
                >
                  Sauvegarder
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <svg class="w-24 h-24 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Aucune machine virtuelle</h3>
      <p class="text-gray-500 mb-4">Synchronisez vos serveurs ESXi pour afficher les VMs</p>
      <router-link to="/esxi-servers" class="btn-primary">
        Gérer les serveurs
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import Loading from '@/components/common/Loading.vue'

const esxiStore = useEsxiStore()
const toast = useToastStore()

const searchQuery = ref('')
const powerStateFilter = ref('')
const serverFilter = ref('')

const servers = computed(() => esxiStore.servers)
const virtualMachines = computed(() => esxiStore.virtualMachines)
const loading = computed(() => esxiStore.loading)

const filteredVMs = computed(() => {
  let vms = virtualMachines.value

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    vms = vms.filter(vm =>
      vm.name.toLowerCase().includes(query) ||
      vm.guest_os.toLowerCase().includes(query) ||
      (vm.ip_address && vm.ip_address.includes(query))
    )
  }

  // Power state filter
  if (powerStateFilter.value) {
    vms = vms.filter(vm => vm.power_state === powerStateFilter.value)
  }

  // Server filter
  if (serverFilter.value) {
    vms = vms.filter(vm => vm.server === parseInt(serverFilter.value))
  }

  return vms
})

onMounted(() => {
  esxiStore.fetchServers()
  esxiStore.fetchVirtualMachines()
})

async function refreshVMs() {
  try {
    toast.info('Actualisation des VMs en cours...')
    await esxiStore.fetchVirtualMachines()
    toast.success(`${virtualMachines.value.length} machine(s) virtuelle(s) chargée(s)`)
  } catch (err) {
    toast.error('Erreur lors du rechargement des VMs')
  }
}

function getServerName(serverId) {
  const server = servers.value.find(s => s.id === serverId)
  return server ? server.hostname : `Server #${serverId}`
}

function getPowerStateBadgeClass(state) {
  const classes = {
    poweredOn: 'badge-success',
    poweredOff: 'badge-gray',
    suspended: 'badge-warning'
  }
  return classes[state] || 'badge-gray'
}

function getPowerStateLabel(state) {
  const labels = {
    poweredOn: 'Allumé',
    poweredOff: 'Éteint',
    suspended: 'Suspendu'
  }
  return labels[state] || state
}

function formatMemory(mb) {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`
  }
  return `${mb} MB`
}
</script>
