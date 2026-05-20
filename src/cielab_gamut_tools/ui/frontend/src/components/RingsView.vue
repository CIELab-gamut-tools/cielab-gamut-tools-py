<template>
  <div class="rings-view">
    <div class="rings-view__content">
      <div v-if="!selection.dutId" class="rings-view__empty">
        Select a DUT gamut (D) to display rings
      </div>
      <div v-else-if="!imageUrl && rendering" class="rings-view__empty">
        <i class="pi pi-spin pi-spinner" /> Rendering…
      </div>
      <div v-else-if="error" class="rings-view__empty rings-view__error">
        <i class="pi pi-exclamation-triangle" /> {{ error }}
      </div>
      <template v-else-if="imageUrl">
        <!-- Spinner overlay on top of stale image while re-rendering -->
        <div v-if="rendering" class="rings-view__spinner-overlay">
          <i class="pi pi-spin pi-spinner" />
        </div>
        <img class="rings-view__img"
             :src="imageUrl"
             alt="Gamut rings plot"
             draggable="false" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useUiStore } from '../stores/uiStore.js'
import { renderRings } from '../api.js'

const selection = useSelectionStore()
const ui = useUiStore()

const imageUrl = ref(null)
const rendering = ref(false)
const error = ref(null)

let prevUrl = null
let renderToken = 0
let debounceTimer = null

function buildOptions() {
  const o = ui.ringsOptions
  return {
    dut_id: selection.dutId,
    reference_ids: [...selection.referenceIds],
    scale: o.scale || null,
    intersection: o.intersection && selection.referenceIds.length > 0,
    l_rings: o.lRings,
    show_bands: o.showBands,
    band_chroma: o.bandChroma,
    band_ls: o.bandLs,
    primaries: o.primaries,
    ref_primaries: o.refPrimaries,
    primary_color: o.primaryColor,
    primary_origin: o.primaryOrigin,
    show_cent_mark: o.showCentMark,
    l_labels: o.lLabels,
    l_label_color: o.lLabelColor,
    chroma_rings: o.chromaRings,
    dut_label: o.dutLabel,
    ref_label: o.refLabel,
    title: o.autoTitle ? 'auto' : (o.customTitle || null),
    dpi: o.dpi,
    format: 'png',
  }
}

function scheduleRender() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(doRender, 400)
}

async function doRender() {
  if (!selection.dutId) {
    imageUrl.value = null
    error.value = null
    return
  }
  const token = ++renderToken
  rendering.value = true
  error.value = null
  try {
    const blob = await renderRings(buildOptions())
    if (token !== renderToken) return
    if (prevUrl) { URL.revokeObjectURL(prevUrl); prevUrl = null }
    prevUrl = URL.createObjectURL(blob)
    imageUrl.value = prevUrl
  } catch (e) {
    if (token !== renderToken) return
    error.value = e.message
  } finally {
    if (token === renderToken) rendering.value = false
  }
}

watch(
  [
    () => selection.dutId,
    () => selection.referenceIds.length,
    () => selection.referenceIds.join(','),
    () => ui.ringsOptions.scale,
    () => ui.ringsOptions.intersection,
    () => ui.ringsOptions.lRings,
    () => ui.ringsOptions.showBands,
    () => ui.ringsOptions.bandChroma,
    () => ui.ringsOptions.bandLs,
    () => ui.ringsOptions.primaries,
    () => ui.ringsOptions.refPrimaries,
    () => ui.ringsOptions.primaryColor,
    () => ui.ringsOptions.primaryOrigin,
    () => ui.ringsOptions.showCentMark,
    () => ui.ringsOptions.lLabels,
    () => ui.ringsOptions.lLabelColor,
    () => ui.ringsOptions.chromaRings,
    () => ui.ringsOptions.dutLabel,
    () => ui.ringsOptions.refLabel,
    () => ui.ringsOptions.autoTitle,
    () => ui.ringsOptions.customTitle,
    () => ui.ringsOptions.dpi,
    () => ui.ringsRenderCounter,
  ],
  scheduleRender,
  { immediate: true },
)

onUnmounted(() => {
  clearTimeout(debounceTimer)
  if (prevUrl) URL.revokeObjectURL(prevUrl)
})
</script>

<style scoped>
.rings-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rings-view__content {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 0.5rem;
}

.rings-view__img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}

.rings-view__spinner-overlay {
  position: absolute;
  top: 0.5rem;
  right: 0.75rem;
  font-size: 0.875rem;
  color: var(--p-primary-500);
  opacity: 0.8;
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
</style>
