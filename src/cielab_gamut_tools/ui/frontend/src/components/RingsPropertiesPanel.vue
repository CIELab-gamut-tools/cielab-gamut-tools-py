<template>
  <div v-if="ui.activeView === 'rings'" class="rpp">
    <button class="rpp__header" @click="open = !open">
      <span class="rpp__title">Ring Options</span>
      <i class="pi" :class="open ? 'pi-chevron-down' : 'pi-chevron-right'" />
    </button>

    <div v-if="open" class="rpp__body">

      <!-- ── Display ─────────────────────────────────────────────── -->
      <div class="rpp__section-label">Display</div>

      <div class="rpp__row">
        <label class="rpp__label">Scale</label>
        <select class="rpp__select" :value="ui.ringsOptions.scale"
                @change="set('scale', $event.target.value)">
          <option value="">Auto</option>
          <option value="emissive">Emissive ±1250</option>
          <option value="150">Reflective 150</option>
          <option value="300">Reflective 300</option>
          <option value="600">Reflective 600</option>
        </select>
      </div>

      <div class="rpp__row">
        <label class="rpp__label" :class="{ 'rpp__label--dim': !hasRef }">Intersection</label>
        <input type="checkbox" :checked="ui.ringsOptions.intersection"
               :disabled="!hasRef"
               @change="set('intersection', $event.target.checked)" />
      </div>

      <!-- ── Colour bands ────────────────────────────────────────── -->
      <div class="rpp__section-label">Colour bands</div>

      <div class="rpp__row">
        <label class="rpp__label">Show bands</label>
        <input type="checkbox" :checked="ui.ringsOptions.showBands"
               @change="set('showBands', $event.target.checked)" />
      </div>

      <template v-if="ui.ringsOptions.showBands">
        <div class="rpp__row">
          <label class="rpp__label">Chroma</label>
          <input class="rpp__num" type="number" min="0" max="200" step="5"
                 :value="ui.ringsOptions.bandChroma"
                 @change="set('bandChroma', +$event.target.value)" />
        </div>
        <div class="rpp__row">
          <label class="rpp__label">L range</label>
          <input class="rpp__text" placeholder="20,90"
                 :value="ui.ringsOptions.bandLs"
                 @change="set('bandLs', $event.target.value)" />
        </div>
      </template>

      <!-- ── Primary indicators ─────────────────────────────────── -->
      <div class="rpp__section-label">Primary indicators</div>

      <div class="rpp__row">
        <label class="rpp__label">DUT prims</label>
        <select class="rpp__select" :value="ui.ringsOptions.primaries"
                @change="set('primaries', $event.target.value)">
          <option value="none">None</option>
          <option value="rgb">RGB</option>
          <option value="all">All (RGBCMY)</option>
        </select>
      </div>

      <div class="rpp__row">
        <label class="rpp__label">Ref prims</label>
        <select class="rpp__select" :value="ui.ringsOptions.refPrimaries"
                @change="set('refPrimaries', $event.target.value)">
          <option value="none">None</option>
          <option value="rgb">RGB</option>
          <option value="all">All (RGBCMY)</option>
        </select>
      </div>

      <template v-if="ui.ringsOptions.primaries !== 'none'">
        <div class="rpp__row">
          <label class="rpp__label">Arrow col</label>
          <select class="rpp__select" :value="ui.ringsOptions.primaryColor"
                  @change="set('primaryColor', $event.target.value)">
            <option value="output">Measured</option>
            <option value="input">Nominal</option>
          </select>
        </div>
        <div class="rpp__row">
          <label class="rpp__label">Origin</label>
          <select class="rpp__select" :value="ui.ringsOptions.primaryOrigin"
                  @change="set('primaryOrigin', $event.target.value)">
            <option value="centre">Centre</option>
            <option value="ring">Ring</option>
          </select>
        </div>
        <div class="rpp__row">
          <label class="rpp__label">Arrow C*</label>
          <input class="rpp__text" placeholder="auto"
                 :value="ui.ringsOptions.primaryChroma"
                 @change="set('primaryChroma', $event.target.value || 'auto')" />
        </div>
      </template>

      <div class="rpp__row">
        <label class="rpp__label">Centre mark</label>
        <input type="checkbox" :checked="ui.ringsOptions.showCentMark"
               @change="set('showCentMark', $event.target.checked)" />
      </div>

      <!-- ── Ring levels & labels ───────────────────────────────── -->
      <div class="rpp__section-label">Ring levels &amp; labels</div>

      <div class="rpp__row">
        <label class="rpp__label">L* rings</label>
        <input class="rpp__text" placeholder="10,20,…,90"
               :value="ui.ringsOptions.lRings"
               @change="set('lRings', $event.target.value)" />
      </div>

      <div class="rpp__row">
        <label class="rpp__label">Label at</label>
        <input class="rpp__text" placeholder="10,50 or none"
               :value="ui.ringsOptions.lLabels"
               @change="set('lLabels', $event.target.value)" />
      </div>

      <div class="rpp__row">
        <label class="rpp__label">Label col</label>
        <input class="rpp__text" placeholder="default"
               :value="ui.ringsOptions.lLabelColor"
               @change="set('lLabelColor', $event.target.value)" />
      </div>

      <div class="rpp__row">
        <label class="rpp__label">C* circles</label>
        <input class="rpp__text" placeholder="e.g. 500,1000"
               :value="ui.ringsOptions.chromaRings"
               @change="set('chromaRings', $event.target.value)" />
      </div>

      <!-- ── Title ──────────────────────────────────────────────── -->
      <div class="rpp__section-label">Title</div>

      <div class="rpp__row">
        <label class="rpp__label">Auto title</label>
        <input type="checkbox" :checked="ui.ringsOptions.autoTitle"
               @change="set('autoTitle', $event.target.checked)" />
      </div>

      <template v-if="!ui.ringsOptions.autoTitle">
        <div class="rpp__row">
          <input class="rpp__text rpp__text--full" placeholder="Title (blank = none)"
                 :value="ui.ringsOptions.customTitle"
                 @input="set('customTitle', $event.target.value)" />
        </div>
      </template>

      <div class="rpp__row">
        <label class="rpp__label">DUT label</label>
        <input class="rpp__text" placeholder="auto"
               :value="ui.ringsOptions.dutLabel"
               @change="set('dutLabel', $event.target.value)" />
      </div>

      <div class="rpp__row">
        <label class="rpp__label">Ref label</label>
        <input class="rpp__text" placeholder="auto"
               :value="ui.ringsOptions.refLabel"
               @change="set('refLabel', $event.target.value)" />
      </div>

      <!-- ── Figure ─────────────────────────────────────────────── -->
      <div class="rpp__section-label">Figure</div>

      <div class="rpp__row">
        <label class="rpp__label">DPI</label>
        <input class="rpp__num" type="number" min="72" max="600" step="1"
               :value="ui.ringsOptions.dpi"
               @change="set('dpi', +$event.target.value)" />
      </div>

      <!-- ── Render ─────────────────────────────────────────────── -->
      <button class="rpp__render-btn" :disabled="!hasDut" @click="ui.forceRender()">
        Render
      </button>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUiStore } from '../stores/uiStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'

