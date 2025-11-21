import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('authToken') || null)
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(credentials) {
    loading.value = true
    error.value = null
    try {
      const response = await authAPI.login(credentials)
      token.value = response.data.token
      user.value = response.data.user
      localStorage.setItem('authToken', response.data.token)
      return true
    } catch (err) {
      error.value = err.response?.data?.message || 'Échec de la connexion'
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authAPI.logout()
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      token.value = null
      user.value = null
      localStorage.removeItem('authToken')
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    try {
      const response = await authAPI.getCurrentUser()
      user.value = response.data
    } catch (err) {
      console.error('Failed to fetch user:', err)
      await logout()
    }
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    fetchCurrentUser,
  }
})
