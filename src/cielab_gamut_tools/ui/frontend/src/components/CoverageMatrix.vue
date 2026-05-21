<template>
  <section class="cm">
    <div class="cm__header">
      <h3 class="cm__title">Coverage Matrix</h3>
      <i v-if="loading" class="pi pi-spin pi-spinner cm__spin" />
      <button class="cm__action" @click="scheduleFetch" :disabled="loading">Refresh</button>
      <div class="cm__spacer" />
      <button class="cm__action" @click="copyTsv" :disabled="!rawMatrix || loading"
              title="Copy matrix as TSV (paste into Excel / Sheets)">Copy</button>
      <button class="cm__action" @click="exportCsv" :disabled="!rawMatrix || loading">Export CSV</button>
    </div>

    <div v-if="!canCompute" class="cm__message">
      Select at least one DUT (D) and one reference (R) in the table above
    </div>
    <div v-else-if="error" class="cm__message cm__message--error">
      <i class="pi pi-exclamation-triangle" /> {{ error }}
    </div>
    <div v-else-if="!rawMatrix" class="cm__message">
      <i class="pi pi-spin pi-spinner" /> Computing…
    </div>
    <div v-else class="cm__scroll">
      <table class="cm__table">
        <thead>
          <tr>
            <th class="cm__corner"></th>
            <th v-for="g in matrixRefGamuts" :key="g.id" class="cm__colhead">
              <span class="cm__swatch" :style="{ background: g.colour }" />
              <span class="cm__head-label" :title="g.label || g.name">{{ g.label || g.name }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(dut, ri) in matrixDutGamuts" :key="dut.id">
            <th class="cm__rowhead">
              <span class="cm__swatch" :style="{ background: dut.colour }" />
              <span class="cm__head-label" :title="dut.label || dut.name">
                {{ dut.label || dut.name }}
              </span>
            </th>
            <td v-for="(ref, ci) in matrixRefGamuts" :key="ref.id"
                class="cm__cell"
                :class="{ 'cm__cell--diag': dut.id === ref.id }"
                :style="{ background: cellBg(ri, ci, getCell(ri, ci)) }"
                :title="`${dut.label || dut.name} covers ${ref.label || ref.name}: ${fmtPct(getCell(ri, ci))} — click to copy`"
                @click="copy(fmtPct(getCell(ri, ci)))">
              {{ fmtPct(getCell(ri, ci)) }}
            </td>
          </tr>
        </tbody>
      </table>
      <p class="cm__caption">Row: DUT gamut. Column: reference. Click a cell to copy.</p>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useGamutStore } from '../stores/gamutStore.js'
import { useUiStore } from '../stores/uiStore.js'
import { getMatrix } from '../api.js'

const gamuts = useGamutStore()
const ui = useUiStore()

// Snapshots at time of last successful fetch
const matrixDutGamuts = ref([])
const matrixRefGamuts = ref([])
const allIds = ref([])         // deduplicated union passed to server
const rawMatrix = ref(null)    // full NxN from server for allIds

const loading = ref(false)
const error = ref(null)
const fetchedKey = ref(null)   // key at time of last successful fetch

// Active selection filtered to gamuts that actually exist in the store
const activeDutIds = computed(() =>
  ui.analysisOptions.dutIds.filter(id => gamuts.gamuts[id]),
)
const activeRefIds = computed(() =>
  ui.analysisOptions.refIds.filter(id => gamuts.gamuts[id]),
)
const canCompute = computed(() => activeDutIds.value.length > 0 && activeRefIds.value.length > 0)

// Stable key that changes when the effective selection changes
const fetchKey = computed(() => {
  const d = activeDutIds.value.slice().sort().join(',')
  const r = activeRefIds.value.slice().sort().join(',')
  return `${d}|${r}`
})

let debounceTimer = null
let fetchToken = 0

function scheduleFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchMatrix, 400)
}

watch(
  [() => ui.activeView, fetchKey],
  ([view, key]) => {
    if (view === 'analysis' && canCompute.value && key !== fetchedKey.value) scheduleFetch()
  },
  { immediate: true },
)

onUnmounted(() => clearTimeout(debounceTimer))

