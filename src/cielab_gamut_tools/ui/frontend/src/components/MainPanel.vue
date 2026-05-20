<template>
  <main class="main-panel">
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
          <div class="main-panel__placeholder">Surface view — coming in Stage 5</div>
        </TabPanel>
        <TabPanel value="analysis">
          <div class="main-panel__placeholder">Analysis view — coming in Stage 6</div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </main>
</template>

<script setup>
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { useUiStore } from '../stores/uiStore.js'
import RingsView from './RingsView.vue'

const ui = useUiStore()
</script>

<style scoped>
.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

.main-panel__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}
</style>
