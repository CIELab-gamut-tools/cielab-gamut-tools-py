<template>
  <Dialog v-model:visible="visible"
          header="Synthetic Gamut"
          modal
          :style="{ width: '920px', maxHeight: '90vh' }"
          :contentStyle="{ overflow: 'hidden' }"
          @hide="onHide">

    <div class="add-modal__synth-body">

      <!-- Left column: controls -->
      <div class="add-modal__synth-left">

        <div class="add-modal__row">
          <label class="add-modal__lbl">Name</label>
          <input class="add-modal__input add-modal__input--wide" type="text"
                 :value="synthName" @input="synthName = $event.target.value"
                 placeholder="Custom gamut" />
        </div>

        <div class="add-modal__row">
          <label class="add-modal__lbl">Preset</label>
          <select class="add-modal__select" :value="primPreset"
                  @change="applyPrimPreset($event.target.value)">
            <option v-for="(p, k) in PRIM_PRESETS" :key="k" :value="k">{{ p.label }}</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <ChromaticityDiagram class="add-modal__diag"
          :r="primR" :g="primG" :b="primB" :w="white"
          @update:r="v => setPrim('r', v)" @update:g="v => setPrim('g', v)"
          @update:b="v => setPrim('b', v)" @update:w="v => setWhite(v)" />

        <!-- Primary + white coordinate table -->
        <table class="add-modal__coord-table">
          <thead>
            <tr>
              <th>Colour</th>
              <th>CIE 1931 x</th>
              <th>CIE 1931 y</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in coordRows" :key="row.key">
              <td :class="['add-modal__clr', `add-modal__clr--${row.key}`]">{{ row.label }}</td>
              <td>
                <input class="add-modal__coord" type="number" step="0.0001" min="0" max="0.9"
                       :value="fmt(row.val[0])"
                       @change="setCoord(row.key, 0, +$event.target.value)" />
              </td>
              <td>
                <input class="add-modal__coord" type="number" step="0.0001" min="0" max="0.9"
                       :value="fmt(row.val[1])"
                       @change="setCoord(row.key, 1, +$event.target.value)" />
              </td>
            </tr>
          </tbody>
        </table>

        <div class="add-modal__row add-modal__row--mt">
          <label class="add-modal__lbl">White</label>
          <select class="add-modal__select" :value="whitePreset"
                  @change="applyWhitePreset($event.target.value)">
            <option v-for="(p, k) in WHITE_PRESETS" :key="k" :value="k">{{ p.label }}</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        <div class="add-modal__section-hdr">White boost</div>

        <div class="add-modal__row">
          <label class="add-modal__lbl">CLO/WLO</label>
          <input class="add-modal__clowlo-slider" type="range" min="0.25" max="1.0" step="0.01"
                 :value="clowlo"
                 @input="clowlo = +$event.target.value" />
          <input class="add-modal__coord add-modal__clowlo-num" type="number" min="0.25" max="1.0" step="0.01"
                 :value="clowlo"
                 @change="clowlo = Math.max(0.25, Math.min(1.0, +$event.target.value))" />
        </div>


      </div>

      <!-- Right column: live preview -->
      <div class="add-modal__synth-right">
        <div class="add-modal__preview-hdr">
          <div class="add-modal__tabs">
            <button :class="['add-modal__tab', previewTab === 'rings'   && 'add-modal__tab--active']"
                    @click="switchTab('rings')">Rings</button>
            <button :class="['add-modal__tab', previewTab === 'surface' && 'add-modal__tab--active']"
                    @click="switchTab('surface')">Surface</button>
          </div>
          <span v-if="previewVolume !== null" class="add-modal__vol">
            {{ Math.round(previewVolume).toLocaleString() }} ΔE³
          </span>
        </div>

        <div class="add-modal__preview-canvas">

          <!-- Rings tab -->
          <template v-if="previewTab === 'rings'">
            <RingsCanvas v-if="previewGamut" :key="previewKey"
                         :gamut="previewGamut"
                         @volume="v => previewVolume = v" />
            <div v-if="!previewGamut" class="add-modal__preview-empty">
              <span v-if="synthError" class="add-modal__preview-err">{{ synthError }}</span>
              <span v-else>Adjust parameters to see a live preview</span>
            </div>
          </template>

          <!-- Surface tab -->
          <template v-else>
            <GamutSurfaceCanvas v-if="previewSurfaceGamuts.length"
                                :gamuts="previewSurfaceGamuts"
                                :perspectiveBlend="1"
                                :cameraElev="surfaceCameraElev"
                                :cameraAzim="surfaceCameraAzim"
                                :cameraDistance="surfaceCameraDistance"
                                @camera-change="e => { surfaceCameraElev = e.elev; surfaceCameraAzim = e.azim; surfaceCameraDistance = e.dist }"
                                colourSpace="srgb"
                                class="add-modal__surface-fill" />
            <div v-else-if="!surfaceLoading" class="add-modal__preview-empty">
              <span v-if="!previewEntry">Adjust parameters to see a live preview</span>
            </div>
          </template>

          <!-- Spinner — synth request or surface fetch -->
          <div v-if="showSpinner || surfaceLoading" class="add-modal__preview-overlay">
            <i class="pi pi-spin pi-spinner add-modal__spinner-lg" />
          </div>

        </div>
      </div>

    </div>

    <template #footer>
      <Button label="Cancel" text @click="visible = false" />
      <Button label="Add Gamut"
              :disabled="!previewEntry || previewLoading"
              @click="addSynthetic" />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import ChromaticityDiagram from './ChromaticityDiagram.vue'
