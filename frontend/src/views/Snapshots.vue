<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Snapshots</h1>
        <p class="mt-1 text-sm text-gray-500">Gérez les snapshots et planifications automatiques</p>
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
          @click="activeTab = 'schedules'"
          :class="[
            activeTab === 'schedules'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
          ]"
        >
          Planifications ({{ schedules.length }})
        </button>
        <button
          @click="activeTab = 'snapshots'"
          :class="[
            activeTab === 'snapshots'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
          ]"
        >
          Snapshots ({{ snapshots.length }})
        </button>
      </nav>
    </div>

    <!-- Loading State -->
    <Loading v-if="loading && schedules.length === 0 && snapshots.length === 0" text="Chargement..." />

    <!-- Schedules Tab -->
    <div v-else-if="activeTab === 'schedules'">
      <div v-if="schedules.length > 0" class="space-y-4">
        <div
          v-for="schedule in schedules"
          :key="schedule.id"
          class="card hover:shadow-lg transition-shadow"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-start space-x-4 flex-1">
              <div :class="schedule.is_active ? 'bg-green-500' : 'bg-gray-400'" class="p-3 rounded-lg">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <h3 class="text-lg font-semibold text-gray-900">{{ schedule.vm_name }}</h3>
                  <span :class="schedule.is_active ? 'badge-success' : 'badge-gray'" class="badge">
                    {{ schedule.is_active ? 'Actif' : 'Inactif' }}
                  </span>
                  <span class="badge badge-info">{{ getFrequencyLabel(schedule.frequency) }}</span>
                </div>
                <div class="mt-2 space-y-1 text-sm text-gray-600">
                  <p>
                    <span class="font-medium">Rétention:</span> {{ schedule.retention_count }} snapshots
                  </p>
                  <p>
                    <span class="font-medium">Mémoire:</span> {{ schedule.include_memory ? 'Oui' : 'Non' }}
                  </p>
                  <p v-if="schedule.last_run">
                    <span class="font-medium">Dernière exécution:</span> {{ formatDate(schedule.last_run) }}
                  </p>
                  <p>
                    <span class="font-medium">Créé:</span> {{ formatDate(schedule.created_at) }}
                  </p>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center space-x-2 ml-4">
              <button
                @click="toggleSchedule(schedule)"
                :class="schedule.is_active ? 'btn-secondary' : 'btn-success'"
                class="text-sm"
              >
                {{ schedule.is_active ? 'Désactiver' : 'Activer' }}
              </button>
              <button
                v-if="schedule.is_active"
                @click="runNow(schedule)"
                class="btn-primary text-sm"
              >
                <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Exécuter maintenant
              </button>
              <button
                @click="deleteScheduleConfirm(schedule)"
                class="p-2 text-red-600 hover:bg-red-50 rounded-lg"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State for Schedules -->
      <div v-else class="text-center py-12">
        <svg class="w-24 h-24 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Aucune planification</h3>
        <p class="text-gray-500 mb-4">Créez votre première planification de snapshots automatiques</p>
        <button @click="showCreateModal = true" class="btn-primary">
          Nouvelle planification
        </button>
      </div>
    </div>

    <!-- Snapshots Tab -->
    <div v-else-if="activeTab === 'snapshots'">
      <div v-if="snapshots.length > 0" class="space-y-4">
        <div
          v-for="snapshot in snapshots"
          :key="snapshot.id"
          class="card hover:shadow-lg transition-shadow"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-start space-x-4 flex-1">
              <div :class="getSnapshotStatusColor(snapshot.status)" class="p-3 rounded-lg">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <h3 class="text-lg font-semibold text-gray-900">{{ snapshot.snapshot_name }}</h3>
                  <span :class="getSnapshotStatusBadge(snapshot.status)" class="badge">
                    {{ getSnapshotStatusLabel(snapshot.status) }}
                  </span>
                </div>
                <div class="mt-2 space-y-1 text-sm text-gray-600">
                  <p>
                    <span class="font-medium">VM:</span> {{ snapshot.vm_name }}
                  </p>
                  <p>
                    <span class="font-medium">Mémoire incluse:</span> {{ snapshot.include_memory ? 'Oui' : 'Non' }}
                  </p>
                  <p v-if="snapshot.description">
                    <span class="font-medium">Description:</span> {{ snapshot.description }}
                  </p>
                  <p>
                    <span class="font-medium">Créé:</span> {{ formatDate(snapshot.created_at) }}
                  </p>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center space-x-2 ml-4">
              <button
                v-if="snapshot.status === 'completed'"
                @click="revertToSnapshot(snapshot)"
                class="btn-primary text-sm"
              >
                <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                </svg>
                Restaurer
              </button>
              <button
                v-if="snapshot.status === 'completed'"
                @click="deleteSnapshotConfirm(snapshot)"
                class="p-2 text-red-600 hover:bg-red-50 rounded-lg"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State for Snapshots -->
      <div v-else class="text-center py-12">
        <svg class="w-24 h-24 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Aucun snapshot</h3>
        <p class="text-gray-500 mb-4">Créez une planification pour générer des snapshots automatiquement</p>
        <button @click="activeTab = 'schedules'" class="btn-primary">
          Voir les planifications
        </button>
      </div>
    </div>

    <!-- Create Modal -->
    <SnapshotScheduleForm
      :show="showCreateModal"
      @close="showCreateModal = false"
      @submit="handleCreateSchedule"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSnapshotsStore } from '@/stores/snapshots'
