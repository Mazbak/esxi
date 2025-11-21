import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardAPI } from '@/services/api'

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref(null)
  const recentBackups = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchStats() {
    loading.value = true
    error.value = null
    try {
      const response = await dashboardAPI.getStats()
      stats.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des statistiques'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchRecentBackups() {
    loading.value = true
    error.value = null
    try {
      const response = await dashboardAPI.getRecentBackups()
      recentBackups.value = response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Erreur lors du chargement des sauvegardes récentes'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function refreshDashboard() {
    await Promise.all([
      fetchStats(),
      fetchRecentBackups()
    ])
  }

  return {
    stats,
    recentBackups,
    loading,
    error,
    fetchStats,
    fetchRecentBackups,
    refreshDashboard,
  }
})