import RingsCanvas from './RingsCanvas.vue'
import GamutSurfaceCanvas from './GamutSurfaceCanvas.vue'
import { createSynthetic, updateSynthetic, deleteGamut, renameGamut, getSurface } from '../api.js'
import { unpackCylmap } from '../gamut/cylmap.js'
import { useGamutStore } from '../stores/gamutStore.js'

const visible = defineModel({ type: Boolean, default: false })
const gamuts  = useGamutStore()

// ── Synthetic state ────────────────────────────────────────────────────────
const synthName   = ref('')
const primPreset  = ref('srgb')
const whitePreset = ref('d65')
const primR = ref([0.640, 0.330])
const primG = ref([0.300, 0.600])
const primB = ref([0.150, 0.060])
const white = ref([0.3127, 0.3290])
const clowlo  = ref(1.0)

// Preview state
const previewLoading  = ref(false)
const showSpinner     = ref(false)
const synthError      = ref(null)
const previewGamut    = ref(null)
const previewVolume   = ref(null)
const previewEntry    = ref(null)
const previewKey      = ref(0)
const previewTab        = ref('rings')
const previewSurface    = ref(null)
const surfaceLoading    = ref(false)
const surfaceCameraElev  = ref(12)
const surfaceCameraAzim  = ref(9)
const surfaceCameraDistance = ref(331)
const surfaceVersion     = ref(0)

const previewSurfaceGamuts = computed(() => {
  if (!previewEntry.value || !previewSurface.value) return []
  return [{ id: previewEntry.value.id, colour: '#888', surface: previewSurface.value,
            visible: true, alpha: 0.85, wireframe: false, chroma: 1.0, lightness: null,
            edgeColour: '#444', _sv: surfaceVersion.value }]
})

let previewId     = null
let debounceTimer = null
let spinnerTimer  = null

// ── Presets ────────────────────────────────────────────────────────────────
const PRIM_PRESETS = {
  srgb:        { label: 'sRGB',                 r:[0.640,0.330], g:[0.300,0.600], b:[0.150,0.060] },
  bt2020:      { label: 'BT.2020',              r:[0.708,0.292], g:[0.170,0.797], b:[0.131,0.046] },
  'dci-p3':    { label: 'DCI-P3 / Display P3',  r:[0.680,0.320], g:[0.265,0.690], b:[0.150,0.060] },
  'adobe-rgb': { label: 'Adobe RGB (1998)',      r:[0.640,0.330], g:[0.210,0.710], b:[0.150,0.060] },
}

