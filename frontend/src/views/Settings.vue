<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 p-6">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center gap-3 mb-2">
        <div class="p-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Paramètres</h1>
          <p class="text-gray-600">Configuration des notifications par email</p>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
    </div>

    <!-- Settings Form -->
    <div v-else class="max-w-5xl">
      <form @submit.prevent="saveSettings" class="space-y-6">

        <!-- Email Activation Card -->
        <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-200">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-4">
              <div class="p-3 bg-gradient-to-r from-green-100 to-emerald-100 rounded-xl">
                <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 class="text-lg font-semibold text-gray-900">Activer les notifications par email</h3>
                <p class="text-sm text-gray-600">Recevoir des alertes par email pour les événements importants</p>
              </div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                v-model="settings.email_notifications_enabled"
                type="checkbox"
                class="sr-only peer"
              />
              <div class="w-14 h-8 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-6 peer-checked:after:border-white after:content-[''] after:absolute after:top-1 after:left-1 after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-blue-600 peer-checked:to-purple-600"></div>
            </label>
          </div>
        </div>

        <!-- Administrator Email Card -->
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl shadow-xl p-6 border-2 border-amber-200">
          <div class="flex items-center gap-3 mb-4">
            <div class="p-2 bg-white rounded-lg shadow-md">
              <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 class="text-xl font-bold text-gray-900">Email Administrateur</h2>
          </div>
          <p class="text-sm text-gray-700 mb-4">Adresse email qui recevra toutes les notifications</p>
          <input
            v-model="settings.admin_email"
            type="email"
            required
            class="w-full px-4 py-3 border-2 border-amber-300 bg-white rounded-xl focus:border-amber-500 focus:ring-4 focus:ring-amber-500/20 transition-all outline-none"
            placeholder="admin@example.com"
          />
        </div>

        <!-- SMTP Configuration Card -->
        <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-200">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-2 bg-gradient-to-r from-blue-100 to-purple-100 rounded-lg">
              <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h2 class="text-xl font-bold text-gray-900">Configuration SMTP</h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- SMTP Host -->
            <div>
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                </svg>
                Serveur SMTP
              </label>
              <input
                v-model="settings.smtp_host"
                type="text"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all outline-none"
                placeholder="smtp.gmail.com"
              />
            </div>

            <!-- SMTP Port -->
            <div>
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Port SMTP
              </label>
              <input
                v-model.number="settings.smtp_port"
                type="number"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-500/20 transition-all outline-none"
                placeholder="587"
              />
            </div>

            <!-- SMTP Username -->
            <div>
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Nom d'utilisateur
              </label>
              <input
                v-model="settings.smtp_username"
                type="text"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-500/20 transition-all outline-none"
                placeholder="votre.email@example.com"
              />
            </div>

            <!-- SMTP Password -->
            <div>
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                Mot de passe
              </label>
              <input
                v-model="settings.smtp_password"
                type="password"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-red-500 focus:ring-4 focus:ring-red-500/20 transition-all outline-none"
                placeholder="••••••••"
              />
            </div>

            <!-- TLS/SSL Options -->
            <div class="md:col-span-2 flex gap-6">
              <label class="flex items-center gap-3 cursor-pointer group">
                <input
                  v-model="settings.smtp_use_tls"
                  type="checkbox"
                  class="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                />
                <span class="text-sm font-medium text-gray-700 group-hover:text-blue-600 transition-colors">Utiliser TLS</span>
              </label>
              <label class="flex items-center gap-3 cursor-pointer group">
                <input
                  v-model="settings.smtp_use_ssl"
                  type="checkbox"
                  class="h-5 w-5 text-purple-600 focus:ring-purple-500 border-gray-300 rounded cursor-pointer"
                />
                <span class="text-sm font-medium text-gray-700 group-hover:text-purple-600 transition-colors">Utiliser SSL</span>
              </label>
            </div>

            <!-- From Email -->
            <div class="md:col-span-2">
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Email d'expédition
              </label>
              <input
                v-model="settings.from_email"
                type="email"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20 transition-all outline-none"
                placeholder="noreply@example.com"
              />
            </div>
          </div>
        </div>

        <!-- Notification Preferences Card -->
        <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-200">
          <div class="flex items-center gap-3 mb-6">
            <div class="p-2 bg-gradient-to-r from-purple-100 to-pink-100 rounded-lg">
              <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <h2 class="text-xl font-bold text-gray-900">Préférences de Notification</h2>
          </div>

          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border-2 border-green-200">
              <div class="flex items-center gap-3">
                <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="font-medium text-gray-900">Sauvegardes réussies</span>
              </div>
              <input
                v-model="settings.notify_backup_success"
                type="checkbox"
                class="h-5 w-5 text-green-600 focus:ring-green-500 border-gray-300 rounded cursor-pointer"
              />
            </div>

            <div class="flex items-center justify-between p-4 bg-gradient-to-r from-red-50 to-pink-50 rounded-xl border-2 border-red-200">
              <div class="flex items-center gap-3">
                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="font-medium text-gray-900">Échecs de sauvegarde</span>
              </div>
              <input
                v-model="settings.notify_backup_failure"
                type="checkbox"
                class="h-5 w-5 text-red-600 focus:ring-red-500 border-gray-300 rounded cursor-pointer"
              />
            </div>

            <div class="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200">
              <div class="flex items-center gap-3">
                <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span class="font-medium text-gray-900">Vérifications SureBackup réussies</span>
              </div>
              <input
                v-model="settings.notify_surebackup_success"
                type="checkbox"
                class="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
              />
            </div>

            <div class="flex items-center justify-between p-4 bg-gradient-to-r from-orange-50 to-red-50 rounded-xl border-2 border-orange-200">
              <div class="flex items-center gap-3">
                <svg class="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span class="font-medium text-gray-900">Échecs de vérification SureBackup</span>
              </div>
              <input
                v-model="settings.notify_surebackup_failure"
                type="checkbox"
                class="h-5 w-5 text-orange-600 focus:ring-orange-500 border-gray-300 rounded cursor-pointer"
              />
            </div>

            <div class="flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border-2 border-purple-200">
              <div class="flex items-center gap-3">
                <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                <span class="font-medium text-gray-900">Échecs de réplication</span>
              </div>
              <input
                v-model="settings.notify_replication_failure"
                type="checkbox"
                class="h-5 w-5 text-purple-600 focus:ring-purple-500 border-gray-300 rounded cursor-pointer"
              />
            </div>
          </div>
        </div>

        <!-- Storage Paths Configuration Card -->
        <div class="bg-white rounded-2xl shadow-xl p-6 border-2 border-gray-200">
          <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-gradient-to-r from-indigo-100 to-blue-100 rounded-lg">
                <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
              <h2 class="text-xl font-bold text-gray-900">Emplacements de Sauvegarde</h2>
            </div>
            <button
              type="button"
              @click="showAddPathModal = true"
              class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-semibold rounded-lg hover:from-indigo-700 hover:to-blue-700 transition-all flex items-center gap-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Ajouter
            </button>
          </div>

          <!-- Storage Paths List -->
          <div v-if="loadingPaths" class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
          </div>

          <div v-else-if="storagePaths.length === 0" class="text-center py-8">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <p class="mt-2 text-sm text-gray-600">Aucun emplacement de sauvegarde configuré</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="path in storagePaths"
              :key="path.id"
              class="flex items-center justify-between p-4 rounded-xl border-2 transition-all"
              :class="path.is_default ? 'bg-gradient-to-r from-indigo-50 to-blue-50 border-indigo-300' : 'bg-gray-50 border-gray-200 hover:border-gray-300'"
            >
              <div class="flex items-center gap-3 flex-1">
                <svg class="w-5 h-5" :class="path.is_default ? 'text-indigo-600' : 'text-gray-400'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <div class="flex-1">
                  <p class="font-medium text-gray-900">{{ path.name }}</p>
                  <p class="text-sm text-gray-600 font-mono">{{ path.path }}</p>
                </div>
                <span
                  v-if="path.is_default"
                  class="px-3 py-1 bg-indigo-600 text-white text-xs font-semibold rounded-full"
                >
                  Par défaut
                </span>
              </div>
              <div class="flex items-center gap-2 ml-4">
                <button
                  v-if="!path.is_default"
                  @click="setDefaultPath(path.id)"
                  type="button"
                  class="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  title="Définir par défaut"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                </button>
                <button
                  @click="deletePath(path.id)"
                  type="button"
                  class="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Supprimer"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-4">
          <button
            type="submit"
            :disabled="saving"
            class="flex-1 px-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-purple-700 hover:shadow-lg hover:scale-[1.02] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            <svg v-if="!saving" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <svg v-else class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ saving ? 'Enregistrement...' : 'Enregistrer les paramètres' }}
          </button>

          <button
            type="button"
            @click="sendTestEmail"
            :disabled="testingSMTP || !settings.admin_email"
            class="px-6 py-4 border-2 border-blue-300 text-blue-700 font-semibold rounded-xl hover:bg-blue-50 hover:border-blue-400 hover:shadow-md transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg v-if="!testingSMTP" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <svg v-else class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ testingSMTP ? 'Envoi...' : 'Envoyer un email de test' }}
          </button>
        </div>
      </form>

      <!-- Add Storage Path Modal -->
      <div v-if="showAddPathModal" class="fixed inset-0 bg-gradient-to-br from-gray-900/80 via-gray-900/70 to-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full transform transition-all">
          <!-- Modal Header -->
          <div class="relative px-6 py-4 bg-gradient-to-r from-indigo-600 to-blue-600">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-white/20 backdrop-blur-sm rounded-lg">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
              <h3 class="text-xl font-bold text-white">Ajouter un Emplacement</h3>
            </div>
            <button @click="closePathModal" class="absolute top-4 right-4 p-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg transition-colors">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Modal Body -->
          <form @submit.prevent="addStoragePath" class="p-6 space-y-4">
            <div>
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                Nom de l'emplacement
              </label>
              <input
                v-model="newPath.name"
                type="text"
                required
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20 transition-all outline-none"
                placeholder="Stockage Principal"
              />
            </div>

            <div>
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                Chemin absolu
              </label>
              <input
                v-model="newPath.path"
                type="text"
                required
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all outline-none font-mono text-sm"
                placeholder="/mnt/backups"
              />
            </div>

            <div class="flex items-center gap-3 p-4 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl border-2 border-indigo-200">
              <input
                v-model="newPath.is_default"
                type="checkbox"
                id="path_is_default"
                class="h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer"
              />
              <label for="path_is_default" class="flex-1 flex items-center gap-2 text-sm font-semibold text-gray-900 cursor-pointer">
                <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                Définir comme emplacement par défaut
              </label>
            </div>

            <!-- Modal Footer -->
            <div class="flex gap-3 pt-4">
              <button
                type="button"
                @click="closePathModal"
                class="flex-1 px-4 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 hover:border-gray-400 transition-all"
              >
                Annuler
              </button>
              <button
                type="submit"
                :disabled="savingPath"
                class="flex-1 px-4 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-semibold rounded-xl hover:from-indigo-700 hover:to-blue-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg v-if="!savingPath" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                <svg v-else class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ savingPath ? 'Ajout...' : 'Ajouter' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { emailSettingsAPI, storagePathsAPI } from '../services/api'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const loading = ref(true)
