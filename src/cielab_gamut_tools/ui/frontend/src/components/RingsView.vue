<template>
  <div class="rings-view">
    <!-- Content area — measured by ResizeObserver -->
    <div class="rings-view__content" ref="contentEl">
      <div v-if="!selection.dutId" class="rings-view__empty">
        Select a DUT gamut (D) to display rings
      </div>
      <div v-else-if="loading" class="rings-view__empty">
        <i class="pi pi-spin pi-spinner" /> Loading cylmap…
      </div>
      <div v-else-if="error" class="rings-view__empty rings-view__error">
        <i class="pi pi-exclamation-triangle" /> {{ error }}
      </div>
      <!-- Canvas is only rendered once squareSize is known -->
      <RingsCanvas
        v-else-if="squareSize > 0"
        :gamut="dutGamut"
        :ref-gamut="refGamut"
        :style="{ width: `${squareSize}px`, height: `${squareSize}px`, flexShrink: 0 }"
        @volume="onVolume"
      />
    </div>

    <!-- Info bar always visible below the content area -->
    <div class="rings-view__info">
      <span v-if="displayedVolume !== null">
        CGV: {{ Math.round(displayedVolume).toLocaleString() }}
      </span>
      <span v-if="refGamut && refName" class="rings-view__ref-label">
        vs {{ refName }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useGamutStore } from '../stores/gamutStore.js'
import { unpackCylmap } from '../gamut/cylmap.js'
import RingsCanvas from './RingsCanvas.vue'

const selection = useSelectionStore()
const gamuts = useGamutStore()

const contentEl = ref(null)
const squareSize = ref(0)

const loading = ref(false)
const error = ref(null)
const dutGamut = ref(null)
const refGamut = ref(null)
const refName = ref(null)
const displayedVolume = ref(null)

// Measure the content area and keep the canvas square within it
let ro = null
onMounted(() => {
  ro = new ResizeObserver(([entry]) => {
    const { width, height } = entry.contentRect
    squareSize.value = Math.max(0, Math.floor(Math.min(width, height)))
  })
  ro.observe(contentEl.value)
})
onUnmounted(() => ro?.disconnect())

function onVolume(v) {
  displayedVolume.value = v
}

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
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0.5rem;
  gap: 0.25rem;
}

.rings-view__content {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.rings-view__empty {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.rings-view__error {
  color: var(--p-red-500);
}

.rings-view__info {
  flex-shrink: 0;
  display: flex;
  gap: 1rem;
  justify-content: center;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  min-height: 1.2rem;
}

.rings-view__ref-label {
  font-style: italic;
}
</style>