const ui = useUiStore()
const selection = useSelectionStore()
const open = ref(true)

const hasDut = computed(() => !!selection.dutId)
const hasRef = computed(() => selection.referenceIds.length > 0)

function set(key, value) {
  ui.setRingsOption(key, value)
}
</script>

<style scoped>
.rpp {
  flex-shrink: 0;
  border-top: 1px solid var(--p-surface-200);
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 55vh;
}

.rpp__header {
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

.rpp__header:hover {
  background: var(--p-surface-100);
}

.rpp__title {
  flex: 1;
  text-align: left;
}

.rpp__body {
  overflow-y: auto;
  padding: 0.25rem 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.rpp__section-label {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--p-text-muted-color);
  margin-top: 0.4rem;
  margin-bottom: 0.1rem;
  border-bottom: 1px solid var(--p-surface-200);
  padding-bottom: 0.1rem;
}

.rpp__section-label:first-child {
  margin-top: 0;
}

.rpp__row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 20px;
}

.rpp__label {
  font-size: 0.72rem;
  color: var(--p-text-color);
  width: 68px;
  flex-shrink: 0;
}

.rpp__label--dim {
  color: var(--p-text-muted-color);
}

.rpp__select {
  flex: 1;
  font-size: 0.72rem;
  padding: 1px 3px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
}

.rpp__text {
  flex: 1;
  font-size: 0.72rem;
  padding: 1px 5px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
  outline: none;
  min-width: 0;
}

.rpp__text--full {
  width: 100%;
}

.rpp__text:focus {
  border-color: var(--p-primary-400);
}

.rpp__num {
  width: 56px;
  font-size: 0.72rem;
  padding: 1px 4px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
  outline: none;
}

.rpp__num:focus {
  border-color: var(--p-primary-400);
}

.rpp__render-btn {
  margin-top: 0.4rem;
  width: 100%;
  padding: 4px 0;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid var(--p-primary-400);
  border-radius: 4px;
  background: transparent;
  color: var(--p-primary-500);
  cursor: pointer;
  flex-shrink: 0;
}

.rpp__render-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--p-primary-50) 60%, transparent);
}

.rpp__render-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
