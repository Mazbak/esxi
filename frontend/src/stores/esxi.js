import { defineStore } from 'pinia'
import { ref } from 'vue'
import { esxiServersAPI, virtualMachinesAPI, datastoresAPI } from '@/services/api'

export const useEsxiStore = defineStore('esxi', () => {
  const servers = ref([])
  const virtualMachines = ref([])
  const datastores = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ===========================
  // ESXI SERVERS
  // ===========================
  async function fetchServers() {
    loading.value = true
    error.value = null
    try {
      const response = await esxiServersAPI.getAll()
      servers.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des serveurs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createServer(data) {
    loading.value = true
    error.value = null
    try {
      const response = await esxiServersAPI.create(data)
      servers.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création du serveur'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateServer(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await esxiServersAPI.update(id, data)
      const index = servers.value.findIndex(s => s.id === id)
      if (index !== -1) {
        servers.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la mise à jour'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteServer(id) {
    loading.value = true
    error.value = null
    try {
      await esxiServersAPI.delete(id)
      servers.value = servers.value.filter(s => s.id !== id)
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function testConnection(id) {
    loading.value = true
    error.value = null
    try {
      const response = await esxiServersAPI.testConnection(id)
      // Update server status
      const index = servers.value.findIndex(s => s.id === id)
      if (index !== -1) {
        servers.value[index].connection_status = 'connected'
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Échec de la connexion'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function syncVMs(id) {
    loading.value = true
    error.value = null
    try {
      const response = await esxiServersAPI.syncVMs(id)
      await fetchVirtualMachines()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la synchronisation'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // VIRTUAL MACHINES
  // ===========================
  async function fetchVirtualMachines(params) {
    loading.value = true
    error.value = null
    try {
      const response = await virtualMachinesAPI.getAll(params)
      virtualMachines.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des VMs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function powerOffVM(vmId) {
    loading.value = true
    error.value = null
    try {
      const response = await virtualMachinesAPI.powerOff(vmId)

      // Mettre à jour le power_state de la VM dans le store
      const vm = virtualMachines.value.find(v => v.id === vmId)
      if (vm) {
        vm.power_state = 'poweredOff'
      }

      return response.data
    } catch (err) {
      error.value = err.response?.data?.error || err.response?.data?.message || 'Erreur lors de l\'extinction de la VM'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // DATASTORES
  // ===========================
  async function fetchDatastores(params) {
    loading.value = true
    error.value = null
    try {
      const response = await datastoresAPI.getAll(params)
      datastores.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des datastores'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    servers,
    virtualMachines,
    datastores,
    loading,
    error,
    fetchServers,
    createServer,
    updateServer,
    deleteServer,
    testConnection,
    syncVMs,
    fetchVirtualMachines,
    powerOffVM,
    fetchDatastores,
  }
})
