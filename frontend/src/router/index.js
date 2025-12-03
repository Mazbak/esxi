import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/pricing',
      name: 'pricing',
      component: () => import('@/views/Pricing.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/components/common/Layout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/Dashboard.vue'),
        },
        {
          path: 'esxi-servers',
          name: 'esxi-servers',
          component: () => import('@/views/ESXiServers.vue'),
        },
        {
          path: 'virtual-machines',
          name: 'virtual-machines',
          component: () => import('@/views/VirtualMachines.vue'),
        },
        {
          path: 'ovf-exports',
          name: 'ovf-exports',
          component: () => import('@/views/OVFExports.vue'),
        },
        {
          path: 'snapshots',
          name: 'snapshots',
          component: () => import('@/views/Snapshots.vue'),
        },
        {
          path: 'restore',
          name: 'restore',
          component: () => import('@/views/Restore.vue'),
        },
        {
          path: 'replication',
          name: 'replication',
          component: () => import('@/views/Replication.vue'),
        },
        {
          path: 'surebackup',
          name: 'surebackup',
          component: () => import('@/views/SureBackup.vue'),
        },
        {
          path: 'schedules',
          name: 'schedules',
          component: () => import('@/views/Schedules.vue'),
        },
        {
          path: 'monitoring',
          name: 'monitoring',
          component: () => import('@/views/Monitoring.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/Settings.vue'),
        },
      ]
    }
  ]
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
