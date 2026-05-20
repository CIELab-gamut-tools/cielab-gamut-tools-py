<template>
  <aside class="gamut-sidebar">
    <div class="gamut-sidebar__header">
      <span class="gamut-sidebar__title">Gamuts</span>
      <button class="gamut-sidebar__add" title="Add gamut" @click="showAdd = true">
        <i class="pi pi-plus" />
      </button>
    </div>

    <div v-if="loading" class="gamut-sidebar__status">
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
  </aside>

  <AddGamutModal v-model="showAdd" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useGamutStore } from '../stores/gamutStore.js'
import GamutItem from './GamutItem.vue'
import AddGamutModal from './AddGamutModal.vue'

const gamuts = useGamutStore()
const loading = ref(false)
const fetchError = ref(null)
const showAdd = ref(false)

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
  overflow-y: auto;
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

.gamut-sidebar__list {
  flex: 1;
  overflow-y: auto;
}

.gamut-sidebar__status {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.gamut-sidebar__status--error {
  color: var(--p-red-500);
  padding: 1rem;
  text-align: center;
}
</style>
