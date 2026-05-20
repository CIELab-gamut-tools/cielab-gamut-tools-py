<template>
  <div class="rings-view">
    <div v-if="!selection.dutId" class="rings-view__empty">
      Select a DUT gamut (D) to display rings
    </div>
    <div v-else-if="loading" class="rings-view__empty">
      <i class="pi pi-spin pi-spinner" /> Loading cylmap…
    </div>
    <div v-else-if="error" class="rings-view__empty rings-view__error">
      <i class="pi pi-exclamation-triangle" /> {{ error }}
    </div>
    <div v-else class="rings-view__content">
      <RingsCanvas
        :gamut="dutGamut"
        :ref-gamut="refGamut"
        @volume="onVolume"
        class="rings-view__canvas"
      />
      <div class="rings-view__info">
        <span v-if="displayedVolume !== null">
          CGV: {{ Math.round(displayedVolume).toLocaleString() }}
        </span>
        <span v-if="refGamut && refName" class="rings-view__ref-label">
          vs {{ refName }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useGamutStore } from '../stores/gamutStore.js'
import { unpackCylmap } from '../gamut/cylmap.js'
import RingsCanvas from './RingsCanvas.vue'

const selection = useSelectionStore()
const gamuts = useGamutStore()

const loading = ref(false)
const error = ref(null)
const dutGamut = ref(null)
const refGamut = ref(null)
const refName = ref(null)
const displayedVolume = ref(null)

function onVolume(v) {
  displayedVolume.value = v
}

// Reload whenever DUT or first reference changes
watch(
  [() => selection.dutId, () => selection.referenceIds[0]],
  async ([dutId, refId]) => {
    dutGamut.value = null
    refGamut.value = null
    refName.value = null
    displayedVolume.value = null
    error.value = null

    if (!dutId) return

    loading.value = true
    try {
      const rawDut = await gamuts.ensureCylmap(dutId)
      dutGamut.value = unpackCylmap(rawDut)

      if (refId) {
        const rawRef = await gamuts.ensureCylmap(refId)
        refGamut.value = unpackCylmap(rawRef)
        refName.value = gamuts.gamuts[refId]?.label ?? null
      }
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.rings-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0.5rem;
}

.rings-view__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.rings-view__error {
  color: var(--p-red-500);
}

.rings-view__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: auto;
}

.rings-view__canvas {
  max-width: min(100%, 640px);
  max-height: min(calc(100vh - 8rem), 640px);
}

.rings-view__info {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  margin-top: 0.25rem;
}

.rings-view__ref-label {
  font-style: italic;
}
</style>
