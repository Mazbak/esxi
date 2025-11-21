import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ovfExportsAPI, vmBackupsAPI } from '@/services/api'
import { useToastStore } from './toast'

export const useVMOperationsStore = defineStore('vmOperations', () => {
  const toastStore = useToastStore()

  // État
  const ovfExports = ref([])
  const vmBackups = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ===========================
  // OVF EXPORTS
  // ===========================

  async function fetchOVFExports(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await ovfExportsAPI.getAll(params)
      ovfExports.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des exports OVF'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createOVFExport(data) {
    loading.value = true
    error.value = null
    try {
      const response = await ovfExportsAPI.create(data)
      ovfExports.value.unshift(response.data)
      toastStore.success('Export OVF créé et démarré avec succès')
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création de l\'export OVF'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelOVFExport(id) {
    loading.value = true
    error.value = null
    try {
      await ovfExportsAPI.cancel(id)
      const index = ovfExports.value.findIndex(e => e.id === id)
      if (index !== -1) {
        ovfExports.value[index].status = 'cancelled'
      }
      toastStore.success('Export OVF annulé')
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de l\'annulation'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteOVFExport(id) {
    loading.value = true
    error.value = null
    try {
      await ovfExportsAPI.delete(id)
      ovfExports.value = ovfExports.value.filter(e => e.id !== id)
      toastStore.success('Export OVF supprimé')
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // VM BACKUPS
  // ===========================

  async function fetchVMBackups(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await vmBackupsAPI.getAll(params)
      vmBackups.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des backups'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createVMBackup(data) {
    loading.value = true
    error.value = null
    try {
      const response = await vmBackupsAPI.create(data)
      vmBackups.value.unshift(response.data)
      toastStore.success('Backup VM créé et démarré avec succès')
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création du backup'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelVMBackup(id) {
    loading.value = true
    error.value = null
    try {
      await vmBackupsAPI.cancel(id)
      const index = vmBackups.value.findIndex(b => b.id === id)
      if (index !== -1) {
        vmBackups.value[index].status = 'cancelled'
      }
      toastStore.success('Backup annulé')
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de l\'annulation'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteVMBackup(id) {
    loading.value = true
    error.value = null
    try {
      await vmBackupsAPI.delete(id)
      vmBackups.value = vmBackups.value.filter(b => b.id !== id)
      toastStore.success('Backup supprimé')
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      toastStore.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getAvailableBaseBackups(vmId) {
    try {
      const response = await vmBackupsAPI.getAvailableBaseBackups(vmId)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la récupération des backups de base'
      throw err
    }
  }

  return {
    // État
    ovfExports,
    vmBackups,
    loading,
    error,

    // OVF Exports
    fetchOVFExports,
    createOVFExport,
    cancelOVFExport,
    deleteOVFExport,

    // VM Backups
    fetchVMBackups,
    createVMBackup,
    cancelVMBackup,
    deleteVMBackup,
    getAvailableBaseBackups,
  }
})