const WHITE_PRESETS = {
  d50: { label: 'D50', xy:[0.34567,0.35850] },
  d55: { label: 'D55', xy:[0.33242,0.34743] },
  d60: { label: 'D60', xy:[0.32168,0.33767] },
  d65: { label: 'D65', xy:[0.31272,0.32903] },
  d75: { label: 'D75', xy:[0.29902,0.31485] },
  d93: { label: 'D93', xy:[0.28480,0.29320] },
  dci: { label: 'DCI', xy:[0.31400,0.35100] },
}

// ── Coordinate table ───────────────────────────────────────────────────────
const coordRows = computed(() => [
  { key:'r', label:'red',   val: primR.value },
  { key:'g', label:'green', val: primG.value },
  { key:'b', label:'blue',  val: primB.value },
  { key:'w', label:'white', val: white.value },
])

function fmt(v) { return v.toFixed(4) }

// ── Preset actions ─────────────────────────────────────────────────────────
function applyPrimPreset(key) {
  primPreset.value = key
  if (key !== 'custom') {
    const p = PRIM_PRESETS[key]
    primR.value = [...p.r]; primG.value = [...p.g]; primB.value = [...p.b]
  }
}

function applyWhitePreset(key) {
  whitePreset.value = key
  if (key !== 'custom') white.value = [...WHITE_PRESETS[key].xy]
}

// ── Setters ────────────────────────────────────────────────────────────────
function setPrim(key, v) {
  if (key === 'r') primR.value = v
  else if (key === 'g') primG.value = v
  else primB.value = v
  primPreset.value = 'custom'
}

function setWhite(v) {
  white.value = v
  whitePreset.value = 'custom'
}

function setCoord(key, idx, val) {
  const set = (ref, preset) => {
    const a = [...ref.value]; a[idx] = val; ref.value = a
    if (preset) primPreset.value = 'custom'
    else whitePreset.value = 'custom'
  }
  if (key === 'r') set(primR, true)
  else if (key === 'g') set(primG, true)
  else if (key === 'b') set(primB, true)
  else set(white, false)
}

// ── Tab switching ──────────────────────────────────────────────────────────
async function switchTab(tab) {
  previewTab.value = tab
  if (tab === 'surface' && previewEntry.value && !previewSurface.value && !surfaceLoading.value) {
    await loadSurface()
  }
}

async function loadSurface() {
  if (!previewEntry.value) return
  surfaceLoading.value = true
  try { previewSurface.value = await getSurface(previewEntry.value.id); surfaceVersion.value++ }
  catch { /* surface load failed; canvas stays empty */ }
  finally { surfaceLoading.value = false }
}

// When the preview entry changes: on null (error/reset) clear surface immediately;
// on a new entry keep the old surface showing until the new fetch completes.
watch(previewEntry, async (entry) => {
  if (!entry) { previewSurface.value = null; return }
  if (previewTab.value === 'surface') await loadSurface()
})

// ── Preview lifecycle ──────────────────────────────────────────────────────
watch([primR, primG, primB, white, clowlo], schedulePreview, { deep: true })
watch(visible, v => { if (v) schedulePreview() })

function schedulePreview() {
  if (!visible.value) return
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(doPreview, 200)  // ← debounce delay
}

async function doPreview() {
  previewLoading.value = true
  synthError.value = null

  // Show spinner only if response takes longer than threshold — avoids flicker on fast calls
  clearTimeout(spinnerTimer)
  spinnerTimer = setTimeout(() => { showSpinner.value = true }, 500)  // ← spinner threshold

  const payload = {
    primaries_xy: [primR.value, primG.value, primB.value],
    white_xy: white.value,
    gamma: 2.2,
    name: synthName.value.trim() || 'Custom',
    clowlo: clowlo.value,
  }

  try {
    const result = previewId
      ? await updateSynthetic(previewId, payload)
      : await createSynthetic(payload)
    if (!previewId) previewId = result.entry.id
    previewEntry.value = result.entry
    previewGamut.value = unpackCylmap(result.packed)
    previewKey.value++
  } catch (e) {
    synthError.value = e.message
    previewGamut.value = null
  } finally {
    previewLoading.value = false
    clearTimeout(spinnerTimer)
    showSpinner.value = false
  }
}

