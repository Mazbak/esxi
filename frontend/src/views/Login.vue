<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-900 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full">
      <!-- Card -->
      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <!-- Logo and Title -->
        <div class="text-center mb-8">
          <div class="flex items-center justify-center mb-4">
            <svg class="w-16 h-16 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
          <h2 class="text-3xl font-bold text-gray-900">ESXi Backup Manager</h2>
          <p class="mt-2 text-sm text-gray-600">Connectez-vous pour gérer vos sauvegardes</p>
        </div>

        <!-- Error Alert -->
        <div
          v-if="authStore.error"
          class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start"
        >
          <svg class="w-5 h-5 text-red-600 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-red-800">{{ authStore.error }}</p>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="space-y-6">
          <div>
            <label for="username" class="label">
              Nom d'utilisateur
            </label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              required
              class="input-field"
              placeholder="admin"
            >
          </div>

          <div>
            <label for="password" class="label">
              Mot de passe
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              class="input-field"
              placeholder="••••••••"
            >
          </div>

          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <input
                id="remember"
                v-model="form.remember"
                type="checkbox"
                class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              >
              <label for="remember" class="ml-2 block text-sm text-gray-700">
                Se souvenir de moi
              </label>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authStore.loading"
            class="w-full btn-primary flex items-center justify-center"
            :class="{ 'opacity-50 cursor-not-allowed': authStore.loading }"
          >
            <svg
              v-if="authStore.loading"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ authStore.loading ? 'Connexion...' : 'Se connecter' }}
          </button>
        </form>

        <!-- Info -->
        <div class="mt-6 text-center">
          <p class="text-xs text-gray-500">
            Version 1.0.0 - ESXi Backup Manager
          </p>
        </div>
      </div>

      <!-- Additional info -->
      <div class="mt-8 text-center">
        <p class="text-sm text-white/80">
          Sécurisé avec authentification Django REST Framework
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToastStore()

const form = reactive({
  username: '',
  password: '',
  remember: false
})

async function handleLogin() {
  try {
    const success = await authStore.login({
      username: form.username,
      password: form.password
    })

    if (success) {
      toast.success('Connexion réussie! Bienvenue.')
      router.push('/')
    } else {
      toast.error('Identifiants invalides. Vérifiez votre nom d\'utilisateur et mot de passe.')
    }
  } catch (error) {
    toast.error('Erreur de connexion au serveur. Veuillez réessayer.')
  }
}
</script>
