<template>
  <main class="main-panel">
    <TabView v-model:activeIndex="activeIndex" class="main-panel__tabs">
      <TabPanel header="Rings">
        <RingsView />
      </TabPanel>
      <TabPanel header="Surface">
        <div class="main-panel__placeholder">Surface view — coming in Stage 5</div>
      </TabPanel>
      <TabPanel header="Analysis">
        <div class="main-panel__placeholder">Analysis view — coming in Stage 6</div>
      </TabPanel>
    </TabView>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import { useUiStore } from '../stores/uiStore.js'
import RingsView from './RingsView.vue'

const ui = useUiStore()

const VIEWS = ['rings', 'surface', 'analysis']

const activeIndex = computed({
  get: () => VIEWS.indexOf(ui.activeView),
  set: (i) => ui.setView(VIEWS[i] ?? 'rings'),
})
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

/* Thread height through PrimeVue's internal TabView elements */
:deep(.p-tabview) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

:deep(.p-tabview-panels) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

:deep(.p-tabview-panel) {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
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
