<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="p-2 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg">
              <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
            </div>
            <div>
              <h1 class="text-2xl font-bold text-gray-900">ESXi Backup Manager</h1>
              <p class="text-sm text-gray-600">Solution de sauvegarde professionnelle</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <button @click="$router.push('/login')" class="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium">
              Se connecter
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="py-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 class="text-5xl font-extrabold text-gray-900 mb-4">
          Choisissez votre
          <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
            Plan Idéal
          </span>
        </h2>
        <p class="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
          Des solutions de sauvegarde adaptées à chaque besoin, de la PME à la grande entreprise
        </p>

        <!-- Billing Toggle -->
        <div class="flex items-center justify-center gap-4 mb-12">
          <span :class="billingCycle === 'monthly' ? 'text-gray-900 font-semibold' : 'text-gray-600'">
            Mensuel
          </span>
          <button
            @click="toggleBillingCycle"
            class="relative inline-flex h-8 w-16 items-center rounded-full transition-colors"
            :class="billingCycle === 'yearly' ? 'bg-indigo-600' : 'bg-gray-300'"
          >
            <span
              class="inline-block h-6 w-6 transform rounded-full bg-white transition-transform"
              :class="billingCycle === 'yearly' ? 'translate-x-9' : 'translate-x-1'"
            />
          </button>
          <span :class="billingCycle === 'yearly' ? 'text-gray-900 font-semibold' : 'text-gray-600'">
            Annuel
            <span class="ml-1 text-green-600 font-bold">(-17%)</span>
          </span>
        </div>
      </div>
    </section>

    <!-- Pricing Cards -->
    <section class="pb-20">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div v-if="loading" class="text-center py-12">
          <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p class="mt-4 text-gray-600">Chargement des plans...</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <!-- Bronze Plan -->
          <div
            v-for="plan in plans"
            :key="plan.id"
            class="relative bg-white rounded-3xl shadow-xl border-2 transition-all duration-300 hover:scale-105"
            :class="plan.name === 'silver' ? 'border-indigo-500 ring-4 ring-indigo-100' : 'border-gray-200 hover:border-indigo-300'"
          >
            <!-- Popular Badge -->
            <div
              v-if="plan.name === 'silver'"
              class="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-2 rounded-full text-sm font-bold shadow-lg"
            >
              ⭐ POPULAIRE
            </div>

            <div class="p-8">
              <!-- Plan Header -->
              <div class="text-center mb-6">
                <h3 class="text-2xl font-bold text-gray-900 mb-2">{{ plan.display_name }}</h3>
                <p class="text-gray-600">{{ plan.description }}</p>
              </div>

              <!-- Price -->
              <div class="text-center mb-8">
                <div class="flex items-baseline justify-center gap-2">
                  <span class="text-5xl font-extrabold text-gray-900">
                    {{ formatPrice(billingCycle === 'monthly' ? plan.monthly_price : plan.yearly_price) }}
                  </span>
                  <span class="text-gray-600">XAF</span>
                </div>
                <p class="text-gray-600 mt-2">{{ billingCycle === 'monthly' ? 'par mois' : 'par an' }}</p>
                <p v-if="billingCycle === 'yearly'" class="text-sm text-green-600 font-semibold mt-1">
                  Économisez {{ Math.round((1 - (plan.yearly_price / (plan.monthly_price * 12))) * 100) }}%
                </p>
              </div>

              <!-- Features -->
              <div class="space-y-4 mb-8">
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-gray-700">
                    <strong>{{ plan.max_esxi_servers }}</strong> serveurs ESXi
                  </span>
                </div>
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-gray-700">
                    <strong>{{ plan.max_vms }}</strong> machines virtuelles
                  </span>
                </div>
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-gray-700">
                    <strong>{{ plan.max_backups_per_month }}</strong> sauvegardes/mois
                  </span>
                </div>
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-gray-700">
                    <strong>{{ plan.max_storage_gb }}</strong> GB de stockage
                  </span>
                </div>
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-gray-700">
                    <strong>{{ plan.max_users }}</strong> utilisateurs
                  </span>
                </div>
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-gray-700">
                    Rétention <strong>{{ plan.backup_retention_days }}</strong> jours
                  </span>
                </div>

                <!-- Advanced Features -->
                <div class="pt-4 border-t border-gray-200">
                  <div v-if="plan.has_replication" class="flex items-start gap-3 mb-3">
                    <svg class="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-gray-700 font-semibold">Réplication inter-sites</span>
                  </div>
                  <div v-if="plan.has_surebackup" class="flex items-start gap-3 mb-3">
                    <svg class="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-gray-700 font-semibold">Vérification SureBackup</span>
                  </div>
                  <div v-if="plan.has_advanced_monitoring" class="flex items-start gap-3 mb-3">
                    <svg class="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-gray-700 font-semibold">Monitoring avancé</span>
                  </div>
                  <div v-if="plan.has_api_access" class="flex items-start gap-3 mb-3">
                    <svg class="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-gray-700 font-semibold">Accès API REST</span>
                  </div>
                  <div v-if="plan.has_priority_support" class="flex items-start gap-3">
                    <svg class="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-gray-700 font-semibold">Support prioritaire 24/7</span>
                  </div>
                </div>
              </div>

              <!-- CTA Button -->
              <button
                @click="selectPlan(plan)"
                class="w-full py-4 rounded-xl font-bold text-lg transition-all duration-300 transform hover:scale-105"
                :class="plan.name === 'silver'
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg hover:shadow-xl'
                  : 'bg-gray-900 text-white hover:bg-gray-800'"
              >
                Commencer maintenant
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="py-16 bg-white">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 mb-12">
          Questions Fréquentes
        </h2>
        <div class="space-y-6">
          <div v-for="(faq, index) in faqs" :key="index" class="border-b border-gray-200 pb-6">
            <button
              @click="toggleFaq(index)"
              class="w-full flex items-center justify-between text-left"
            >
              <h3 class="text-lg font-semibold text-gray-900">{{ faq.question }}</h3>
              <svg
                class="w-5 h-5 text-gray-600 transition-transform"
                :class="{ 'rotate-180': faq.open }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <transition
              enter-active-class="transition-all duration-300 ease-out"
              leave-active-class="transition-all duration-200 ease-in"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-96 opacity-100"
              leave-from-class="max-h-96 opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <p v-show="faq.open" class="mt-4 text-gray-600 overflow-hidden">
                {{ faq.answer }}
              </p>
            </transition>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="bg-gray-900 text-white py-12">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <p class="text-gray-400">© 2024 ESXi Backup Manager. Tous droits réservés.</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import axios from 'axios'

