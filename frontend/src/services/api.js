import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - Add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login if unauthorized
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ===========================
// AUTH API
// ===========================
export const authAPI = {
  login: (credentials) => apiClient.post('/auth/login/', credentials),
  logout: () => apiClient.post('/auth/logout/'),
  getCurrentUser: () => apiClient.get('/auth/user/'),
}

// ===========================
// ESXI SERVERS API
// ===========================
export const esxiServersAPI = {
  getAll: (params) => apiClient.get('/esxi-servers/', { params }),
  getById: (id) => apiClient.get(`/esxi-servers/${id}/`),
  create: (data) => apiClient.post('/esxi-servers/', data),
  update: (id, data) => apiClient.put(`/esxi-servers/${id}/`, data),
  patch: (id, data) => apiClient.patch(`/esxi-servers/${id}/`, data),
  delete: (id) => apiClient.delete(`/esxi-servers/${id}/`),
  testConnection: (id) => apiClient.post(`/esxi-servers/${id}/test_connection/`),
  syncVMs: (id) => apiClient.post(`/esxi-servers/${id}/sync_vms/`),
  getDatastores: (id) => apiClient.get(`/esxi-servers/${id}/get_datastores/`),
  getNetworks: (id) => apiClient.get(`/esxi-servers/${id}/get_networks/`),
  restoreOVF: (id, data) => apiClient.post(`/esxi-servers/${id}/restore_ovf/`, data),
  getRestoreProgress: (restoreId) => apiClient.get(`/esxi-servers/restore-progress/${restoreId}/`),
  cancelRestore: (restoreId) => apiClient.post(`/esxi-servers/cancel-restore/${restoreId}/`),
}

// ===========================
// VIRTUAL MACHINES API
// ===========================
export const virtualMachinesAPI = {
  getAll: (params) => apiClient.get('/virtual-machines/', { params }),
  getById: (id) => apiClient.get(`/virtual-machines/${id}/`),
  search: (query) => apiClient.get('/virtual-machines/', { params: { search: query } }),
  removeAllSnapshots: (id) => apiClient.post(`/virtual-machines/${id}/remove_all_snapshots/`),
  powerOff: (id) => apiClient.post(`/virtual-machines/${id}/power_off/`),
  powerOn: (id) => apiClient.post(`/virtual-machines/${id}/power_on/`),
}

// ===========================
// DATASTORES API
// ===========================
export const datastoresAPI = {
  getAll: (params) => apiClient.get('/datastores/', { params }),
  getById: (id) => apiClient.get(`/datastores/${id}/`),
}

// ===========================
// BACKUP CONFIGURATIONS API
// ===========================
export const backupConfigsAPI = {
  getAll: (params) => apiClient.get('/backup-configs/', { params }),
  getById: (id) => apiClient.get(`/backup-configs/${id}/`),
  create: (data) => apiClient.post('/backup-configs/', data),
  update: (id, data) => apiClient.put(`/backup-configs/${id}/`, data),
  delete: (id) => apiClient.delete(`/backup-configs/${id}/`),
}

// ===========================
// BACKUP JOBS API
// ===========================
export const backupJobsAPI = {
  getAll: (params) => apiClient.get('/backup-jobs/', { params }),
  getById: (id) => apiClient.get(`/backup-jobs/${id}/`),
  create: (data) => apiClient.post('/backup-jobs/', data),
  update: (id, data) => apiClient.put(`/backup-jobs/${id}/`, data),
  delete: (id) => apiClient.delete(`/backup-jobs/${id}/`),
  start: (id) => apiClient.post(`/backup-jobs/${id}/start/`),
  cancel: (id) => apiClient.post(`/backup-jobs/${id}/cancel/`),
  restore: (id, data) => apiClient.post(`/backup-jobs/${id}/restore/`, data),
  getStatistics: () => apiClient.get('/backup-jobs/statistics/'),
}

// ===========================
// BACKUP SCHEDULES API
// ===========================
export const backupSchedulesAPI = {
  getAll: (params) => apiClient.get('/backup-schedules/', { params }),
  getById: (id) => apiClient.get(`/backup-schedules/${id}/`),
  create: (data) => apiClient.post('/backup-schedules/', data),
  update: (id, data) => apiClient.put(`/backup-schedules/${id}/`, data),
  delete: (id) => apiClient.delete(`/backup-schedules/${id}/`),
  toggleActive: (id) => apiClient.post(`/backup-schedules/${id}/toggle_active/`),
}

// ===========================
// SNAPSHOT SCHEDULES API
// ===========================
export const snapshotSchedulesAPI = {
  getAll: (params) => apiClient.get('/snapshot-schedules/', { params }),
  getById: (id) => apiClient.get(`/snapshot-schedules/${id}/`),
  create: (data) => apiClient.post('/snapshot-schedules/', data),
  update: (id, data) => apiClient.put(`/snapshot-schedules/${id}/`, data),
  delete: (id) => apiClient.delete(`/snapshot-schedules/${id}/`),
  toggleActive: (id) => apiClient.post(`/snapshot-schedules/${id}/toggle_active/`),
  runNow: (id) => apiClient.post(`/snapshot-schedules/${id}/run_now/`),
}

