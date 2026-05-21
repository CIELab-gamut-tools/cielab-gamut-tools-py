<template>
  <div class="av">
    <VolumeTable />
    <CoverageMatrix />
  </div>
</template>

<script setup>
import { watch } from 'vue'
import VolumeTable from './VolumeTable.vue'
import CoverageMatrix from './CoverageMatrix.vue'
import { useGamutStore } from '../stores/gamutStore.js'
import { useUiStore } from '../stores/uiStore.js'

const gamuts = useGamutStore()
const ui = useUiStore()

// Auto-include new gamuts as both DUT and reference; clean up removed ones.
watch(
  () => gamuts.list.map(g => g.id),
  (ids, prevIds) => {
    const prev = new Set(prevIds ?? [])
    const curr = new Set(ids)
    for (const id of ids) {
      if (!prev.has(id)) ui.initAnalysisGamut(id)
    }
    for (const id of (prevIds ?? [])) {
      if (!curr.has(id)) ui.removeAnalysisGamut(id)
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.av {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
</style>
