<template>
  <Modal :show="show" :title="isEdit ? 'Modifier la planification' : 'Nouvelle planification'" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="space-y-6">
      <!-- Machine virtuelle -->
      <div class="group">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
          Machine virtuelle
        </label>
        <div class="relative">
          <select v-model="form.virtual_machine" required class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer">
            <option value="">Sélectionner une VM à sauvegarder...</option>
            <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">
              {{ vm.name }} ({{ vm.guest_os }})
            </option>
          </select>
          <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      <!-- Fréquence -->
      <div class="group">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Fréquence de sauvegarde
        </label>
        <div class="relative">
          <select v-model="form.frequency" required class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer">
            <option value="daily">📅 Quotidienne (tous les jours)</option>
            <option value="weekly">📆 Hebdomadaire (une fois par semaine)</option>
            <option value="monthly">🗓️ Mensuelle (une fois par mois)</option>
          </select>
          <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      <!-- Heure d'exécution -->
      <div class="group">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Heure d'exécution
        </label>
        <div class="grid grid-cols-2 gap-4">
          <div class="relative">
            <select v-model.number="form.time_hour" required class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer">
              <option v-for="h in 24" :key="h-1" :value="h-1">{{ String(h-1).padStart(2, '0') }}h</option>
            </select>
            <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
          <div class="relative">
            <select v-model.number="form.time_minute" required class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer">
              <option v-for="m in [0, 15, 30, 45]" :key="m" :value="m">{{ String(m).padStart(2, '0') }} min</option>
            </select>
            <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        <p class="mt-2 text-xs text-gray-600">
          🕐 Sauvegarde à {{ String(form.time_hour).padStart(2, '0') }}:{{ String(form.time_minute).padStart(2, '0') }}
        </p>
      </div>

      <!-- Jour de la semaine (pour weekly) -->
      <div v-if="form.frequency === 'weekly'" class="group">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Jour de la semaine
        </label>
        <div class="relative">
          <select v-model.number="form.day_of_week" required class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer">
            <option :value="0">Lundi</option>
            <option :value="1">Mardi</option>
            <option :value="2">Mercredi</option>
            <option :value="3">Jeudi</option>
            <option :value="4">Vendredi</option>
            <option :value="5">Samedi</option>
            <option :value="6">Dimanche</option>
          </select>
          <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      <!-- Jour du mois (pour monthly) -->
      <div v-if="form.frequency === 'monthly'" class="group">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <svg class="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Jour du mois
        </label>
        <div class="relative">
          <select v-model.number="form.day_of_month" required class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-4 focus:ring-orange-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer">
            <option v-for="d in 31" :key="d" :value="d">Le {{ d }}</option>
          </select>
          <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
        <p class="mt-2 text-xs text-gray-600">
          💡 Si le jour n'existe pas (ex: 31 février), le dernier jour du mois sera utilisé
        </p>
      </div>

      <!-- Répertoire de sauvegarde -->
      <div class="group">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
          <svg class="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          Répertoire de sauvegarde
        </label>
        <div class="relative">
          <input
            v-model="form.backup_location"
            type="text"
            placeholder="/mnt/backups ou /var/backups/vms"
            class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-teal-500 focus:ring-4 focus:ring-teal-500/20 transition-all outline-none text-gray-900 bg-white"
          >
          <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
        </div>
        <p class="mt-2 text-xs text-gray-600">
          📁 Laissez vide pour utiliser le répertoire par défaut
        </p>
      </div>

      <!-- Aperçu de la planification -->
      <div v-if="schedulePreview" class="p-4 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl shadow-sm">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-white rounded-lg shadow-sm">
            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p class="text-xs text-green-700 font-medium mb-1">Planification configurée</p>
            <p class="text-sm text-green-900 font-semibold">✓ {{ schedulePreview }}</p>
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
  interval_hours: null,
  backup_location: ''
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
    form.backup_location = newSchedule.backup_location || ''
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
  form.backup_location = ''
}
</script>
