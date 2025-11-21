<template>
  <Modal :show="show" title="Planifier des snapshots automatiques" @close="$emit('close')">
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

      <div>
        <label class="label">Fréquence</label>
        <select v-model="form.frequency" required class="input-field">
          <option value="hourly">Toutes les heures</option>
          <option value="daily">Quotidienne</option>
          <option value="weekly">Hebdomadaire</option>
          <option value="monthly">Mensuelle</option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          À quelle fréquence créer des snapshots automatiquement
        </p>
      </div>

      <!-- Heure d'exécution (pas pour hourly) -->
      <div v-if="form.frequency !== 'hourly'" class="grid grid-cols-2 gap-4">
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

      <!-- Minute seulement pour hourly -->
      <div v-if="form.frequency === 'hourly'">
        <label class="label">Minute</label>
        <select v-model.number="form.time_minute" required class="input-field">
          <option v-for="m in [0, 15, 30, 45]" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
        </select>
        <p class="mt-1 text-sm text-gray-500">
          À quelle minute de chaque heure exécuter le snapshot
        </p>
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

      <div>
        <label class="label">Nombre de snapshots à conserver</label>
        <input
          v-model.number="form.retention_count"
          type="number"
          min="1"
          max="100"
          required
          class="input-field"
        >
        <p class="mt-1 text-sm text-gray-500">
          Les snapshots les plus anciens seront automatiquement supprimés
        </p>
      </div>

      <div class="flex items-center">
        <input
          v-model="form.include_memory"
          type="checkbox"
          id="include_memory"
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        >
        <label for="include_memory" class="ml-2 block text-sm text-gray-900">
          Inclure la mémoire RAM dans le snapshot
        </label>
      </div>
      <p class="text-sm text-gray-500 ml-6">
        ⚠️ Les snapshots avec mémoire sont plus lents mais permettent de restaurer l'état exact de la VM
      </p>

      <div class="flex items-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <svg class="w-5 h-5 text-blue-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
        </svg>
        <p class="text-sm text-blue-800">
          Les snapshots permettent de restaurer rapidement une VM à un état antérieur sans sauvegarde complète.
        </p>
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
        {{ loading ? 'Création...' : 'Créer la planification' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useEsxiStore } from '@/stores/esxi'
import Modal from '@/components/common/Modal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

const esxiStore = useEsxiStore()

const loading = ref(false)
const error = ref(null)

const form = reactive({
  virtual_machine: '',
  frequency: 'daily',
  time_hour: 2,
  time_minute: 0,
  day_of_week: 0,
  day_of_month: 1,
  retention_count: 7,
  include_memory: false,
  is_active: true
})

const virtualMachines = computed(() => esxiStore.virtualMachines)

const schedulePreview = computed(() => {
  const timeStr = `${String(form.time_hour).padStart(2, '0')}:${String(form.time_minute).padStart(2, '0')}`
  const days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

  if (form.frequency === 'hourly') {
    return `Toutes les heures à la minute ${String(form.time_minute).padStart(2, '0')}`
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

onMounted(() => {
  if (virtualMachines.value.length === 0) {
    esxiStore.fetchVirtualMachines()
  }
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
  form.retention_count = 7
  form.include_memory = false
  form.is_active = true
}
</script>