const saving = ref(false)
const testingSMTP = ref(false)

// Storage Paths
const loadingPaths = ref(false)
const savingPath = ref(false)
const showAddPathModal = ref(false)
const storagePaths = ref([])
const newPath = ref({
  name: '',
  path: '',
  is_default: false
})

const settings = ref({
  smtp_host: 'smtp.gmail.com',
  smtp_port: 587,
  smtp_username: '',
  smtp_password: '',
  smtp_use_tls: true,
  smtp_use_ssl: false,
  from_email: '',
  admin_email: '',
  notify_backup_success: false,
  notify_backup_failure: true,
  notify_surebackup_success: true,
  notify_surebackup_failure: true,
  notify_replication_failure: true,
  email_notifications_enabled: false
})

onMounted(async () => {
  await Promise.all([loadSettings(), loadStoragePaths()])
})

async function loadSettings() {
  loading.value = true
  try {
    const response = await emailSettingsAPI.getSettings()
    // API returns an array, get first element
    const data = Array.isArray(response.data) ? response.data[0] : response.data
    if (data) {
      settings.value = { ...settings.value, ...data }
    }
  } catch (error) {
    console.error('Error loading settings:', error)
    toast.error('Erreur lors du chargement des paramètres')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await emailSettingsAPI.updateSettings(settings.value)
    toast.success('Paramètres enregistrés avec succès')
  } catch (error) {
    console.error('Error saving settings:', error)
    toast.error("Erreur lors de l'enregistrement des paramètres")
  } finally {
    saving.value = false
  }
}

