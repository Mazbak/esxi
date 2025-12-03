<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
      <p class="text-gray-600">Vue d'ensemble de l'activité et des revenus</p>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Revenue Card -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100 hover:shadow-2xl transition-shadow">
        <div class="flex items-center justify-between mb-4">
          <div class="p-3 bg-gradient-to-r from-green-100 to-emerald-100 rounded-xl">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <span class="text-xs font-semibold text-green-600 bg-green-100 px-2 py-1 rounded-full">
            +12.5%
          </span>
        </div>
        <h3 class="text-sm font-medium text-gray-600 mb-1">Revenus du mois</h3>
        <p class="text-2xl font-bold text-gray-900">{{ formatCurrency(stats.monthlyRevenue) }}</p>
        <p class="text-xs text-gray-500 mt-2">{{ stats.completedOrders }} commandes</p>
      </div>

      <!-- Active Organizations -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100 hover:shadow-2xl transition-shadow">
        <div class="flex items-center justify-between mb-4">
          <div class="p-3 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <span class="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
            +8
          </span>
        </div>
        <h3 class="text-sm font-medium text-gray-600 mb-1">Organisations actives</h3>
        <p class="text-2xl font-bold text-gray-900">{{ stats.activeOrganizations }}</p>
        <p class="text-xs text-gray-500 mt-2">{{ stats.totalOrganizations }} au total</p>
      </div>

      <!-- Pending Orders -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100 hover:shadow-2xl transition-shadow">
        <div class="flex items-center justify-between mb-4">
          <div class="p-3 bg-gradient-to-r from-orange-100 to-yellow-100 rounded-xl">
            <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <span class="text-xs font-semibold text-orange-600 bg-orange-100 px-2 py-1 rounded-full">
            {{ stats.pendingOrders }}
          </span>
        </div>
        <h3 class="text-sm font-medium text-gray-600 mb-1">Commandes en attente</h3>
        <p class="text-2xl font-bold text-gray-900">{{ stats.pendingOrders }}</p>
        <p class="text-xs text-gray-500 mt-2">Nécessitent une action</p>
      </div>

      <!-- Pending Payments -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100 hover:shadow-2xl transition-shadow">
        <div class="flex items-center justify-between mb-4">
          <div class="p-3 bg-gradient-to-r from-purple-100 to-pink-100 rounded-xl">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <span class="text-xs font-semibold text-purple-600 bg-purple-100 px-2 py-1 rounded-full">
            {{ stats.pendingPayments }}
          </span>
        </div>
        <h3 class="text-sm font-medium text-gray-600 mb-1">Paiements en attente</h3>
        <p class="text-2xl font-bold text-gray-900">{{ stats.pendingPayments }}</p>
        <p class="text-xs text-gray-500 mt-2">Virements à vérifier</p>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Revenue Chart -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-gray-900">Revenus mensuels</h2>
          <select class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-600">
            <option>6 derniers mois</option>
            <option>12 derniers mois</option>
            <option>Cette année</option>
          </select>
        </div>
        <div class="h-64 flex items-end justify-between gap-2">
          <div v-for="(value, index) in revenueData" :key="index" class="flex-1 group">
            <div class="relative">
              <div
                class="bg-gradient-to-t from-indigo-600 to-purple-600 rounded-t-lg transition-all duration-300 hover:from-indigo-700 hover:to-purple-700 cursor-pointer"
                :style="{ height: `${(value / Math.max(...revenueData)) * 100}%` }"
              >
                <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                  {{ formatCurrency(value) }}
                </div>
              </div>
            </div>
            <p class="text-xs text-gray-600 text-center mt-2">{{ months[index] }}</p>
          </div>
        </div>
      </div>

      <!-- Plan Distribution -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100">
        <h2 class="text-xl font-bold text-gray-900 mb-6">Répartition des plans</h2>
        <div class="space-y-4">
          <div v-for="plan in planDistribution" :key="plan.name" class="group">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: plan.color }"></div>
                <span class="text-sm font-medium text-gray-700">{{ plan.name }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-bold text-gray-900">{{ plan.count }}</span>
                <span class="text-xs text-gray-500">({{ plan.percentage }}%)</span>
              </div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :style="{ width: `${plan.percentage}%`, backgroundColor: plan.color }"
              ></div>
            </div>
          </div>
        </div>

        <!-- Total -->
        <div class="mt-6 pt-6 border-t border-gray-200">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-700">Total organisations</span>
            <span class="text-lg font-bold text-gray-900">
              {{ planDistribution.reduce((sum, p) => sum + p.count, 0) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Recent Orders -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-gray-900">Commandes récentes</h2>
          <router-link to="/admin/orders" class="text-sm font-medium text-indigo-600 hover:text-indigo-700">
            Voir tout →
          </router-link>
        </div>
        <div class="space-y-4">
          <div
            v-for="order in recentOrders"
            :key="order.id"
            class="flex items-center gap-4 p-4 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-r from-indigo-100 to-purple-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-900 truncate">{{ order.customer_name }}</p>
              <p class="text-xs text-gray-600">{{ order.plan }} - {{ formatCurrency(order.amount) }}</p>
            </div>
            <div class="flex-shrink-0">
              <span
                class="px-3 py-1 text-xs font-semibold rounded-full"
                :class="getStatusClass(order.status)"
              >
                {{ order.status }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Payments -->
      <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-gray-900">Paiements récents</h2>
          <router-link to="/admin/payments" class="text-sm font-medium text-indigo-600 hover:text-indigo-700">
            Voir tout →
          </router-link>
        </div>
        <div class="space-y-4">
          <div
            v-for="payment in recentPayments"
            :key="payment.id"
            class="flex items-center gap-4 p-4 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-r from-green-100 to-emerald-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-900 truncate">{{ payment.organization }}</p>
              <p class="text-xs text-gray-600">{{ payment.method }} - {{ payment.date }}</p>
            </div>
            <div class="flex-shrink-0">
              <p class="text-sm font-bold text-gray-900">{{ formatCurrency(payment.amount) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// Stats
const stats = ref({
  monthlyRevenue: 2500000,
  completedOrders: 45,
  activeOrganizations: 67,
  totalOrganizations: 89,
  pendingOrders: 3,
  pendingPayments: 2
})

// Revenue data (last 6 months)
const revenueData = ref([1800000, 2100000, 1950000, 2300000, 2450000, 2500000])
const months = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Plan distribution
const planDistribution = ref([
  { name: 'Bronze', count: 25, percentage: 37, color: '#CD7F32' },
  { name: 'Silver', count: 30, percentage: 45, color: '#C0C0C0' },
  { name: 'Gold', count: 12, percentage: 18, color: '#FFD700' }
])

// Recent orders
const recentOrders = ref([
  { id: 1, customer_name: 'Entreprise ABC', plan: 'Silver', amount: 50000, status: 'completed' },
  { id: 2, customer_name: 'Tech Solutions', plan: 'Gold', amount: 100000, status: 'pending' },
  { id: 3, customer_name: 'StartUp XYZ', plan: 'Bronze', amount: 25000, status: 'processing' },
  { id: 4, customer_name: 'Digital Corp', plan: 'Silver', amount: 50000, status: 'completed' }
])

// Recent payments
const recentPayments = ref([
  { id: 1, organization: 'Entreprise ABC', method: 'PayPal', amount: 50000, date: '03 Déc 2024' },
  { id: 2, organization: 'StartUp XYZ', method: 'MTN MoMo', amount: 25000, date: '02 Déc 2024' },
  { id: 3, organization: 'Digital Corp', method: 'Virement', amount: 50000, date: '01 Déc 2024' }
])

// Methods
const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XAF',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

const getStatusClass = (status) => {
  const classes = {
    completed: 'bg-green-100 text-green-700',
    pending: 'bg-orange-100 text-orange-700',
    processing: 'bg-blue-100 text-blue-700',
    failed: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

const loadStats = async () => {
  try {
    // TODO: Load real stats from API
    // const response = await axios.get('http://localhost:8000/api/tenants/admin/stats/')
    // stats.value = response.data
  } catch (error) {
    console.error('Error loading stats:', error)
  }
}

// Lifecycle
onMounted(() => {
  loadStats()
})
</script>

<style scoped>
/* Add any additional custom styles here */
</style>
