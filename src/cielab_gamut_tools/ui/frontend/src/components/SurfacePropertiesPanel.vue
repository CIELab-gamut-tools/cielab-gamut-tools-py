<template>
  <div v-if="ui.activeView === 'surface'" class="spp">
    <button class="spp__header" @click="open = !open">
      <span class="spp__title">Surface Options</span>
      <i class="pi" :class="open ? 'pi-chevron-down' : 'pi-chevron-up'" />
    </button>

    <div v-if="open" class="spp__body">

      <!-- Projection -->
      <div class="spp__proj-row">
        <span class="spp__proj-label">Projection</span>
        <span class="spp__proj-end">Iso</span>
        <input class="spp__proj-slider" type="range" min="0" max="1" step="0.01"
               :value="ui.surfaceOptions.perspectiveBlend"
               @input="ui.setSurfacePerspective(+$event.target.value)" />
        <span class="spp__proj-end">Persp</span>
      </div>

      <!-- Camera angle -->
      <div class="spp__camera-row">
        <span class="spp__cam-label">Elevation</span>
        <input class="spp__angle-input" type="number"
               :value="ui.surfaceOptions.cameraElev"
               min="-85" max="85" step="1"
               @change="ui.setCameraAngle(+$event.target.value, ui.surfaceOptions.cameraAzim)" />
        <span class="spp__cam-unit">°</span>
        <span class="spp__cam-label">Azimuth</span>
        <input class="spp__angle-input" type="number"
               :value="ui.surfaceOptions.cameraAzim"
               min="-180" max="180" step="1"
               @change="ui.setCameraAngle(ui.surfaceOptions.cameraElev, +$event.target.value)" />
        <span class="spp__cam-unit">°</span>
      </div>

      <!-- Per-gamut controls -->
      <div v-if="activeGamuts.length === 0" class="spp__empty">
        No gamuts selected
      </div>
      <template v-else>
        <div v-for="g in activeGamuts" :key="g.id" class="spp__row">
          <span class="spp__swatch" :style="{ background: g.colour }" />
          <span class="spp__label" :title="g.label">{{ g.label }}</span>
          <button class="spp__eye" :title="opts(g.id).visible ? 'Hide' : 'Show'"
                  @click="ui.setSurfaceVisible(g.id, !opts(g.id).visible)">
            <i class="pi" :class="opts(g.id).visible ? 'pi-eye' : 'pi-eye-slash'" />
          </button>
          <button class="spp__wire"
                  :title="opts(g.id).wireframe ? 'Switch to solid' : 'Switch to wireframe'"
                  :class="{ 'spp__wire--active': opts(g.id).wireframe }"
                  @click="ui.setSurfaceWireframe(g.id, !opts(g.id).wireframe)">
            <i class="pi pi-th-large" />
          </button>
          <input class="spp__alpha" type="range" min="0.05" max="1" step="0.05"
                 :value="opts(g.id).alpha"
                 :disabled="!opts(g.id).visible"
                 @input="ui.setSurfaceAlpha(g.id, +$event.target.value)" />
          <span class="spp__alpha-val">{{ Math.round(opts(g.id).alpha * 100) }}%</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUiStore } from '../stores/uiStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useGamutStore } from '../stores/gamutStore.js'

const ui = useUiStore()
const selection = useSelectionStore()
const gamuts = useGamutStore()
const open = ref(true)

const activeGamuts = computed(() => {
  const ids = []
  if (selection.dutId) ids.push(selection.dutId)
  for (const id of selection.referenceIds) ids.push(id)
  return ids.map(id => gamuts.gamuts[id]).filter(Boolean)
})

function opts(id) {
  return ui.surfaceOptions.perGamut[id] ?? { visible: true, alpha: 0.75, wireframe: false }
}
</script>

<style scoped>
.spp {
  flex-shrink: 0;
  border-top: 1px solid var(--p-surface-200);
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 55vh;
}

.spp__header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.35rem 0.75rem;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--p-text-muted-color);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.spp__header:hover {
  background: var(--p-surface-100);
}

.spp__title {
  flex: 1;
  text-align: left;
}

.spp__body {
  overflow-y: auto;
  padding: 0.35rem 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.spp__empty {
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 0.25rem 0;
}

/* Projection row */
.spp__proj-row {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 0.4rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid var(--p-surface-200);
  margin-bottom: 0.1rem;
}

.spp__proj-label {
  font-size: 0.72rem;
  color: var(--p-text-color);
  flex-shrink: 0;
}

.spp__proj-end {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
  flex-shrink: 0;
}

.spp__proj-slider {
  flex: 1;
  width: 100%;
  cursor: pointer;
  accent-color: var(--p-primary-500);
}

/* Camera angle row */
.spp__camera-row {
  display: grid;
  grid-template-columns: auto auto auto auto auto auto;
  align-items: center;
  gap: 0.3rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid var(--p-surface-200);
  margin-bottom: 0.1rem;
}

.spp__cam-label {
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.spp__angle-input {
  width: 48px;
  font-size: 0.72rem;
  text-align: right;
  border: 1px solid var(--p-surface-300);
  border-radius: 3px;
  padding: 1px 3px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
}

.spp__angle-input:focus {
  outline: none;
  border-color: var(--p-primary-500);
}

.spp__cam-unit {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
}

/* Per-gamut row */
.spp__row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 22px;
}

.spp__swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
  border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
}

.spp__label {
  flex: 1;
  font-size: 0.72rem;
  color: var(--p-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.spp__eye,
.spp__wire {
  flex-shrink: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--p-text-muted-color);
  padding: 0 2px;
  font-size: 0.75rem;
  line-height: 1;
}

.spp__eye:hover,
.spp__wire:hover {
  color: var(--p-primary-500);
}

.spp__wire--active {
  color: var(--p-primary-500);
}

.spp__alpha {
  width: 60px;
  flex-shrink: 0;
  cursor: pointer;
  accent-color: var(--p-primary-500);
}

.spp__alpha:disabled {
  opacity: 0.35;
  cursor: default;
}

.spp__alpha-val {
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}
</style>
