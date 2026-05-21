<template>
  <main class="main-panel" v-bind="dropHandlers">
    <Tabs :value="ui.activeView" @update:value="ui.setView" class="main-panel__tabs">
      <TabList>
        <Tab value="rings">Rings</Tab>
        <Tab value="surface">Surface</Tab>
        <Tab value="analysis">Analysis</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="rings">
          <RingsView />
        </TabPanel>
        <TabPanel value="surface">
          <SurfaceView />
        </TabPanel>
        <TabPanel value="analysis">
          <AnalysisView />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <Transition name="drop-fade">
      <div v-if="isDragging || isUploading" class="main-panel__drop-overlay"
           :class="{ 'main-panel__drop-overlay--uploading': isUploading }">
        <i :class="isUploading ? 'pi pi-spin pi-spinner' : 'pi pi-upload'" />
        <span>{{ isUploading ? 'Uploading…' : 'Drop to add as DUT' }}</span>
      </div>
    </Transition>

    <Transition name="drop-fade">
      <div v-if="dropError" class="main-panel__drop-error">
        <i class="pi pi-exclamation-triangle" /> {{ dropError }}
      </div>
    </Transition>
  </main>
</template>

<script setup>
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { useUiStore } from '../stores/uiStore.js'
import { useGamutStore } from '../stores/gamutStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'
import RingsView from './RingsView.vue'
import SurfaceView from './SurfaceView.vue'
import AnalysisView from './AnalysisView.vue'
import { useFileDrop } from '../composables/useFileDrop.js'

const ui = useUiStore()
const gamuts = useGamutStore()
const selection = useSelectionStore()

const { isDragging, isUploading, error: dropError, dropHandlers } = useFileDrop(entry => {
  gamuts.add(entry)
  selection.setDut(entry.id)
})
</script>

<style scoped>
.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.main-panel__drop-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: color-mix(in srgb, var(--p-primary-50) 85%, transparent);
  border: 3px dashed var(--p-primary-400);
  border-radius: 4px;
  pointer-events: none;
  z-index: 10;
  font-size: 1rem;
  color: var(--p-primary-600);
}

.main-panel__drop-overlay .pi {
  font-size: 2rem;
}

.main-panel__drop-overlay--uploading {
  background: color-mix(in srgb, var(--p-surface-100) 85%, transparent);
  border-style: solid;
  border-color: var(--p-surface-300);
  color: var(--p-text-muted-color);
}

.main-panel__drop-error {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  background: var(--p-red-50);
  border: 1px solid var(--p-red-300);
  border-radius: 6px;
  padding: 0.5rem 1rem;
  color: var(--p-red-700);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 10;
  white-space: nowrap;
}

.drop-fade-enter-active,
.drop-fade-leave-active {
  transition: opacity 0.15s ease;
}

.drop-fade-enter-from,
.drop-fade-leave-to {
  opacity: 0;
}

.main-panel__tabs {
  flex: 1;
  min-height: 0;
}

/* Thread height through PrimeVue's internal Tabs elements */
:deep(.p-tabs) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

:deep(.p-tabpanels) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

:deep(.p-tabpanel) {
  height: 100%;
  display: none;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

:deep(.p-tabpanel.p-tabpanel-active) {
  display: flex;
}
</style>
