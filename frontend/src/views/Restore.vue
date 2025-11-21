<template>
  <div class="restore-container">
    <div class="page-header">
      <h1>⚙️ Restauration de Sauvegardes</h1>
      <p class="subtitle">Restaurez vos VMs, disques ou fichiers depuis les backups</p>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['tab', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab: Restauration VM -->
    <div v-if="activeTab === 'vm'" class="tab-content">
      <h2>Restaurer une VM Complète</h2>

      <div class="restore-form">
        <div class="form-group">
          <label>Serveur ESXi</label>
          <select v-model="selectedServer" @change="onServerChange" required>
            <option value="">Sélectionnez un serveur</option>
            <option v-for="server in servers" :key="server.id" :value="server.id">
              {{ server.hostname }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Nom de la VM</label>
          <input v-model="vmRestoreForm.vm_name" type="text" placeholder="WebServer" />
        </div>

        <div class="form-group">
          <label>ID de la Sauvegarde</label>
          <input v-model="vmRestoreForm.backup_id" type="text" placeholder="full_18-01-2025_14-00-00" />
          <small>Format: full_DD-MM-YYYY_HH-MM-SS ou incr_DD-MM-YYYY_HH-MM-SS</small>
        </div>

        <div class="form-group">
          <label>Datastore de Destination</label>
          <select v-model="vmRestoreForm.target_datastore" :disabled="!selectedServer">
            <option value="">{{ selectedServer ? 'Sélectionnez un datastore' : 'Sélectionnez d\'abord un serveur' }}</option>
            <option v-for="ds in datastores" :key="ds.name" :value="ds.name">
              {{ ds.name }} ({{ ds.free_space_gb }} GB libre)
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Nom de la VM Restaurée (optionnel)</label>
          <input v-model="vmRestoreForm.target_vm_name" type="text" placeholder="Restored_WebServer" />
          <small>Laissez vide pour utiliser le nom d'origine</small>
        </div>

        <div class="form-group">
          <label>Mode de Restauration</label>
          <select v-model="vmRestoreForm.restore_mode">
            <option value="new">Nouvelle VM</option>
            <option value="replace">Remplacer VM existante</option>
            <option value="test">VM de test</option>
          </select>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="vmRestoreForm.power_on" />
            Démarrer la VM après restauration
          </label>
        </div>

        <div class="form-actions">
          <button @click="validateVMRestore" class="btn btn-secondary">
            Valider
          </button>
          <button @click="restoreVM" class="btn btn-primary" :disabled="isRestoring">
            {{ isRestoring ? 'Restauration...' : 'Restaurer VM' }}
          </button>
        </div>
      </div>

      <!-- Validation Results -->
      <div v-if="validationResults.vm" class="validation-results">
        <h3>Résultats de Validation</h3>
        <div :class="['status', validationResults.vm.valid ? 'success' : 'error']">
          {{ validationResults.vm.valid ? '✓ Restauration possible' : '✗ Restauration impossible' }}
        </div>
        <ul v-if="validationResults.vm.errors && validationResults.vm.errors.length">
          <li v-for="(error, idx) in validationResults.vm.errors" :key="idx" class="error">
            {{ error }}
          </li>
        </ul>
      </div>
    </div>

    <!-- Tab: Restauration VMDK -->
    <div v-if="activeTab === 'vmdk'" class="tab-content">
      <h2>Restaurer un Disque VMDK</h2>

      <div class="restore-form">
        <div class="form-group">
          <label>Serveur ESXi</label>
          <select v-model="selectedServer" @change="onServerChange" required>
            <option value="">Sélectionnez un serveur</option>
            <option v-for="server in servers" :key="server.id" :value="server.id">
              {{ server.hostname }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Nom de la VM</label>
          <input v-model="vmdkRestoreForm.vm_name" type="text" placeholder="WebServer" />
        </div>

        <div class="form-group">
          <label>ID de la Sauvegarde</label>
          <input v-model="vmdkRestoreForm.backup_id" type="text" placeholder="full_18-01-2025_14-00-00" />
          <button @click="listVMDKs" class="btn btn-small">Lister les VMDK</button>
        </div>

        <div class="form-group">
          <label>Fichier VMDK</label>
          <select v-model="vmdkRestoreForm.vmdk_filename">
            <option value="">Sélectionnez un VMDK</option>
            <option v-for="vmdk in availableVMDKs" :key="vmdk.filename" :value="vmdk.filename">
              {{ vmdk.filename }} ({{ vmdk.size_gb }} GB)
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Datastore de Destination</label>
          <select v-model="vmdkRestoreForm.target_datastore" :disabled="!selectedServer">
            <option value="">{{ selectedServer ? 'Sélectionnez un datastore' : 'Sélectionnez d\'abord un serveur' }}</option>
            <option v-for="ds in datastores" :key="ds.name" :value="ds.name">
              {{ ds.name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Nom du VMDK Restauré (optionnel)</label>
          <input v-model="vmdkRestoreForm.target_name" type="text" placeholder="restored_disk.vmdk" />
        </div>

        <div class="form-group">
          <label>Attacher à une VM (optionnel)</label>
          <input v-model="vmdkRestoreForm.attach_to_vm" type="text" placeholder="WebServer" />
          <small>Laissez vide pour créer un disque orphelin</small>
        </div>

        <div class="form-actions">
          <button @click="validateVMDKRestore" class="btn btn-secondary">
            Valider
          </button>
          <button @click="restoreVMDK" class="btn btn-primary" :disabled="isRestoring">
            {{ isRestoring ? 'Restauration...' : 'Restaurer VMDK' }}
          </button>
        </div>
      </div>

      <!-- VMDK List -->
      <div v-if="availableVMDKs.length" class="vmdk-list">
        <h3>VMDK Disponibles</h3>
        <table>
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Taille</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="vmdk in availableVMDKs" :key="vmdk.filename">
              <td>{{ vmdk.filename }}</td>
              <td>{{ vmdk.size_gb }} GB</td>
              <td>
                <button @click="selectVMDK(vmdk)" class="btn btn-small">
                  Sélectionner
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab: Récupération de Fichiers -->
    <div v-if="activeTab === 'files'" class="tab-content">
      <h2>Récupérer des Fichiers</h2>

      <div class="restore-form">
        <div class="form-group">
          <label>Nom de la VM</label>
          <input v-model="fileRecoveryForm.vm_name" type="text" placeholder="WebServer" />
        </div>

        <div class="form-group">
          <label>ID de la Sauvegarde</label>
          <input v-model="fileRecoveryForm.backup_id" type="text" placeholder="full_18-01-2025_14-00-00" />
        </div>

        <div class="form-group">
          <label>Fichier VMDK</label>
          <input v-model="fileRecoveryForm.vmdk_filename" type="text" placeholder="VM_WebServer.vmdk" />
        </div>

        <div class="form-group">
          <label>Répertoire à Explorer</label>
          <input v-model="fileRecoveryForm.directory_path" type="text" placeholder="/" />
          <button @click="listFiles" class="btn btn-small">Explorer</button>
        </div>

        <div class="form-group">
          <label>Rechercher des Fichiers</label>
          <input v-model="fileRecoveryForm.search_pattern" type="text" placeholder="*.conf" />
          <button @click="searchFiles" class="btn btn-small">Rechercher</button>
        </div>

        <div class="form-group">
          <label>Dossier de Destination</label>
          <input v-model="fileRecoveryForm.destination_folder" type="text" placeholder="C:\Restored_Files" />
        </div>

        <div class="form-group">
          <label>Fichiers Sélectionnés</label>
          <div class="selected-files">
            <div v-for="(file, idx) in fileRecoveryForm.file_paths" :key="idx" class="file-item">
              <span>{{ file }}</span>
              <button @click="removeSelectedFile(idx)" class="btn-remove">×</button>
            </div>
          </div>
          <button @click="addFileManually" class="btn btn-small">Ajouter un chemin</button>
        </div>

        <div class="form-actions">
          <button @click="recoverFiles" class="btn btn-primary" :disabled="isRestoring || !fileRecoveryForm.file_paths.length">
            {{ isRestoring ? 'Récupération...' : 'Récupérer les Fichiers' }}
          </button>
        </div>
      </div>

      <!-- File Browser -->
      <div v-if="fileBrowser.files.length || fileBrowser.directories.length" class="file-browser">
        <h3>Explorateur de Fichiers: {{ fileBrowser.current_path }}</h3>

        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Nom</th>
              <th>Taille</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="dir in fileBrowser.directories" :key="dir.path" class="directory-row">
              <td>📁</td>
              <td>{{ dir.name }}</td>
              <td>-</td>
              <td>
                <button @click="navigateToDirectory(dir.path)" class="btn btn-small">
                  Ouvrir
                </button>
              </td>
            </tr>
            <tr v-for="file in fileBrowser.files" :key="file.path" class="file-row">
              <td>📄</td>
              <td>{{ file.name }}</td>
              <td>{{ file.size_mb }} MB</td>
              <td>
                <button @click="addFileToRecovery(file.path)" class="btn btn-small">
                  Sélectionner
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Search Results -->
      <div v-if="searchResults.length" class="search-results">
        <h3>Résultats de Recherche ({{ searchResults.length }})</h3>

        <table>
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Chemin</th>
              <th>Taille</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="result in searchResults" :key="result.path">
              <td>{{ result.filename }}</td>
              <td>{{ result.path }}</td>
              <td>{{ result.size_kb }} KB</td>
              <td>
                <button @click="addFileToRecovery(result.path)" class="btn btn-small">
                  Sélectionner
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Progress/Results Modal -->
    <div v-if="showResults" class="modal">
      <div class="modal-content">
        <h3>{{ resultsTitle }}</h3>

        <div v-if="restoreResults.success !== undefined" :class="['result-status', restoreResults.success ? 'success' : 'error']">
          {{ restoreResults.success ? '✓ Succès' : '✗ Échec' }}
        </div>

        <div v-if="restoreResults.message" class="result-message">
          {{ restoreResults.message }}
        </div>

        <div v-if="restoreResults.results">
          <h4>Détails:</h4>
          <pre>{{ JSON.stringify(restoreResults.results, null, 2) }}</pre>
        </div>

        <div v-if="restoreResults.errors && restoreResults.errors.length" class="errors">
          <h4>Erreurs:</h4>
          <ul>
            <li v-for="(error, idx) in restoreResults.errors" :key="idx">{{ error }}</li>
          </ul>
        </div>

        <button @click="showResults = false" class="btn btn-primary">Fermer</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { datastoresAPI, restoreAPI, esxiServersAPI } from '@/services/api'

// Tab Management
const activeTab = ref('vm')
const tabs = [
  { id: 'vm', label: 'Restauration VM' },
  { id: 'vmdk', label: 'Restauration VMDK' },
  { id: 'files', label: 'Récupération Fichiers' }
]

// Data
const servers = ref([])
const selectedServer = ref('')
const datastores = ref([])
const isRestoring = ref(false)
const showResults = ref(false)
const resultsTitle = ref('')
const restoreResults = ref({})
const validationResults = ref({
  vm: null,
  vmdk: null
})
const availableVMDKs = ref([])
const fileBrowser = ref({
  current_path: '/',
  files: [],
  directories: []
})
const searchResults = ref([])

// Forms
const vmRestoreForm = ref({
  vm_name: '',
  backup_id: '',
  target_datastore: '',
  target_vm_name: '',
  restore_mode: 'new',
  power_on: false
})

const vmdkRestoreForm = ref({
  vm_name: '',
  backup_id: '',
  vmdk_filename: '',
  target_datastore: '',
  target_name: '',
  attach_to_vm: ''
})

const fileRecoveryForm = ref({
  vm_name: '',
  backup_id: '',
  vmdk_filename: '',
  directory_path: '/',
  search_pattern: '',
  destination_folder: '',
  file_paths: []
})

// Lifecycle
onMounted(() => {
  loadServers()
})

// Methods
async function loadServers() {
  try {
    const response = await esxiServersAPI.getAll()
    servers.value = response.data
  } catch (error) {
    console.error('Erreur chargement serveurs:', error)
  }
}

async function onServerChange() {
  if (selectedServer.value) {
    await loadDatastores(selectedServer.value)
  } else {
    datastores.value = []
  }
}

async function loadDatastores(serverId) {
  try {
    const response = await datastoresAPI.getAll({ server: serverId })
    datastores.value = response.data
  } catch (error) {
    console.error('Erreur chargement datastores:', error)
  }
}

// VM Restore
async function validateVMRestore() {
  try {
    const response = await restoreAPI.validateVM({
      vm_name: vmRestoreForm.value.vm_name,
      backup_id: vmRestoreForm.value.backup_id
    })

    validationResults.value.vm = response.data
  } catch (error) {
    console.error('Erreur validation:', error)
    alert('Erreur lors de la validation: ' + (error.response?.data?.error || error.message))
  }
}

async function restoreVM() {
  if (!confirm('Êtes-vous sûr de vouloir restaurer cette VM ?')) {
    return
  }

  isRestoring.value = true

  try {
    const response = await restoreAPI.restoreVM(vmRestoreForm.value)

    restoreResults.value = response.data
    resultsTitle.value = 'Restauration VM'
    showResults.value = true
  } catch (error) {
    console.error('Erreur restauration:', error)
    restoreResults.value = {
      success: false,
      message: 'Échec de la restauration',
      errors: [error.response?.data?.error || error.message]
    }
    resultsTitle.value = 'Erreur Restauration VM'
    showResults.value = true
  } finally {
    isRestoring.value = false
  }
}

// VMDK Restore
async function listVMDKs() {
  try {
    const response = await restoreAPI.listVMDKs(
      vmdkRestoreForm.value.backup_id,
      vmdkRestoreForm.value.vm_name
    )

    availableVMDKs.value = response.data.vmdks
  } catch (error) {
    console.error('Erreur listage VMDK:', error)
    alert('Erreur: ' + (error.response?.data?.error || error.message))
  }
}

function selectVMDK(vmdk) {
  vmdkRestoreForm.value.vmdk_filename = vmdk.filename
}

async function validateVMDKRestore() {
  try {
    const response = await restoreAPI.validateVMDK({
      vm_name: vmdkRestoreForm.value.vm_name,
      backup_id: vmdkRestoreForm.value.backup_id,
      vmdk_filename: vmdkRestoreForm.value.vmdk_filename
    })

    validationResults.value.vmdk = response.data
    alert(response.data.valid ? 'Restauration possible ✓' : 'Restauration impossible ✗')
  } catch (error) {
    console.error('Erreur validation:', error)
    alert('Erreur: ' + (error.response?.data?.error || error.message))
  }
}

async function restoreVMDK() {
  if (!confirm('Restaurer ce VMDK ?')) {
    return
  }

  isRestoring.value = true

  try {
    const response = await restoreAPI.restoreVMDK(vmdkRestoreForm.value)

    restoreResults.value = response.data
    resultsTitle.value = 'Restauration VMDK'
    showResults.value = true
  } catch (error) {
    console.error('Erreur:', error)
    restoreResults.value = {
      success: false,
      errors: [error.response?.data?.error || error.message]
    }
    resultsTitle.value = 'Erreur Restauration VMDK'
    showResults.value = true
  } finally {
    isRestoring.value = false
  }
}

// File Recovery
async function listFiles() {
  try {
    const response = await restoreAPI.listFiles({
      vm_name: fileRecoveryForm.value.vm_name,
      backup_id: fileRecoveryForm.value.backup_id,
      vmdk_filename: fileRecoveryForm.value.vmdk_filename,
      directory_path: fileRecoveryForm.value.directory_path
    })

    fileBrowser.value = response.data
  } catch (error) {
    console.error('Erreur:', error)
    alert('Erreur: ' + (error.response?.data?.error || error.message))
  }
}

async function searchFiles() {
  try {
    const response = await restoreAPI.searchFiles({
      vm_name: fileRecoveryForm.value.vm_name,
      backup_id: fileRecoveryForm.value.backup_id,
      vmdk_filename: fileRecoveryForm.value.vmdk_filename,
      search_pattern: fileRecoveryForm.value.search_pattern
    })

    searchResults.value = response.data.matches
  } catch (error) {
    console.error('Erreur:', error)
    alert('Erreur: ' + (error.response?.data?.error || error.message))
  }
}

function navigateToDirectory(path) {
  fileRecoveryForm.value.directory_path = path
  listFiles()
}

function addFileToRecovery(path) {
  if (!fileRecoveryForm.value.file_paths.includes(path)) {
    fileRecoveryForm.value.file_paths.push(path)
  }
}

function removeSelectedFile(index) {
  fileRecoveryForm.value.file_paths.splice(index, 1)
}

function addFileManually() {
  const path = prompt('Entrez le chemin du fichier:')
  if (path) {
    addFileToRecovery(path)
  }
}

async function recoverFiles() {
  if (!confirm(`Récupérer ${fileRecoveryForm.value.file_paths.length} fichier(s) ?`)) {
    return
  }

  isRestoring.value = true

  try {
    const response = await restoreAPI.recoverFiles(fileRecoveryForm.value)

    restoreResults.value = response.data
    resultsTitle.value = 'Récupération de Fichiers'
    showResults.value = true
  } catch (error) {
    console.error('Erreur:', error)
    restoreResults.value = {
      success: false,
      errors: [error.response?.data?.error || error.message]
    }
    resultsTitle.value = 'Erreur Récupération'
    showResults.value = true
  } finally {
    isRestoring.value = false
  }
}
</script>

<style scoped>
.restore-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 32px;
  margin-bottom: 10px;
  color: #2c3e50;
}

.subtitle {
  color: #7f8c8d;
  font-size: 16px;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
  border-bottom: 2px solid #e0e0e0;
}

.tab {
  padding: 12px 24px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-size: 16px;
  color: #7f8c8d;
  transition: all 0.3s;
}

.tab:hover {
  color: #2c3e50;
  background: #f8f9fa;
}

.tab.active {
  color: #3498db;
  border-bottom-color: #3498db;
  font-weight: 600;
}

.tab-content {
  background: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.restore-form {
  max-width: 800px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group small {
  display: block;
  margin-top: 5px;
  color: #7f8c8d;
  font-size: 13px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input {
  width: auto;
}

.form-actions {
  display: flex;
  gap: 15px;
  margin-top: 30px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-primary:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.btn-small {
  padding: 6px 12px;
  font-size: 14px;
  margin-left: 10px;
}

.validation-results {
  margin-top: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.status {
  padding: 12px;
  border-radius: 4px;
  font-weight: 600;
  margin-bottom: 15px;
}

.status.success {
  background: #d4edda;
  color: #155724;
}

.status.error {
  background: #f8d7da;
  color: #721c24;
}

.vmdk-list,
.file-browser,
.search-results {
  margin-top: 30px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

thead {
  background: #f8f9fa;
}

th,
td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

th {
  font-weight: 600;
  color: #2c3e50;
}

.directory-row {
  background: #f0f8ff;
}

.file-row:hover,
.directory-row:hover {
  background: #f8f9fa;
}

.selected-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
}

.btn-remove {
  background: #e74c3c;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.btn-remove:hover {
  background: #c0392b;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
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

.result-status {
  padding: 15px;
  border-radius: 4px;
  font-size: 18px;
  font-weight: 600;
  margin: 20px 0;
}

.result-message {
  font-size: 16px;
  margin: 15px 0;
  color: #2c3e50;
}

pre {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
}

.errors {
  margin-top: 20px;
}

.errors ul {
  list-style: none;
  padding: 0;
}

.errors li {
  padding: 10px;
  background: #f8d7da;
  color: #721c24;
  margin-bottom: 8px;
  border-radius: 4px;
}
</style>