// ===========================
// SNAPSHOTS API
// ===========================
export const snapshotsAPI = {
  getAll: (params) => apiClient.get('/snapshots/', { params }),
  getById: (id) => apiClient.get(`/snapshots/${id}/`),
  revert: (id) => apiClient.post(`/snapshots/${id}/revert/`),
  deleteSnapshot: (id) => apiClient.delete(`/snapshots/${id}/delete_snapshot/`),
}

// ===========================
// REMOTE STORAGE API (Phase 4/5)
// ===========================
export const remoteStorageAPI = {
  getAll: (params) => apiClient.get('/remote-storage/', { params }),
  getById: (id) => apiClient.get(`/remote-storage/${id}/`),
  create: (data) => apiClient.post('/remote-storage/', data),
  update: (id, data) => apiClient.put(`/remote-storage/${id}/`, data),
  delete: (id) => apiClient.delete(`/remote-storage/${id}/`),
  test: (id) => apiClient.post(`/remote-storage/${id}/test/`),
  setDefault: (id) => apiClient.post(`/remote-storage/${id}/set_default/`),
}

// ===========================
// BACKUP CHAINS API (Phase 4)
// ===========================
export const backupChainsAPI = {
  getChain: (vmName) => apiClient.get(`/backup-chains/${vmName}/chain/`),
  getStats: (vmName) => apiClient.get(`/backup-chains/${vmName}/stats/`),
  applyRetention: (vmName, data) => apiClient.post(`/backup-chains/${vmName}/apply-retention/`, data),
  verifyIntegrity: (vmName) => apiClient.post(`/backup-chains/${vmName}/verify-integrity/`),
  getBackups: (vmName) => apiClient.get(`/backup-chains/${vmName}/backups/`),
}

// ===========================
// RESTORE API (Phase 3)
// ===========================
export const restoreAPI = {
  restoreVM: (data) => apiClient.post('/restore/vm/', data),
  restoreVMDK: (data) => apiClient.post('/restore/vmdk/', data),
  recoverFiles: (data) => apiClient.post('/restore/files/', data),
  listFiles: (data) => apiClient.post('/restore/list-files/', data),
  searchFiles: (data) => apiClient.post('/restore/search-files/', data),
  validateRestore: (data) => apiClient.post('/restore/validate/', data),
  validateVM: (data) => apiClient.post('/restore/validate-vm/', data),
  validateVMDK: (data) => apiClient.post('/restore/validate-vmdk/', data),
  listVMDKs: (backupId, vmName) => apiClient.get(`/restore/${backupId}/list-vmdks/`, { params: { vm_name: vmName } }),
  getAvailableBackups: (params) => apiClient.get('/restore/available-backups/', { params }),
  getRestoreChain: (backupId) => apiClient.get(`/restore/restore-chain/${backupId}/`),
  listBackupFiles: (params) => apiClient.get('/restore/list_backup_files/', { params }),
  restoreOVF: (serverId, data) => apiClient.post(`/esxi-servers/${serverId}/restore-ovf/`, data),
}

// ===========================
// NOTIFICATIONS API (Phase 6)
// ===========================
export const notificationsAPI = {
  getAll: (params) => apiClient.get('/notifications/', { params }),
  getById: (id) => apiClient.get(`/notifications/${id}/`),
  create: (data) => apiClient.post('/notifications/', data),
  update: (id, data) => apiClient.put(`/notifications/${id}/`, data),
  delete: (id) => apiClient.delete(`/notifications/${id}/`),
  test: (id, data) => apiClient.post(`/notifications/${id}/test/`, data),
  toggle: (id) => apiClient.post(`/notifications/${id}/toggle/`),
}

// ===========================
// NOTIFICATION LOGS API (Phase 6)
// ===========================
export const notificationLogsAPI = {
  getAll: (params) => apiClient.get('/notification-logs/', { params }),
  getById: (id) => apiClient.get(`/notification-logs/${id}/`),
  getStats: () => apiClient.get('/notification-logs/stats/'),
}

// ===========================
// DASHBOARD API
// ===========================
export const dashboardAPI = {
  getStats: () => apiClient.get('/dashboard/stats/'),
  getRecentBackups: () => apiClient.get('/dashboard/recent_backups/'),
}

// ===========================
// HEALTH MONITORING API (Phase 6)
// ===========================
export const healthAPI = {
  getOverall: () => apiClient.get('/health/overall/'),
  getVMHealth: (vmId) => apiClient.get(`/health/vm/${vmId}/`),
  getIssues: () => apiClient.get('/health/issues/'),
  getMetrics: () => apiClient.get('/health/metrics/'),
}

