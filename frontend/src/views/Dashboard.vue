<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Tableau de bord</h1>
        <p class="mt-1 text-sm text-gray-500">Vue d'ensemble de votre infrastructure ESXi</p>
      </div>
      <button @click="refreshDashboard" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Actualiser
      </button>
    </div>

    <!-- Stats Cards -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div v-for="i in 4" :key="i" class="card animate-pulse">
        <div class="h-24 bg-gray-200 rounded"></div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatsCard
        title="Serveurs ESXi"
        :value="stats?.total_servers || 0"
        subtitle="Serveurs actifs"
        icon="server"
        color="blue"
      />
      <StatsCard
        title="Machines Virtuelles"
        :value="stats?.total_vms || 0"
        subtitle="VMs managées"
        icon="vm"
        color="purple"
      />
      <StatsCard
        title="Sauvegardes réussies"
        :value="stats?.successful_backups || 0"
        :subtitle="`${stats?.total_backups || 0} sauvegardes totales`"
        icon="check"
        color="green"
      />
      <StatsCard
        title="Stockage utilisé"
        :value="`${stats?.total_backup_size_gb || 0} GB`"
        subtitle="Espace de sauvegarde"
        icon="backup"
        color="yellow"
      />
    </div>

    <!-- Additional Stats -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Sauvegardes en cours</p>
            <p class="mt-2 text-3xl font-bold text-blue-600">{{ stats?.running_backups || 0 }}</p>
          </div>
          <div class="p-3 bg-blue-100 rounded-lg">
            <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Sauvegardes échouées</p>
            <p class="mt-2 text-3xl font-bold text-red-600">{{ stats?.failed_backups || 0 }}</p>
          </div>
          <div class="p-3 bg-red-100 rounded-lg">
            <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Planifications actives</p>
            <p class="mt-2 text-3xl font-bold text-purple-600">{{ stats?.active_schedules || 0 }}</p>
          </div>
          <div class="p-3 bg-purple-100 rounded-lg">
            <svg class="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Backups -->
    <RecentBackups :backups="recentBackups" :loading="loading" />

    <!-- Quick Actions -->
    <div class="card">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">Actions rapides</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <router-link
          to="/ovf-exports"
          class="flex items-center p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all"
        >
          <div class="p-3 bg-primary-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <div>
            <p class="font-medium text-gray-900">Nouvelle sauvegarde</p>
            <p class="text-sm text-gray-500">Créer une sauvegarde manuelle</p>
          </div>
        </router-link>

        <router-link
          to="/schedules"
          class="flex items-center p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all"
        >
          <div class="p-3 bg-purple-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <p class="font-medium text-gray-900">Planifier une sauvegarde</p>
            <p class="text-sm text-gray-500">Configuration automatique</p>
          </div>
        </router-link>

        <router-link
          to="/esxi-servers"
          class="flex items-center p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all"
        >
          <div class="p-3 bg-blue-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
          <div>
            <p class="font-medium text-gray-900">Gérer les serveurs</p>
            <p class="text-sm text-gray-500">Configuration ESXi</p>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import StatsCard from '@/components/dashboard/StatsCard.vue'
import RecentBackups from '@/components/dashboard/RecentBackups.vue'

const dashboardStore = useDashboardStore()

const stats = computed(() => dashboardStore.stats)
const recentBackups = computed(() => dashboardStore.recentBackups)
const loading = computed(() => dashboardStore.loading)

async function refreshDashboard() {
  await dashboardStore.refreshDashboard()
}

onMounted(() => {
  refreshDashboard()
})
</script>