const router = useRouter()
const toast = useToast()

// State
const billingCycle = ref('monthly')
const plans = ref([])
const loading = ref(true)

const faqs = ref([
  {
    question: 'Puis-je changer de plan à tout moment ?',
    answer: 'Oui, vous pouvez upgrader ou downgrader votre plan à tout moment. Les changements prennent effet immédiatement et la facturation est ajustée au prorata.',
    open: false
  },
  {
    question: 'Quelles méthodes de paiement acceptez-vous ?',
    answer: 'Nous acceptons PayPal, MTN Mobile Money et les virements bancaires. Les paiements sont sécurisés et vos données sont protégées.',
    open: false
  },
  {
    question: 'Y a-t-il une période d\'essai gratuite ?',
    answer: 'Oui, nous offrons une période d\'essai de 14 jours sur tous nos plans, sans engagement et sans carte bancaire requise.',
    open: false
  },
  {
    question: 'Que se passe-t-il si je dépasse mes quotas ?',
    answer: 'Vous recevrez une notification avant d\'atteindre vos limites. Vous pouvez alors upgrader votre plan ou supprimer des ressources.',
    open: false
  },
  {
    question: 'Les données sont-elles sécurisées ?',
    answer: 'Absolument. Vos sauvegardes sont chiffrées en transit et au repos. Nous utilisons les mêmes standards de sécurité que les banques.',
    open: false
  }
])

// Methods
const toggleBillingCycle = () => {
  billingCycle.value = billingCycle.value === 'monthly' ? 'yearly' : 'monthly'
}

const formatPrice = (price) => {
  return new Intl.NumberFormat('fr-FR').format(price)
}

const toggleFaq = (index) => {
  faqs.value[index].open = !faqs.value[index].open
}

const selectPlan = (plan) => {
  // Store selected plan in localStorage
  localStorage.setItem('selectedPlan', JSON.stringify({
    ...plan,
    billingCycle: billingCycle.value
  }))

  // Redirect to registration or order page
  router.push('/register')
}

const loadPlans = async () => {
  try {
    loading.value = true
    const response = await axios.get('http://localhost:8000/api/tenants/plans/')
    plans.value = response.data
  } catch (error) {
    console.error('Error loading plans:', error)
    toast.error('Erreur lors du chargement des plans')
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadPlans()
})
</script>

<style scoped>
/* Add any additional custom styles here */
</style>