async function sendTestEmail() {
  if (!settings.value.admin_email) {
    toast.error('Veuillez spécifier un email administrateur')
    return
  }

  testingSMTP.value = true
  try {
    // Save settings first
    await emailSettingsAPI.updateSettings(settings.value)

    // Send test email
    await emailSettingsAPI.testEmail(settings.value.admin_email)

    toast.success(`Email de test envoyé à ${settings.value.admin_email}`)
  } catch (error) {
    console.error('Error sending test email:', error)
    const errorMessage = error.response?.data?.message || "Erreur lors de l'envoi de l'email de test"
    toast.error(errorMessage)
  } finally {
    testingSMTP.value = false
  }
}

// Storage Paths Functions
async function loadStoragePaths() {
  loadingPaths.value = true
  try {
    const response = await storagePathsAPI.getAll()
    storagePaths.value = response.data.results || response.data
  } catch (error) {
    console.error('Error loading storage paths:', error)
    toast.error('Erreur lors du chargement des emplacements')
  } finally {
    loadingPaths.value = false
  }
}

function closePathModal() {
  showAddPathModal.value = false
  newPath.value = {
    name: '',
    path: '',
    is_default: false
  }
}

async function addStoragePath() {
  savingPath.value = true
  try {
    await storagePathsAPI.create(newPath.value)
    toast.success('Emplacement ajouté avec succès')
    closePathModal()
    await loadStoragePaths()
  } catch (error) {
    console.error('Error adding storage path:', error)
    toast.error("Erreur lors de l'ajout de l'emplacement")
  } finally {
    savingPath.value = false
  }
}

async function setDefaultPath(pathId) {
  try {
    await storagePathsAPI.setDefault(pathId)
    toast.success('Emplacement défini par défaut')
    await loadStoragePaths()
  } catch (error) {
    console.error('Error setting default path:', error)
    toast.error('Erreur lors de la définition par défaut')
  }
}

async function deletePath(pathId) {
  if (!confirm('Êtes-vous sûr de vouloir supprimer cet emplacement ?')) {
    return
  }

  try {
    await storagePathsAPI.delete(pathId)
    toast.success('Emplacement supprimé')
    await loadStoragePaths()
  } catch (error) {
    console.error('Error deleting path:', error)
    toast.error("Erreur lors de la suppression de l'emplacement")
  }
}
</script>

<style scoped>
/* Custom animations for smooth transitions */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bg-white,
.bg-gradient-to-r {
  animation: fadeIn 0.3s ease-out;
}
</style>
