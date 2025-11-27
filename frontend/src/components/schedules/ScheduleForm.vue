<template>
  <Modal :show="show" :title="isEdit ? 'Modifier la planification' : 'Nouvelle planification'" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label class="label">Machine virtuelle</label>
        <select v-model="form.virtual_machine" required class="input-field">
          <option value="">Sélectionnez une VM</option>
          <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">
            {{ vm.name }} ({{ vm.guest_os }})
          </option>
        </select>
      </div>

      <!-- Stratégie de Backup -->
      <div>
        <label class="label">Stratégie de backup</label>
        <select v-model="form.backup_strategy" required class="input-field">
          <option value="full_weekly">Full hebdomadaire + Incremental quotidien</option>
          <option value="full_only">Full uniquement</option>
          <option value="incremental_only">Incremental uniquement</option>
          <option value="smart">Smart (Décision automatique)</option>
        </select>
        <p class="mt-1 text-xs text-gray-500">
          {{ getStrategyDescription(form.backup_strategy) }}
        </p>
      </div>

      <!-- Mode de Backup (OVF vs VMDK) -->
      <div class="border-2 rounded-lg p-4" :class="form.backup_mode === 'ovf' ? 'border-green-500 bg-green-50' : 'border-gray-300'">
        <label class="label flex items-center">
          <svg class="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Mode de backup (Recommandé: OVF)
        </label>
        <select v-model="form.backup_mode" required class="input-field mt-2">
          <option value="ovf">✅ OVF Export (Optimisé thin-provisioning - Recommandé)</option>
          <option value="vmdk">⚠️ VMDK Direct (Copie disque complet)</option>
        </select>
        <div v-if="form.backup_mode === 'ovf'" class="mt-2 p-3 bg-green-100 rounded-lg">
          <p class="text-sm text-green-800 font-medium">✅ Mode OVF (Recommandé)</p>
          <ul class="mt-1 text-xs text-green-700 list-disc list-inside space-y-1">
            <li>Télécharge uniquement les données réelles (~34.6%)</li>
            <li>Gère correctement le thin provisioning</li>
            <li>Format standard VMware (100% restaurable)</li>
            <li>Exemple: VM 500GB alloué, 50GB utilisés → backup 17GB</li>
            <li>Beaucoup plus rapide et économe en espace disque</li>
          </ul>
        </div>
        <div v-else class="mt-2 p-3 bg-yellow-100 rounded-lg">
          <p class="text-sm text-yellow-800 font-medium">⚠️ Mode VMDK (Legacy)</p>
          <ul class="mt-1 text-xs text-yellow-700 list-disc list-inside space-y-1">
            <li>Télécharge le fichier VMDK complet (100%)</li>
            <li>Ne gère PAS le thin provisioning</li>
            <li>Exemple: VM 500GB alloué, 50GB utilisés → backup 500GB</li>
            <li>Beaucoup plus lent et consomme énormément d'espace</li>
            <li>À utiliser uniquement si besoin spécifique</li>
          </ul>
        </div>
      </div>

      <!-- Intervalle Full Backup (pour full_weekly) -->
      <div v-if="form.backup_strategy === 'full_weekly'">
        <label class="label">Intervalle Full Backup (jours)</label>
        <input
          v-model.number="form.full_backup_interval_days"
          type="number"
          min="1"
          max="365"
          required
          class="input-field"
          placeholder="7"
        >
        <p class="mt-1 text-xs text-gray-500">
          Un Full backup sera créé tous les {{ form.full_backup_interval_days }} jours, avec des Incrementals entre-temps
        </p>
      </div>

      <!-- Remote Storage -->
      <div>
        <label class="label">Stockage distant</label>
        <select v-model.number="form.remote_storage" class="input-field">
          <option :value="null">Stockage par défaut</option>
          <option v-for="storage in remoteStorages" :key="storage.id" :value="storage.id">
            {{ storage.name }} ({{ storage.protocol.toUpperCase() }})
          </option>
        </select>
      </div>

      <!-- Backup Configuration -->
      <div>
        <label class="label">Configuration de backup</label>
        <select v-model.number="form.backup_configuration" class="input-field">
          <option :value="null">Configuration par défaut</option>
          <option v-for="config in backupConfigs" :key="config.id" :value="config.id">
            {{ config.name }}
          </option>
        </select>
      </div>

      <div>
        <label class="label">Fréquence</label>
        <select v-model="form.frequency" required class="input-field">
          <option value="daily">Quotidienne</option>
          <option value="weekly">Hebdomadaire</option>
          <option value="monthly">Mensuelle</option>
          <option value="custom">Personnalisée (intervalle en heures)</option>
        </select>
      </div>

      <!-- Intervalle personnalisé en heures -->
      <div v-if="form.frequency === 'custom'">
        <label class="label">Intervalle (heures)</label>
        <input
          v-model.number="form.interval_hours"
          type="number"
          min="1"
          max="8760"
          required
          class="input-field"
          placeholder="24"
        >
        <p class="mt-1 text-xs text-gray-500">
          La sauvegarde sera exécutée toutes les {{ form.interval_hours }} heures
        </p>
      </div>

      <!-- Heure d'exécution -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">Heure</label>
          <select v-model.number="form.time_hour" required class="input-field">
            <option v-for="h in 24" :key="h-1" :value="h-1">{{ String(h-1).padStart(2, '0') }}h</option>
          </select>
        </div>
        <div>
          <label class="label">Minute</label>
          <select v-model.number="form.time_minute" required class="input-field">
            <option v-for="m in [0, 15, 30, 45]" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
          </select>
        </div>
      </div>

      <!-- Jour de la semaine (pour weekly) -->
      <div v-if="form.frequency === 'weekly'">
        <label class="label">Jour de la semaine</label>
        <select v-model.number="form.day_of_week" required class="input-field">
          <option :value="0">Lundi</option>
          <option :value="1">Mardi</option>
          <option :value="2">Mercredi</option>
          <option :value="3">Jeudi</option>
          <option :value="4">Vendredi</option>
          <option :value="5">Samedi</option>
          <option :value="6">Dimanche</option>
        </select>
      </div>

      <!-- Jour du mois (pour monthly) -->
      <div v-if="form.frequency === 'monthly'">
        <label class="label">Jour du mois</label>
        <select v-model.number="form.day_of_month" required class="input-field">
          <option v-for="d in 31" :key="d" :value="d">{{ d }}</option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          Si le jour n'existe pas dans un mois (ex: 31 février), le dernier jour du mois sera utilisé
        </p>
      </div>

      <div class="flex items-center">
        <input
          v-model="form.is_active"
          type="checkbox"
          id="is_active"
          class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
        >
        <label for="is_active" class="ml-2 block text-sm text-gray-700">
          Activer la planification
        </label>
      </div>

      <!-- Aperçu de la planification -->
      <div v-if="schedulePreview" class="p-4 bg-green-50 border border-green-200 rounded-lg">
        <div class="flex">
          <svg class="w-5 h-5 text-green-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <div class="text-sm text-green-800">
            <p class="font-medium">Planification: {{ schedulePreview }}</p>
          </div>
        </div>
      </div>

      <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div class="flex">
          <svg class="w-5 h-5 text-blue-600 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
          <div class="text-sm text-blue-800">
            <p class="font-medium mb-1">Information</p>
            <ul class="list-disc list-inside space-y-1">
              <li>Les sauvegardes automatiques seront exécutées selon la fréquence choisie</li>
              <li>Vous pouvez activer ou désactiver la planification à tout moment</li>
              <li>Les paramètres de sauvegarde (emplacement, type) seront configurés automatiquement</li>
            </ul>
          </div>
        </div>
      </div>

      <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>
    </form>

    <template #footer>
      <button type="button" @click="$emit('close')" class="btn-secondary">
        Annuler
      </button>
      <button
        type="button"
        @click="handleSubmit"
        :disabled="loading"
        class="btn-primary"
        :class="{ 'opacity-50 cursor-not-allowed': loading }"
      >
        {{ loading ? 'Enregistrement...' : (isEdit ? 'Mettre à jour' : 'Créer') }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import { useBackupsStore } from '@/stores/backups'
import Modal from '@/components/common/Modal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  schedule: {
    type: Object,
    default: null
  },
  isEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

