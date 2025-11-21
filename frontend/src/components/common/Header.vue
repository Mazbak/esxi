<template>
  <header class="bg-white shadow-sm sticky top-0 z-30">
    <div class="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
      <!-- Mobile menu button -->
      <button
        @click="$emit('toggle-sidebar')"
        class="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <!-- Page title -->
      <div class="flex-1 lg:flex-none">
        <h1 class="text-xl font-semibold text-gray-900">{{ pageTitle }}</h1>
      </div>

      <!-- Right side actions -->
      <div class="flex items-center space-x-4">
        <!-- Notifications -->
        <button class="p-2 text-gray-400 hover:text-gray-500 rounded-full hover:bg-gray-100 relative">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span class="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        <!-- Refresh button -->
        <button
          @click="refresh"
          class="p-2 text-gray-400 hover:text-gray-500 rounded-full hover:bg-gray-100"
          :class="{ 'animate-spin': isRefreshing }"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>

        <!-- User menu -->
        <div class="relative">
          <button
            @click="userMenuOpen = !userMenuOpen"
            class="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100"
          >
            <div class="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
              <span class="text-sm font-medium text-white">A</span>
            </div>
          </button>

          <!-- Dropdown menu -->
          <div
            v-if="userMenuOpen"
            v-click-outside="() => userMenuOpen = false"
            class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 ring-1 ring-black ring-opacity-5"
          >
            <router-link
              to="/settings"
              class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              @click="userMenuOpen = false"
            >
              Paramètres
            </router-link>
            <button
              @click="handleLogout"
              class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineEmits(['toggle-sidebar'])

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userMenuOpen = ref(false)
const isRefreshing = ref(false)

const pageTitle = computed(() => {
  const titles = {
    'dashboard': 'Tableau de bord',
    'esxi-servers': 'Serveurs ESXi',
    'virtual-machines': 'Machines Virtuelles',
    'backups': 'Sauvegardes',
    'schedules': 'Planifications',
    'settings': 'Paramètres'
  }
  return titles[route.name] || 'ESXi Backup Manager'
})

async function refresh() {
  isRefreshing.value = true
  // Simulate refresh
  setTimeout(() => {
    isRefreshing.value = false
    window.location.reload()
  }, 1000)
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

// Click outside directive
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value()
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
}
</script>
