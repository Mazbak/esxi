<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Gestion des Commandes</h1>
        <p class="text-gray-600">Gérez toutes les commandes clients</p>
      </div>
      <button class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium hover:shadow-lg transition-shadow flex items-center gap-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export CSV
      </button>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-100">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Recherche</label>
          <input
            v-model="filters.search"
            type="text"
            placeholder="Nom, email, numéro..."
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Statut</label>
          <select v-model="filters.status" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600">
            <option value="">Tous les statuts</option>
            <option value="pending">En attente</option>
            <option value="payment_pending">Paiement en attente</option>
            <option value="paid">Payé</option>
            <option value="processing">En traitement</option>
            <option value="completed">Terminé</option>
            <option value="failed">Échoué</option>
            <option value="cancelled">Annulé</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Plan</label>
          <select v-model="filters.plan" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600">
            <option value="">Tous les plans</option>
            <option value="bronze">Bronze</option>
            <option value="silver">Silver</option>
            <option value="gold">Gold</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Période</label>
          <select v-model="filters.period" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600">
            <option value="all">Toutes</option>
            <option value="today">Aujourd'hui</option>
            <option value="week">Cette semaine</option>
            <option value="month">Ce mois</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Orders Table -->
    <div class="bg-white rounded-2xl shadow-xl border-2 border-gray-100 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gradient-to-r from-gray-50 to-gray-100 border-b-2 border-gray-200">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Numéro
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Client
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Plan
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Montant
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Paiement
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Statut
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Date
              </th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr
              v-for="order in filteredOrders"
              :key="order.id"
              class="hover:bg-gray-50 transition-colors"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <span class="text-sm font-mono font-semibold text-indigo-600">
                  {{ order.order_number }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div>
                  <p class="text-sm font-semibold text-gray-900">{{ order.customer_name }}</p>
                  <p class="text-xs text-gray-600">{{ order.customer_email }}</p>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-3 py-1 text-xs font-semibold rounded-full"
                  :class="getPlanClass(order.plan)"
                >
                  {{ order.plan }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <p class="text-sm font-bold text-gray-900">{{ formatCurrency(order.total_amount) }}</p>
                <p class="text-xs text-gray-600">{{ order.billing_cycle }}</p>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-3 py-1 text-xs font-semibold rounded-full"
                  :class="getPaymentStatusClass(order.payment_status)"
                >
                  {{ order.payment_status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-3 py-1 text-xs font-semibold rounded-full"
                  :class="getStatusClass(order.status)"
                >
                  {{ order.status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {{ formatDate(order.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center gap-2">
                  <button
                    @click="viewOrder(order)"
                    class="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title="Voir détails"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  <button
                    v-if="order.status === 'pending'"
                    @click="processOrder(order)"
                    class="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                    title="Traiter"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                  </button>
                  <button
                    @click="deleteOrder(order)"
                    class="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Supprimer"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="bg-gray-50 px-6 py-4 flex items-center justify-between border-t border-gray-200">
        <div class="text-sm text-gray-600">
          Affichage de <span class="font-semibold">1</span> à <span class="font-semibold">{{ filteredOrders.length }}</span> sur <span class="font-semibold">{{ orders.length }}</span> résultats
        </div>
        <div class="flex items-center gap-2">
          <button class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-white transition-colors">
            Précédent
          </button>
          <button class="px-3 py-2 bg-indigo-600 text-white rounded-lg">
            1
          </button>
          <button class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-white transition-colors">
            2
          </button>
          <button class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-white transition-colors">
            Suivant
          </button>
        </div>
      </div>
    </div>

    <!-- Order Details Modal -->
    <div v-if="selectedOrder" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 class="text-2xl font-bold text-gray-900">Détails de la commande</h2>
          <button @click="selectedOrder = null" class="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-6">
          <!-- Order info -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-sm text-gray-600 mb-1">Numéro</p>
              <p class="font-mono font-bold text-indigo-600">{{ selectedOrder.order_number }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-1">Date</p>
              <p class="font-semibold">{{ formatDate(selectedOrder.created_at) }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-1">Client</p>
              <p class="font-semibold">{{ selectedOrder.customer_name }}</p>
              <p class="text-sm text-gray-600">{{ selectedOrder.customer_email }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-1">Plan</p>
              <span :class="getPlanClass(selectedOrder.plan)" class="inline-block px-3 py-1 text-sm font-semibold rounded-full">
                {{ selectedOrder.plan }}
              </span>
            </div>
          </div>

          <!-- Amounts -->
          <div class="bg-gray-50 rounded-xl p-4 space-y-2">
            <div class="flex justify-between">
              <span class="text-gray-600">Sous-total</span>
              <span class="font-semibold">{{ formatCurrency(selectedOrder.subtotal) }}</span>
            </div>
            <div class="flex justify-between text-green-600">
              <span>Réduction</span>
              <span class="font-semibold">-{{ formatCurrency(selectedOrder.discount_amount) }}</span>
            </div>
            <div class="flex justify-between border-t border-gray-200 pt-2">
              <span class="font-bold text-gray-900">Total</span>
              <span class="font-bold text-gray-900">{{ formatCurrency(selectedOrder.total_amount) }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3">
            <button class="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors">
              Approuver
            </button>
            <button class="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-colors">
              Refuser
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import axios from 'axios'

const toast = useToast()

// State
const orders = ref([
  {
    id: 1,
    order_number: 'ORD-20241203-12345',
    customer_name: 'Entreprise ABC',
    customer_email: 'contact@abc.com',
    plan: 'Silver',
    billing_cycle: 'Mensuel',
    subtotal: 50000,
    discount_amount: 0,
    total_amount: 50000,
    payment_status: 'pending',
    status: 'pending',
    created_at: '2024-12-03T10:30:00Z'
  },
  {
    id: 2,
    order_number: 'ORD-20241203-12346',
    customer_name: 'Tech Solutions',
    customer_email: 'info@techsolutions.com',
    plan: 'Gold',
    billing_cycle: 'Annuel',
    subtotal: 1000000,
    discount_amount: 100000,
    total_amount: 900000,
    payment_status: 'paid',
    status: 'completed',
    created_at: '2024-12-02T15:20:00Z'
  }
])

const filters = ref({
  search: '',
  status: '',
  plan: '',
  period: 'all'
})

const selectedOrder = ref(null)

// Computed
const filteredOrders = computed(() => {
  return orders.value.filter(order => {
    if (filters.value.search && !order.customer_name.toLowerCase().includes(filters.value.search.toLowerCase()) &&
        !order.customer_email.toLowerCase().includes(filters.value.search.toLowerCase()) &&
        !order.order_number.toLowerCase().includes(filters.value.search.toLowerCase())) {
      return false
    }
    if (filters.value.status && order.status !== filters.value.status) {
      return false
    }
    if (filters.value.plan && order.plan.toLowerCase() !== filters.value.plan.toLowerCase()) {
      return false
    }
    return true
  })
})

// Methods
const formatCurrency = (value) => {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XAF',
    minimumFractionDigits: 0
  }).format(value)
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getPlanClass = (plan) => {
  const classes = {
    Bronze: 'bg-orange-100 text-orange-700',
    Silver: 'bg-gray-200 text-gray-700',
    Gold: 'bg-yellow-100 text-yellow-700'
  }
  return classes[plan] || 'bg-gray-100 text-gray-700'
}

const getStatusClass = (status) => {
  const classes = {
    pending: 'bg-orange-100 text-orange-700',
    payment_pending: 'bg-yellow-100 text-yellow-700',
    paid: 'bg-green-100 text-green-700',
    processing: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

const getPaymentStatusClass = (status) => {
  const classes = {
    pending: 'bg-orange-100 text-orange-700',
    paid: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-700'
}

const viewOrder = (order) => {
  selectedOrder.value = order
}

const processOrder = async (order) => {
  if (confirm(`Traiter la commande ${order.order_number} ?`)) {
    try {
      // TODO: Call API to process order
      toast.success('Commande traitée avec succès')
    } catch (error) {
      toast.error('Erreur lors du traitement')
    }
  }
}

const deleteOrder = async (order) => {
  if (confirm(`Supprimer la commande ${order.order_number} ?`)) {
    try {
      // TODO: Call API to delete order
      orders.value = orders.value.filter(o => o.id !== order.id)
      toast.success('Commande supprimée')
    } catch (error) {
      toast.error('Erreur lors de la suppression')
    }
  }
}

const loadOrders = async () => {
  try {
    // TODO: Load from API
    // const response = await axios.get('http://localhost:8000/api/tenants/orders/')
    // orders.value = response.data
  } catch (error) {
    console.error('Error loading orders:', error)
    toast.error('Erreur lors du chargement des commandes')
  }
}

// Lifecycle
onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
/* Add any additional custom styles here */
</style>
