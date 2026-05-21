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
               min="-90" max="90" step="1"
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
        <div v-for="g in activeGamuts" :key="g.id" class="spp__card">

          <!-- Row 1: identity + mode controls -->
          <div class="spp__row1">
            <span class="spp__swatch" :style="{ background: g.colour }" />
            <span class="spp__label" :title="g.label">{{ g.label }}</span>
            <button class="spp__icon-btn" :title="opts(g.id).visible ? 'Hide' : 'Show'"
                    @click="ui.setSurfaceVisible(g.id, !opts(g.id).visible)">
              <i class="pi" :class="opts(g.id).visible ? 'pi-eye' : 'pi-eye-slash'" />
            </button>
            <button class="spp__icon-btn"
                    :title="opts(g.id).wireframe ? 'Switch to solid' : 'Switch to wireframe'"
                    :class="{ 'spp__icon-btn--active': opts(g.id).wireframe }"
                    @click="ui.setSurfaceWireframe(g.id, !opts(g.id).wireframe)">
              <i class="pi pi-th-large" />
            </button>
            <!-- Edge colour control — only shown in wireframe mode -->
            <span v-if="opts(g.id).wireframe" class="spp__ec">
              <label class="spp__ec-swatch"
                     :class="opts(g.id).edgeColour ? 'spp__ec-swatch--fixed' : 'spp__ec-swatch--lab'"
                     :style="opts(g.id).edgeColour ? { background: opts(g.id).edgeColour } : {}"
                     title="Edge colour (click to set fixed colour)">
                <span v-if="!opts(g.id).edgeColour" class="spp__ec-text">Lab</span>
                <input type="color" class="spp__ec-picker"
                       :value="opts(g.id).edgeColour ?? '#808080'"
                       @change="ui.setSurfaceEdgeColour(g.id, $event.target.value)" />
              </label>
              <button v-if="opts(g.id).edgeColour" class="spp__ec-reset"
                      title="Revert to Lab-derived colour"
                      @click.stop="ui.setSurfaceEdgeColour(g.id, null)">×</button>
            </span>
          </div>

          <!-- Row 2: α · C · L* controls -->
          <div class="spp__row2" :class="{ 'spp__row2--dim': !opts(g.id).visible }">
            <span class="spp__ctrl-lbl">α</span>
            <input class="spp__slider" type="range" min="0.05" max="1" step="0.05"
                   :value="opts(g.id).alpha"
                   :disabled="!opts(g.id).visible"
                   @input="ui.setSurfaceAlpha(g.id, +$event.target.value)" />
            <span class="spp__ctrl-val">{{ Math.round(opts(g.id).alpha * 100) }}%</span>

            <span class="spp__ctrl-lbl">C</span>
            <input class="spp__slider" type="range" min="0" max="2" step="0.05"
                   :value="opts(g.id).chroma"
                   :disabled="!opts(g.id).visible"
                   @input="ui.setSurfaceChroma(g.id, +$event.target.value)" />
            <span class="spp__ctrl-val">{{ opts(g.id).chroma.toFixed(2) }}</span>

            <span class="spp__ctrl-lbl">L*</span>
            <input class="spp__slider" type="range" min="0" max="100" step="1"
                   :value="opts(g.id).lightness ?? 50"
                   :class="{ 'spp__slider--auto': opts(g.id).lightness === null }"
                   :disabled="!opts(g.id).visible"
                   @input="ui.setSurfaceLightness(g.id, +$event.target.value)" />
            <span class="spp__ctrl-val spp__l-val">
              <template v-if="opts(g.id).lightness === null">
                <span class="spp__auto-lbl">auto</span>
              </template>
              <template v-else>
                {{ opts(g.id).lightness }}
                <button class="spp__l-reset" title="Reset to auto"
                        @click="ui.setSurfaceLightness(g.id, null)">×</button>
              </template>
            </span>
          </div>

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
  return {
    visible: true, alpha: 0.75, wireframe: false,
    chroma: 1.0, lightness: null, edgeColour: null,
    ...ui.surfaceOptions.perGamut[id],
  }
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
.spp__header:hover { background: var(--p-surface-100); }
.spp__title { flex: 1; text-align: left; }

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
.spp__proj-label { font-size: 0.72rem; color: var(--p-text-color); }
.spp__proj-end   { font-size: 0.65rem; color: var(--p-text-muted-color); flex-shrink: 0; }
.spp__proj-slider { width: 100%; cursor: pointer; accent-color: var(--p-primary-500); }

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
.spp__cam-label { font-size: 0.68rem; color: var(--p-text-muted-color); white-space: nowrap; }
.spp__cam-unit  { font-size: 0.65rem; color: var(--p-text-muted-color); }
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
.spp__angle-input:focus { outline: none; border-color: var(--p-primary-500); }

