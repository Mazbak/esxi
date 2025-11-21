<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Planifications</h1>
        <p class="mt-1 text-sm text-gray-500">Configurez des sauvegardes automatiques</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvelle planification
      </button>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button
          @click="activeTab = 'overview'"
          :class="activeTab === 'overview' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
        >
          Vue d'ensemble
        </button>
        <button
          @click="activeTab = 'schedules'"
          :class="activeTab === 'schedules' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
        >
          Planifications ({{ schedules.length }})
        </button>
      </nav>
    </div>

    <!-- Loading State -->
    <Loading v-if="loading && schedules.length === 0" text="Chargement des planifications..." />

    <!-- Dashboard Tab -->
    <SchedulingDashboard v-else-if="activeTab === 'overview'" />

    <!-- Schedules List -->
    <div v-else-if="schedules.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div
        v-for="schedule in schedules"
        :key="schedule.id"
        class="card hover:shadow-lg transition-all"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center space-x-3 flex-1">
            <div :class="schedule.is_active ? 'bg-green-500' : 'bg-gray-400'" class="p-3 rounded-lg">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{{ getVMName(schedule.virtual_machine) }}</h3>
              <p class="text-sm text-gray-500">{{ schedule.schedule_description || getFrequencyLabel(schedule.frequency) }}</p>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <!-- Toggle Active -->
            <button
              @click="toggleActive(schedule)"
              :class="schedule.is_active ? 'bg-green-500' : 'bg-gray-300'"
              class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
            >
              <span
                :class="schedule.is_active ? 'translate-x-6' : 'translate-x-1'"
                class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
              />
            </button>
            <span :class="schedule.is_active ? 'badge-success' : 'badge-gray'" class="badge">
              {{ schedule.is_active ? 'Actif' : 'Inactif' }}
            </span>
          </div>
        </div>

        <!-- Info -->
        <div class="space-y-2 mb-4">
          <div class="flex items-center text-sm">
            <svg class="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-600">Créé:</span>
            <span class="ml-2 text-gray-900">{{ formatDate(schedule.created_at) }}</span>
          </div>
          <div class="flex items-center text-sm">
            <svg class="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span class="text-gray-600">Fréquence:</span>
            <span class="ml-2 text-gray-900">{{ getFrequencyLabel(schedule.frequency) }}</span>
          </div>
          <div class="flex items-center text-sm">
            <svg class="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <span class="text-gray-600">Stratégie:</span>
            <span class="ml-2 text-gray-900">{{ getStrategyLabel(schedule.backup_strategy) }}</span>
          </div>
          <div v-if="schedule.last_run_at" class="flex items-center text-sm">
            <svg class="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-gray-600">Dernière exécution:</span>
            <span class="ml-2 text-gray-900">{{ formatDate(schedule.last_run_at) }}</span>
          </div>
        </div>

        <!-- Schedule Description -->
        <div class="p-3 bg-blue-50 rounded-lg mb-4">
          <p class="text-sm text-blue-800">
            {{ schedule.schedule_description || getFrequencyDescription(schedule.frequency) }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center space-x-2 pt-4 border-t border-gray-200">
          <button
            @click="editSchedule(schedule)"
            class="flex-1 btn-primary text-sm"
          >
            <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Modifier
          </button>
          <button
            @click="confirmDelete(schedule)"
            class="flex-1 btn-danger text-sm"
          >
            <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Supprimer
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="activeTab === 'schedules'" class="text-center py-12">
      <svg class="w-24 h-24 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Aucune planification</h3>
      <p class="text-gray-500 mb-4">Créez votre première planification automatique</p>
      <button @click="showCreateModal = true" class="btn-primary">
        Nouvelle planification
      </button>
    </div>

    <!-- Create/Edit Modal -->
    <ScheduleForm
      :show="showCreateModal || showEditModal"
      :schedule="selectedSchedule"
      :is-edit="showEditModal"
      @close="closeModal"
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useBackupsStore } from '@/stores/backups'
import { useEsxiStore } from '@/stores/esxi'
import { useToastStore } from '@/stores/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import Loading from '@/components/common/Loading.vue'
import ScheduleForm from '@/components/schedules/ScheduleForm.vue'
import SchedulingDashboard from '@/components/schedules/SchedulingDashboard.vue'

const backupsStore = useBackupsStore()
const esxiStore = useEsxiStore()
const toast = useToastStore()

const activeTab = ref('overview')
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedSchedule = ref(null)

const schedules = computed(() => backupsStore.schedules)
const loading = computed(() => backupsStore.loading)
const virtualMachines = computed(() => esxiStore.virtualMachines)

onMounted(async () => {
  await Promise.all([
    backupsStore.fetchSchedules(),
    esxiStore.fetchVirtualMachines()
  ])
})

function getVMName(vmId) {
  const vm = virtualMachines.value.find(v => v.id === vmId)
  return vm ? vm.name : `VM #${vmId}`
}

function formatDate(date) {
  if (!date) return '-'
  return format(new Date(date), 'dd MMM yyyy HH:mm', { locale: fr })
}

function getFrequencyLabel(frequency) {
  const labels = {
    daily: 'Quotidienne',
    weekly: 'Hebdomadaire',
    monthly: 'Mensuelle',
    custom: 'Personnalisée'
  }
  return labels[frequency] || frequency
}

function getFrequencyDescription(frequency) {
  const descriptions = {
    daily: 'La sauvegarde s\'exécutera tous les jours à minuit',
    weekly: 'La sauvegarde s\'exécutera tous les lundis à minuit',
    monthly: 'La sauvegarde s\'exécutera le 1er de chaque mois à minuit',
    custom: 'La sauvegarde s\'exécutera selon l\'intervalle défini'
  }
  return descriptions[frequency] || ''
}

function getStrategyLabel(strategy) {
  const labels = {
    'full_weekly': 'Full hebdomadaire + Incremental',
    'full_only': 'Full uniquement',
    'incremental_only': 'Incremental uniquement',
    'smart': 'Smart (Auto)'
  }
  return labels[strategy] || 'Full hebdomadaire + Incremental'
}

async function toggleActive(schedule) {
  try {
    await backupsStore.toggleScheduleActive(schedule.id)
    if (schedule.is_active) {
      toast.info('Planification désactivée')
    } else {
      toast.success('Planification activée')
    }
  } catch (err) {
    toast.error(`Erreur: ${err.message}`)
  }
}

function editSchedule(schedule) {
  selectedSchedule.value = schedule
  showEditModal.value = true
}

function confirmDelete(schedule) {
  if (confirm(`Êtes-vous sûr de vouloir supprimer cette planification?`)) {
    deleteSchedule(schedule)
  }
}

async function deleteSchedule(schedule) {
  try {
    await backupsStore.deleteSchedule(schedule.id)
    toast.success('Planification supprimée avec succès')
  } catch (err) {
    toast.error(`Erreur lors de la suppression: ${err.message}`)
  }
}

async function handleSubmit(formData) {
  try {
    if (showEditModal.value && selectedSchedule.value) {
      await backupsStore.updateSchedule(selectedSchedule.value.id, formData)
      toast.success('Planification modifiée avec succès')
    } else {
      const result = await backupsStore.createSchedule(formData)
      const description = result.schedule_description || 'Planification créée avec succès'
      toast.success(description)
    }
    closeModal()
  } catch (err) {
    toast.error(`Erreur: ${err.message}`)
    throw err
  }
}

function closeModal() {
  showCreateModal.value = false
  showEditModal.value = false
  selectedSchedule.value = null
}
</script>