const esxiStore = useEsxiStore()
const backupsStore = useBackupsStore()

const loading = ref(false)
const error = ref(null)

const form = reactive({
  virtual_machine: '',
  frequency: 'daily',
  time_hour: 2,
  time_minute: 0,
  day_of_week: 0,
  day_of_month: 1,
  is_active: true,
  // Nouveaux champs Phase 5
  backup_strategy: 'full_weekly',
  backup_mode: 'ovf',  // OVF par défaut (recommandé pour thin provisioning)
  full_backup_interval_days: 7,
  backup_configuration: null,
  remote_storage: null,
  interval_hours: null
})

const virtualMachines = computed(() => esxiStore.virtualMachines)
const remoteStorages = computed(() => backupsStore.remoteStorages)
const backupConfigs = computed(() => backupsStore.backupConfigurations)

const schedulePreview = computed(() => {
  const timeStr = `${String(form.time_hour).padStart(2, '0')}:${String(form.time_minute).padStart(2, '0')}`
  const days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

  if (form.frequency === 'custom' && form.interval_hours) {
    return `Toutes les ${form.interval_hours} heures`
  } else if (form.frequency === 'daily') {
    return `Tous les jours à ${timeStr}`
  } else if (form.frequency === 'weekly') {
    const dayName = days[form.day_of_week] || 'Lundi'
    return `Chaque ${dayName} à ${timeStr}`
  } else if (form.frequency === 'monthly') {
    return `Le ${form.day_of_month} de chaque mois à ${timeStr}`
  }
  return ''
})