/* Per-gamut card */
.spp__card {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.2rem 0;
  border-bottom: 1px solid var(--p-surface-100);
}
.spp__card:last-child { border-bottom: none; }

/* Row 1 */
.spp__row1 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 22px;
}
.spp__swatch {
  width: 10px; height: 10px;
  border-radius: 2px; flex-shrink: 0;
  border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
}
.spp__label {
  flex: 1;
  font-size: 0.72rem;
  color: var(--p-text-color);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  min-width: 0;
}
.spp__icon-btn {
  flex-shrink: 0;
  background: transparent; border: none; cursor: pointer;
  color: var(--p-text-muted-color);
  padding: 0 2px; font-size: 0.75rem; line-height: 1;
}
.spp__icon-btn:hover      { color: var(--p-primary-500); }
.spp__icon-btn--active    { color: var(--p-primary-500); }

/* Edge colour controls */
.spp__ec { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.spp__ec-swatch {
  position: relative;
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 14px;
  border-radius: 2px; cursor: pointer;
  border: 1px solid var(--p-surface-300);
  overflow: hidden;
}
.spp__ec-swatch--lab  { background: var(--p-surface-100); }
.spp__ec-text { font-size: 0.6rem; color: var(--p-text-muted-color); pointer-events: none; }
.spp__ec-picker {
  position: absolute; inset: 0; opacity: 0;
  cursor: pointer; width: 100%; height: 100%; padding: 0; border: none;
}
.spp__ec-reset {
  background: transparent; border: none; cursor: pointer;
  color: var(--p-text-muted-color); font-size: 0.75rem;
  padding: 0; line-height: 1; flex-shrink: 0;
}
.spp__ec-reset:hover { color: var(--p-primary-500); }

/* Row 2: α / C / L* — one control per line */
.spp__row2 {
  display: grid;
  grid-template-columns: 14px 1fr 30px;
  align-items: center;
  gap: 0.18rem 0.3rem;
  padding-left: 14px;
}
.spp__row2--dim { opacity: 0.4; pointer-events: none; }

.spp__ctrl-lbl {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
  text-align: center;
}
.spp__slider {
  width: 100%; cursor: pointer;
  accent-color: var(--p-primary-500);
}
.spp__slider:disabled   { opacity: 0.35; cursor: default; }
.spp__slider--auto      { opacity: 0.45; }
.spp__ctrl-val {
  font-size: 0.65rem; color: var(--p-text-muted-color);
  text-align: right; white-space: nowrap;
}
/* L* value cell — holds either "auto" label or number + reset button */
.spp__l-val {
  display: flex; align-items: center; justify-content: flex-end;
  gap: 1px;
}
.spp__auto-lbl {
  font-size: 0.6rem; font-style: italic;
  color: var(--p-text-muted-color);
}
.spp__l-reset {
  background: transparent; border: none; cursor: pointer;
  color: var(--p-text-muted-color); font-size: 0.75rem;
  padding: 0; line-height: 1; flex-shrink: 0;
}
.spp__l-reset:hover { color: var(--p-primary-500); }
</style>