// ===========================
// OVF EXPORT API (NOUVEAU)
// ===========================
export const ovfExportsAPI = {
  getAll: (params) => apiClient.get('/ovf-exports/', { params }),
  getById: (id) => apiClient.get(`/ovf-exports/${id}/`),
  create: (data) => apiClient.post('/ovf-exports/', data),
  cancel: (id) => apiClient.post(`/ovf-exports/${id}/cancel/`),
  delete: (id) => apiClient.delete(`/ovf-exports/${id}/`),
}

// ===========================
// VM BACKUP API (NOUVEAU)
// ===========================
export const vmBackupsAPI = {
  getAll: (params) => apiClient.get('/vm-backups/', { params }),
  getById: (id) => apiClient.get(`/vm-backups/${id}/`),
  create: (data) => apiClient.post('/vm-backups/', data),
  cancel: (id) => apiClient.post(`/vm-backups/${id}/cancel/`),
  delete: (id) => apiClient.delete(`/vm-backups/${id}/`),
  getAvailableBaseBackups: (vmId) => apiClient.get('/vm-backups/available_base_backups/', { params: { vm_id: vmId } }),
}

// ===========================
// STORAGE PATHS API
// ===========================
export const storagePathsAPI = {
  getAll: (params) => apiClient.get('/storage-paths/', { params }),
  getById: (id) => apiClient.get(`/storage-paths/${id}/`),
  create: (data) => apiClient.post('/storage-paths/', data),
  update: (id, data) => apiClient.put(`/storage-paths/${id}/`, data),
  patch: (id, data) => apiClient.patch(`/storage-paths/${id}/`, data),
  delete: (id) => apiClient.delete(`/storage-paths/${id}/`),
  getActive: () => apiClient.get('/storage-paths/active/'),
  setDefault: (id) => apiClient.post(`/storage-paths/${id}/set_default/`),
}

// ===========================
// VM REPLICATION API (Enterprise)
// ===========================
export const vmReplicationsAPI = {
  getAll: (params) => apiClient.get('/vm-replications/', { params }),
  getById: (id) => apiClient.get(`/vm-replications/${id}/`),
  create: (data) => apiClient.post('/vm-replications/', data),
  update: (id, data) => apiClient.put(`/vm-replications/${id}/`, data),
  patch: (id, data) => apiClient.patch(`/vm-replications/${id}/`, data),
  delete: (id) => apiClient.delete(`/vm-replications/${id}/`),
  startReplication: (id) => apiClient.post(`/vm-replications/${id}/start_replication/`),
  getReplicationProgress: (replicationId) => apiClient.get(`/vm-replications/replication-progress/${replicationId}/`),
  cancelReplication: (replicationId) => apiClient.post(`/vm-replications/cancel-replication/${replicationId}/`),
  checkReplicaExists: (id) => apiClient.get(`/vm-replications/${id}/check_replica_exists/`),
  performFailover: (id, data) => apiClient.post(`/vm-replications/${id}/trigger_failover/`, data),
}

// ===========================
// FAILOVER EVENTS API (Enterprise)
// ===========================
export const failoverEventsAPI = {
  getAll: (params) => apiClient.get('/failover-events/', { params }),
  getById: (id) => apiClient.get(`/failover-events/${id}/`),
}

// ===========================
// BACKUP VERIFICATION API - SureBackup (Enterprise)
// ===========================
export const backupVerificationsAPI = {
  getAll: (params) => apiClient.get('/backup-verifications/', { params }),
  getById: (id) => apiClient.get(`/backup-verifications/${id}/`),
  create: (data) => apiClient.post('/backup-verifications/', data),
  getStatistics: () => apiClient.get('/backup-verifications/statistics/'),
  startVerification: (id) => apiClient.post(`/backup-verifications/${id}/start_verification/`),
}

// ===========================
// VERIFICATION SCHEDULES API (Enterprise)
// ===========================
export const verificationSchedulesAPI = {
  getAll: (params) => apiClient.get('/verification-schedules/', { params }),
  getById: (id) => apiClient.get(`/verification-schedules/${id}/`),
  create: (data) => apiClient.post('/verification-schedules/', data),
  update: (id, data) => apiClient.put(`/verification-schedules/${id}/`, data),
  patch: (id, data) => apiClient.patch(`/verification-schedules/${id}/`, data),
  delete: (id) => apiClient.delete(`/verification-schedules/${id}/`),
  toggleActive: (id) => apiClient.post(`/verification-schedules/${id}/toggle_active/`),
}

// ===========================
// EMAIL SETTINGS API
// ===========================
export const emailSettingsAPI = {
  getSettings: () => apiClient.get('/email-settings/'),
  updateSettings: (data) => apiClient.put('/email-settings/1/', data),
  testEmail: (recipientEmail) => apiClient.post('/email-settings/test_email/', { recipient_email: recipientEmail }),
}

export default apiClient
