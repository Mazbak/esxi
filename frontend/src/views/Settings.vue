<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Paramètres</h1>
      <p class="mt-1 text-sm text-gray-500">Configuration de l'application</p>
    </div>

    <!-- General Settings -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Paramètres généraux</h2>
      <div class="space-y-4">
        <div>
          <label class="label">Répertoire de sauvegarde par défaut</label>
          <input
            v-model="settings.defaultBackupLocation"
            type="text"
            class="input-field"
            placeholder="/mnt/backup_esxi"
          >
          <p class="mt-1 text-sm text-gray-500">
            Emplacement par défaut pour les nouvelles sauvegardes
          </p>
        </div>

        <div>
          <label class="label">Rétention des sauvegardes (jours)</label>
          <input
            v-model.number="settings.retentionDays"
            type="number"
            class="input-field"
            placeholder="30"
          >
          <p class="mt-1 text-sm text-gray-500">
            Nombre de jours de conservation des sauvegardes
          </p>
        </div>

        <div class="flex items-center">
          <input
            v-model="settings.autoStartBackups"
            type="checkbox"
            id="autoStart"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          >
          <label for="autoStart" class="ml-2 block text-sm text-gray-700">
            Démarrer automatiquement les nouvelles sauvegardes
          </label>
        </div>

        <div class="flex items-center">
          <input
            v-model="settings.emailNotifications"
            type="checkbox"
            id="emailNotif"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          >
          <label for="emailNotif" class="ml-2 block text-sm text-gray-700">
            Activer les notifications par email
          </label>
        </div>
      </div>

      <div class="mt-6">
        <button @click="saveSettings" class="btn-primary">
          Enregistrer les paramètres
        </button>
      </div>
    </div>

    <!-- About -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">À propos</h2>
      <div class="space-y-3 text-sm">
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Application</span>
          <span class="font-medium text-gray-900">ESXi Backup Manager</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Version</span>
          <span class="font-medium text-gray-900">1.0.0</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Backend</span>
          <span class="font-medium text-gray-900">Django + Django REST Framework</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-gray-600">Frontend</span>
          <span class="font-medium text-gray-900">Vue.js 3 + Tailwind CSS</span>
        </div>
      </div>
    </div>

    <!-- Danger Zone -->
    <div class="card border-2 border-red-200">
      <h2 class="text-lg font-semibold text-red-900 mb-4">Zone dangereuse</h2>
      <p class="text-sm text-gray-600 mb-4">
        Actions irréversibles qui nécessitent une confirmation
      </p>
      <button class="btn-danger">
        Réinitialiser toutes les données
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const settings = reactive({
  defaultBackupLocation: '/mnt/backup_esxi',
  retentionDays: 30,
  autoStartBackups: true,
  emailNotifications: false
})

function saveSettings() {
  try {
    // TODO: Implement actual save logic
    // await settingsAPI.save(settings)
    toast.success('Paramètres enregistrés avec succès')
  } catch (err) {
    toast.error(`Erreur lors de l'enregistrement: ${err.message}`)
  }
}
</script>
