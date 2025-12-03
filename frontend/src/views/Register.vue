<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 py-12">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-4xl font-bold text-gray-900 mb-2">Créer votre compte</h1>
        <p class="text-gray-600">Quelques étapes pour commencer</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Order Form -->
        <div class="lg:col-span-2">
          <div class="bg-white rounded-2xl shadow-xl p-8">
            <!-- Steps Progress -->
            <div class="flex items-center justify-between mb-8">
              <div v-for="(step, index) in steps" :key="index" class="flex items-center flex-1">
                <div class="flex flex-col items-center flex-1">
                  <div
                    class="w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all"
                    :class="currentStep >= index + 1
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-200 text-gray-600'"
                  >
                    {{ index + 1 }}
                  </div>
                  <span class="text-xs mt-2 font-medium" :class="currentStep >= index + 1 ? 'text-indigo-600' : 'text-gray-600'">
                    {{ step }}
                  </span>
                </div>
                <div v-if="index < steps.length - 1" class="flex-1 h-0.5 mx-2" :class="currentStep > index + 1 ? 'bg-indigo-600' : 'bg-gray-200'"></div>
              </div>
            </div>

            <!-- Step 1: Account Info -->
            <div v-show="currentStep === 1">
              <h2 class="text-2xl font-bold text-gray-900 mb-6">Informations du compte</h2>
              <form @submit.prevent="nextStep" class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Nom complet / Entreprise *
                  </label>
                  <input
                    v-model="orderData.customer_name"
                    type="text"
                    required
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                    placeholder="Entreprise XYZ"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Email *
                  </label>
                  <input
                    v-model="orderData.customer_email"
                    type="email"
                    required
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                    placeholder="contact@entreprise.com"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Téléphone
                  </label>
                  <input
                    v-model="orderData.customer_phone"
                    type="tel"
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                    placeholder="237XXXXXXXXX"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Code promo (optionnel)
                  </label>
                  <div class="flex gap-2">
                    <input
                      v-model="couponCode"
                      type="text"
                      class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                      placeholder="PROMO2024"
                      :disabled="couponApplied"
                    />
                    <button
                      v-if="!couponApplied"
                      type="button"
                      @click="validateCoupon"
                      :disabled="!couponCode || validatingCoupon"
                      class="px-6 py-3 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {{ validatingCoupon ? 'Vérification...' : 'Appliquer' }}
                    </button>
                    <button
                      v-else
                      type="button"
                      @click="removeCoupon"
                      class="px-6 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700"
                    >
                      Retirer
                    </button>
                  </div>
                  <p v-if="couponApplied" class="mt-2 text-sm text-green-600">
                    ✓ Code promo appliqué: {{ discount.discount_amount }} XAF de réduction
                  </p>
                </div>

                <button
                  type="submit"
                  class="w-full py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
                >
                  Continuer
                </button>
              </form>
            </div>

            <!-- Step 2: Payment Method -->
            <div v-show="currentStep === 2">
              <h2 class="text-2xl font-bold text-gray-900 mb-6">Méthode de paiement</h2>

              <div class="space-y-4 mb-6">
                <div
                  v-for="method in paymentMethods"
                  :key="method.id"
                  @click="selectedPaymentMethod = method"
                  class="border-2 rounded-xl p-4 cursor-pointer transition-all"
                  :class="selectedPaymentMethod?.id === method.id
                    ? 'border-indigo-600 bg-indigo-50'
                    : 'border-gray-200 hover:border-indigo-300'"
                >
                  <div class="flex items-center gap-4">
                    <div class="flex-shrink-0">
                      <div class="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center">
                        <svg v-if="method.name === 'paypal'" class="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M20.067 8.478c.492.88.556 2.014.3 3.327-.74 3.806-3.276 5.12-6.514 5.12h-.5a.805.805 0 00-.794.68l-.04.22-.63 3.993-.03.168a.804.804 0 01-.793.679H8.318c-.24 0-.418-.216-.377-.453l1.237-7.834h-.09a2.806 2.806 0 01-2.775-3.206L7.934 3.84a.805.805 0 01.793-.68h5.52c2.005 0 3.445.522 4.27 1.55.354.434.603.945.756 1.525.032.125.06.252.083.381.024.132.043.266.057.402l.01.11c.013.125.022.251.027.378.012.287.01.584-.007.894z"/>
                        </svg>
                        <svg v-else-if="method.name === 'mtn_momo'" class="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.31-8.86c-1.77-.45-2.34-.94-2.34-1.67 0-.84.79-1.43 2.1-1.43 1.38 0 1.9.66 1.94 1.64h1.71c-.05-1.34-.87-2.57-2.49-2.97V5H10.9v1.69c-1.51.32-2.72 1.3-2.72 2.81 0 1.79 1.49 2.69 3.66 3.21 1.95.46 2.34 1.15 2.34 1.87 0 .53-.39 1.39-2.1 1.39-1.6 0-2.23-.72-2.32-1.64H8.04c.1 1.7 1.36 2.66 2.86 2.97V19h2.34v-1.67c1.52-.29 2.72-1.16 2.73-2.77-.01-2.2-1.9-2.96-3.66-3.42z"/>
                        </svg>
                        <svg v-else class="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
                        </svg>
                      </div>
                    </div>
                    <div class="flex-1">
                      <h3 class="font-semibold text-gray-900">{{ method.display_name }}</h3>
                      <p class="text-sm text-gray-600">{{ method.description }}</p>
                    </div>
                    <div v-if="selectedPaymentMethod?.id === method.id" class="flex-shrink-0">
                      <svg class="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MTN Phone Number -->
              <div v-if="selectedPaymentMethod?.name === 'mtn_momo'" class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Numéro MTN Mobile Money *
                </label>
                <input
                  v-model="mtnPhoneNumber"
                  type="tel"
                  required
                  class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                  placeholder="237XXXXXXXXX"
                />
              </div>

              <div class="flex gap-4">
                <button
                  type="button"
                  @click="currentStep = 1"
                  class="flex-1 py-3 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
                >
                  Retour
                </button>
                <button
                  @click="createOrder"
                  :disabled="!selectedPaymentMethod || processing"
                  class="flex-1 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {{ processing ? 'Traitement...' : 'Continuer au paiement' }}
                </button>
              </div>
            </div>

            <!-- Step 3: Payment Status -->
            <div v-show="currentStep === 3">
              <div class="text-center py-12">
                <div v-if="paymentStatus === 'pending'" class="space-y-4">
                  <div class="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600"></div>
                  <h2 class="text-2xl font-bold text-gray-900">Paiement en cours...</h2>
                  <p class="text-gray-600">Vérification du paiement. Veuillez patienter.</p>
                </div>

                <div v-else-if="paymentStatus === 'completed'" class="space-y-4">
                  <div class="inline-block w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                    <svg class="w-10 h-10 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <h2 class="text-2xl font-bold text-green-600">Paiement réussi!</h2>
                  <p class="text-gray-600">Votre espace de travail est en cours de création...</p>
                  <p class="text-sm text-gray-500">Vous serez redirigé automatiquement.</p>
                </div>

                <div v-else-if="paymentStatus === 'failed'" class="space-y-4">
                  <div class="inline-block w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
                    <svg class="w-10 h-10 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <h2 class="text-2xl font-bold text-red-600">Paiement échoué</h2>
                  <p class="text-gray-600">{{ paymentError || 'Une erreur est survenue lors du paiement.' }}</p>
                  <button
                    @click="currentStep = 2"
                    class="mt-4 px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700"
                  >
                    Réessayer
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Order Summary -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-2xl shadow-xl p-6 sticky top-6">
            <h2 class="text-xl font-bold text-gray-900 mb-6">Récapitulatif</h2>

            <div v-if="selectedPlan" class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-gray-600">Plan</span>
                <span class="font-semibold text-gray-900">{{ selectedPlan.display_name }}</span>
              </div>

              <div class="flex items-center justify-between">
                <span class="text-gray-600">Cycle de facturation</span>
                <span class="font-semibold text-gray-900">
                  {{ selectedPlan.billingCycle === 'monthly' ? 'Mensuel' : 'Annuel' }}
                </span>
              </div>

              <div class="border-t border-gray-200 pt-4">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-gray-600">Sous-total</span>
                  <span class="font-semibold text-gray-900">
                    {{ formatPrice(getSubtotal()) }} XAF
                  </span>
                </div>

                <div v-if="couponApplied" class="flex items-center justify-between text-green-600 mb-2">
                  <span>Réduction ({{ couponCode }})</span>
                  <span>-{{ formatPrice(discount.discount_amount) }} XAF</span>
                </div>

                <div class="flex items-center justify-between text-lg font-bold text-gray-900 pt-4 border-t border-gray-200">
                  <span>Total</span>
                  <span>{{ formatPrice(getTotal()) }} XAF</span>
                </div>
              </div>

              <!-- Plan Features Summary -->
              <div class="border-t border-gray-200 pt-4 mt-4">
                <p class="text-sm font-semibold text-gray-900 mb-3">Inclus dans votre plan:</p>
                <div class="space-y-2 text-sm text-gray-600">
                  <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>{{ selectedPlan.max_esxi_servers }} serveurs ESXi</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>{{ selectedPlan.max_vms }} machines virtuelles</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>{{ selectedPlan.max_storage_gb }} GB de stockage</span>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="text-center text-gray-500 py-8">
              <p>Aucun plan sélectionné</p>
              <button @click="$router.push('/pricing')" class="mt-4 text-indigo-600 hover:text-indigo-700 font-medium">
                Voir les plans
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import axios from 'axios'

