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
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source → Destination</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Intervalle</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dernière Réplication</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="replication in replications" :key="replication.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ replication.vm_name }}</div>
                <div class="text-sm text-gray-500">{{ replication.name }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">
                  {{ replication.source_server_name }} → {{ replication.destination_server_name }}
                </div>
                <div class="text-sm text-gray-500">{{ replication.destination_datastore }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ replication.replication_interval_minutes }} min
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getStatusClass(replication.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ replication.status_display }}
                </span>
                <div v-if="replication.failover_mode === 'automatic'" class="mt-1">
                  <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                    Auto-Failover
                  </span>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <div v-if="replication.last_replication_at">
                  {{ formatDateTime(replication.last_replication_at) }}
                </div>
                <div v-else class="text-gray-400">Jamais</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
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
                <button
                  @click="showFailoverModal(replication)"
                  :disabled="!replication.is_active"
                  class="text-orange-600 hover:text-orange-900 disabled:text-gray-400"
                  title="Failover manuel"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
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
                Intervalle (minutes)
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { vmReplicationsAPI, failoverEventsAPI, virtualMachinesAPI, esxiServersAPI } from '../services/api'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

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

// Progress tracking
const replicationProgress = ref(0)
const replicationStatus = ref('')
const replicationMessage = ref('')
const currentReplicationId = ref(null)

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
  } catch (error) {
    console.error('Erreur chargement données:', error)
    toast.error('Impossible de charger les données')
  } finally {
    loading.value = false
  }
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

      // Polling toutes les 500ms pour récupérer la progression
      pollInterval = setInterval(async () => {
        try {
          const progressResponse = await vmReplicationsAPI.getReplicationProgress(replicationId)
          const progressData = progressResponse.data

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
              // Réinitialiser les valeurs de progression après 3 secondes
              setTimeout(() => {
                replicationProgress.value = 0
                replicationStatus.value = ''
                replicationMessage.value = ''
              }, 3000)
            } else if (progressData.status === 'cancelled') {
              toast.info('Réplication annulée par l\'utilisateur')
              replicationProgress.value = 0
              replicationStatus.value = ''
              replicationMessage.value = ''
            } else if (progressData.status === 'error') {
              // Détecter l'erreur de snapshot
              const errorMessage = progressData.message || ''
              if (errorMessage.includes('snapshot')) {
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
              } else {
                toast.error(errorMessage || 'La réplication a échoué')
              }

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
    replicatingId.value = null
    replicationProgress.value = 0
    replicationStatus.value = ''
    replicationMessage.value = ''
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

      // Attendre 2 secondes puis relancer la réplication automatiquement
      setTimeout(() => {
        const replication = replications.value.find(r => r.id === snapshotModalData.value.replicationId)
        if (replication) {
          startReplication(replication)
        }
      }, 2000)
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