async function fetchMatrix() {
  if (!canCompute.value) return

  const token = ++fetchToken
  const dutSnap = activeDutIds.value.map(id => gamuts.gamuts[id])
  const refSnap = activeRefIds.value.map(id => gamuts.gamuts[id])
  const key = fetchKey.value
  const union = [...new Set([...activeDutIds.value, ...activeRefIds.value])]

  loading.value = true
  error.value = null
  try {
    const result = await getMatrix(union)
    if (token !== fetchToken) return   // superseded by a newer request
    allIds.value = union
    matrixDutGamuts.value = dutSnap
    matrixRefGamuts.value = refSnap
    rawMatrix.value = result.matrix
    fetchedKey.value = key
  } catch (e) {
    if (token !== fetchToken) return
    error.value = e.message
    rawMatrix.value = null
  } finally {
    if (token === fetchToken) {
      loading.value = false
      // Selection may have drifted while the fetch was in flight; if so, go again.
      if (canCompute.value && fetchKey.value !== fetchedKey.value) scheduleFetch()
    }
  }
}

function getCell(ri, ci) {
  if (!rawMatrix.value) return 0
  const di = allIds.value.indexOf(matrixDutGamuts.value[ri]?.id)
  const rj = allIds.value.indexOf(matrixRefGamuts.value[ci]?.id)
  if (di === -1 || rj === -1) return 0
  return rawMatrix.value[di][rj]
}

function hexToRgb(hex) {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
}

function cellBg(ri, ci, val) {
  if (matrixDutGamuts.value[ri]?.id === matrixRefGamuts.value[ci]?.id) {
    return 'rgba(100,100,100,0.12)'
  }
  const g = matrixDutGamuts.value[ri]
  if (!g?.colour) return ''
  const [r, gv, b] = hexToRgb(g.colour)
  return `rgba(${r},${gv},${b},${(val / 100) * 0.45})`
}

function fmtPct(v) {
  return v.toFixed(1) + '%'
}

function copy(text) {
  navigator.clipboard?.writeText(text)
}

function buildTsvRows() {
  const colNames = matrixRefGamuts.value.map(g => g.label || g.name)
  const rows = [['', ...colNames]]
  for (let ri = 0; ri < matrixDutGamuts.value.length; ri++) {
    const name = matrixDutGamuts.value[ri].label || matrixDutGamuts.value[ri].name
    rows.push([name, ...matrixRefGamuts.value.map((_, ci) => fmtPct(getCell(ri, ci)))])
  }
  return rows
}

function copyTsv() {
  if (!rawMatrix.value) return
  navigator.clipboard?.writeText(buildTsvRows().map(r => r.join('\t')).join('\n'))
}

function exportCsv() {
  if (!rawMatrix.value) return
  const csv = buildTsvRows()
    .map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'coverage-matrix.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.cm {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.cm__header {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.cm__title {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-color);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cm__spin {
  font-size: 0.75rem;
  color: var(--p-primary-500);
}

.cm__spacer { flex: 1; }

.cm__action {
  font-size: 0.72rem;
  padding: 2px 8px;
  border: 1px solid var(--p-surface-300);
  border-radius: 3px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.cm__action:hover:not(:disabled) {
  border-color: var(--p-primary-400);
  color: var(--p-primary-500);
}
.cm__action:disabled { opacity: 0.4; cursor: default; }

.cm__message {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  font-style: italic;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 0;
}
.cm__message--error {
  color: var(--p-red-500);
  font-style: normal;
}

.cm__scroll {
  overflow-x: auto;
}

.cm__table {
  border-collapse: collapse;
  font-size: 0.75rem;
  white-space: nowrap;
}

.cm__corner {
  padding: 4px 8px;
}

.cm__colhead {
  padding: 4px 8px 4px 4px;
  font-weight: 600;
  color: var(--p-text-muted-color);
  border-bottom: 1px solid var(--p-surface-200);
  text-align: left;
  max-width: 100px;
  overflow: hidden;
}

.cm__rowhead {
  padding: 4px 8px 4px 4px;
  font-weight: 600;
  color: var(--p-text-muted-color);
  border-right: 1px solid var(--p-surface-200);
  text-align: left;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
}

.cm__swatch {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
  flex-shrink: 0;
}

.cm__head-label {
  vertical-align: middle;
  display: inline-block;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cm__cell {
  padding: 4px 10px;
  text-align: right;
  border-bottom: 1px solid var(--p-surface-100);
  border-left: 1px solid var(--p-surface-100);
  cursor: pointer;
  transition: filter 0.1s;
  color: var(--p-text-color);
}
.cm__cell:hover { filter: brightness(0.92); }
.cm__cell--diag {
  font-weight: 600;
  color: var(--p-text-muted-color);
}

.cm__caption {
  margin: 0.4rem 0 0;
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
  font-style: italic;
}
</style>
