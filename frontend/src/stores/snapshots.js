import { defineStore } from 'pinia'
import { ref } from 'vue'
import { snapshotSchedulesAPI, snapshotsAPI } from '@/services/api'

export const useSnapshotsStore = defineStore('snapshots', () => {
  const schedules = ref([])
  const snapshots = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Fetch snapshot schedules
  async function fetchSchedules() {
    loading.value = true
    error.value = null
    try {
      const response = await snapshotSchedulesAPI.getAll()
      schedules.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Fetch snapshots
  async function fetchSnapshots() {
    loading.value = true
    error.value = null
    try {
      const response = await snapshotsAPI.getAll()
      snapshots.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Create snapshot schedule
  async function createSchedule(data) {
    loading.value = true
    error.value = null
    try {
      const response = await snapshotSchedulesAPI.create(data)
      schedules.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Toggle schedule active status
  async function toggleSchedule(scheduleId) {
    try {
      const response = await snapshotSchedulesAPI.toggleActive(scheduleId)
      const index = schedules.value.findIndex(s => s.id === scheduleId)
      if (index !== -1) {
        schedules.value[index].is_active = response.data.is_active
      }
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Run schedule now
  async function runScheduleNow(scheduleId) {
    try {
      const response = await snapshotSchedulesAPI.runNow(scheduleId)
      await fetchSnapshots() // Refresh snapshots list
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Delete schedule
  async function deleteSchedule(scheduleId) {
    try {
      await snapshotSchedulesAPI.delete(scheduleId)
      schedules.value = schedules.value.filter(s => s.id !== scheduleId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Revert to snapshot
  async function revertSnapshot(snapshotId) {
    try {
      const response = await snapshotsAPI.revert(snapshotId)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Delete snapshot
  async function deleteSnapshot(snapshotId) {
    try {
      await snapshotsAPI.deleteSnapshot(snapshotId)
      snapshots.value = snapshots.value.filter(s => s.id !== snapshotId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    schedules,
    snapshots,
    loading,
    error,
    fetchSchedules,
    fetchSnapshots,
    createSchedule,
    toggleSchedule,
    runScheduleNow,
    deleteSchedule,
    revertSnapshot,
    deleteSnapshot
  }
})