function getStrategyDescription(strategy) {
  const descriptions = {
    'full_weekly': 'Full backup périodique avec incrementals entre-temps (recommandé)',
    'full_only': 'Toujours créer des Full backups (plus sûr mais plus lent)',
    'incremental_only': 'Toujours créer des Incrementals (nécessite une base Full existante)',
    'smart': 'Décision automatique basée sur l\'âge, la taille et le nombre d\'incrementals'
  }
  return descriptions[strategy] || ''
}

watch(() => props.schedule, (newSchedule) => {
  if (newSchedule) {
    form.virtual_machine = newSchedule.virtual_machine || ''
    form.frequency = newSchedule.frequency || 'daily'
    form.time_hour = newSchedule.time_hour !== undefined ? newSchedule.time_hour : 2
    form.time_minute = newSchedule.time_minute !== undefined ? newSchedule.time_minute : 0
    form.day_of_week = newSchedule.day_of_week !== undefined ? newSchedule.day_of_week : 0
    form.day_of_month = newSchedule.day_of_month !== undefined ? newSchedule.day_of_month : 1
    form.is_active = newSchedule.is_active !== undefined ? newSchedule.is_active : true
    // Nouveaux champs Phase 5
    form.backup_strategy = newSchedule.backup_strategy || 'full_weekly'
    form.backup_mode = newSchedule.backup_mode || 'ovf'
    form.full_backup_interval_days = newSchedule.full_backup_interval_days || 7
    form.backup_configuration = newSchedule.backup_configuration || null
    form.remote_storage = newSchedule.remote_storage || null
    form.interval_hours = newSchedule.interval_hours || null
  }
}, { immediate: true })

onMounted(async () => {
  // Charger les données nécessaires
  const promises = []

  if (virtualMachines.value.length === 0) {
    promises.push(esxiStore.fetchVirtualMachines())
  }

  if (remoteStorages.value.length === 0) {
    promises.push(backupsStore.fetchRemoteStorages())
  }

  if (backupConfigs.value.length === 0) {
    promises.push(backupsStore.fetchBackupConfigurations())
  }

  await Promise.all(promises)
})

async function handleSubmit() {
  error.value = null
  loading.value = true

  try {
    await emit('submit', { ...form })
    resetForm()
  } catch (err) {
    error.value = err.message || 'Une erreur est survenue'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.virtual_machine = ''
  form.frequency = 'daily'
  form.time_hour = 2
  form.time_minute = 0
  form.day_of_week = 0
  form.day_of_month = 1
  form.is_active = true
  // Nouveaux champs Phase 5
  form.backup_strategy = 'full_weekly'
  form.backup_mode = 'ovf'  // OVF par défaut
  form.full_backup_interval_days = 7
  form.backup_configuration = null
  form.remote_storage = null
  form.interval_hours = null
}
</script>
