<template>
  <div class="surface-view">
    <div v-if="!hasSelection" class="surface-view__status">
      Select a gamut as a DUT [D] or reference [R] to view its surface
    </div>
    <div v-else-if="isLoading" class="surface-view__status">
      <i class="pi pi-spin pi-spinner" /> Loading surface…
    </div>
    <GamutSurfaceCanvas v-else
      :gamuts="activeGamuts"
      :perspectiveBlend="ui.surfaceOptions.perspectiveBlend"
      :cameraElev="ui.surfaceOptions.cameraElev"
      :cameraAzim="ui.surfaceOptions.cameraAzim"
      :cameraDistance="ui.surfaceOptions.cameraDistance"
      :colourSpace="ui.surfaceOptions.colourSpace"
      @camera-change="ui.setCameraAngle($event.elev, $event.azim, $event.dist)"
      class="surface-view__canvas" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useGamutStore } from '../stores/gamutStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useUiStore } from '../stores/uiStore.js'
import GamutSurfaceCanvas from './GamutSurfaceCanvas.vue'

const gamuts = useGamutStore()
const selection = useSelectionStore()
const ui = useUiStore()

const loadingCount = ref(0)

const activeIds = computed(() => {
  const ids = []
  if (selection.dutId) ids.push(selection.dutId)
  for (const id of selection.referenceIds) ids.push(id)
  return ids
})

const hasSelection = computed(() => activeIds.value.length > 0)

const isLoading = computed(
  () => loadingCount.value > 0 && activeGamuts.value.length === 0,
)

async function ensureOne(id) {
  if (gamuts.gamuts[id]?.surface) return
  loadingCount.value++
  try {
    await gamuts.ensureSurface(id)
  } finally {
    loadingCount.value--
  }
}

watch(activeIds, (ids) => {
  for (const id of ids) ensureOne(id)
}, { immediate: true })

const activeGamuts = computed(() =>
  activeIds.value
    .map(id => {
      const g = gamuts.gamuts[id]
      if (!g?.surface) return null
      const opts = ui.surfaceOptions.perGamut[id]
      return {
        id,
        colour:     g.colour,
        surface:    g.surface,
        visible:    opts?.visible    ?? true,
        alpha:      opts?.alpha      ?? 0.75,
        wireframe:  opts?.wireframe  ?? false,
        chroma:     opts?.chroma     ?? 1.0,
        lightness:  opts?.lightness  ?? null,
        edgeColour: opts?.edgeColour ?? null,
      }
    })
    .filter(Boolean),
)
</script>

<style scoped>
.surface-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.surface-view__status {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  gap: 6px;
}

.surface-view__canvas {
  flex: 1;
  min-height: 0;
  position: relative;
}
</style>
