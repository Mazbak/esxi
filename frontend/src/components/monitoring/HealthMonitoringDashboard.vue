<template>
  <div class="space-y-6">
    <!-- Health Score Section -->
    <div class="card">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-bold text-gray-900">Santé du Système de Backup</h2>
        <button @click="refreshHealth" :disabled="loading" class="btn-secondary">
          <svg
            class="w-5 h-5 mr-2 inline"
            :class="{ 'animate-spin': loading }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Actualiser
        </button>
      </div>

      <div v-if="loading && !health" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>

      <div v-else-if="health" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Health Score Gauge -->
        <div class="flex flex-col items-center justify-center p-6 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg">
          <div class="relative">
            <svg class="transform -rotate-90" width="160" height="160">
              <!-- Background circle -->
              <circle
                cx="80"
                cy="80"
                r="70"
                stroke="#e5e7eb"
                stroke-width="12"
                fill="none"
              />
              <!-- Progress circle -->
              <circle
                cx="80"
                cy="80"
                r="70"
                :stroke="getHealthColor(health.status)"
                stroke-width="12"
                fill="none"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="dashOffset"
                class="transition-all duration-1000 ease-out"
                stroke-linecap="round"
              />
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <div class="text-4xl font-bold" :class="getHealthTextColor(health.status)">
                {{ health.score }}
              </div>
              <div class="text-sm text-gray-500">/ 100</div>
            </div>
          </div>
          <div class="mt-4 text-center">
            <div class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
                 :class="getHealthBadgeClass(health.status)">
              <span class="w-2 h-2 rounded-full mr-2" :class="getHealthDotClass(health.status)"></span>
              {{ getHealthLabel(health.status) }}
            </div>
          </div>
        </div>

        <!-- Key Metrics -->
        <div class="lg:col-span-2 grid grid-cols-2 gap-4">
          <div class="p-4 bg-blue-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <p class="text-sm font-medium text-blue-900">Backups totaux</p>
                <p class="text-2xl font-bold text-blue-600 mt-1">{{ health.metrics?.total_jobs || 0 }}</p>
              </div>
              <div class="p-3 bg-blue-100 rounded-lg">
                <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
              </div>
            </div>
          </div>

          <div class="p-4 bg-green-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <p class="text-sm font-medium text-green-900">Taux de succès (24h)</p>
                <p class="text-2xl font-bold text-green-600 mt-1">{{ health.metrics?.success_rate_24h || 0 }}%</p>
              </div>
              <div class="p-3 bg-green-100 rounded-lg">
                <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div class="p-4 bg-purple-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <p class="text-sm font-medium text-purple-900">VMs protégées</p>
                <p class="text-2xl font-bold text-purple-600 mt-1">{{ health.metrics?.total_vms || 0 }}</p>
              </div>
              <div class="p-3 bg-purple-100 rounded-lg">
                <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
              </div>
            </div>
          </div>

          <div class="p-4 bg-yellow-50 rounded-lg">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <p class="text-sm font-medium text-yellow-900">Taille totale</p>
                <p class="text-2xl font-bold text-yellow-600 mt-1">{{ health.metrics?.total_backup_size_gb || 0 }} GB</p>
              </div>
              <div class="p-3 bg-yellow-100 rounded-lg">
                <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Issues and Warnings -->
    <div v-if="health && (health.issues?.length > 0 || health.warnings?.length > 0)" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Critical Issues -->
      <div v-if="health.issues?.length > 0" class="card">
        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <svg class="w-5 h-5 mr-2 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Problèmes détectés ({{ health.issues.length }})
        </h3>
        <div class="space-y-3">
          <div
            v-for="(issue, idx) in health.issues"
            :key="idx"
            class="p-4 rounded-lg"
            :class="issue.severity === 'critical' ? 'bg-red-50 border border-red-200' : 'bg-yellow-50 border border-yellow-200'"
          >
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <svg
                  class="w-5 h-5 mt-0.5"
                  :class="issue.severity === 'critical' ? 'text-red-500' : 'text-yellow-500'"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3 flex-1">
                <p
                  class="text-sm font-medium"
                  :class="issue.severity === 'critical' ? 'text-red-800' : 'text-yellow-800'"
                >
                  {{ issue.message }}
                </p>
                <p
                  class="mt-1 text-xs"
                  :class="issue.severity === 'critical' ? 'text-red-600' : 'text-yellow-600'"
                >
                  Type: {{ issue.type }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Warnings -->
      <div v-if="health.warnings?.length > 0" class="card">
        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <svg class="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Avertissements ({{ health.warnings.length }})
        </h3>
        <div class="space-y-3">
          <div
            v-for="(warning, idx) in health.warnings"
            :key="idx"
            class="p-4 bg-blue-50 border border-blue-200 rounded-lg"
          >
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <svg class="w-5 h-5 mt-0.5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3 flex-1">
                <p class="text-sm font-medium text-blue-800">{{ warning.message }}</p>
                <p class="mt-1 text-xs text-blue-600">Type: {{ warning.type }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- No Issues State -->
    <div v-else-if="health && health.issues?.length === 0 && health.warnings?.length === 0" class="card">
      <div class="text-center py-8">
        <svg class="w-16 h-16 mx-auto mb-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Tout va bien!</h3>
        <p class="text-gray-500">Aucun problème détecté dans votre système de backup</p>
      </div>
    </div>

    <!-- Recommendations -->
    <div v-if="health && health.recommendations?.length > 0" class="card">
      <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <svg class="w-5 h-5 mr-2 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        Recommandations ({{ health.recommendations.length }})
      </h3>
      <div class="space-y-3">
        <div
          v-for="(rec, idx) in health.recommendations"
          :key="idx"
          class="p-4 border-l-4 rounded-lg"
          :class="getPriorityClass(rec.priority)"
        >
          <div class="flex items-start">
            <div class="flex-1">
              <div class="flex items-center mb-1">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-2"
                  :class="getPriorityBadgeClass(rec.priority)"
                >
                  {{ rec.priority.toUpperCase() }}
                </span>
              </div>
              <p class="text-sm text-gray-800">{{ rec.message }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { healthAPI } from '@/services/api'

const health = ref(null)
const loading = ref(false)

const circumference = 2 * Math.PI * 70 // rayon = 70
const dashOffset = computed(() => {
  if (!health.value) return circumference
  const progress = health.value.score / 100
  return circumference * (1 - progress)
})

async function refreshHealth() {
  loading.value = true
  try {
    const response = await healthAPI.getOverall()
    health.value = response.data
  } catch (error) {
    console.error('Erreur lors de la récupération de la santé:', error)
  } finally {
    loading.value = false
  }
}

function getHealthColor(status) {
  const colors = {
    healthy: '#10b981',    // green-500
    warning: '#f59e0b',    // yellow-500
    critical: '#ef4444',   // red-500
    unknown: '#6b7280'     // gray-500
  }
  return colors[status] || colors.unknown
}

function getHealthTextColor(status) {
  const colors = {
    healthy: 'text-green-600',
    warning: 'text-yellow-600',
    critical: 'text-red-600',
    unknown: 'text-gray-600'
  }
  return colors[status] || colors.unknown
}

function getHealthBadgeClass(status) {
  const classes = {
    healthy: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    critical: 'bg-red-100 text-red-800',
    unknown: 'bg-gray-100 text-gray-800'
  }
  return classes[status] || classes.unknown
}

function getHealthDotClass(status) {
  const classes = {
    healthy: 'bg-green-500',
    warning: 'bg-yellow-500',
    critical: 'bg-red-500',
    unknown: 'bg-gray-500'
  }
  return classes[status] || classes.unknown
}

function getHealthLabel(status) {
  const labels = {
    healthy: 'Excellent',
    warning: 'Attention',
    critical: 'Critique',
    unknown: 'Inconnu'
  }
  return labels[status] || 'Inconnu'
}

function getPriorityClass(priority) {
  const classes = {
    critical: 'border-red-500 bg-red-50',
    high: 'border-orange-500 bg-orange-50',
    medium: 'border-yellow-500 bg-yellow-50',
    low: 'border-blue-500 bg-blue-50'
  }
  return classes[priority] || classes.low
}

function getPriorityBadgeClass(priority) {
  const classes = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800'
  }
  return classes[priority] || classes.low
}

onMounted(() => {
  refreshHealth()
})

// Auto-refresh every 5 minutes
setInterval(() => {
  refreshHealth()
}, 5 * 60 * 1000)
</script>

<style scoped>
@keyframes spin {
  to { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