// ── Add action ─────────────────────────────────────────────────────────────
async function addSynthetic() {
  if (!previewEntry.value) return
  const finalName = synthName.value.trim() || previewEntry.value.name
  if (finalName !== previewEntry.value.name) {
    await renameGamut(previewEntry.value.id, finalName).catch(() => {})
  }
  gamuts.add({ ...previewEntry.value, name: finalName, label: finalName })
  previewId = null
  visible.value = false
}

// ── Cleanup ────────────────────────────────────────────────────────────────
function onHide() {
  clearTimeout(debounceTimer)
  clearTimeout(spinnerTimer)
  showSpinner.value = false
  synthError.value = null
  if (previewId) { deleteGamut(previewId).catch(() => {}); previewId = null }
  previewGamut.value = null
  previewEntry.value = null
  previewVolume.value = null
  previewSurface.value = null
  previewTab.value = 'rings'
  surfaceCameraElev.value  = 12
  surfaceCameraAzim.value  = 9
  surfaceCameraDistance.value = 331
}

onUnmounted(() => {
  clearTimeout(debounceTimer)
  clearTimeout(spinnerTimer)
  if (previewId) deleteGamut(previewId).catch(() => {})
})
</script>

<style scoped>
.add-modal__synth-body {
  display: flex;
  gap: 1rem;
  height: min(calc(90vh - 160px), 600px);
  align-items: stretch;
}

.add-modal__synth-left {
  width: 310px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  overflow: hidden;
}

.add-modal__synth-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.add-modal__row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.add-modal__row--mt { margin-top: 0.2rem; }

.add-modal__lbl {
  width: 62px;
  flex-shrink: 0;
  font-size: 0.72rem;
  color: var(--p-text-color);
}

.add-modal__input {
  font-size: 0.72rem;
  padding: 2px 5px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
  outline: none;
}

.add-modal__input--wide { flex: 1; }

.add-modal__select {
  flex: 1;
  font-size: 0.72rem;
  padding: 2px 4px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
}

.add-modal__hint {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.add-modal__section-hdr {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--p-text-muted-color);
  border-bottom: 1px solid var(--p-surface-200);
  padding-bottom: 0.1rem;
  margin-top: 0.25rem;
}

.add-modal__diag {
  width: 100%;
  flex: 1 1 0;
  min-height: 0;
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  background: var(--p-surface-0);
}

.add-modal__coord-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.72rem;
}

.add-modal__coord-table th {
  font-weight: 600;
  text-align: left;
  padding: 2px 3px;
  color: var(--p-text-muted-color);
  border-bottom: 1px solid var(--p-surface-200);
}

.add-modal__coord-table td { padding: 1px 2px; }

.add-modal__clr       { font-size: 0.72rem; width: 44px; }
.add-modal__clr--r    { color: #c62828; }
.add-modal__clr--g    { color: #2e7d32; }
.add-modal__clr--b    { color: #1565c0; }
.add-modal__clr--w    { color: #555; }

.add-modal__coord {
  width: 70px;
  font-size: 0.72rem;
  padding: 1px 4px;
  border: 1px solid var(--p-surface-300);
  border-radius: 4px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
  outline: none;
  font-family: monospace;
}

.add-modal__coord:focus { border-color: var(--p-primary-400); }

.add-modal__clowlo-slider {
  flex: 1;
  min-width: 0;
  accent-color: var(--p-primary-400);
  cursor: pointer;
}

.add-modal__clowlo-num {
  width: 56px;
}

.add-modal__preview-hdr {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.add-modal__tabs {
  display: flex;
  background: var(--p-surface-100);
  border-radius: 4px;
  padding: 2px;
  gap: 1px;
}

.add-modal__tab {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 10px;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}

.add-modal__tab--active {
  background: var(--p-surface-0);
  color: var(--p-text-color);
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}

.add-modal__surface-fill {
  position: absolute;
  inset: 0;
}

.add-modal__vol {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.add-modal__spinner { font-size: 0.8rem; color: var(--p-primary-400); }

.add-modal__preview-canvas {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  background: var(--p-surface-0);
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-modal__preview-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  gap: 6px;
}

.add-modal__preview-err { color: var(--p-red-500); }

.add-modal__preview-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.12);
  border-radius: 6px;
}

.add-modal__spinner-lg {
  font-size: 1.6rem;
  color: var(--p-primary-400);
}
</style>
