<template>
  <Dialog v-model:visible="visible" header="Load Gamut File" modal
          :style="{ width: '380px' }" @hide="reset">

    <div class="drop-zone" :class="{ 'drop-zone--over': dragging }"
         @dragover.prevent="dragging = true"
         @dragleave.prevent="dragging = false"
         @drop.prevent="handleDrop">
      <i class="pi pi-upload drop-zone__icon" />
      <span>Drop a CGATS file here, or</span>
      <a href="#" class="drop-zone__link" @click.prevent="fileInput.click()">browse</a>
      <input ref="fileInput" type="file" style="display:none"
             accept=".txt,.cgats,.csv" @change="handleSelect" />
    </div>

    <Message v-if="error" severity="error" :closable="false" class="mt-3">{{ error }}</Message>

    <template #footer>
      <Button label="Cancel" text @click="visible = false" :disabled="loading" />
    </template>
  </Dialog>
</template>

<script setup>
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { uploadGamut } from '../api.js'
import { useGamutStore } from '../stores/gamutStore.js'

const visible = defineModel({ type: Boolean, default: false })
const gamuts  = useGamutStore()

const dragging = ref(false)
const loading  = ref(false)
const error    = ref(null)
const fileInput = ref(null)

function reset() {
  error.value   = null
  loading.value = false
  dragging.value = false
}

async function upload(file) {
  loading.value = true
  error.value   = null
  try {
    const entry = await uploadGamut(file)
    gamuts.add(entry)
    visible.value = false
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
    dragging.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function handleDrop(e) { const f = e.dataTransfer.files[0]; if (f) upload(f) }
function handleSelect(e) { const f = e.target.files[0]; if (f) upload(f) }
</script>

<style scoped>
.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 2rem;
  border: 2px dashed var(--p-surface-300);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone--over {
  border-color: var(--p-primary-400);
  background: color-mix(in srgb, var(--p-primary-50) 60%, transparent);
}

.drop-zone__icon { font-size: 2rem; color: var(--p-surface-400); }
.drop-zone__link { color: var(--p-primary-500); }
.mt-3 { margin-top: 0.75rem; }
</style>