const router = useRouter()
const toast = useToast()

// State
const currentStep = ref(1)
const steps = ['Informations', 'Paiement', 'Confirmation']
const selectedPlan = ref(null)
const paymentMethods = ref([])
const selectedPaymentMethod = ref(null)
const processing = ref(false)
const paymentStatus = ref(null)
const paymentError = ref(null)
const mtnPhoneNumber = ref('')

// Coupon
const couponCode = ref('')
const couponApplied = ref(false)
const validatingCoupon = ref(false)
const discount = ref({})

// Order Data
const orderData = ref({
  customer_name: '',
  customer_email: '',
  customer_phone: '',
  coupon_code: ''
})

const createdOrder = ref(null)

// Computed
const formatPrice = (price) => {
  return new Intl.NumberFormat('fr-FR').format(price)
}

const getSubtotal = () => {
  if (!selectedPlan.value) return 0
  return selectedPlan.value.billingCycle === 'monthly'
    ? selectedPlan.value.monthly_price
    : selectedPlan.value.yearly_price
}

const getTotal = () => {
  const subtotal = getSubtotal()
  const discountAmount = couponApplied.value ? parseFloat(discount.value.discount_amount) : 0
  return subtotal - discountAmount
}

// Methods
const nextStep = () => {
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

const validateCoupon = async () => {
  if (!couponCode.value) return

  validatingCoupon.value = true

  try {
    const response = await axios.post('http://localhost:8000/api/tenants/coupons/validate/', {
      code: couponCode.value,
      order_amount: getSubtotal(),
      plan_id: selectedPlan.value.id
    })

    if (response.data.valid) {
      couponApplied.value = true
      discount.value = response.data
      orderData.value.coupon_code = couponCode.value
      toast.success('Code promo appliqué avec succès!')
    }
  } catch (error) {
    console.error('Coupon validation error:', error)
    toast.error(error.response?.data?.message || 'Code promo invalide')
  } finally {
    validatingCoupon.value = false
  }
}

const removeCoupon = () => {
  couponCode.value = ''
  couponApplied.value = false
  discount.value = {}
  orderData.value.coupon_code = ''
  toast.info('Code promo retiré')
}

const createOrder = async () => {
  processing.value = true

  try {
    // Step 1: Create order
    const orderPayload = {
      plan_id: selectedPlan.value.id,
      billing_cycle: selectedPlan.value.billingCycle,
      customer_name: orderData.value.customer_name,
      customer_email: orderData.value.customer_email,
      customer_phone: orderData.value.customer_phone,
      coupon_code: orderData.value.coupon_code
    }

    const orderResponse = await axios.post('http://localhost:8000/api/tenants/orders/', orderPayload)
    createdOrder.value = orderResponse.data

    // Step 2: Initiate payment
    const paymentPayload = {
      order_id: createdOrder.value.id,
      payment_method_id: selectedPaymentMethod.value.id
    }

    // Add phone number for MTN MoMo
    if (selectedPaymentMethod.value.name === 'mtn_momo') {
      paymentPayload.phone_number = mtnPhoneNumber.value
    }

    // Add return URLs for PayPal
    if (selectedPaymentMethod.value.name === 'paypal') {
      paymentPayload.return_url = `${window.location.origin}/payment/success`
      paymentPayload.cancel_url = `${window.location.origin}/payment/cancel`
    }

    const paymentResponse = await axios.post(
      `http://localhost:8000/api/tenants/orders/${createdOrder.value.id}/initiate_payment/`,
      paymentPayload
    )

    currentStep.value = 3
    paymentStatus.value = 'pending'

    // Handle different payment methods
    if (selectedPaymentMethod.value.name === 'paypal') {
      // Redirect to PayPal
      window.location.href = paymentResponse.data.redirect_url
    } else if (selectedPaymentMethod.value.name === 'mtn_momo') {
      // Show message and poll status
      toast.info('Vérifiez votre téléphone pour confirmer le paiement')
      startPaymentPolling()
    } else if (selectedPaymentMethod.value.name === 'bank_transfer') {
      // Show bank details
      toast.info('Effectuez le virement et téléchargez le reçu')
      // TODO: Show bank details modal
    }

  } catch (error) {
    console.error('Order creation error:', error)
    toast.error(error.response?.data?.error || 'Erreur lors de la création de la commande')
    paymentStatus.value = 'failed'
    paymentError.value = error.response?.data?.error || 'Une erreur est survenue'
  } finally {
    processing.value = false
  }
}

const startPaymentPolling = () => {
  const pollInterval = setInterval(async () => {
    try {
      const response = await axios.post(
        `http://localhost:8000/api/tenants/orders/${createdOrder.value.id}/verify_payment/`
      )

      if (response.data.success && response.data.organization) {
        clearInterval(pollInterval)
        paymentStatus.value = 'completed'
        toast.success('Paiement confirmé! Redirection...')

        // Redirect to login/dashboard
        setTimeout(() => {
          router.push('/login')
        }, 2000)
      }
    } catch (error) {
      console.error('Payment verification error:', error)
      if (error.response?.status === 400) {
        clearInterval(pollInterval)
        paymentStatus.value = 'failed'
        paymentError.value = 'Le paiement a échoué'
      }
    }
  }, 5000) // Poll every 5 seconds

  // Stop polling after 5 minutes
  setTimeout(() => {
    clearInterval(pollInterval)
    if (paymentStatus.value === 'pending') {
      paymentStatus.value = 'failed'
      paymentError.value = 'Délai de paiement dépassé'
    }
  }, 300000)
}

const loadPaymentMethods = async () => {
  try {
    // TODO: Fetch from API
    paymentMethods.value = [
      {
        id: 1,
        name: 'paypal',
        display_name: 'PayPal',
        description: 'Paiement rapide et sécurisé via PayPal',
        is_active: true
      },
      {
        id: 2,
        name: 'mtn_momo',
        display_name: 'MTN Mobile Money',
        description: 'Paiement mobile via MTN MoMo',
        is_active: true
      },
      {
        id: 3,
        name: 'bank_transfer',
        display_name: 'Virement Bancaire',
        description: 'Virement bancaire (vérification manuelle)',
        is_active: true
      }
    ]
  } catch (error) {
    console.error('Error loading payment methods:', error)
  }
}

// Lifecycle
onMounted(() => {
  // Load selected plan from localStorage
  const storedPlan = localStorage.getItem('selectedPlan')
  if (storedPlan) {
    selectedPlan.value = JSON.parse(storedPlan)
  } else {
    router.push('/pricing')
  }

  loadPaymentMethods()
})
</script>

<style scoped>
/* Add any custom styles here */
</style>
