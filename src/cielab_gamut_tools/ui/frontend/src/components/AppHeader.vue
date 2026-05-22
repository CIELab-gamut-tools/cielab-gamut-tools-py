<template>
  <header class="app-header">
    <span class="app-header__title">CIELab Gamut Tools</span>
    <div class="app-header__actions">
      <Button label="Export" icon="pi pi-download" size="small" outlined
              :disabled="!canExport"
              @click="ep.toggle($event)" />
      <Button icon="pi pi-info-circle" size="small" text rounded aria-label="About"
              @click="showAbout = true" />
      <Button icon="pi pi-power-off" size="small" text rounded aria-label="Close"
              severity="danger"
              @click="handleClose" />
    </div>
    <ExportPanel ref="ep" />
    <AboutDialog v-model="showAbout" />
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import Button from 'primevue/button'
import ExportPanel from './ExportPanel.vue'
import AboutDialog from './AboutDialog.vue'
import { useUiStore } from '../stores/uiStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'
import { closeKeepalive } from '../api.js'

const ui = useUiStore()
const selection = useSelectionStore()
const ep = ref(null)
const showAbout = ref(false)

const canExport = computed(() => {
  if (ui.activeView === 'rings') return !!selection.dutId
  if (ui.activeView === 'surface') return !!selection.dutId || selection.referenceIds.length > 0
  return false
})

function handleClose() {
  ui.clientClosing = true
  // Fire DELETE without awaiting — keepalive:true ensures it's sent even on unload.
  // A 200 ms delay before window.close() gives the request time to leave the browser.
  closeKeepalive().catch(() => {})
  setTimeout(() => window.close(), 500)
}
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

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
</style>
