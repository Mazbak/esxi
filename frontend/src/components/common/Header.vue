<template>
  <header class="bg-white/70 backdrop-blur-xl shadow-lg border-b border-gray-200/50 sticky top-0 z-30">
    <div class="flex items-center justify-between h-18 px-4 sm:px-6 lg:px-8">
      <!-- Mobile menu button -->
      <button
        @click="$emit('toggle-sidebar')"
        class="lg:hidden p-3 rounded-xl text-gray-600 hover:text-blue-600 hover:bg-blue-50 transition-all duration-300 hover:scale-110"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <!-- Page title -->
      <div class="flex-1 lg:flex-none">
        <h1 class="text-2xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-800 bg-clip-text text-transparent">
          {{ pageTitle }}
        </h1>
      </div>

      <!-- Right side actions -->
      <div class="flex items-center space-x-2">
        <!-- Notifications -->
        <button class="relative p-3 text-gray-600 hover:text-blue-600 rounded-xl hover:bg-blue-50 transition-all duration-300 hover:scale-110 group">
          <svg class="w-6 h-6 transition-transform duration-300 group-hover:rotate-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span class="absolute top-2 right-2 flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-gradient-to-r from-red-500 to-pink-500 shadow-lg"></span>
          </span>
        </button>

        <!-- Refresh button -->
        <button
          @click="refresh"
          class="p-3 text-gray-600 hover:text-green-600 rounded-xl hover:bg-green-50 transition-all duration-300 hover:scale-110 group"
          :class="{ 'animate-spin': isRefreshing }"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>

        <!-- Search button -->
        <button class="p-3 text-gray-600 hover:text-purple-600 rounded-xl hover:bg-purple-50 transition-all duration-300 hover:scale-110 group">
          <svg class="w-6 h-6 transition-transform duration-300 group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>

        <!-- User menu -->
        <div class="relative ml-2">
          <button
            @click="userMenuOpen = !userMenuOpen"
            class="flex items-center space-x-3 p-2 pl-3 pr-4 rounded-xl hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all duration-300 hover:shadow-lg group"
          >
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg group-hover:shadow-blue-500/50 transition-all duration-300 group-hover:scale-110">
              <span class="text-sm font-bold text-white">{{ userInitials }}</span>
            </div>
            <div class="hidden md:block text-left">
              <p class="text-sm font-semibold text-gray-900">{{ username }}</p>
              <p class="text-xs text-gray-500">Administrateur</p>
            </div>
            <svg class="w-5 h-5 text-gray-400 transition-transform duration-300" :class="{ 'rotate-180': userMenuOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Dropdown menu with modern design -->
          <transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="opacity-0 scale-95 -translate-y-2"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="opacity-100 scale-100 translate-y-0"
            leave-to-class="opacity-0 scale-95 -translate-y-2"
          >
            <div
              v-if="userMenuOpen"
              v-click-outside="() => userMenuOpen = false"
              class="absolute right-0 mt-3 w-64 bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl py-2 ring-1 ring-gray-200/50 border border-gray-100 animate-slide-down"
            >
              <!-- User info header -->
              <div class="px-4 py-3 border-b border-gray-100">
                <p class="text-sm font-semibold text-gray-900">{{ username }}</p>
                <p class="text-xs text-gray-500 mt-1">{{ userEmail }}</p>
              </div>

              <!-- Menu items -->
              <div class="py-2">
                <router-link
                  to="/settings"
                  class="flex items-center px-4 py-3 text-sm text-gray-700 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all duration-200 group"
                  @click="userMenuOpen = false"
                >
                  <svg class="w-5 h-5 mr-3 text-gray-400 group-hover:text-blue-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span class="font-medium">Paramètres</span>
                </router-link>

                <router-link
                  to="/admin"
                  class="flex items-center px-4 py-3 text-sm text-indigo-600 hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 transition-all duration-200 font-semibold group"
                  @click="userMenuOpen = false"
                >
                  <svg class="w-5 h-5 mr-3 text-indigo-500 group-hover:text-indigo-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>Administration</span>
                </router-link>
              </div>

              <!-- Logout button -->
              <div class="pt-2 border-t border-gray-100">
                <button
                  @click="handleLogout"
                  class="w-full flex items-center px-4 py-3 text-sm text-red-600 hover:bg-gradient-to-r hover:from-red-50 hover:to-pink-50 transition-all duration-200 font-semibold group"
                >
                  <svg class="w-5 h-5 mr-3 text-red-500 group-hover:rotate-12 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>Déconnexion</span>
                </button>
              </div>
            </div>
          </transition>
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

const username = computed(() => authStore.user?.username || 'Admin')
const userEmail = computed(() => authStore.user?.email || 'admin@esxi.local')
const userInitials = computed(() => {
  const name = username.value
  return name.charAt(0).toUpperCase()
})

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
