<template>
  <aside class="gamut-sidebar" :class="{ 'gamut-sidebar--drop': isDragging }"
         v-bind="dropHandlers">
    <div class="gamut-sidebar__header">
      <span class="gamut-sidebar__title">Gamuts</span>
      <button class="gamut-sidebar__add" title="Add gamut" @click="showAdd = true">
        <i class="pi pi-plus" />
      </button>
    </div>

    <div class="gamut-sidebar__list-area">
      <div v-if="isUploading" class="gamut-sidebar__status">
        <i class="pi pi-spin pi-spinner" /> Uploading…
      </div>
      <div v-else-if="dropError" class="gamut-sidebar__status gamut-sidebar__status--error">
        <i class="pi pi-exclamation-triangle" /> {{ dropError }}
      </div>
      <div v-else-if="loading" class="gamut-sidebar__status">
        <i class="pi pi-spin pi-spinner" /> Loading…
      </div>
      <div v-else-if="fetchError" class="gamut-sidebar__status gamut-sidebar__status--error">
        <i class="pi pi-exclamation-triangle" /> {{ fetchError }}
      </div>
      <div v-else-if="gamuts.list.length === 0" class="gamut-sidebar__status">
        No gamuts loaded
      </div>
      <div v-else class="gamut-sidebar__list">
        <GamutItem v-for="g in gamuts.list" :key="g.id" :gamut="g" />
      </div>

      <div v-if="isDragging" class="gamut-sidebar__drop-overlay">
        <i class="pi pi-upload" />
        <span>Add gamut</span>
      </div>
    </div>

    <RingsPropertiesPanel />
  </aside>

  <AddGamutModal v-model="showAdd" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useGamutStore } from '../stores/gamutStore.js'
import GamutItem from './GamutItem.vue'
import AddGamutModal from './AddGamutModal.vue'
import RingsPropertiesPanel from './RingsPropertiesPanel.vue'
import { useFileDrop } from '../composables/useFileDrop.js'

const gamuts = useGamutStore()
const loading = ref(false)
const fetchError = ref(null)
const showAdd = ref(false)

const { isDragging, isUploading, error: dropError, dropHandlers } = useFileDrop(entry => {
  gamuts.add(entry)
})

onMounted(async () => {
  loading.value = true
  fetchError.value = null
  try {
    await gamuts.fetchList()
  } catch (e) {
    fetchError.value = 'Cannot reach server — is the API running?'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.gamut-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--p-surface-200);
  background: var(--p-surface-50);
  overflow: hidden;
}

.gamut-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid var(--p-surface-200);
  flex-shrink: 0;
}

.gamut-sidebar__title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
}

.gamut-sidebar__add {
  width: 22px;
  height: 22px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}

.gamut-sidebar__add:hover {
  border-color: var(--p-primary-400);
  color: var(--p-primary-500);
}

.gamut-sidebar__list-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  position: relative;
}

.gamut-sidebar__list {
  /* GamutItems stack naturally */
}

.gamut-sidebar__status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.gamut-sidebar__status--error {
  color: var(--p-red-500);
  text-align: center;
}

.gamut-sidebar--drop {
  border-right-color: var(--p-primary-400);
}

.gamut-sidebar__drop-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: color-mix(in srgb, var(--p-primary-50) 80%, transparent);
  border: 2px dashed var(--p-primary-400);
  border-radius: 4px;
  pointer-events: none;
  font-size: 0.85rem;
  color: var(--p-primary-600);
}

.gamut-sidebar__drop-overlay .pi {
  font-size: 1.4rem;
}
</style>
