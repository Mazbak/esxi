<template>
  <Modal :show="show" :title="isEdit ? 'Modifier le serveur ESXi' : 'Ajouter un serveur ESXi'" @close="$emit('close')">
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label class="label">Nom d'hôte / IP</label>
        <input
          v-model="form.hostname"
          type="text"
          required
          class="input-field"
          placeholder="esxi.example.com ou 192.168.1.100"
        >
      </div>

      <div>
        <label class="label">Nom d'utilisateur</label>
        <input
          v-model="form.username"
          type="text"
          required
          class="input-field"
          placeholder="root"
        >
      </div>

      <div>
        <label class="label">Mot de passe</label>
        <input
          v-model="form.password"
          type="password"
          required
          class="input-field"
          placeholder="••••••••"
        >
      </div>

      <div>
        <label class="label">Port</label>
        <input
          v-model.number="form.port"
          type="number"
          required
          class="input-field"
          placeholder="443"
        >
      </div>

      <div class="flex items-center">
        <input
          v-model="form.is_active"
          type="checkbox"
          id="is_active"
          class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
        >
        <label for="is_active" class="ml-2 block text-sm text-gray-700">
          Serveur actif
        </label>
      </div>

      <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ error }}</p>
      </div>
    </form>

    <template #footer>
      <button type="button" @click="$emit('close')" class="btn-secondary">
        Annuler
      </button>
      <button
        type="button"
        @click="handleSubmit"
        :disabled="loading"
        class="btn-primary"
        :class="{ 'opacity-50 cursor-not-allowed': loading }"
      >
        {{ loading ? 'Enregistrement...' : (isEdit ? 'Mettre à jour' : 'Ajouter') }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import Modal from '@/components/common/Modal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  server: {
    type: Object,
    default: null
  },
  isEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'submit'])

const loading = ref(false)
const error = ref(null)

const form = reactive({
  hostname: '',
  username: '',
  password: '',
  port: 443,
  is_active: true
})

watch(() => props.server, (newServer) => {
  if (newServer) {
    form.hostname = newServer.hostname || ''
    form.username = newServer.username || ''
    form.password = newServer.password || ''
    form.port = newServer.port || 443
    form.is_active = newServer.is_active !== undefined ? newServer.is_active : true
  }
}, { immediate: true })

async function handleSubmit() {
  error.value = null
  loading.value = true

  try {
    await emit('submit', { ...form })
    resetForm()
  } catch (err) {
    error.value = err.message || 'Une erreur est survenue'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.hostname = ''
  form.username = ''
  form.password = ''
  form.port = 443
  form.is_active = true
}
</script>
