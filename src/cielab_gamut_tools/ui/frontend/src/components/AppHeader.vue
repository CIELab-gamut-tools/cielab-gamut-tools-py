<template>
  <header class="app-header">
    <span class="app-header__title">CIELab Gamut Tools</span>
    <Button label="Export" icon="pi pi-download" size="small" outlined
            :disabled="!canExport"
            @click="ep.toggle($event)" />
    <ExportPanel ref="ep" />
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import Button from 'primevue/button'
import ExportPanel from './ExportPanel.vue'
import { useUiStore } from '../stores/uiStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'

const ui = useUiStore()
const selection = useSelectionStore()
const ep = ref(null)

const canExport = computed(() => {
  if (ui.activeView === 'rings') return !!selection.dutId
  if (ui.activeView === 'surface') return !!selection.dutId || selection.referenceIds.length > 0
  return false
})
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  height: 3rem;
  border-bottom: 1px solid var(--p-surface-200);
  background: var(--p-surface-0);
  flex-shrink: 0;
}

.app-header__title {
  font-weight: 600;
  font-size: 1rem;
}
</style>
