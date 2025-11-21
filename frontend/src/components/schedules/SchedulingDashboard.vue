<template>
  <div class="space-y-6">
    <!-- Statistics Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Total Schedules -->
      <div class="card bg-gradient-to-br from-primary-500 to-primary-600 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-primary-100 text-sm font-medium">Total Planifications</p>
            <p class="text-3xl font-bold mt-2">{{ stats.total }}</p>
          </div>
          <div class="bg-white bg-opacity-20 p-3 rounded-lg">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Active Schedules -->
      <div class="card bg-gradient-to-br from-green-500 to-green-600 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-green-100 text-sm font-medium">Actives</p>
            <p class="text-3xl font-bold mt-2">{{ stats.active }}</p>
          </div>
          <div class="bg-white bg-opacity-20 p-3 rounded-lg">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Inactive Schedules -->
      <div class="card bg-gradient-to-br from-gray-500 to-gray-600 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-100 text-sm font-medium">Inactives</p>
            <p class="text-3xl font-bold mt-2">{{ stats.inactive }}</p>
          </div>
          <div class="bg-white bg-opacity-20 p-3 rounded-lg">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Total Executions -->
      <div class="card bg-gradient-to-br from-purple-500 to-purple-600 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-purple-100 text-sm font-medium">Exécutions (7j)</p>
            <p class="text-3xl font-bold mt-2">{{ stats.executions }}</p>
          </div>
          <div class="bg-white bg-opacity-20 p-3 rounded-lg">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Strategy Distribution -->
    <div class="card">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">Distribution des stratégies</h3>
      <div class="space-y-3">
        <div v-for="(count, strategy) in stats.strategies" :key="strategy" class="flex items-center">
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-gray-700">{{ getStrategyLabel(strategy) }}</span>
              <span class="text-sm text-gray-500">{{ count }}</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                :class="getStrategyColor(strategy)"
                class="h-2 rounded-full transition-all"
                :style="{ width: getPercentage(count, stats.total) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Upcoming Schedules -->
    <div class="card">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">Prochaines exécutions</h3>
      <div v-if="upcomingSchedules.length > 0" class="space-y-3">
        <div
          v-for="schedule in upcomingSchedules"
          :key="schedule.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <div class="flex items-center space-x-3">
            <div class="bg-primary-100 p-2 rounded-lg">
              <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-900">{{ getVMName(schedule.virtual_machine) }}</p>
              <p class="text-xs text-gray-500">{{ getStrategyLabel(schedule.backup_strategy) }}</p>
            </div>
          </div>
          <div class="text-right">
            <p class="text-sm font-medium text-gray-900">{{ getTimeUntil(schedule.next_run) }}</p>
            <p class="text-xs text-gray-500">{{ formatDateTime(schedule.next_run) }}</p>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-500">
        <svg class="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <p class="text-sm">Aucune exécution planifiée</p>
      </div>
    </div>

    <!-- Recent Executions -->
    <div class="card">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">Exécutions récentes</h3>
      <div v-if="recentExecutions.length > 0" class="space-y-3">
        <div
          v-for="execution in recentExecutions"
          :key="execution.schedule.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div class="flex items-center space-x-3">
            <div
              :class="execution.schedule.last_run_at ? 'bg-green-100' : 'bg-gray-100'"
              class="p-2 rounded-lg"
            >
              <svg
                class="w-5 h-5"
                :class="execution.schedule.last_run_at ? 'text-green-600' : 'text-gray-400'"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-900">{{ getVMName(execution.schedule.virtual_machine) }}</p>
              <p class="text-xs text-gray-500">{{ getStrategyLabel(execution.schedule.backup_strategy) }}</p>
            </div>
          </div>
          <div class="text-right">
            <p class="text-sm font-medium text-gray-900">{{ getTimeAgo(execution.schedule.last_run_at) }}</p>
            <p class="text-xs text-gray-500">{{ formatDateTime(execution.schedule.last_run_at) }}</p>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-500">
        <svg class="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-sm">Aucune exécution récente</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useBackupsStore } from '@/stores/backups'
import { useEsxiStore } from '@/stores/esxi'
import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { fr } from 'date-fns/locale'

const backupsStore = useBackupsStore()
const esxiStore = useEsxiStore()

const schedules = computed(() => backupsStore.schedules || [])
const virtualMachines = computed(() => esxiStore.virtualMachines || [])

const stats = computed(() => {
  const total = schedules.value.length
  const active = schedules.value.filter(s => s.is_active || s.is_enabled).length
  const inactive = total - active

  // Count executions in last 7 days
  const sevenDaysAgo = new Date()
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
  const executions = schedules.value.filter(s => {
    if (!s.last_run_at) return false
    return new Date(s.last_run_at) >= sevenDaysAgo
  }).length

  // Strategy distribution
  const strategies = {}
  schedules.value.forEach(s => {
    const strategy = s.backup_strategy || 'full_weekly'
    strategies[strategy] = (strategies[strategy] || 0) + 1
  })

  return {
    total,
    active,
    inactive,
    executions,
    strategies
  }
})

const upcomingSchedules = computed(() => {
  return schedules.value
    .filter(s => (s.is_active || s.is_enabled) && s.next_run)
    .sort((a, b) => new Date(a.next_run) - new Date(b.next_run))
    .slice(0, 5)
})

const recentExecutions = computed(() => {
  return schedules.value
    .filter(s => s.last_run_at)
    .map(s => ({ schedule: s }))
    .sort((a, b) => new Date(b.schedule.last_run_at) - new Date(a.schedule.last_run_at))
    .slice(0, 5)
})

function getVMName(vmId) {
  const vm = virtualMachines.value.find(v => v.id === vmId)
  return vm ? vm.name : `VM #${vmId}`
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

function getStrategyColor(strategy) {
  const colors = {
    'full_weekly': 'bg-primary-500',
    'full_only': 'bg-blue-500',
    'incremental_only': 'bg-green-500',
    'smart': 'bg-purple-500'
  }
  return colors[strategy] || 'bg-gray-500'
}

function getPercentage(value, total) {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

function formatDateTime(date) {
  if (!date) return '-'
  return format(parseISO(date), 'dd MMM yyyy HH:mm', { locale: fr })
}

function getTimeUntil(date) {
  if (!date) return '-'
  return formatDistanceToNow(parseISO(date), { locale: fr, addSuffix: true })
}

function getTimeAgo(date) {
  if (!date) return '-'
  return formatDistanceToNow(parseISO(date), { locale: fr, addSuffix: true })
}
</script>
