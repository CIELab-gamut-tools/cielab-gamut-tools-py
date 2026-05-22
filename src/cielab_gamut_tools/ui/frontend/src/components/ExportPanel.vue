<template>
  <Popover ref="pop">
    <div class="ep">
      <div class="ep__title">Export {{ viewLabel }}</div>

      <!-- Source picker — surface view only -->
      <div v-if="ui.activeView === 'surface'" class="ep__row">
        <label class="ep__label">Source</label>
        <select class="ep__select" :value="ui.exportOptions.surfaceSource"
                @change="ui.setExportOption('surfaceSource', $event.target.value)">
          <option value="python">Plot</option>
          <option value="canvas">Screenshot</option>
        </select>
      </div>

      <!-- Format + DPI — not relevant for canvas capture -->
      <template v-if="showFormatDpi">
        <div class="ep__row">
          <label class="ep__label">Format</label>
          <select class="ep__select" :value="ui.exportOptions.format"
                  @change="ui.setExportOption('format', $event.target.value)">
            <option value="png">PNG</option>
            <option value="pdf">PDF</option>
          </select>
        </div>

        <div class="ep__row">
          <label class="ep__label">DPI</label>
          <input class="ep__num" type="number" min="72" max="600" step="1"
                 :value="ui.exportOptions.dpi"
                 @change="ui.setExportOption('dpi', +$event.target.value)" />
        </div>
      </template>

      <button class="ep__btn" :disabled="busy" @click="doExport">
        <i v-if="busy" class="pi pi-spin pi-spinner" style="margin-right:4px" />
        {{ busy ? 'Downloading…' : 'Download' }}
      </button>

      <div v-if="error" class="ep__error">{{ error }}</div>
    </div>
  </Popover>
</template>

<script setup>
import { ref, computed } from 'vue'
import Popover from 'primevue/popover'
import { useUiStore } from '../stores/uiStore.js'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useGamutStore } from '../stores/gamutStore.js'
import { useCanvasCapture } from '../composables/useCanvasCapture.js'
import { downloadRings, downloadSurface } from '../api.js'

const ui = useUiStore()
const selection = useSelectionStore()
const gamuts = useGamutStore()
const { captureCanvas } = useCanvasCapture()

const pop = ref(null)
const busy = ref(false)
const error = ref(null)

const viewLabel = computed(() => ui.activeView === 'rings' ? 'rings' : 'surface')

const showFormatDpi = computed(() =>
  ui.activeView !== 'surface' || ui.exportOptions.surfaceSource !== 'canvas'
)

function toggle(event) {
  error.value = null
  pop.value.toggle(event)
}

defineExpose({ toggle })

function buildRingsOptions() {
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
    primary_chroma: o.primaryChroma,
    show_cent_mark: o.showCentMark,
    l_labels: o.lLabels,
    l_label_color: o.lLabelColor,
    chroma_rings: o.chromaRings,
    dut_label: o.dutLabel,
    ref_label: o.refLabel,
    title: o.autoTitle ? 'auto' : (o.customTitle || null),
    dpi: ui.exportOptions.dpi,
    format: ui.exportOptions.format,
    download: true,
  }
}

function buildSurfaceOptions() {
  const ids = [selection.dutId, ...selection.referenceIds].filter(Boolean)
  const showLegend = ids.length > 1

  const gamutList = ids
    .map(id => {
      const g = gamuts.gamuts[id]
      const opts = {
        visible: true, alpha: 0.75, wireframe: false,
        chroma: 1.0, lightness: null, edgeColour: null,
        ...ui.surfaceOptions.perGamut[id],
      }
      if (!opts.visible) return null
      return {
        id,
        alpha: opts.alpha,
        wireframe: opts.wireframe,
        chroma: opts.wireframe ? opts.chroma : null,
        lightness: opts.wireframe ? opts.lightness : null,
        edge_colour: opts.wireframe ? (opts.edgeColour ?? null) : null,
        label: showLegend ? (g?.label || g?.name || id) : null,
      }
    })
    .filter(Boolean)

  return {
    gamuts: gamutList,
    format: ui.exportOptions.format,
    dpi: ui.exportOptions.dpi,
    elev: ui.surfaceOptions.cameraElev,
    azim: ui.surfaceOptions.cameraAzim,
    show_legend: showLegend,
  }
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function doExport() {
  busy.value = true
  error.value = null
  try {
    if (ui.activeView === 'rings') {
      await downloadRings(buildRingsOptions())
    } else if (ui.exportOptions.surfaceSource === 'canvas') {
      if (!captureCanvas.value) throw new Error('Canvas not available')
      const blob = await captureCanvas.value()
      triggerBlobDownload(blob, 'surface.png')
    } else {
      await downloadSurface(buildSurfaceOptions())
    }
    pop.value?.hide()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.ep {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.25rem 0;
  min-width: 160px;
}

.ep__title {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-text-muted-color);
  margin-bottom: 0.1rem;
}

.ep__row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.ep__label {
  font-size: 0.72rem;
  color: var(--p-text-color);
  width: 44px;
  flex-shrink: 0;
}

.ep__select {
  flex: 1;
  font-size: 0.72rem;
  padding: 2px 4px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
}

.ep__num {
  width: 64px;
  font-size: 0.72rem;
  padding: 2px 4px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
  outline: none;
}

.ep__num:focus {
  border-color: var(--p-primary-400);
}

.ep__btn {
  margin-top: 0.2rem;
  width: 100%;
  padding: 5px 0;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid var(--p-primary-400);
  border-radius: 4px;
  background: transparent;
  color: var(--p-primary-500);
  cursor: pointer;
}

.ep__btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--p-primary-50) 60%, transparent);
}

.ep__btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.ep__error {
  font-size: 0.68rem;
  color: var(--p-red-500);
  word-break: break-word;
}
</style>
