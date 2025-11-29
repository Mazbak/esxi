<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">✅ SureBackup - Vérification Automatique</h1>
        <p class="mt-1 text-sm text-gray-500">Vérifiez automatiquement l'intégrité et la restaurabilité de vos sauvegardes</p>
      </div>
      <button @click="showCreateVerificationModal = true" class="btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Nouvelle Vérification
      </button>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-6">
      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-blue-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Total</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ statistics.total || 0 }}</dd>
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
              <dt class="text-sm font-medium text-gray-500 truncate">Réussies</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ statistics.passed || 0 }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-red-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Échouées</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ statistics.failed || 0 }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-yellow-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">En cours</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ statistics.running || 0 }}</dd>
            </dl>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-purple-500 rounded-md p-3">
            <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">Taux de Succès</dt>
              <dd class="text-lg font-semibold text-gray-900">{{ statistics.success_rate || 0 }}%</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button
          @click="activeTab = 'verifications'"
          :class="activeTab === 'verifications' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
        >
          Vérifications ({{ verifications.length }})
        </button>
        <button
          @click="activeTab = 'schedules'"
          :class="activeTab === 'schedules' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
        >
          Planifications ({{ schedules.length }})
        </button>
      </nav>
    </div>

    <!-- Verifications Tab -->
    <div v-if="activeTab === 'verifications'" class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">Historique des Vérifications</h2>
        <button @click="fetchData" class="btn-secondary text-sm">
          <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Actualiser
        </button>
      </div>

      <div v-if="loading" class="text-center py-8">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p class="mt-2 text-gray-500">Chargement...</p>
      </div>

      <div v-else-if="verifications.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">Aucune vérification</h3>
        <p class="mt-1 text-sm text-gray-500">Lancez une vérification pour valider vos sauvegardes</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Backup</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Serveur Test</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tests</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Durée</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="verification in verifications" :key="verification.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ verification.backup_name }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ verification.server_name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ verification.test_type_display }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getStatusClass(verification.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ verification.status_display }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <div class="flex flex-col space-y-1">
                  <div class="flex items-center">
                    <svg :class="verification.vm_restored ? 'text-green-500' : 'text-gray-300'" class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-xs">Restauré</span>
                  </div>
                  <div class="flex items-center">
                    <svg :class="verification.vm_booted ? 'text-green-500' : 'text-gray-300'" class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-xs">Démarré</span>
                  </div>
                  <div class="flex items-center">
                    <svg :class="verification.ping_successful ? 'text-green-500' : 'text-gray-300'" class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-xs">Ping OK</span>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ verification.total_duration_seconds ? Math.round(verification.total_duration_seconds) + 's' : '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDateTime(verification.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button
                  v-if="verification.detailed_log"
                  @click="showLog(verification)"
                  class="text-blue-600 hover:text-blue-900"
                  title="Voir les logs"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Schedules Tab -->
    <div v-if="activeTab === 'schedules'" class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">Planifications de Vérification</h2>
        <button @click="showCreateScheduleModal = true" class="btn-primary text-sm">
          <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Nouvelle Planification
        </button>
      </div>

      <div v-if="loading" class="text-center py-8">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>

      <div v-else-if="schedules.length === 0" class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">Aucune planification</h3>
        <p class="mt-1 text-sm text-gray-500">Automatisez vos vérifications en créant une planification</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fréquence</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="schedule in schedules" :key="schedule.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ schedule.name }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ schedule.vm_name || 'Toutes' }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ schedule.frequency_display }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ schedule.test_type_display }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="schedule.is_active ? 'badge-success' : 'badge-gray'" class="badge">
                  {{ schedule.is_active ? 'Actif' : 'Inactif' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                <button
                  @click="toggleSchedule(schedule)"
                  class="text-blue-600 hover:text-blue-900"
                  :title="schedule.is_active ? 'Désactiver' : 'Activer'"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path v-if="schedule.is_active" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  </svg>
                </button>
                <button
                  @click="editSchedule(schedule)"
                  class="text-indigo-600 hover:text-indigo-900"
                  title="Modifier"
                >
                  <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  @click="deleteSchedule(schedule)"
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

    <!-- Create Verification Modal -->
    <div v-if="showCreateVerificationModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-xl w-full max-h-[90vh] overflow-y-auto">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900">Nouvelle Vérification Manuelle</h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Serveur ESXi de Test</label>
            <select v-model="verificationForm.esxi_server" class="input">
              <option value="">Sélectionner un serveur...</option>
              <option v-for="server in esxiServers" :key="server.id" :value="server.id">{{ server.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Type de Test</label>
            <select v-model="verificationForm.test_type" class="input">
              <option value="boot_only">Démarrage uniquement</option>
              <option value="ping_test">Test de Ping</option>
              <option value="service_check">Vérification des services</option>
              <option value="full">Complet (tous les tests)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Réseau de Test</label>
            <input v-model="verificationForm.test_network" type="text" class="input" placeholder="Ex: VM Network Test" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Datastore de Test</label>
            <input v-model="verificationForm.test_datastore" type="text" class="input" placeholder="Ex: datastore_test" />
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3">
          <button @click="showCreateVerificationModal = false" class="btn-secondary">Annuler</button>
          <button @click="createVerification" class="btn-primary" :disabled="saving">
            {{ saving ? 'Lancement...' : 'Lancer la Vérification' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Create Schedule Modal -->
    <div v-if="showCreateScheduleModal || editingSchedule" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-xl w-full max-h-[90vh] overflow-y-auto">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold text-gray-900">
            {{ editingSchedule ? 'Modifier la Planification' : 'Nouvelle Planification' }}
          </h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nom</label>
            <input v-model="scheduleForm.name" type="text" class="input" placeholder="Ex: Vérification quotidienne" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Machine Virtuelle (optionnel)</label>
            <select v-model="scheduleForm.virtual_machine" class="input">
              <option value="">Toutes les VMs</option>
              <option v-for="vm in virtualMachines" :key="vm.id" :value="vm.id">{{ vm.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Serveur ESXi de Test</label>
            <select v-model="scheduleForm.esxi_server" class="input">
              <option value="">Sélectionner un serveur...</option>
              <option v-for="server in esxiServers" :key="server.id" :value="server.id">{{ server.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Fréquence</label>
            <select v-model="scheduleForm.frequency" class="input">
              <option value="daily">Quotidien</option>
              <option value="weekly">Hebdomadaire</option>
              <option value="monthly">Mensuel</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Type de Test</label>
            <select v-model="scheduleForm.test_type" class="input">
              <option value="boot_only">Démarrage uniquement</option>
              <option value="ping_test">Test de Ping</option>
              <option value="service_check">Vérification des services</option>
              <option value="full">Complet</option>
            </select>
          </div>
          <div class="flex items-center">
            <input v-model="scheduleForm.is_active" type="checkbox" id="schedule_active" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
            <label for="schedule_active" class="ml-2 block text-sm text-gray-900">Activer la planification</label>
          </div>
        </div>
        <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3">
          <button @click="closeScheduleModal" class="btn-secondary">Annuler</button>
          <button @click="saveSchedule" class="btn-primary" :disabled="saving">
            {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Log Viewer Modal -->
    <div v-if="showLogModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-semibold text-gray-900">Logs de Vérification</h3>
          <button @click="showLogModal = false" class="text-gray-400 hover:text-gray-500">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="px-6 py-4">
          <pre class="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm">{{ selectedLog }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { backupVerificationsAPI, verificationSchedulesAPI, virtualMachinesAPI, esxiServersAPI } from '../services/api'
import { useToast } from 'vue-toastification'

const toast = useToast()

const activeTab = ref('verifications')
const verifications = ref([])
const schedules = ref([])
const virtualMachines = ref([])
const esxiServers = ref([])
const statistics = ref({})
const loading = ref(false)
const saving = ref(false)
const showCreateVerificationModal = ref(false)
const showCreateScheduleModal = ref(false)
const showLogModal = ref(false)
const selectedLog = ref('')
const editingSchedule = ref(null)

const verificationForm = ref({
  esxi_server: '',
  test_type: 'full',
  test_network: 'VM Network',
  test_datastore: ''
})

const scheduleForm = ref({
  name: '',
  virtual_machine: '',
  esxi_server: '',
  frequency: 'weekly',
  test_type: 'full',
  is_active: true
})

onMounted(() => {
  fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const [verificationsRes, schedulesRes, vmsRes, serversRes, statsRes] = await Promise.all([
      backupVerificationsAPI.getAll(),
      verificationSchedulesAPI.getAll(),
      virtualMachinesAPI.getAll(),
      esxiServersAPI.getAll(),
      backupVerificationsAPI.getStatistics()
    ])
    verifications.value = verificationsRes.data.results || verificationsRes.data
    schedules.value = schedulesRes.data.results || schedulesRes.data
    virtualMachines.value = vmsRes.data.results || vmsRes.data
    esxiServers.value = serversRes.data.results || serversRes.data
    statistics.value = statsRes.data
  } catch (error) {
    console.error('Erreur chargement données:', error)
    toast.error('Erreur lors du chargement des données')
  } finally {
    loading.value = false
  }
}

async function createVerification() {
  saving.value = true
  try {
    await backupVerificationsAPI.create(verificationForm.value)
    toast.success('Vérification lancée avec succès')
    showCreateVerificationModal.value = false
    fetchData()
  } catch (error) {
    console.error('Erreur création vérification:', error)
    toast.error('Erreur lors du lancement de la vérification')
  } finally {
    saving.value = false
  }
}

async function saveSchedule() {
  saving.value = true
  try {
    if (editingSchedule.value) {
      await verificationSchedulesAPI.update(editingSchedule.value.id, scheduleForm.value)
      toast.success('Planification mise à jour avec succès')
    } else {
      await verificationSchedulesAPI.create(scheduleForm.value)
      toast.success('Planification créée avec succès')
    }
    closeScheduleModal()
    fetchData()
  } catch (error) {
    console.error('Erreur sauvegarde planification:', error)
    toast.error('Erreur lors de la sauvegarde')
  } finally {
    saving.value = false
  }
}

function editSchedule(schedule) {
  editingSchedule.value = schedule
  scheduleForm.value = { ...schedule }
  showCreateScheduleModal.value = true
}

function closeScheduleModal() {
  showCreateScheduleModal.value = false
  editingSchedule.value = null
  scheduleForm.value = {
    name: '',
    virtual_machine: '',
    esxi_server: '',
    frequency: 'weekly',
    test_type: 'full',
    is_active: true
  }
}

async function toggleSchedule(schedule) {
  try {
    await verificationSchedulesAPI.toggleActive(schedule.id)
    toast.success(`Planification ${schedule.is_active ? 'désactivée' : 'activée'}`)
    fetchData()
  } catch (error) {
    console.error('Erreur toggle planification:', error)
    toast.error('Erreur lors de la modification')
  }
}

async function deleteSchedule(schedule) {
  if (!confirm(`Supprimer la planification "${schedule.name}" ?`)) return

  try {
    await verificationSchedulesAPI.delete(schedule.id)
    toast.success('Planification supprimée')
    fetchData()
  } catch (error) {
    console.error('Erreur suppression:', error)
    toast.error('Erreur lors de la suppression')
  }
}

function showLog(verification) {
  selectedLog.value = verification.detailed_log || 'Aucun log disponible'
  showLogModal.value = true
}

function getStatusClass(status) {
  const classes = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    passed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800'
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
