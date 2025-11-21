<template>
  <div class="backup-chain-view">
    <!-- Header -->
    <div class="chain-header">
      <h2>📦 Chaîne de Backup: {{ vmName }}</h2>
      <button @click="refreshChain" class="btn btn-refresh">
        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Actualiser
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      Chargement de la chaîne...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Content -->
    <div v-else-if="chain">
      <!-- Statistics -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Backups</div>
          <div class="stat-value">{{ chain.total_backups || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Full Backups</div>
          <div class="stat-value full">{{ stats.full_backups || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Incrementals</div>
          <div class="stat-value incremental">{{ stats.incremental_backups || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Taille Totale</div>
          <div class="stat-value">{{ stats.total_size_gb || 0 }} GB</div>
        </div>
      </div>

      <!-- Chain Info -->
      <div class="chain-info">
        <div class="info-row">
          <span class="label">Dernière sauvegarde:</span>
          <span class="value">{{ formatDate(chain.last_backup_at) }}</span>
        </div>
        <div class="info-row">
          <span class="label">Dernière Full:</span>
          <span class="value">{{ formatDate(chain.last_full_backup_at) }}</span>
        </div>
        <div class="info-row">
          <span class="label">CBT Enabled:</span>
          <span :class="['badge', chain.cbt_enabled ? 'success' : 'warning']">
            {{ chain.cbt_enabled ? 'Oui' : 'Non' }}
          </span>
        </div>
        <div class="info-row">
          <span class="label">Change ID actuel:</span>
          <span class="value">{{ chain.current_change_id }}</span>
        </div>
      </div>

      <!-- Retention Policy -->
      <div class="retention-section">
        <h3>Politique de Rétention</h3>
        <div class="retention-info">
          <span>Type: <strong>{{ chain.retention_policy?.type }}</strong></span>
          <span>Valeur: <strong>{{ chain.retention_policy?.value }}</strong></span>
          <span v-if="chain.retention_policy?.keep_monthly">
            Keep Monthly: <strong>Oui</strong>
          </span>
        </div>
        <div class="retention-actions">
          <button @click="previewRetention" class="btn btn-secondary">
            Prévisualiser Rétention
          </button>
          <button @click="applyRetention" class="btn btn-danger">
            Appliquer Rétention
          </button>
        </div>
      </div>

      <!-- Backups Table -->
      <div class="backups-section">
        <h3>Backups dans la Chaîne ({{ backups.length }})</h3>

        <table class="backups-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>ID</th>
              <th>Date</th>
              <th>Taille</th>
              <th>Status</th>
              <th>Base</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="backup in backups" :key="backup.id" :class="['backup-row', backup.type]">
              <td>
                <span :class="['type-badge', backup.type]">
                  {{ backup.type === 'full' ? '🔵 Full' : '🟢 Incr' }}
                </span>
              </td>
              <td class="backup-id">{{ backup.id }}</td>
              <td>{{ formatDate(backup.timestamp) }}</td>
              <td>{{ formatSize(backup.size_bytes) }}</td>
              <td>
                <span :class="['status-badge', backup.status]">
                  {{ backup.status }}
                </span>
              </td>
              <td>
                <span v-if="backup.base_backup_id" class="base-link">
                  {{ backup.base_backup_id }}
                </span>
                <span v-else class="na">-</span>
              </td>
              <td>
                <div class="action-buttons">
                  <button @click="viewRestoreChain(backup.id)" class="btn-icon" title="Chaîne de restauration">
                    🔗
                  </button>
                  <button @click="verifyBackup(backup.id)" class="btn-icon" title="Vérifier intégrité">
                    ✓
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Actions -->
      <div class="actions-section">
        <button @click="verifyAllIntegrity" class="btn btn-primary">
          Vérifier Intégrité de Tous les Backups
        </button>
        <button @click="showChainJSON = !showChainJSON" class="btn btn-secondary">
          {{ showChainJSON ? 'Masquer' : 'Voir' }} chain.json
        </button>
      </div>

      <!-- Chain JSON -->
      <div v-if="showChainJSON" class="chain-json">
        <h3>chain.json</h3>
        <pre>{{ JSON.stringify(chain, null, 2) }}</pre>
      </div>
    </div>

    <!-- Modal for Results -->
    <div v-if="showModal" class="modal">
      <div class="modal-content">
        <h3>{{ modalTitle }}</h3>
        <pre class="modal-body">{{ JSON.stringify(modalData, null, 2) }}</pre>
        <button @click="showModal = false" class="btn btn-primary">Fermer</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({
  vmName: {
    type: String,
    required: true
  }
})

const API_BASE = 'http://localhost:8000/api'

// Data
const chain = ref(null)
const stats = ref({})
const loading = ref(false)
const error = ref(null)
const showChainJSON = ref(false)
const showModal = ref(false)
const modalTitle = ref('')
const modalData = ref(null)

// Computed
const backups = computed(() => {
  if (!chain.value || !chain.value.backups) return []
  // Trier par timestamp décroissant (plus récents en premier)
  return [...chain.value.backups].sort((a, b) =>
    new Date(b.timestamp) - new Date(a.timestamp)
  )
})

// Lifecycle
onMounted(() => {
  loadChain()
})

// Methods
async function loadChain() {
  loading.value = true
  error.value = null

  try {
    // Charger la chaîne
    const chainResponse = await axios.get(`${API_BASE}/backup-chains/${props.vmName}/chain/`)
    chain.value = chainResponse.data

    // Charger les statistiques
    const statsResponse = await axios.get(`${API_BASE}/backup-chains/${props.vmName}/stats/`)
    stats.value = statsResponse.data

  } catch (err) {
    console.error('Erreur chargement chaîne:', err)
    error.value = err.response?.data?.error || 'Erreur lors du chargement de la chaîne'
  } finally {
    loading.value = false
  }
}

function refreshChain() {
  loadChain()
}

async function previewRetention() {
  try {
    const response = await axios.get(`${API_BASE}/backup-chains/${props.vmName}/retention-preview/`)

    modalTitle.value = 'Prévisualisation Rétention'
    modalData.value = response.data
    showModal.value = true
  } catch (err) {
    alert('Erreur: ' + (err.response?.data?.error || err.message))
  }
}

async function applyRetention() {
  if (!confirm('Êtes-vous sûr de vouloir appliquer la politique de rétention ?')) {
    return
  }

  try {
    const response = await axios.post(`${API_BASE}/backup-chains/${props.vmName}/apply-retention/`, {
      dry_run: false
    })

    alert(`Rétention appliquée:\n${response.data.deleted_count} backup(s) supprimé(s)\n${response.data.kept_count} conservé(s)`)

    loadChain()
  } catch (err) {
    alert('Erreur: ' + (err.response?.data?.error || err.message))
  }
}

async function verifyAllIntegrity() {
  loading.value = true

  try {
    const response = await axios.post(`${API_BASE}/backup-chains/${props.vmName}/verify-integrity/`)

    modalTitle.value = 'Vérification d\'Intégrité'
    modalData.value = response.data
    showModal.value = true
  } catch (err) {
    alert('Erreur: ' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

async function viewRestoreChain(backupId) {
  try {
    const response = await axios.get(`${API_BASE}/backup-chains/${props.vmName}/restore-chain/${backupId}/`)

    modalTitle.value = `Chaîne de Restauration: ${backupId}`
    modalData.value = response.data
    showModal.value = true
  } catch (err) {
    alert('Erreur: ' + (err.response?.data?.error || err.message))
  }
}

function verifyBackup(backupId) {
  alert(`Vérification du backup ${backupId} (fonctionnalité à implémenter)`)
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('fr-FR')
}

function formatSize(bytes) {
  if (!bytes) return '-'
  const gb = bytes / (1024 ** 3)
  if (gb >= 1) return `${gb.toFixed(2)} GB`
  const mb = bytes / (1024 ** 2)
  return `${mb.toFixed(2)} MB`
}
</script>

<style scoped>
.backup-chain-view {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.chain-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.chain-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #3498db;
  color: white;
}

.btn-refresh:hover {
  background: #2980b9;
}

.icon {
  width: 20px;
  height: 20px;
}

.loading {
  text-align: center;
  padding: 60px;
  font-size: 18px;
  color: #7f8c8d;
}

.error-message {
  padding: 20px;
  background: #fee;
  color: #c33;
  border-radius: 4px;
  border-left: 4px solid #c33;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stat-label {
  font-size: 14px;
  color: #7f8c8d;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #2c3e50;
}

.stat-value.full {
  color: #3498db;
}

.stat-value.incremental {
  color: #27ae60;
}

.chain-info,
.retention-section,
.backups-section,
.actions-section {
  background: white;
  padding: 25px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #ecf0f1;
}

.info-row:last-child {
  border-bottom: none;
}

.label {
  font-weight: 600;
  color: #7f8c8d;
}

.value {
  color: #2c3e50;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.badge.success {
  background: #d4edda;
  color: #155724;
}

.badge.warning {
  background: #fff3cd;
  color: #856404;
}

.retention-section h3 {
  margin-bottom: 15px;
  color: #2c3e50;
}

.retention-info {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
  color: #7f8c8d;
}

.retention-actions {
  display: flex;
  gap: 15px;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-danger:hover {
  background: #c0392b;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover {
  background: #2980b9;
}

.backups-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.backups-table thead {
  background: #f8f9fa;
}

.backups-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #2c3e50;
  border-bottom: 2px solid #e0e0e0;
}

.backups-table td {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
}

.backup-row:hover {
  background: #f8f9fa;
}

.type-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.type-badge.full {
  background: #d4e6f1;
  color: #1f618d;
}

.type-badge.incremental {
  background: #d5f4e6;
  color: #0e6655;
}

.backup-id {
  font-family: monospace;
  font-size: 13px;
  color: #7f8c8d;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.completed {
  background: #d4edda;
  color: #155724;
}

.base-link {
  font-family: monospace;
  font-size: 12px;
  color: #3498db;
  cursor: pointer;
}

.na {
  color: #bdc3c7;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-icon {
  padding: 6px 10px;
  border: none;
  background: #ecf0f1;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.btn-icon:hover {
  background: #3498db;
  color: white;
}

.actions-section {
  display: flex;
  gap: 15px;
}

.chain-json {
  background: white;
  padding: 25px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.chain-json pre {
  background: #2c3e50;
  color: #ecf0f1;
  padding: 20px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
  font-family: monospace;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 8px;
  max-width: 800px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

.modal-content h3 {
  margin-bottom: 20px;
  color: #2c3e50;
}

.modal-body {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 20px;
  font-size: 13px;
  font-family: monospace;
  max-height: 400px;
}
</style>
