<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">🔄 Réplication VM</h1>
        <p class="mt-1 text-sm text-gray-500">Configurez la réplication et le failover automatique entre serveurs ESXi</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvelle Réplication
      </button>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-blue-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Total Réplications</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ replications.length }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-green-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Actives</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ activeCount }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-yellow-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">En Cours</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ inProgressCount }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-red-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Total Failovers</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ failoverEvents.length }}</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>

    <!-- Progress Display -->
    <div v-if="replicatingId" class="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <svg class="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <div>
              <p class="text-base font-semibold text-blue-900">Réplication en cours...</p>
              <p class="text-sm text-blue-700 mt-1">{{ replicationMessage }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-3xl font-bold text-blue-600">{{ replicationProgress }}%</span>
            <button
              @click="cancelReplication"
              class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Arrêter
            </button>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="w-full bg-blue-200 rounded-full h-4 overflow-hidden shadow-inner">
          <div
            class="bg-gradient-to-r from-blue-500 to-indigo-600 h-4 rounded-full transition-all duration-300 ease-out shadow-lg"
            :style="{ width: replicationProgress + '%' }"
          ></div>
        </div>

        <!-- Progress Details -->
        <div class="flex items-center justify-between text-sm text-blue-800">
          <span class="font-medium">{{ replications.find(r => r.id === replicatingId)?.vm_name }}</span>
          <span class="capitalize">{{ replicationStatus }}</span>
        </div>
      </div>
    </div>

    <!-- Replication List -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Réplications Configurées</h2>

      <!-- Skeleton Loader -->
      <div v-if="loading" class="space-y-4 animate-pulse">
        <div v-for="i in 3" :key="i" class="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
          <div class="flex-1 space-y-3">
            <div class="h-4 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-3/4"></div>
            <div class="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-1/2"></div>
          </div>
          <div class="flex space-x-2">
            <div class="h-8 w-8 bg-gradient-to-r from-blue-200 to-blue-300 rounded-full"></div>
            <div class="h-8 w-8 bg-gradient-to-r from-orange-200 to-orange-300 rounded-full"></div>
            <div class="h-8 w-8 bg-gradient-to-r from-indigo-200 to-indigo-300 rounded-full"></div>
          </div>
        </div>
      </div>

      <div v-else-if="replications.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">Aucune réplication</h3>
        <p class="mt-1 text-sm text-gray-500">Commencez par créer une nouvelle réplication</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8"></th>
              <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM</th>
              <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Master ⇄ Slave</th>
              <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Info Synchronisation</th>
              <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <template v-for="replication in replications" :key="replication.id">
              <!-- Main Row -->
              <tr class="hover:bg-gray-50 transition-colors">
                <!-- Expand Button -->
                <td class="px-4 py-4 whitespace-nowrap text-center">
                  <button
                    @click="toggleRowExpansion(replication.id)"
                    class="text-gray-400 hover:text-gray-600 focus:outline-none"
                    title="Voir l'historique"
                  >
                    <svg class="w-5 h-5 transition-transform" :class="{'rotate-90': expandedRows.has(replication.id)}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </td>

                <!-- VM Info -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900">{{ replication.vm_name }}</div>
                  <div class="text-sm text-gray-500">{{ replication.name }}</div>
                  <div class="text-xs text-gray-400 mt-1">{{ replication.replication_interval_minutes }} min</div>
                </td>

                <!-- Master/Slave States -->
                <td class="px-4 py-4">
                  <div v-if="vmStates[replication.id]" class="space-y-2">
                    <!-- Master (Source) -->
                    <div class="flex items-center gap-2 text-sm">
                      <span class="font-medium text-blue-600">🖥️ Master:</span>
                      <span class="text-gray-700">{{ replication.source_server_name }}</span>
                      <span v-if="vmStates[replication.id].source_vm">
                        {{ getPowerStateIcon(vmStates[replication.id].source_vm.power_state) }}
                        <span class="text-xs text-gray-500">
                          {{ getPowerStateText(vmStates[replication.id].source_vm.power_state) }}
                        </span>
                      </span>
                    </div>
                    <!-- Slave (Destination) -->
                    <div class="flex items-center gap-2 text-sm">
                      <span class="font-medium text-purple-600">🔄 Slave:</span>
                      <span class="text-gray-700">{{ replication.destination_server_name }}</span>
                      <span v-if="vmStates[replication.id].destination_vm && vmStates[replication.id].destination_vm.exists">
                        {{ getPowerStateIcon(vmStates[replication.id].destination_vm.power_state) }}
                        <span class="text-xs text-gray-500">
                          {{ getPowerStateText(vmStates[replication.id].destination_vm.power_state) }}
                        </span>
                      </span>
                      <span v-else class="text-xs text-orange-500">⚠️ Pas encore répliquée</span>
                    </div>
                    <div class="text-xs text-gray-400">{{ replication.destination_datastore }}</div>
                  </div>
                  <div v-else class="flex items-center gap-2 text-sm text-gray-400">
                    <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Chargement états...
                  </div>
                </td>

                <!-- Sync Info -->
                <td class="px-4 py-4">
                  <div class="space-y-1">
                    <!-- Syncing Indicator with Progress -->
                    <div v-if="isSyncing(replication)" class="flex items-center gap-2 text-xs mb-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5">
                      <svg class="animate-spin h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span class="font-semibold text-blue-700">
                        🔄 Synchronisation en cours...
                        <span class="text-blue-900 ml-1">{{ getSyncProgress(replication.id) }}%</span>
                      </span>
                    </div>

                    <!-- Last Sync -->
                    <div class="flex items-center gap-2 text-xs">
                      <span class="text-gray-500">Dernier sync:</span>
                      <span class="font-medium text-gray-700">{{ formatRelativeTime(replication.last_replication_at) }}</span>
                    </div>

                    <!-- Next Sync with Countdown -->
                    <div v-if="replication.is_active && getNextSyncCountdown(replication)" class="flex items-center gap-2 text-xs">
                      <span class="text-gray-500">Prochain sync:</span>
                      <span class="font-medium" :class="getNextSyncCountdown(replication).color">
                        {{ getNextSyncCountdown(replication).text }}
                      </span>
                      <svg v-if="getNextSyncCountdown(replication).isImminent" class="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                      </svg>
                    </div>
                    <div v-else-if="!replication.is_active" class="text-xs text-gray-400">
                      ⏸️ Désactivée
                    </div>

                    <!-- Duration if available -->
                    <div v-if="replication.last_replication_duration_seconds" class="text-xs text-gray-500">
                      <span class="text-gray-400">Durée dernière sync:</span>
                      <span class="font-medium ml-1">⏱️ {{ formatDuration(replication.last_replication_duration_seconds) }}</span>
                    </div>
                  </div>
                </td>

                <!-- Status -->
                <td class="px-4 py-4 whitespace-nowrap">
                  <span :class="getStatusClass(replication.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                    {{ replication.status_display }}
                  </span>

                  <!-- Failover Status -->
                  <div class="mt-1 space-y-1">
                    <div v-if="replication.failover_active" class="flex items-center gap-1">
                      <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                        ⚡ Failover Actif
                      </span>
                    </div>
                    <div v-else-if="replication.failover_mode === 'automatic'">
                      <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        ✅ Normal (Auto)
                      </span>
                    </div>
                    <div v-else-if="replication.failover_mode === 'manual'">
                      <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-700">
                        🔧 Manuel
                      </span>
                    </div>
                  </div>
                </td>

                <!-- Actions -->
                <td class="px-4 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  <button
                    @click="startReplication(replication)"
                    :disabled="!replication.is_active || replicatingId === replication.id"
                    class="text-blue-600 hover:text-blue-900 disabled:text-gray-400 transition-all relative"
                    :class="{'animate-pulse': replicatingId === replication.id}"
                    title="Démarrer la réplication"
                  >
                    <svg v-if="replicatingId === replication.id" class="w-5 h-5 inline animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <svg v-else class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </button>
                  <!-- Failover button (only if failover NOT active) -->
                  <button
                    v-if="!replication.failover_active"
                    @click="showFailoverModal(replication)"
                    :disabled="!replication.is_active"
                    class="text-orange-600 hover:text-orange-900 disabled:text-gray-400"
                    title="Failover manuel"
                  >
                    <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </button>

                  <!-- Failback button (only if failover IS active) -->
                  <button
                    v-if="replication.failover_active"
                    @click="triggerFailback(replication)"
                    class="text-green-600 hover:text-green-900"
                    title="Failback - Retour à la normale"
                  >
                    <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                    </svg>
                  </button>

                  <button
                    @click="editReplication(replication)"
                    class="text-indigo-600 hover:text-indigo-900"
                    title="Modifier"
                  >
                    <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    @click="deleteReplication(replication)"
                    class="text-red-600 hover:text-red-900"
                    title="Supprimer"
                  >
                    <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </td>
              </tr>

              <!-- Expandable History Row -->
              <tr v-if="expandedRows.has(replication.id)" class="bg-gray-50">
                <td colspan="6" class="px-4 py-4">
                  <div class="bg-white rounded-lg shadow p-4 border border-gray-200">
                    <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Historique des réplications
                    </h4>

                    <!-- Loading State -->
                    <div v-if="loadingHistory.has(replication.id)" class="flex items-center justify-center py-4 text-gray-400">
                      <svg class="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Chargement de l'historique...
                    </div>

                    <!-- History Table -->
                    <div v-else-if="replicationHistory[replication.id] && replicationHistory[replication.id].length > 0" class="overflow-x-auto">
                      <table class="min-w-full divide-y divide-gray-200 text-sm">
                        <thead class="bg-gray-100">
                          <tr>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date/Heure</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Durée</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Taille</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
                          </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-100">
                          <tr v-for="log in replicationHistory[replication.id]" :key="log.id" class="hover:bg-gray-50">
                            <td class="px-3 py-2 whitespace-nowrap text-xs text-gray-600">
                              {{ formatDateTime(log.started_at) }}
                            </td>
                            <td class="px-3 py-2 whitespace-nowrap">
                              <span :class="getStatusClass(log.status)" class="px-2 py-1 text-xs font-semibold rounded">
                                {{ log.status_display }}
                              </span>
                            </td>
                            <td class="px-3 py-2 whitespace-nowrap text-xs text-gray-600">
                              {{ formatDuration(log.duration_seconds) }}
                            </td>
                            <td class="px-3 py-2 whitespace-nowrap text-xs text-gray-600">
                              {{ log.replicated_size_mb > 0 ? `${log.replicated_size_mb.toFixed(0)} MB` : '-' }}
                            </td>
                            <td class="px-3 py-2 whitespace-nowrap text-xs">
                              <span :class="log.triggered_by === 'automatic' ? 'text-blue-600' : 'text-purple-600'">
                                {{ log.triggered_by === 'automatic' ? '🤖 Auto' : '👤 Manuel' }}
                              </span>
                            </td>
                            <td class="px-3 py-2 text-xs text-gray-600 max-w-xs truncate" :title="log.message">
                              {{ log.message || '-' }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <!-- Empty State -->
                    <div v-else class="text-center py-4 text-gray-400 text-sm">
                      📋 Aucun historique de réplication disponible
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Failover Events History -->
    <div class="card" v-if="failoverEvents.length > 0">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Historique des Failovers</h2>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Déclenché par</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="event in failoverEvents.slice(0, 5)" :key="event.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ event.vm_name }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ event.failover_type_display }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getFailoverStatusClass(event.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ event.status_display }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ event.triggered_by_username || 'Système' }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDateTime(event.started_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create/Edit Modal - Modern Design -->
    <div v-if="showCreateModal || editingReplication" class="fixed inset-0 bg-gradient-to-br from-gray-900/80 via-gray-900/70 to-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
      <div class="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden transform transition-all animate-slide-up">
        <!-- Modern Header with Gradient -->
        <div class="relative px-8 py-6 bg-gradient-to-r from-blue-600 via-blue-500 to-purple-600 overflow-hidden">
          <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-10"></div>
          <div class="relative flex items-center gap-4">
            <div class="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
              <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            </div>
            <div>
              <h3 class="text-2xl font-bold text-white">
                {{ editingReplication ? 'Modifier la Réplication' : 'Nouvelle Réplication' }}
              </h3>
              <p class="text-blue-100 text-sm mt-1">Configurez la réplication entre vos serveurs ESXi</p>
            </div>
          </div>
          <button @click="closeModal" class="absolute top-6 right-6 p-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg transition-colors">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Form Content with Beautiful Spacing -->
        <div class="px-8 py-6 space-y-6 overflow-y-auto max-h-[calc(90vh-180px)] custom-scrollbar">
          <!-- Nom du replication -->
          <div class="group">
            <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              Nom de la réplication
            </label>
            <input
              v-model="form.name"
              type="text"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all outline-none text-gray-900 placeholder-gray-400"
              placeholder="Ex: Réplication WebServer Prod"
            />
          </div>

          <!-- Machine Virtuelle -->
          <div class="group">
            <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <svg class="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
              Machine Virtuelle
            </label>
            <div class="relative">
              <select
                v-model="form.virtual_machine"
                class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer"
                :class="{'border-amber-400 bg-amber-50': virtualMachines.length === 0}"
              >
                <option value="">{{ virtualMachines.length === 0 ? 'Aucune VM disponible - Ajoutez un serveur ESXi' : 'Sélectionner une VM...' }}</option>
                <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">{{ vm.name }}</option>
              </select>
              <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
            <p v-if="virtualMachines.length === 0" class="mt-2 text-xs text-amber-600 flex items-center gap-1">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
              Ajoutez d'abord un serveur ESXi et synchronisez les VMs dans le menu Serveurs ESXi
            </p>
          </div>

          <!-- Serveur Destination -->
          <div class="group">
            <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <svg class="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
              Serveur Destination
            </label>
            <div class="relative">
              <select
                v-model="form.destination_server"
                class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-4 focus:ring-orange-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer"
                :class="{'border-amber-400 bg-amber-50': availableDestinationServers.length === 0}"
              >
                <option value="">{{ availableDestinationServers.length === 0 ? 'Aucun serveur disponible' : 'Sélectionner le serveur de destination...' }}</option>
                <option v-for="server in availableDestinationServers" :key="server.id" :value="server.id">{{ server.name }} ({{ server.host }})</option>
              </select>
              <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
            <p v-if="selectedVM" class="mt-2 text-xs text-blue-600 flex items-center gap-1">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
              La VM sera répliquée depuis {{ selectedVM.server_name }} vers le serveur sélectionné
            </p>
          </div>

          <!-- Alert if no servers -->
          <div v-if="esxiServers.length < 2" class="bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-amber-500 rounded-lg p-4">
            <div class="flex items-start gap-3">
              <svg class="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
              <div>
                <h4 class="text-sm font-semibold text-amber-900 mb-1">Serveurs insuffisants</h4>
                <p class="text-sm text-amber-800">Vous devez avoir au moins deux serveurs ESXi pour pouvoir répliquer une VM d'un serveur vers un autre.</p>
              </div>
            </div>
          </div>

          <!-- Datastore Destination -->
          <div class="group">
            <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              Datastore Destination
            </label>
            <div class="relative">
              <select
                v-model="form.destination_datastore"
                class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer"
                :class="{'border-amber-400 bg-amber-50': !form.destination_server || loadingDatastores, 'animate-pulse': loadingDatastores}"
                :disabled="!form.destination_server || loadingDatastores"
              >
                <option value="">
                  {{ !form.destination_server ? 'Sélectionnez d\'abord un serveur' :
                     loadingDatastores ? '⏳ Chargement des datastores...' :
                     destinationDatastores.length === 0 ? 'Aucun datastore disponible' :
                     'Sélectionner un datastore...' }}
                </option>
                <option v-for="ds in destinationDatastores" :key="ds.name" :value="ds.name">
                  {{ ds.name }} - {{ formatDatastoreInfo(ds) }}
                </option>
              </select>
              <!-- Loading spinner -->
              <svg v-if="loadingDatastores" class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-indigo-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <!-- Dropdown arrow -->
              <svg v-else class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
            <p v-if="form.destination_server && !loadingDatastores && selectedDatastore" class="mt-2 text-xs text-indigo-600 flex items-center gap-1">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
              Capacité: {{ selectedDatastore.capacity_gb }}GB | Libre: {{ selectedDatastore.free_space_gb }}GB ({{ selectedDatastore.free_percent }}%)
            </p>
          </div>

          <!-- Intervalle et Mode -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Intervalle -->
            <div class="group">
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Intervalle entre les synchronisations (minutes)
              </label>
              <input
                v-model.number="form.replication_interval_minutes"
                type="number"
                min="15"
                step="15"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all outline-none text-gray-900"
              />
            </div>

            <!-- Mode Failover -->
            <div class="group">
              <label class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Mode de Failover
              </label>
              <div class="relative">
                <select
                  v-model="form.failover_mode"
                  class="w-full px-4 py-3 pr-10 border-2 border-gray-200 rounded-xl focus:border-red-500 focus:ring-4 focus:ring-red-500/20 transition-all outline-none text-gray-900 appearance-none bg-white cursor-pointer"
                >
                  <option value="manual">Manuel</option>
                  <option value="automatic">Automatique</option>
                </select>
                <svg class="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Auto-Failover Threshold (conditional) -->
          <div v-if="form.failover_mode === 'automatic'" class="group bg-gradient-to-br from-red-50 to-orange-50 border-2 border-red-200 rounded-xl p-4">
            <label class="flex items-center gap-2 text-sm font-semibold text-red-800 mb-2">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Seuil Auto-Failover (minutes)
            </label>
            <input
              v-model.number="form.auto_failover_threshold_minutes"
              type="number"
              min="5"
              class="w-full px-4 py-3 border-2 border-red-300 bg-white rounded-xl focus:border-red-500 focus:ring-4 focus:ring-red-500/20 transition-all outline-none text-gray-900"
            />
            <p class="mt-2 text-xs text-red-700 flex items-center gap-1">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
              Temps d'indisponibilité avant déclenchement automatique du failover
            </p>
          </div>

          <!-- Activer la réplication -->
          <div class="flex items-center gap-3 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200">
            <input
              v-model="form.is_active"
              type="checkbox"
              id="is_active"
              class="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
            />
            <label for="is_active" class="flex-1 flex items-center gap-2 text-sm font-semibold text-gray-900 cursor-pointer">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Activer la réplication immédiatement
            </label>
          </div>
        </div>

        <!-- Modern Footer with Gradient Buttons -->
        <div class="px-8 py-6 bg-gradient-to-r from-gray-50 to-gray-100 border-t border-gray-200 flex justify-end gap-3">
          <button
            @click="closeModal"
            class="px-6 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-white hover:border-gray-400 hover:shadow-md transition-all duration-200 flex items-center gap-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Annuler
          </button>
          <button
            @click="saveReplication"
            class="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-purple-700 hover:shadow-lg hover:scale-[1.02] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            :disabled="saving"
          >
            <svg v-if="!saving" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <svg v-else class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Failover Confirmation Modal -->
    <div v-if="showFailoverConfirmModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900">⚡ Déclencher le Failover</h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <p class="text-sm text-gray-600">
            Vous êtes sur le point de basculer la VM <strong>{{ selectedReplication?.vm_name }}</strong>
            vers le serveur de destination <strong>{{ selectedReplication?.destination_server_name }}</strong>.
          </p>
          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm text-yellow-700">Cette opération va arrêter la VM source et démarrer la VM destination.</p>
              </div>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Raison du failover</label>
            <textarea v-model="failoverReason" rows="3" class="input" placeholder="Décrire la raison du failover..."></textarea>
          </div>
          <div class="flex items-center">
            <input v-model="failoverTestMode" type="checkbox" id="test_mode" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
            <label for="test_mode" class="ml-2 block text-sm text-gray-900">Mode test (ne pas arrêter la VM source)</label>
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3">
          <button @click="showFailoverConfirmModal = false" class="btn-secondary">Annuler</button>
          <button @click="performFailover" class="btn-danger" :disabled="saving">
            {{ saving ? 'Failover en cours...' : 'Confirmer le Failover' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Snapshot Warning Modal - Modern Design -->
    <div v-if="showSnapshotModal" class="fixed inset-0 bg-gradient-to-br from-gray-900/90 via-purple-900/80 to-blue-900/90 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-fade-in">
      <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden transform transition-all animate-slide-up">
        <!-- Header avec gradient -->
        <div class="relative px-8 py-6 bg-gradient-to-r from-orange-500 via-red-500 to-pink-500 overflow-hidden">
          <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-20"></div>
          <div class="relative flex items-center gap-4">
            <div class="p-4 bg-white/20 backdrop-blur-sm rounded-2xl">
              <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 class="text-2xl font-bold text-white">🚫 Snapshots Détectés</h3>
              <p class="text-orange-100 text-sm mt-1">La réplication ne peut pas continuer</p>
            </div>
          </div>
        </div>

        <!-- Content -->
        <div class="px-8 py-6 space-y-6">
          <!-- Explication du problème -->
          <div class="bg-gradient-to-br from-orange-50 to-red-50 border-2 border-orange-200 rounded-2xl p-6">
            <div class="flex gap-4">
              <div class="flex-shrink-0">
                <div class="w-12 h-12 bg-gradient-to-br from-orange-400 to-red-500 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-bold text-gray-900 mb-2">Pourquoi ce problème ?</h4>
                <p class="text-gray-700 leading-relaxed">
                  La machine virtuelle <strong class="text-orange-600">{{ snapshotModalData.vmName }}</strong>
                  possède <strong class="text-red-600">{{ snapshotModalData.snapshotCount }} snapshot(s)</strong>.
                </p>
                <p class="text-gray-600 mt-3 text-sm">
                  📸 Les snapshots empêchent l'export OVF nécessaire pour la réplication.
                  VMware ne permet pas d'exporter une VM avec des snapshots actifs car ils créent des fichiers delta complexes.
                </p>
              </div>
            </div>
          </div>

          <!-- Solution -->
          <div class="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-2xl p-6">
            <div class="flex gap-4">
              <div class="flex-shrink-0">
                <div class="w-12 h-12 bg-gradient-to-br from-blue-400 to-cyan-500 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-bold text-gray-900 mb-2">✨ Solution automatique</h4>
                <p class="text-gray-700 leading-relaxed">
                  Je peux supprimer automatiquement tous les snapshots pour vous.
                  Cette opération :
                </p>
                <ul class="mt-3 space-y-2 text-sm text-gray-600">
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>Consolide tous les snapshots en un seul disque</span>
                  </li>
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>Libère de l'espace disque</span>
                  </li>
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>Relance automatiquement la réplication après</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Warning -->
          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
            <div class="flex gap-3">
              <svg class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <p class="text-sm text-yellow-800">
                <strong>Important :</strong> Une fois supprimés, les snapshots ne pourront pas être restaurés.
                Assurez-vous de ne pas avoir besoin de revenir à un état antérieur.
              </p>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="px-8 py-6 bg-gradient-to-r from-gray-50 to-gray-100 border-t border-gray-200 flex justify-between items-center">
          <button
            @click="showSnapshotModal = false"
            :disabled="snapshotModalData.removing"
            class="px-6 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-white hover:border-gray-400 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Annuler
          </button>
          <button
            @click="removeSnapshotsAndRetry"
            :disabled="snapshotModalData.removing"
            class="px-8 py-3 bg-gradient-to-r from-red-500 to-pink-500 text-white font-bold rounded-xl hover:from-red-600 hover:to-pink-600 hover:shadow-lg hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-3"
          >
            <svg v-if="!snapshotModalData.removing" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <svg v-else class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>
              {{ snapshotModalData.removing ? 'Suppression en cours...' : 'Supprimer les Snapshots' }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Powered-On VM Modal - Modern Design -->
    <div v-if="showPoweredOnModal" class="fixed inset-0 bg-gradient-to-br from-gray-900/90 via-blue-900/80 to-indigo-900/90 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-fade-in">
      <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden transform transition-all animate-slide-up">
        <!-- Header avec gradient -->
        <div class="relative px-8 py-6 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 overflow-hidden">
          <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-20"></div>
          <div class="relative flex items-center gap-4">
            <div class="p-4 bg-white/20 backdrop-blur-sm rounded-2xl">
              <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h3 class="text-2xl font-bold text-white">⚡ VM Allumée Détectée</h3>
              <p class="text-blue-100 text-sm mt-1">La VM doit être éteinte pour la réplication</p>
            </div>
          </div>
        </div>

        <!-- Content -->
        <div class="px-8 py-6 space-y-6">
          <!-- Explication du problème -->
          <div class="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl p-6">
            <div class="flex gap-4">
              <div class="flex-shrink-0">
                <div class="w-12 h-12 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-bold text-gray-900 mb-2">Pourquoi ce problème ?</h4>
                <p class="text-gray-700 leading-relaxed">
                  La machine virtuelle <strong class="text-blue-600">{{ poweredOnModalData.vmName }}</strong>
                  est actuellement <strong class="text-indigo-600">allumée (powered on)</strong>.
                </p>
                <p class="text-gray-600 mt-3 text-sm">
                  ⚡ Pour garantir la <strong>cohérence des données</strong> lors de la réplication,
                  la VM doit être éteinte. Cela évite les problèmes de corruption de données et assure
                  une copie exacte de l'état de la VM.
                </p>
              </div>
            </div>
          </div>

          <!-- Solution automatique -->
          <div class="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-2xl p-6">
            <div class="flex gap-4">
              <div class="flex-shrink-0">
                <div class="w-12 h-12 bg-gradient-to-br from-green-400 to-emerald-500 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-bold text-gray-900 mb-2">✨ Processus automatique</h4>
                <p class="text-gray-700 leading-relaxed">
                  Je peux gérer tout le processus automatiquement pour vous :
                </p>
                <ul class="mt-3 space-y-2 text-sm text-gray-600">
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span><strong>Étape 1 :</strong> Éteindre la VM proprement</span>
                  </li>
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-indigo-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span><strong>Étape 2 :</strong> Effectuer la réplication</span>
                  </li>
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span><strong>Étape 3 :</strong> Rallumer la VM automatiquement après</span>
                  </li>
                </ul>
                <div class="mt-4 flex items-center gap-2 text-xs text-gray-500 bg-white rounded-lg p-3 border border-gray-200">
                  <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  <span>Aucune intervention manuelle requise - tout est automatisé</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Warning -->
          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
            <div class="flex gap-3">
              <svg class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <p class="text-sm text-yellow-800">
                <strong>Important :</strong> L'extinction de la VM interrompra temporairement les services en cours d'exécution.
                La VM sera automatiquement rallumée une fois la réplication terminée.
              </p>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="px-8 py-6 bg-gradient-to-r from-gray-50 to-gray-100 border-t border-gray-200 flex justify-between items-center">
          <button
            @click="showPoweredOnModal = false"
            :disabled="poweredOnModalData.poweringOff"
            class="px-6 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-white hover:border-gray-400 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Annuler
          </button>
          <button
            @click="powerOffAndRetry"
            :disabled="poweredOnModalData.poweringOff"
            class="px-8 py-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-xl hover:from-blue-600 hover:to-indigo-600 hover:shadow-lg hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-3"
          >
            <svg v-if="!poweredOnModalData.poweringOff" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <svg v-else class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>
              {{ poweredOnModalData.poweringOff ? 'Extinction en cours...' : 'Éteindre et Continuer' }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Existing Replica Modal - Modern Design -->
    <div v-if="showReplicaExistsModal" class="fixed inset-0 bg-gradient-to-br from-gray-900/90 via-purple-900/80 to-red-900/90 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-fade-in">
      <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden transform transition-all animate-slide-up">
        <!-- Header avec gradient -->
        <div class="relative px-8 py-6 bg-gradient-to-r from-purple-500 via-pink-500 to-red-500 overflow-hidden">
          <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAgTSAwIDIwIEwgNDAgMjAgTSAyMCAwIEwgMjAgNDAgTSAwIDMwIEwgNDAgMzAgTSAzMCAwIEwgMzAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-20"></div>
          <div class="relative flex items-center gap-4">
            <div class="p-4 bg-white/20 backdrop-blur-sm rounded-2xl">
              <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 class="text-2xl font-bold text-white">🔄 Replica Existante Détectée</h3>
              <p class="text-purple-100 text-sm mt-1">Une VM replica existe déjà sur le serveur de destination</p>
            </div>
          </div>
        </div>

        <!-- Content -->
        <div class="px-8 py-6 space-y-6">
          <!-- Explication du problème -->
          <div class="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200 rounded-2xl p-6">
            <div class="flex gap-4">
              <div class="flex-shrink-0">
                <div class="w-12 h-12 bg-gradient-to-br from-purple-400 to-pink-500 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-bold text-gray-900 mb-2">Replica de la Même VM Détectée</h4>
                <p class="text-gray-700 leading-relaxed">
                  La VM <strong class="text-blue-600">{{ replicaExistsModalData.vmName }}</strong> possède déjà une replica <strong class="text-purple-600">{{ replicaExistsModalData.replicaName }}</strong> sur le serveur de destination.
                </p>
                <div class="mt-3 bg-white rounded-lg p-3 border border-purple-200">
                  <div class="flex items-center gap-2 text-sm">
                    <svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
                    </svg>
                    <span class="font-medium text-gray-700">VM Source :</span>
                    <span class="text-blue-600 font-semibold">{{ replicaExistsModalData.vmName }}</span>
                  </div>
                  <div class="flex items-center gap-2 text-sm mt-2">
                    <svg class="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M4 2a2 2 0 00-2 2v11a3 3 0 106 0V4a2 2 0 00-2-2H4zm1 14a1 1 0 100-2 1 1 0 000 2zm5-1.757l4.9-4.9a2 2 0 000-2.828L13.485 5.1a2 2 0 00-2.828 0L10 5.757v8.486zM16 18H9.071l6-6H16a2 2 0 012 2v2a2 2 0 01-2 2z" clip-rule="evenodd" />
                    </svg>
                    <span class="font-medium text-gray-700">Replica Existante :</span>
                    <span class="text-purple-600 font-semibold">{{ replicaExistsModalData.replicaName }}</span>
                  </div>
                </div>
                <p class="text-gray-600 mt-3 text-sm">
                  ⚠️ Pour lancer une nouvelle réplication de <strong>{{ replicaExistsModalData.vmName }}</strong>, l'ancienne replica doit être supprimée d'abord.
                </p>
              </div>
            </div>
          </div>

          <!-- Options -->
          <div class="bg-gradient-to-br from-red-50 to-orange-50 border-2 border-red-200 rounded-2xl p-6">
            <div class="flex gap-4">
              <div class="flex-shrink-0">
                <div class="w-12 h-12 bg-gradient-to-br from-red-400 to-orange-500 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
              </div>
              <div class="flex-1">
                <h4 class="text-lg font-bold text-gray-900 mb-2">⚠️ Action Requise</h4>
                <p class="text-gray-700 leading-relaxed">
                  Pour continuer, je vais :
                </p>
                <ul class="mt-3 space-y-2 text-sm text-gray-600">
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                    <span><strong>Étape 1 :</strong> Supprimer l'ancienne VM replica</span>
                  </li>
                  <li class="flex items-start gap-2">
                    <svg class="w-5 h-5 text-indigo-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span><strong>Étape 2 :</strong> Lancer la nouvelle réplication</span>
                  </li>
                </ul>
                <div class="mt-4 flex items-center gap-2 text-xs text-gray-500 bg-white rounded-lg p-3 border border-gray-200">
                  <svg class="w-4 h-4 text-purple-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                  </svg>
                  <span>Cette opération est automatique et sécurisée</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Warning -->
          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
            <div class="flex gap-3">
              <svg class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <p class="text-sm text-yellow-800">
                <strong>Important :</strong> L'ancienne replica sera définitivement supprimée et remplacée par la nouvelle.
              </p>
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="px-8 py-6 bg-gradient-to-r from-gray-50 to-gray-100 border-t border-gray-200 flex justify-between items-center">
          <button
            @click="showReplicaExistsModal = false"
            :disabled="replicaExistsModalData.deleting"
            class="px-6 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-white hover:border-gray-400 hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Annuler
          </button>
          <button
            @click="deleteReplicaAndRetry"
            :disabled="replicaExistsModalData.deleting"
            class="px-8 py-3 bg-gradient-to-r from-red-500 to-pink-500 text-white font-bold rounded-xl hover:from-red-600 hover:to-pink-600 hover:shadow-lg hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-3"
          >
            <svg v-if="!replicaExistsModalData.deleting" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <svg v-else class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>
              {{ replicaExistsModalData.deleting ? 'Suppression en cours...' : 'Supprimer et Continuer' }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { vmReplicationsAPI, failoverEventsAPI, virtualMachinesAPI, esxiServersAPI } from '../services/api'
import { useToastStore } from '@/stores/toast'
import { useOperationsStore } from '@/stores/operations'

const toast = useToastStore()
const operationsStore = useOperationsStore()

const replications = ref([])
const failoverEvents = ref([])
const virtualMachines = ref([])
const esxiServers = ref([])
const destinationDatastores = ref([])
const loading = ref(false)
const saving = ref(false)
const loadingDatastores = ref(false)
const replicatingId = ref(null)
const performingFailoverId = ref(null)
const showCreateModal = ref(false)
const showFailoverConfirmModal = ref(false)
const editingReplication = ref(null)
const selectedReplication = ref(null)
const failoverReason = ref('')
const failoverTestMode = ref(false)

// Snapshot Modal
const showSnapshotModal = ref(false)
const snapshotModalData = ref({
  vmId: null,
  vmName: '',
  snapshotCount: 0,
  replicationId: null,
  removing: false
})

// Powered-On VM Modal
const showPoweredOnModal = ref(false)
const poweredOnModalData = ref({
  vmId: null,
  vmName: '',
  replicationId: null,
  poweringOff: false,
  poweringOn: false,
  wasPoweredOn: false
})

// Existing Replica Modal
const showReplicaExistsModal = ref(false)
const replicaExistsModalData = ref({
  replicationId: null,
  replicaName: '',
  vmName: '', // Nom de la VM source
  deleting: false
})

// Progress tracking
const replicationProgress = ref(0)
const replicationStatus = ref('')
const replicationMessage = ref('')
const currentReplicationId = ref(null)

// VM States and History
const vmStates = ref({}) // { replicationId: { source_vm, destination_vm, sync_info } }
const expandedRows = ref(new Set()) // Set of expanded replication IDs
const replicationHistory = ref({}) // { replicationId: [...logs] }
const loadingStates = ref(new Set()) // Set of replication IDs being loaded
const loadingHistory = ref(new Set()) // Set of replication IDs with history being loaded

// Auto-refresh intervals
let statesRefreshInterval = null
let countdownInterval = null

const form = ref({
  name: '',
  virtual_machine: '',
  destination_server: '',
  destination_datastore: '',
  replication_interval_minutes: 60,
  failover_mode: 'manual',
  auto_failover_threshold_minutes: 15,
  is_active: true
})

const activeCount = computed(() => replications.value.filter(r => r.is_active).length)
const inProgressCount = computed(() => replications.value.filter(r => r.status === 'in_progress').length)

// Get selected VM details
const selectedVM = computed(() => {
  if (!form.value.virtual_machine) return null
  return virtualMachines.value.find(vm => vm.id === form.value.virtual_machine)
})

// Get available destination servers (all except the source server of selected VM)
const availableDestinationServers = computed(() => {
  if (!selectedVM.value) return esxiServers.value
  return esxiServers.value.filter(server => server.id !== selectedVM.value.server)
})

// Get selected datastore details
const selectedDatastore = computed(() => {
  if (!form.value.destination_datastore) return null
  return destinationDatastores.value.find(ds => ds.name === form.value.destination_datastore)
})

// Watch destination server changes to fetch its datastores
watch(() => form.value.destination_server, async (newServerId) => {
  if (!newServerId) {
    destinationDatastores.value = []
    form.value.destination_datastore = ''
    return
  }

  await fetchDatastores(newServerId)
})

onMounted(() => {
  fetchData()

  // Restaurer les réplications en cours depuis le store après chargement
  setTimeout(() => {
    const activeReplications = operationsStore.getOperationsByType('replication')
    console.log('[REPLICATION-RESTORE] Réplications actives trouvées:', activeReplications.length)

    if (activeReplications.length > 0) {
      // Reprendre le polling pour chaque réplication active (même si completed récemment)
      activeReplications.forEach(op => {
        console.log('[REPLICATION-RESTORE] Tentative restauration:', op.id, 'Status:', op.status, 'Progress:', op.progress)

        // Restaurer si pas completed/error/cancelled ET si progress < 100
        if (!['completed', 'error', 'cancelled'].includes(op.status) || op.progress < 100) {
          console.log('[REPLICATION-RESTORE] ✓ Restauration de la réplication', op.id)
          resumeReplication(op.id, op)
        } else {
          console.log('[REPLICATION-RESTORE] ✗ Skip (terminée ou annulée)')
        }
      })
    }
  }, 500) // Attendre que les données soient chargées

  // Auto-refresh des états VMs toutes les 30 secondes
  statesRefreshInterval = setInterval(() => {
    if (replications.value.length > 0) {
      fetchAllVMStates()
    }
  }, 30000) // 30 secondes

  // Force re-render toutes les secondes pour le compte à rebours
  countdownInterval = setInterval(() => {
    // Force Vue to re-render by creating a new reference
    vmStates.value = { ...vmStates.value }
  }, 1000) // 1 seconde
})

// Nettoyer tous les intervalles quand le composant est démonté
onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
  if (statesRefreshInterval) {
    clearInterval(statesRefreshInterval)
    statesRefreshInterval = null
  }
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
})

async function fetchData() {
  loading.value = true
  try {
    const [replicationsRes, failoverRes, vmsRes, serversRes] = await Promise.all([
      vmReplicationsAPI.getAll(),
      failoverEventsAPI.getAll(),
      virtualMachinesAPI.getAll(),
      esxiServersAPI.getAll()
    ])
    replications.value = replicationsRes.data.results || replicationsRes.data
    failoverEvents.value = failoverRes.data.results || failoverRes.data
    virtualMachines.value = vmsRes.data.results || vmsRes.data
    esxiServers.value = serversRes.data.results || serversRes.data

    // Fetch VM states for all active replications
    await fetchAllVMStates()
  } catch (error) {
    console.error('Erreur chargement données:', error)
    toast.error('Impossible de charger les données')
  } finally {
    loading.value = false
  }
}

async function fetchAllVMStates() {
  // Fetch VM states for all replications in parallel
  const promises = replications.value.map(replication => fetchVMStates(replication.id))
  await Promise.allSettled(promises)
}

async function fetchVMStates(replicationId) {
  loadingStates.value.add(replicationId)
  try {
    const response = await vmReplicationsAPI.getVMStates(replicationId)
    vmStates.value[replicationId] = response.data
  } catch (error) {
    console.error(`Erreur récupération états VM pour réplication ${replicationId}:`, error)
    // Don't show error toast for each replication, just log it
  } finally {
    loadingStates.value.delete(replicationId)
  }
}

async function toggleRowExpansion(replicationId) {
  if (expandedRows.value.has(replicationId)) {
    expandedRows.value.delete(replicationId)
  } else {
    expandedRows.value.add(replicationId)
    // Load history if not already loaded
    if (!replicationHistory.value[replicationId]) {
      await fetchReplicationHistory(replicationId)
    }
  }
  // Force reactivity
  expandedRows.value = new Set(expandedRows.value)
}

async function fetchReplicationHistory(replicationId, limit = 20) {
  loadingHistory.value.add(replicationId)
  try {
    const response = await vmReplicationsAPI.getReplicationHistory(replicationId, limit)
    replicationHistory.value[replicationId] = response.data
  } catch (error) {
    console.error(`Erreur récupération historique pour réplication ${replicationId}:`, error)
    toast.error('Impossible de charger l\'historique de réplication')
  } finally {
    loadingHistory.value.delete(replicationId)
  }
}

function formatRelativeTime(dateString) {
  if (!dateString) return 'Jamais'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'À l\'instant'
  if (diffMins < 60) return `Il y a ${diffMins} min`
  if (diffHours < 24) return `Il y a ${diffHours}h`
  if (diffDays < 7) return `Il y a ${diffDays}j`
  return formatDateTime(dateString)
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}

function getPowerStateIcon(powerState) {
  if (powerState === 'poweredOn') {
    return '🟢'
  } else if (powerState === 'poweredOff') {
    return '🔴'
  } else if (powerState === 'suspended') {
    return '🟡'
  }
  return '⚪'
}

function getPowerStateText(powerState) {
  if (powerState === 'poweredOn') return 'Allumée'
  if (powerState === 'poweredOff') return 'Éteinte'
  if (powerState === 'suspended') return 'Suspendue'
  return 'Inconnue'
}

function getNextSyncCountdown(replication) {
  if (!replication.is_active) return null
  if (!vmStates.value[replication.id]?.sync_info) return null

  const syncInfo = vmStates.value[replication.id].sync_info
  if (!syncInfo.next_sync) return { text: 'En attente...', color: 'text-gray-500', isImminent: false }

  const nextSync = new Date(syncInfo.next_sync)
  const now = new Date()
  const diffSeconds = Math.floor((nextSync - now) / 1000)

  // Si en retard (dans le passé)
  if (diffSeconds < 0) {
    return { text: 'En cours...', color: 'text-blue-600 animate-pulse', isImminent: true }
  }

  // Si très proche (< 30 secondes)
  if (diffSeconds < 30) {
    return { text: 'Imminent (< 30s)', color: 'text-green-600 animate-pulse', isImminent: true }
  }

  // Afficher en minutes et secondes
  const minutes = Math.floor(diffSeconds / 60)
  const seconds = diffSeconds % 60

  if (minutes > 0) {
    return {
      text: `Dans ${minutes}m ${seconds}s`,
      color: minutes <= 2 ? 'text-orange-500 font-medium' : 'text-gray-700',
      isImminent: minutes <= 2
    }
  } else {
    return {
      text: `Dans ${seconds}s`,
      color: 'text-orange-500 font-semibold',
      isImminent: true
    }
  }
}

function isSyncing(replication) {
  return replication.status === 'syncing' || replicatingId.value === replication.id
}

function getSyncProgress(replicationId) {
  // Si c'est la réplication en cours, retourner le progress actuel
  if (replicatingId.value === replicationId) {
    return replicationProgress.value
  }

  // Sinon, chercher dans operationsStore au cas où
  const activeOps = operationsStore.getOperationsByType('replication')
  const op = activeOps.find(o => o.id === replicationId)
  return op?.progress || 0
}

async function fetchDatastores(serverId) {
  loadingDatastores.value = true
  try {
    const response = await esxiServersAPI.getDatastores(serverId)
    // Add computed free_percent to each datastore
    const datastores = (response.data.datastores || []).map(ds => ({
      ...ds,
      free_percent: ds.capacity_gb > 0 ? Math.round((ds.free_space_gb / ds.capacity_gb) * 100) : 0
    }))
    destinationDatastores.value = datastores
    // Reset datastore selection
    form.value.destination_datastore = ''
  } catch (error) {
    console.error('Erreur chargement datastores:', error)
    toast.error('Impossible de charger les datastores')
    destinationDatastores.value = []
  } finally {
    loadingDatastores.value = false
  }
}

function formatDatastoreInfo(datastore) {
  const capacityGB = Math.round(datastore.capacity_gb || 0)
  const freeGB = Math.round(datastore.free_space_gb || 0)
  const usedGB = capacityGB - freeGB
  const freePercent = capacityGB > 0 ? Math.round((freeGB / capacityGB) * 100) : 0

  return `${freeGB}GB libre / ${usedGB}GB utilisé (${capacityGB}GB total)`
}

async function saveReplication() {
  saving.value = true
  try {
    if (editingReplication.value) {
      // Mode édition
      await vmReplicationsAPI.update(editingReplication.value.id, form.value)
      toast.success('Réplication mise à jour')
    } else {
      // Mode création - Vérifier si une réplication existe déjà
      const existingReplication = replications.value.find(
        r => r.virtual_machine === form.value.virtual_machine &&
             r.destination_server === form.value.destination_server
      )

      if (existingReplication) {
        // Une réplication existe déjà pour cette VM vers ce serveur
        const vmName = virtualMachines.value.find(vm => vm.id === form.value.virtual_machine)?.name || 'cette VM'
        const serverName = esxiServers.value.find(s => s.id === form.value.destination_server)?.name || 'ce serveur'

        toast.error(
          `Erreur, ${vmName} est déjà répliquée sur ${serverName}`,
          { duration: 5000 }
        )
        return
      }

      // Créer la nouvelle réplication
      await vmReplicationsAPI.create(form.value)
      toast.success('Réplication créée')
    }
    closeModal()
    fetchData()
  } catch (error) {
    console.error('Erreur sauvegarde:', error)
    console.error('Détails erreur:', error.response?.data)

    // Gérer les erreurs de validation du backend
    if (error.response?.status === 400) {
      const errors = error.response.data

      // Erreur de contrainte unique
      if (errors.non_field_errors) {
        const uniqueError = errors.non_field_errors.find(
          err => err.includes('unique') || err.includes('must make a unique set')
        )

        if (uniqueError) {
          const vmName = virtualMachines.value.find(vm => vm.id === form.value.virtual_machine)?.name || 'cette VM'
          const serverName = esxiServers.value.find(s => s.id === form.value.destination_server)?.name || 'ce serveur'

          toast.error(
            `Erreur, ${vmName} est déjà répliquée sur ${serverName}`,
            { duration: 5000 }
          )
          return
        }
      }

      // Autres erreurs de validation
      if (errors.destination_datastore) {
        toast.error(`Datastore invalide: ${errors.destination_datastore[0]}`)
        return
      }

      if (errors.virtual_machine) {
        toast.error(`Machine virtuelle invalide: ${errors.virtual_machine[0]}`)
        return
      }

      if (errors.destination_server) {
        toast.error(`Serveur de destination invalide: ${errors.destination_server[0]}`)
        return
      }
    }

    // Erreur générique
    toast.error('Erreur, la VM sélectionnée est déjà répliquée sur ce serveur')
  } finally {
    saving.value = false
  }
}

function editReplication(replication) {
  editingReplication.value = replication
  form.value = { ...replication }
  showCreateModal.value = true
}

function closeModal() {
  showCreateModal.value = false
  editingReplication.value = null
  form.value = {
    name: '',
    virtual_machine: '',
    destination_server: '',
    destination_datastore: '',
    replication_interval_minutes: 60,
    failover_mode: 'manual',
    auto_failover_threshold_minutes: 15,
    is_active: true
  }
}

let pollInterval = null // Stocker l'intervalle de polling

async function startReplication(replication) {
  if (!confirm(`Voulez-vous démarrer la réplication de ${replication.vm_name} ?`)) return

  try {
    // TOUJOURS vérifier si une replica existe déjà AVANT chaque réplication
    console.log('[CHECK-REPLICA] Vérification replica pour VM:', replication.vm_name)
    const checkResponse = await vmReplicationsAPI.checkReplicaExists(replication.id)

    if (checkResponse.data.exists) {
      console.log('[CHECK-REPLICA] ⚠️ Replica trouvée:', checkResponse.data.replica_name)
      // Afficher le modal de confirmation - OBLIGATOIRE pour la même VM
      replicaExistsModalData.value = {
        replicationId: replication.id,
        replicaName: checkResponse.data.replica_name,
        vmName: replication.vm_name, // Ajouter le nom de la VM source
        deleting: false
      }
      showReplicaExistsModal.value = true
      return
    }

    console.log('[CHECK-REPLICA] ✓ Aucune replica trouvée, démarrage...')
    // Pas de replica existante, continuer normalement
    await startReplicationWithoutCheck(replication)

  } catch (error) {
    console.error('Erreur vérification replica:', error)
    // En cas d'erreur de vérification, continuer quand même
    await startReplicationWithoutCheck(replication)
  }
}

async function startReplicationWithoutCheck(replication) {
  // Initialiser dans le store pour persistence
  operationsStore.setOperation('replication', replication.id, {
    vmName: replication.vm_name,
    progress: 0,
    status: 'starting',
    message: 'Démarrage de la réplication...'
  })

  replicatingId.value = replication.id
  replicationProgress.value = 0
  replicationStatus.value = 'starting'
  replicationMessage.value = 'Démarrage de la réplication...'

  try {
    const response = await vmReplicationsAPI.startReplication(replication.id)
    const replicationId = response.data.replication_id

    // Afficher message approprié selon le type de réponse
    if (response.data.warning) {
      toast.warning(response.data.message)
    } else {
      toast.success(response.data.message || 'Réplication démarrée')
    }

    // Si on a un replication_id, démarrer le polling de la progression
    if (replicationId) {
      currentReplicationId.value = replicationId

      // Sauvegarder le currentReplicationId dans le store pour restauration après refresh
      operationsStore.setOperation('replication', replication.id, {
        vmName: replication.vm_name,
        progress: 0,
        status: 'starting',
        message: 'Démarrage de la réplication...',
        currentReplicationId: replicationId  // UUID pour le polling
      })

      // Polling toutes les 500ms pour récupérer la progression
      pollInterval = setInterval(async () => {
        try {
          const progressResponse = await vmReplicationsAPI.getReplicationProgress(replicationId)
          const progressData = progressResponse.data

          // Mettre à jour le store ET les variables locales
          operationsStore.updateProgress(
            'replication',
            replication.id,
            progressData.progress,
            progressData.status,
            progressData.message
          )

          replicationProgress.value = progressData.progress
          replicationStatus.value = progressData.status
          replicationMessage.value = progressData.message

          // Arrêter le polling si terminé, en erreur ou annulé
          if (progressData.status === 'completed' || progressData.status === 'error' || progressData.status === 'cancelled') {
            clearInterval(pollInterval)
            pollInterval = null
            replicatingId.value = null
            currentReplicationId.value = null

            if (progressData.status === 'completed') {
              toast.success('Réplication terminée')
              // Retirer du store après 10 secondes
              setTimeout(() => {
                operationsStore.removeOperation('replication', replication.id)
                replicationProgress.value = 0
                replicationStatus.value = ''
                replicationMessage.value = ''
              }, 10000)
            } else if (progressData.status === 'cancelled') {
              toast.info('Réplication annulée par l\'utilisateur')
              operationsStore.removeOperation('replication', replication.id)
              replicationProgress.value = 0
              replicationStatus.value = ''
              replicationMessage.value = ''
            } else if (progressData.status === 'error') {
              // Détecter le type d'erreur
              const errorMessage = progressData.message || ''

              // 1. Détecter l'erreur de VM allumée (powered on)
              if (errorMessage.includes('powered on') || errorMessage.includes('allumée')) {
                // Afficher le modal de gestion de VM allumée
                poweredOnModalData.value = {
                  vmId: replication.virtual_machine,
                  vmName: replication.vm_name,
                  replicationId: replication.id,
                  poweringOff: false,
                  poweringOn: false,
                  wasPoweredOn: false
                }
                showPoweredOnModal.value = true
              }
              // 2. Détecter l'erreur de snapshot
              else if (errorMessage.includes('snapshot')) {
                // Extraire le nombre de snapshots si possible
                const snapshotMatch = errorMessage.match(/(\d+)\s+snapshot/)
                const snapshotCount = snapshotMatch ? parseInt(snapshotMatch[1]) : 0

                // Afficher le modal de gestion des snapshots
                snapshotModalData.value = {
                  vmId: replication.virtual_machine,
                  vmName: replication.vm_name,
                  snapshotCount: snapshotCount,
                  replicationId: replication.id,
                  removing: false
                }
                showSnapshotModal.value = true
              }
              // 3. Autres erreurs
              else {
                toast.error(errorMessage || 'La réplication a échoué')
              }

              operationsStore.removeOperation('replication', replication.id)
              replicationProgress.value = 0
              replicationStatus.value = ''
              replicationMessage.value = ''
            }
          }
        } catch (pollErr) {
          console.error('Erreur polling progression:', pollErr)
          if (pollInterval) {
            clearInterval(pollInterval)
            pollInterval = null
          }
          operationsStore.removeOperation('replication', replication.id)
          replicatingId.value = null
          currentReplicationId.value = null
        }
      }, 500)
    } else {
      replicatingId.value = null
    }

    fetchData()
  } catch (error) {
    console.error('Erreur démarrage réplication:', error)
    const errorMsg = error.response?.data?.error || 'Impossible de démarrer la réplication'
    toast.error(errorMsg)
    operationsStore.removeOperation('replication', replication.id)
    replicatingId.value = null
    replicationProgress.value = 0
    replicationStatus.value = ''
    replicationMessage.value = ''
  }
}

// Fonction pour reprendre une réplication en cours après rechargement de page
function resumeReplication(replicationId, opData) {
  const replication = replications.value.find(r => r.id === replicationId)
  if (!replication) {
    console.warn('[REPLICATION-RESTORE] Réplication introuvable:', replicationId)
    return
  }

  console.log('[REPLICATION-RESTORE] Restauration des données:', {
    replicationId,
    progress: opData.progress,
    status: opData.status,
    currentReplicationId: opData.currentReplicationId
  })

  replicatingId.value = replicationId
  replicationProgress.value = opData.progress || 0
  replicationStatus.value = opData.status || 'starting'
  replicationMessage.value = opData.message || 'Synchronisation en cours...'

  // Relancer le polling pour suivre la progression
  if (!currentReplicationId.value && opData.currentReplicationId) {
    // On utilise opData.currentReplicationId qui contient le UUID de la réplication en cours
    currentReplicationId.value = opData.currentReplicationId
    console.log('[REPLICATION-RESTORE] Reprise du polling avec UUID:', opData.currentReplicationId)

    pollInterval = setInterval(async () => {
      try {
        const progressResponse = await vmReplicationsAPI.getReplicationProgress(opData.currentReplicationId)
        const progressData = progressResponse.data

        operationsStore.updateProgress(
          'replication',
          replicationId,
          progressData.progress,
          progressData.status,
          progressData.message
        )

        replicationProgress.value = progressData.progress
        replicationStatus.value = progressData.status
        replicationMessage.value = progressData.message

        if (['completed', 'error', 'cancelled'].includes(progressData.status)) {
          clearInterval(pollInterval)
          pollInterval = null
          replicatingId.value = null
          currentReplicationId.value = null

          if (progressData.status === 'completed') {
            toast.success('Réplication terminée')
            setTimeout(() => {
              operationsStore.removeOperation('replication', replicationId)
              replicationProgress.value = 0
              replicationStatus.value = ''
              replicationMessage.value = ''
            }, 10000)
          } else {
            operationsStore.removeOperation('replication', replicationId)
            replicationProgress.value = 0
            replicationStatus.value = ''
            replicationMessage.value = ''
          }
        }
      } catch (pollErr) {
        console.error('Erreur polling reprise:', pollErr)
        clearInterval(pollInterval)
        pollInterval = null
        operationsStore.removeOperation('replication', replicationId)
        replicatingId.value = null
        currentReplicationId.value = null
      }
    }, 500)
  }
}

// Fonction pour supprimer la replica existante et relancer la réplication
async function deleteReplicaAndRetry() {
  replicaExistsModalData.value.deleting = true

  try {
    const replication = replications.value.find(r => r.id === replicaExistsModalData.value.replicationId)
    if (!replication) {
      toast.error('Réplication introuvable')
      return
    }

    toast.info('Suppression de l\'ancienne replica en cours...')

    // Supprimer la réplication qui va automatiquement supprimer la replica
    await vmReplicationsAPI.delete(replication.id)

    // Recréer la réplication avec les mêmes paramètres
    const newReplication = await vmReplicationsAPI.create({
      name: replication.name,
      virtual_machine: replication.virtual_machine,
      destination_server: replication.destination_server,
      destination_datastore: replication.destination_datastore,
      replication_interval_minutes: replication.replication_interval_minutes,
      failover_mode: replication.failover_mode,
      auto_failover_threshold_minutes: replication.auto_failover_threshold_minutes,
      is_active: replication.is_active
    })

    toast.success('Ancienne replica supprimée, nouvelle réplication créée')

    // Fermer le modal
    showReplicaExistsModal.value = false

    // Rafraîchir la liste
    await fetchData()

    // Lancer la nouvelle réplication
    const newReplData = newReplication.data
    await startReplicationWithoutCheck(newReplData)

  } catch (error) {
    console.error('Erreur suppression replica:', error)
    toast.error(error.response?.data?.error || 'Erreur lors de la suppression de la replica')
  } finally {
    replicaExistsModalData.value.deleting = false
  }
}

// Fonction pour supprimer les snapshots et réessayer la réplication
async function removeSnapshotsAndRetry() {
  snapshotModalData.value.removing = true

  try {
    // Appeler l'API pour supprimer les snapshots
    const response = await virtualMachinesAPI.removeAllSnapshots(snapshotModalData.value.vmId)

    if (response.data.success) {
      toast.success(`${response.data.snapshots_removed} snapshot(s) supprimé(s)`, { duration: 5000 })

      // Fermer le modal
      showSnapshotModal.value = false

      // Informer l'utilisateur que la réplication va redémarrer
      toast.info('⏱️ Attente de la consolidation des disques ESXi... La réplication redémarrera dans 15 secondes', { duration: 6000 })

      // Attendre 15 secondes pour que ESXi finisse la consolidation en arrière-plan
      setTimeout(() => {
        const replication = replications.value.find(r => r.id === snapshotModalData.value.replicationId)
        if (replication) {
          toast.info('🔄 Relancement de la réplication...')
          startReplication(replication)
        }
      }, 15000)
    } else {
      toast.error(`Échec: ${response.data.message}`)
    }
  } catch (error) {
    console.error('Erreur suppression snapshots:', error)
    const errorMsg = error.response?.data?.error || 'Impossible de supprimer les snapshots'
    toast.error(errorMsg)
  } finally {
    snapshotModalData.value.removing = false
  }
}

// Fonction pour éteindre la VM, faire l'opération, puis rallumer la VM
async function powerOffAndRetry() {
  poweredOnModalData.value.poweringOff = true

  try {
    // 1. Éteindre la VM
    toast.info('⏹️ Extinction de la VM en cours...')
    const powerOffResponse = await virtualMachinesAPI.powerOff(poweredOnModalData.value.vmId)

    if (powerOffResponse.data.success) {
      poweredOnModalData.value.wasPoweredOn = powerOffResponse.data.was_powered_on

      toast.success('VM éteinte avec succès')
      poweredOnModalData.value.poweringOff = false

      // Fermer le modal
      showPoweredOnModal.value = false

      // 2. Attendre un peu pour que ESXi finalise l'extinction
      toast.info('⏱️ Démarrage de la réplication...')
      await new Promise(resolve => setTimeout(resolve, 3000))

      // 3. Lancer la réplication
      const replication = replications.value.find(r => r.id === poweredOnModalData.value.replicationId)
      if (replication) {
        // Démarrer la réplication sans confirmation
        replicatingId.value = replication.id
        replicationProgress.value = 0
        replicationStatus.value = 'starting'
        replicationMessage.value = 'Démarrage de la réplication...'

        const response = await vmReplicationsAPI.startReplication(replication.id)
        const replicationId = response.data.replication_id

        if (response.data.warning) {
          toast.warning(response.data.message)
        } else {
          toast.success(response.data.message || 'Réplication démarrée')
        }

        // Polling de la réplication
        if (replicationId) {
          currentReplicationId.value = replicationId

          pollInterval = setInterval(async () => {
            try {
              const progressResponse = await vmReplicationsAPI.getReplicationProgress(replicationId)
              const progressData = progressResponse.data

              replicationProgress.value = progressData.progress
              replicationStatus.value = progressData.status
              replicationMessage.value = progressData.message

              // Vérifier si terminé
              if (progressData.status === 'completed' || progressData.status === 'error' || progressData.status === 'cancelled') {
                clearInterval(pollInterval)
                pollInterval = null
                replicatingId.value = null
                currentReplicationId.value = null

                if (progressData.status === 'completed') {
                  toast.success('✅ Réplication terminée')

                  // 4. Rallumer la VM si elle était allumée avant
                  if (poweredOnModalData.value.wasPoweredOn) {
                    poweredOnModalData.value.poweringOn = true
                    toast.info('🔌 Rallumage de la VM...')

                    try {
                      const powerOnResponse = await virtualMachinesAPI.powerOn(poweredOnModalData.value.vmId)
                      if (powerOnResponse.data.success) {
                        toast.success('✅ VM rallumée avec succès')
                      } else {
                        toast.warning('⚠️ Impossible de rallumer la VM automatiquement')
                      }
                    } catch (powerOnError) {
                      console.error('Erreur rallumage VM:', powerOnError)
                      toast.warning('⚠️ Impossible de rallumer la VM automatiquement')
                    } finally {
                      poweredOnModalData.value.poweringOn = false
                    }
                  }

                  // Réinitialiser après 3 secondes
                  setTimeout(() => {
                    replicationProgress.value = 0
                    replicationStatus.value = ''
                    replicationMessage.value = ''
                  }, 3000)
                } else if (progressData.status === 'error') {
                  toast.error(progressData.message || 'La réplication a échoué')
                  replicationProgress.value = 0
                  replicationStatus.value = ''
                  replicationMessage.value = ''
                }
              }
            } catch (pollErr) {
              console.error('Erreur polling:', pollErr)
            }
          }, 500)
        }

        fetchData()
      }
    } else {
      toast.error(`Échec de l'extinction: ${powerOffResponse.data.message}`)
    }
  } catch (error) {
    console.error('Erreur extinction VM:', error)
    const errorMsg = error.response?.data?.error || 'Impossible d\'éteindre la VM'
    toast.error(errorMsg)
  } finally {
    poweredOnModalData.value.poweringOff = false
  }
}

async function cancelReplication() {
  if (!currentReplicationId.value) {
    toast.error('Aucune réplication n\'est en cours')
    return
  }

  if (!confirm('Voulez-vous vraiment arrêter cette réplication ?')) return

  try {
    await vmReplicationsAPI.cancelReplication(currentReplicationId.value)
    toast.info('Arrêt de la réplication en cours...')

    // Arrêter le polling
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }

    // Réinitialiser l'UI
    replicatingId.value = null
    currentReplicationId.value = null
    replicationProgress.value = 0
    replicationStatus.value = ''
    replicationMessage.value = ''
  } catch (error) {
    console.error('Erreur arrêt réplication:', error)
    toast.error('Impossible d\'arrêter la réplication')
  }
}

function showFailoverModal(replication) {
  selectedReplication.value = replication
  failoverReason.value = ''
  failoverTestMode.value = false
  showFailoverConfirmModal.value = true
}

async function performFailover() {
  saving.value = true
  try {
    await vmReplicationsAPI.performFailover(selectedReplication.value.id, {
      reason: failoverReason.value,
      test_mode: failoverTestMode.value
    })
    toast.success('Basculement vers le serveur de secours effectué')
    showFailoverConfirmModal.value = false
    fetchData()
  } catch (error) {
    console.error('Erreur failover:', error)
    toast.error('Le basculement a échoué')
  } finally {
    saving.value = false
  }
}

async function triggerFailback(replication) {
  if (!confirm(
    `🔄 Retour à la normale ?\n\n` +
    `Cette action va :\n` +
    `✅ Rallumer la VM master: ${replication.vm_name} sur ${replication.source_server_name}\n` +
    `🛑 Arrêter la VM slave sur ${replication.destination_server_name}\n\n` +
    `Confirmer le failback ?`
  )) return

  saving.value = true
  try {
    const response = await vmReplicationsAPI.performFailback(replication.id)
    toast.success('✅ Failback réussi - Retour à la normale')
    console.log('[FAILBACK] Succès:', response.data)
    fetchData()
    fetchAllVMStates()
  } catch (error) {
    console.error('Erreur failback:', error)
    toast.error(`❌ Erreur failback: ${error.response?.data?.error || error.message}`)
  } finally {
    saving.value = false
  }
}

async function deleteReplication(replication) {
  if (!confirm(
    `Voulez-vous vraiment supprimer la réplication "${replication.name}" ?\n\n` +
    `⚠️ La VM répliquée sera également supprimée du serveur de destination ${replication.destination_server_name}.`
  )) return

  try {
    const response = await vmReplicationsAPI.delete(replication.id)

    // Gérer les avertissements (si la VM n'a pas pu être supprimée du serveur)
    if (response.data?.warning) {
      toast.warning(response.data.message, { duration: 8000 })
    } else {
      toast.success('Réplication et VM répliquée supprimées')
    }

    fetchData()
  } catch (error) {
    console.error('Erreur suppression:', error)
    const errorMsg = error.response?.data?.message || 'Impossible de supprimer la réplication'
    toast.error(errorMsg, { duration: 6000 })
  }
}

function getStatusClass(status) {
  const classes = {
    idle: 'bg-gray-100 text-gray-800',
    in_progress: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function getFailoverStatusClass(status) {
  const classes = {
    initiated: 'bg-yellow-100 text-yellow-800',
    in_progress: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    rolled_back: 'bg-orange-100 text-orange-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function formatDateTime(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #3b82f6, #8b5cf6);
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #2563eb, #7c3aed);
}

/* Fade in animation */
@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.animate-fade-in {
  animation: fade-in 0.2s ease-out;
}

/* Slide up animation */
@keyframes slide-up {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.animate-slide-up {
  animation: slide-up 0.3s ease-out;
}
</style>