import { useToastStore } from '@/stores/toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import Loading from '@/components/common/Loading.vue'
import SnapshotScheduleForm from '@/components/snapshots/SnapshotScheduleForm.vue'

const snapshotsStore = useSnapshotsStore()
const toast = useToastStore()

const activeTab = ref('schedules')
const showCreateModal = ref(false)

const schedules = computed(() => snapshotsStore.schedules)
const snapshots = computed(() => snapshotsStore.snapshots)
const loading = computed(() => snapshotsStore.loading)

let pollingInterval = null

onMounted(async () => {
  await Promise.all([
    snapshotsStore.fetchSchedules(),
    snapshotsStore.fetchSnapshots()
  ])

  // Polling pour les snapshots en cours de création
  pollingInterval = setInterval(async () => {
    const hasCreatingSnapshots = snapshots.value.some(s => s.status === 'creating')
    if (hasCreatingSnapshots) {
      await snapshotsStore.fetchSnapshots()
    }
  }, 3000) // Rafraîchir toutes les 3 secondes
})

onUnmounted(() => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
})

async function handleCreateSchedule(formData) {
  try {
    const result = await snapshotsStore.createSchedule(formData)
    toast.success(`Planification de snapshot créée: ${result.schedule_description || 'Configuration enregistrée'}`)
    showCreateModal.value = false
  } catch (err) {
    toast.error(`Erreur lors de la création: ${err.message}`)
  }
}

async function toggleSchedule(schedule) {
  try {
    await snapshotsStore.toggleSchedule(schedule.id)
    if (schedule.is_active) {
      toast.info('Planification de snapshot désactivée')
    } else {
      toast.success('Planification de snapshot activée')
    }
  } catch (err) {
    toast.error(`Erreur: ${err.message}`)
  }
}

async function runNow(schedule) {
  if (confirm(`Créer un snapshot maintenant pour ${schedule.vm_name} ?`)) {
    try {
      toast.info('Création du snapshot en cours...')
      const response = await snapshotsStore.runScheduleNow(schedule.id)
      toast.success(`Snapshot créé pour ${schedule.vm_name}`)
      // Switch to snapshots tab to see the result
      activeTab.value = 'snapshots'
    } catch (err) {
      toast.error(`Erreur: ${err.message}`)
    }
  }
}

async function deleteScheduleConfirm(schedule) {
  if (confirm(`Voulez-vous vraiment supprimer la planification pour ${schedule.vm_name} ?`)) {
    try {
      await snapshotsStore.deleteSchedule(schedule.id)
      toast.success('Planification supprimée avec succès')
    } catch (err) {
      toast.error(`Erreur lors de la suppression: ${err.message}`)
    }
  }
}

async function revertToSnapshot(snapshot) {
  if (confirm(`⚠️ ATTENTION: Restaurer le snapshot "${snapshot.snapshot_name}" ?\n\nCela va restaurer la VM "${snapshot.vm_name}" à son état au moment du snapshot.\nToutes les modifications depuis seront perdues.`)) {
    try {
      toast.warning('La restauration du snapshot écrasera l\'état actuel de la VM')
      await snapshotsStore.revertSnapshot(snapshot.id)
      toast.success(`Snapshot ${snapshot.snapshot_name} restauré avec succès`)
    } catch (err) {
      toast.error(`Erreur lors de la restauration: ${err.message}`)
    }
  }
}

async function deleteSnapshotConfirm(snapshot) {
  if (confirm(`Voulez-vous vraiment supprimer le snapshot "${snapshot.snapshot_name}" ?`)) {
    try {
      await snapshotsStore.deleteSnapshot(snapshot.id)
      toast.success(`Snapshot ${snapshot.snapshot_name} supprimé`)
    } catch (err) {
      toast.error(`Erreur lors de la suppression: ${err.message}`)
    }
  }
}

function getFrequencyLabel(frequency) {
  const labels = {
    hourly: 'Horaire',
    daily: 'Quotidienne',
    weekly: 'Hebdomadaire',
    monthly: 'Mensuelle'
  }
  return labels[frequency] || frequency
}

function getSnapshotStatusColor(status) {
  const colors = {
    completed: 'bg-green-500',
    creating: 'bg-blue-500',
    failed: 'bg-red-500',
    pending: 'bg-yellow-500'
  }
  return colors[status] || 'bg-gray-500'
}

function getSnapshotStatusBadge(status) {
  const classes = {
    completed: 'badge-success',
    creating: 'badge-info',
    failed: 'badge-danger',
    pending: 'badge-warning'
  }
  return classes[status] || 'badge-gray'
}

function getSnapshotStatusLabel(status) {
  const labels = {
    completed: 'Terminé',
    creating: 'En cours',
    failed: 'Échec',
    pending: 'En attente'
  }
  return labels[status] || status
}

function formatDate(date) {
  if (!date) return '-'
  return format(new Date(date), 'dd MMM yyyy HH:mm', { locale: fr })
}
</script>
