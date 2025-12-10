<template>
  <!-- Mobile sidebar overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-40 lg:hidden animate-fade-in"
    @click="$emit('close')"
  >
    <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm"></div>
  </div>

  <!-- Sidebar -->
  <div
    :class="[
      'fixed inset-y-0 left-0 z-50 w-72 bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 transform transition-all duration-500 ease-in-out lg:translate-x-0 shadow-2xl',
      isOpen ? 'translate-x-0' : '-translate-x-full'
    ]"
  >
    <div class="flex flex-col h-full relative">
      <!-- Decorative background -->
      <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAxMCAwIEwgMCAwIDAgMTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-40"></div>

      <!-- Logo -->
      <div class="relative flex items-center justify-center h-20 px-6 border-b border-white/10">
        <div class="flex items-center space-x-3 group">
          <div class="p-2.5 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg group-hover:shadow-blue-500/50 transition-all duration-300 group-hover:scale-110">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
              ESXi Backup
            </h1>
            <p class="text-xs text-blue-300/70">Pro Edition</p>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto scrollbar-modern relative">
        <router-link
          v-for="item in navigation"
          :key="item.name"
          :to="item.path"
          class="group relative flex items-center px-4 py-3.5 text-sm font-medium rounded-xl transition-all duration-300 overflow-hidden"
          :class="isActiveRoute(item.path)
            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/30'
            : 'text-blue-100/80 hover:text-white hover:bg-white/10'"
          @click="$emit('close')"
        >
          <!-- Active indicator -->
          <div v-if="isActiveRoute(item.path)" class="absolute inset-0 bg-gradient-to-r from-blue-400/20 to-indigo-400/20 animate-pulse-slow"></div>

          <!-- Icon -->
          <div class="relative z-10 flex-shrink-0 mr-3.5 transition-transform duration-300 group-hover:scale-110">
            <component :is="item.icon" class="w-5 h-5" />
          </div>

          <!-- Text -->
          <span class="relative z-10 flex-1">{{ item.name }}</span>

          <!-- Arrow indicator for active route -->
          <svg v-if="isActiveRoute(item.path)" class="relative z-10 w-4 h-4 ml-auto animate-fade-in" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>

          <!-- Hover effect -->
          <div class="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        </router-link>
      </nav>

      <!-- User section -->
      <div class="relative px-4 py-5 border-t border-white/10 bg-black/20">
        <!-- User info -->
        <div class="flex items-center mb-4 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all duration-300 group cursor-pointer">
          <div class="flex-shrink-0">
            <div class="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg group-hover:shadow-blue-500/50 transition-all duration-300 group-hover:scale-110">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          </div>
          <div class="ml-3 flex-1 min-w-0">
            <p class="text-sm font-semibold text-white truncate">{{ username }}</p>
            <p class="text-xs text-blue-300/70">Administrateur</p>
          </div>
          <svg class="w-5 h-5 text-blue-300/50 group-hover:text-blue-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
          </svg>
        </div>

        <!-- Logout button -->
        <button
          @click="handleLogout"
          class="w-full flex items-center justify-center px-4 py-3 text-sm font-semibold text-white bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-red-500/30 hover:scale-105 group"
        >
          <svg class="w-5 h-5 mr-2 group-hover:rotate-12 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Déconnexion
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close'])

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || 'Admin')

async function handleLogout() {
  try {
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    console.error('Erreur lors de la déconnexion:', error)
  }
}

const navigation = [
  {
    name: 'Tableau de bord',
    path: '/',
    icon: 'IconDashboard'
  },
  {
    name: 'Serveurs ESXi',
    path: '/esxi-servers',
    icon: 'IconServer'
  },
  {
    name: 'Machines Virtuelles',
    path: '/virtual-machines',
    icon: 'IconVM'
  },
  {
    name: 'Sauvegardes',
    path: '/ovf-exports',
    icon: 'IconBackup'
  },
  {
    name: 'Snapshots',
    path: '/snapshots',
    icon: 'IconSnapshot'
  },
  {
    name: 'Restauration',
    path: '/restore',
    icon: 'IconRestore'
  },
  {
    name: 'Réplication',
    path: '/replication',
    icon: 'IconReplication'
  },
  {
    name: 'SureBackup',
    path: '/surebackup',
    icon: 'IconSureBackup'
  },
  {
    name: 'Planifications',
    path: '/schedules',
    icon: 'IconCalendar'
  },
  {
    name: 'Monitoring',
    path: '/monitoring',
    icon: 'IconMonitoring'
  },
  {
    name: 'Paramètres',
    path: '/settings',
    icon: 'IconSettings'
  }
]

function isActiveRoute(path) {
  return route.path === path
}

// Icon components (inline SVG)
const IconDashboard = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>`
}

const IconServer = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
  </svg>`
}

const IconVM = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
  </svg>`
}

const IconBackup = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>`
}

const IconSnapshot = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>`
}

const IconCalendar = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>`
}

const IconRestore = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>`
}

const IconMonitoring = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>`
}

const IconSettings = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>`
}

const IconReplication = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>`
}

const IconSureBackup = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>`
}
</script>
