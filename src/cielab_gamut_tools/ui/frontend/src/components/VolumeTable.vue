<template>
  <section class="vt">
    <div class="vt__header">
      <h3 class="vt__title">Gamut Volumes</h3>
      <div class="vt__spacer" />
      <button class="vt__action" @click="copyTsv" :disabled="gamuts.list.length === 0"
              title="Copy table as TSV (paste into Excel / Sheets)">Copy</button>
      <button class="vt__action" @click="exportCsv" :disabled="gamuts.list.length === 0">Export CSV</button>
    </div>

    <table class="vt__table">
      <thead>
        <tr>
          <th class="vt__th" @click="setSort('name')">
            Name
            <span class="vt__sort-icon">{{ sortKey === 'name' ? (sortDir === 1 ? '▲' : '▼') : '' }}</span>
          </th>
          <th class="vt__th" @click="setSort('source')">
            Source
            <span class="vt__sort-icon">{{ sortKey === 'source' ? (sortDir === 1 ? '▲' : '▼') : '' }}</span>
          </th>
          <th class="vt__th vt__th--r" @click="setSort('volume')">
            Volume
            <span class="vt__sort-icon">{{ sortKey === 'volume' ? (sortDir === 1 ? '▲' : '▼') : '' }}</span>
          </th>
          <th class="vt__th vt__th--c" title="Include in coverage matrix as DUT (D) or reference (R)">Coverage Matrix</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="gamuts.list.length === 0">
          <td class="vt__empty" colspan="4">No gamuts loaded</td>
        </tr>
        <tr v-else v-for="g in sortedGamuts" :key="g.id" class="vt__row">
          <td class="vt__td">
            <span class="vt__swatch" :style="{ background: g.colour }" />
            {{ g.label || g.name }}
          </td>
          <td class="vt__td vt__td--muted">{{ g.source }}</td>
          <td class="vt__td vt__td--r vt__td--copy"
              :title="g.volume != null ? 'Click to copy' : ''"
              @click="g.volume != null && copy(formatVol(g.volume))">
            {{ formatVol(g.volume) }}
          </td>
          <td class="vt__td vt__td--c">
            <button class="vt__sel" :class="{ 'vt__sel--on': isDut(g.id) }"
                    title="Include as DUT in coverage matrix"
                    @click="ui.setAnalysisDut(g.id, !isDut(g.id))">D</button>
            <button class="vt__sel" :class="{ 'vt__sel--on': isRef(g.id) }"
                    title="Include as reference in coverage matrix"
                    @click="ui.setAnalysisRef(g.id, !isRef(g.id))">R</button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGamutStore } from '../stores/gamutStore.js'
import { useUiStore } from '../stores/uiStore.js'

const gamuts = useGamutStore()
const ui = useUiStore()

const sortKey = ref('name')
const sortDir = ref(1)

function setSort(key) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = 1
  }
}

const sortedGamuts = computed(() => {
  return [...gamuts.list].sort((a, b) => {
    let av, bv
    if (sortKey.value === 'volume') {
      av = a.volume ?? -Infinity
      bv = b.volume ?? -Infinity
    } else if (sortKey.value === 'source') {
      av = a.source
      bv = b.source
    } else {
      av = (a.label || a.name).toLowerCase()
      bv = (b.label || b.name).toLowerCase()
    }
    if (av < bv) return -sortDir.value
    if (av > bv) return sortDir.value
    return 0
  })
})

function isDut(id) { return ui.analysisOptions.dutIds.includes(id) }
function isRef(id) { return ui.analysisOptions.refIds.includes(id) }

function formatVol(v) {
  if (v == null) return '—'
  return Math.round(v).toLocaleString('en-US')
}

function copy(text) {
  navigator.clipboard?.writeText(text)
}

function copyTsv() {
  const rows = [['Name', 'Source', 'Volume']]
  for (const g of sortedGamuts.value) {
    rows.push([g.label || g.name, g.source, g.volume == null ? '' : Math.round(g.volume)])
  }
  navigator.clipboard?.writeText(rows.map(r => r.join('\t')).join('\n'))
}

function exportCsv() {
  const rows = [['Name', 'Source', 'Volume']]
  for (const g of sortedGamuts.value) {
    rows.push([g.label || g.name, g.source, g.volume == null ? '' : Math.round(g.volume)])
  }
  triggerDownload('gamut-volumes.csv', toCsv(rows))
}

function toCsv(rows) {
  return rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
}

function triggerDownload(filename, csv) {
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.vt {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.vt__header {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.vt__title {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-color);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.vt__spacer { flex: 1; }

.vt__action {
  font-size: 0.72rem;
  padding: 2px 8px;
  border: 1px solid var(--p-surface-300);
  border-radius: 3px;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.vt__action:hover:not(:disabled) {
  border-color: var(--p-primary-400);
  color: var(--p-primary-500);
}
.vt__action:disabled { opacity: 0.4; cursor: default; }

.vt__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

.vt__th {
  text-align: left;
  padding: 4px 8px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  border-bottom: 1px solid var(--p-surface-200);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}
.vt__th:hover { color: var(--p-text-color); }
.vt__th--r { text-align: right; }
.vt__th--c { text-align: center; cursor: default; }

.vt__sort-icon {
  font-size: 0.6rem;
  margin-left: 2px;
  opacity: 0.7;
}

.vt__row:hover { background: var(--p-surface-50); }

.vt__td {
  padding: 4px 8px;
  border-bottom: 1px solid var(--p-surface-100);
  color: var(--p-text-color);
  vertical-align: middle;
}
.vt__td--r       { text-align: right; }
.vt__td--c       { text-align: center; }
.vt__td--muted   { color: var(--p-text-muted-color); font-size: 0.72rem; }
.vt__td--copy    { cursor: pointer; }
.vt__td--copy:hover { color: var(--p-primary-500); }

.vt__swatch {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  margin-right: 5px;
  vertical-align: middle;
  flex-shrink: 0;
}

.vt__empty {
  padding: 16px 8px;
  text-align: center;
  color: var(--p-text-muted-color);
  font-size: 0.78rem;
  font-style: italic;
}

/* D / R selection toggle buttons */
.vt__sel {
  width: 18px;
  height: 18px;
  border: 1px solid var(--p-surface-300);
  border-radius: 3px;
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: 0.65rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.vt__sel + .vt__sel { margin-left: 3px; }
.vt__sel:hover { border-color: var(--p-primary-400); color: var(--p-primary-500); }
.vt__sel--on {
  background: var(--p-primary-500);
  border-color: var(--p-primary-500);
  color: #fff;
}
</style>
