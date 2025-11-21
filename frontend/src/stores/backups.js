import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  backupJobsAPI,
  backupConfigsAPI,
  backupSchedulesAPI,
  remoteStorageAPI,
  notificationsAPI,
  notificationLogsAPI
} from '@/services/api'

export const useBackupsStore = defineStore('backups', () => {
  const jobs = ref([])
  const backupConfigurations = ref([])
  const schedules = ref([])
  const remoteStorages = ref([])
  const notifications = ref([])
  const notificationLogs = ref([])
  const statistics = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // ===========================
  // BACKUP JOBS
  // ===========================
  async function fetchJobs(params) {
    loading.value = true
    error.value = null
    try {
      const response = await backupJobsAPI.getAll(params)
      jobs.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des jobs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createJob(data) {
    loading.value = true
    error.value = null
    try {
      const response = await backupJobsAPI.create(data)
      jobs.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création du job'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startJob(id) {
    loading.value = true
    error.value = null
    try {
      // Optimistic update: set status to running immediately
      const index = jobs.value.findIndex(j => j.id === id)
      if (index !== -1) {
        jobs.value[index].status = 'running'
        jobs.value[index].progress_percentage = 0
      }

      const response = await backupJobsAPI.start(id)
      return response.data
    } catch (err) {
      // Revert on error: fetch fresh data
      await fetchJobs()
      error.value = err.response?.data?.message || 'Erreur lors du démarrage'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelJob(id) {
    loading.value = true
    error.value = null
    try {
      const response = await backupJobsAPI.cancel(id)
      const index = jobs.value.findIndex(j => j.id === id)
      if (index !== -1) {
        jobs.value[index].status = 'cancelled'
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de l\'annulation'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteJob(id) {
    loading.value = true
    error.value = null
    try {
      await backupJobsAPI.delete(id)
      jobs.value = jobs.value.filter(j => j.id !== id)
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStatistics() {
    try {
      const response = await backupJobsAPI.getStatistics()
      statistics.value = response.data
    } catch (err) {
      console.error('Failed to fetch statistics:', err)
    }
  }

  async function restoreJob(id, restoreData) {
    loading.value = true
    error.value = null
    try {
      const response = await backupJobsAPI.restore(id, restoreData)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la restauration'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // BACKUP CONFIGURATIONS
  // ===========================
  async function fetchBackupConfigurations() {
    loading.value = true
    error.value = null
    try {
      const response = await backupConfigsAPI.getAll()
      backupConfigurations.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des configurations'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createBackupConfiguration(data) {
    loading.value = true
    error.value = null
    try {
      const response = await backupConfigsAPI.create(data)
      backupConfigurations.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateBackupConfiguration(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await backupConfigsAPI.update(id, data)
      const index = backupConfigurations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        backupConfigurations.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la mise à jour'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteBackupConfiguration(id) {
    loading.value = true
    error.value = null
    try {
      await backupConfigsAPI.delete(id)
      backupConfigurations.value = backupConfigurations.value.filter(c => c.id !== id)
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // BACKUP SCHEDULES
  // ===========================
  async function fetchSchedules(params) {
    loading.value = true
    error.value = null
    try {
      const response = await backupSchedulesAPI.getAll(params)
      schedules.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des planifications'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createSchedule(data) {
    loading.value = true
    error.value = null
    try {
      const response = await backupSchedulesAPI.create(data)
      schedules.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateSchedule(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await backupSchedulesAPI.update(id, data)
      const index = schedules.value.findIndex(s => s.id === id)
      if (index !== -1) {
        schedules.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la mise à jour'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteSchedule(id) {
    loading.value = true
    error.value = null
    try {
      await backupSchedulesAPI.delete(id)
      schedules.value = schedules.value.filter(s => s.id !== id)
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function toggleScheduleActive(id) {
    loading.value = true
    error.value = null
    try {
      const response = await backupSchedulesAPI.toggleActive(id)
      const index = schedules.value.findIndex(s => s.id === id)
      if (index !== -1) {
        schedules.value[index].is_active = response.data.is_active
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du changement de statut'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // REMOTE STORAGE
  // ===========================
  async function fetchRemoteStorages() {
    loading.value = true
    error.value = null
    try {
      const response = await remoteStorageAPI.getAll()
      remoteStorages.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des stockages distants'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createRemoteStorage(data) {
    loading.value = true
    error.value = null
    try {
      const response = await remoteStorageAPI.create(data)
      remoteStorages.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateRemoteStorage(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await remoteStorageAPI.update(id, data)
      const index = remoteStorages.value.findIndex(s => s.id === id)
      if (index !== -1) {
        remoteStorages.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la mise à jour'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteRemoteStorage(id) {
    loading.value = true
    error.value = null
    try {
      await remoteStorageAPI.delete(id)
      remoteStorages.value = remoteStorages.value.filter(s => s.id !== id)
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function testRemoteStorage(id) {
    loading.value = true
    error.value = null
    try {
      const response = await remoteStorageAPI.test(id)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du test de connexion'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function setDefaultRemoteStorage(id) {
    loading.value = true
    error.value = null
    try {
      const response = await remoteStorageAPI.setDefault(id)
      // Update all storages to reflect the new default
      remoteStorages.value.forEach(s => {
        s.is_default = s.id === id
      })
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la définition du stockage par défaut'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // NOTIFICATIONS (Phase 6)
  // ===========================
  async function fetchNotifications() {
    loading.value = true
    error.value = null
    try {
      const response = await notificationsAPI.getAll()
      notifications.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des notifications'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createNotification(data) {
    loading.value = true
    error.value = null
    try {
      const response = await notificationsAPI.create(data)
      notifications.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la création'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateNotification(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await notificationsAPI.update(id, data)
      const index = notifications.value.findIndex(n => n.id === id)
      if (index !== -1) {
        notifications.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la mise à jour'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteNotification(id) {
    loading.value = true
    error.value = null
    try {
      await notificationsAPI.delete(id)
      notifications.value = notifications.value.filter(n => n.id !== id)
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors de la suppression'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function testNotification(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await notificationsAPI.test(id, data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du test de notification'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function toggleNotification(id) {
    loading.value = true
    error.value = null
    try {
      const response = await notificationsAPI.toggle(id)
      const index = notifications.value.findIndex(n => n.id === id)
      if (index !== -1) {
        notifications.value[index].is_enabled = response.data.is_enabled
      }
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du changement de statut'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ===========================
  // NOTIFICATION LOGS (Phase 6)
  // ===========================
  async function fetchNotificationLogs(params) {
    loading.value = true
    error.value = null
    try {
      const response = await notificationLogsAPI.getAll(params)
      notificationLogs.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des logs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchNotificationStats() {
    loading.value = true
    error.value = null
    try {
      const response = await notificationLogsAPI.getStats()
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des statistiques'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    jobs,
    backupConfigurations,
    schedules,
    remoteStorages,
    notifications,
    notificationLogs,
    statistics,
    loading,
    error,
    // Jobs
    fetchJobs,
    createJob,
    startJob,
    cancelJob,
    deleteJob,
    fetchStatistics,
    restoreJob,
    // Backup Configurations
    fetchBackupConfigurations,
    createBackupConfiguration,
    updateBackupConfiguration,
    deleteBackupConfiguration,
    // Schedules
    fetchSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    toggleScheduleActive,
    // Remote Storage
    fetchRemoteStorages,
    createRemoteStorage,
    updateRemoteStorage,
    deleteRemoteStorage,
    testRemoteStorage,
    setDefaultRemoteStorage,
    // Notifications
    fetchNotifications,
    createNotification,
    updateNotification,
    deleteNotification,
    testNotification,
    toggleNotification,
    // Notification Logs
    fetchNotificationLogs,
    fetchNotificationStats,
  }
})
