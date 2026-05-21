<template>
  <!-- SVG uses a y-flipped inner group so all content uses chromaticity (x,y) directly.
       viewBox covers x ∈ [-0.03, 0.81] and the equivalent y range. -->
  <svg ref="svgEl" class="cie-diag"
       viewBox="-0.03 -0.04 0.84 0.96"
       @pointerup="onUp"
       @pointercancel="onUp">

    <!-- scale(1,-1) flips y so higher chromaticity y is drawn upward.
         translate(0,-0.90) shifts the "floor" (y=0) to SVG y=0.90. -->
    <g transform="scale(1,-1) translate(0,-0.90)">

      <!-- Spectral locus filled area -->
      <path :d="locusClosedPath"
            fill="rgba(180,180,200,0.18)"
            stroke="none" />

      <!-- Spectral locus outline -->
      <path :d="locusPath"
            fill="none"
            stroke="#555"
            stroke-width="0.005"
            stroke-linejoin="round" />

      <!-- Line of purples (closing segment) -->
      <line :x1="locusFirst[0]" :y1="locusFirst[1]"
            :x2="locusLast[0]"  :y2="locusLast[1]"
            stroke="#555" stroke-width="0.004"
            stroke-dasharray="0.018 0.010" />

      <!-- Gamut triangle -->
      <polygon :points="trianglePts"
               fill="rgba(255,255,255,0.08)"
               stroke="#999"
               stroke-width="0.004" />

      <!-- RGB handles (circles) -->
      <circle v-for="key in ['r','g','b']" :key="key"
              :cx="get(key)[0]" :cy="get(key)[1]"
              :r="dragging === key ? 0.020 : 0.015"
              :fill="HANDLE_FILL[key]"
              stroke="white"
              :stroke-width="dragging === key ? 0.007 : 0.005"
              class="handle"
              @pointerdown.stop.prevent="startDrag(key, $event)" />

      <!-- W handle (square, rotated 45° = diamond) -->
      <rect :x="get('w')[0] - 0.011" :y="get('w')[1] - 0.011"
            width="0.022" height="0.022"
            :transform="`rotate(45,${get('w')[0]},${get('w')[1]})`"
            :fill="dragging === 'w' ? '#fff' : '#eee'"
            :stroke="dragging === 'w' ? '#333' : '#666'"
            :stroke-width="dragging === 'w' ? 0.007 : 0.005"
            class="handle"
            @pointerdown.stop.prevent="startDrag('w', $event)" />

    </g>

    <!-- Axis labels (outside the y-flip group, positioned in SVG space)
         SVG y for chromaticity y=0 → SVG y = 0.90 + 0.04 (offset) = 0.94 relative to group top
         But with translate(0,-0.90) and scale(1,-1), SVG y_screen = 0.90 - y_chrom
         So y_chrom=0 → SVG y_screen=0.90, y_chrom=0.84 → SVG y_screen=0.06 -->
    <text x="0.38" y="0.91" class="diag-axis-label">x</text>
    <text x="-0.025" y="0.07" class="diag-axis-label">y</text>

  </svg>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { spectralLocus, locusFirst, locusLast } from '../gamut/cie1931.js'

const props = defineProps({
  r: { type: Array, required: true },
  g: { type: Array, required: true },
  b: { type: Array, required: true },
  w: { type: Array, required: true },
})
const emit = defineEmits(['update:r', 'update:g', 'update:b', 'update:w'])

const HANDLE_FILL = { r: '#dd2222', g: '#22aa22', b: '#2244ee' }

const svgEl  = ref(null)
const dragging = ref(null)

function get(key) {
  return key === 'r' ? props.r : key === 'g' ? props.g : key === 'b' ? props.b : props.w
}

// Spectral locus SVG path (points used directly — y-flip handled by group transform)
const locusPath = computed(() => {
  if (!spectralLocus.length) return ''
  const [[x0, y0], ...rest] = spectralLocus
  return `M${x0},${y0}` + rest.map(([x, y]) => `L${x},${y}`).join('')
})

const locusClosedPath = computed(() =>
  locusPath.value + `L${locusLast[0]},${locusLast[1]}L${locusFirst[0]},${locusFirst[1]}Z`
)

const trianglePts = computed(() =>
  `${props.r[0]},${props.r[1]} ${props.g[0]},${props.g[1]} ${props.b[0]},${props.b[1]}`
)

// Convert a mouse/pointer event to chromaticity coordinates using SVG's built-in
// coordinate transform — correctly handles scaling, zoom, and CSS transforms.
function eventToChrom(event) {
  const pt = svgEl.value.createSVGPoint()
  pt.x = event.clientX
  pt.y = event.clientY
  const svgPt = pt.matrixTransform(svgEl.value.getScreenCTM().inverse())
  // Inside the group: scale(1,-1) translate(0,-0.90)
  // SVG screen y = 0.90 - chrom_y  →  chrom_y = 0.90 - svgPt.y
  return [svgPt.x, 0.90 - svgPt.y]
}

function clamp(v) {
  return [Math.max(0, Math.min(0.80, v[0])), Math.max(0, Math.min(0.90, v[1]))]
}

function startDrag(key, event) {
  dragging.value = key
  // Use window listeners so the drag continues outside the SVG bounds
  window.addEventListener('pointermove', onWindowMove)
  window.addEventListener('pointerup',   onWindowUp)
}

function onWindowMove(event) {
  if (!dragging.value || !svgEl.value) return
  emit(`update:${dragging.value}`, clamp(eventToChrom(event)))
}

function onWindowUp() {
  dragging.value = null
  window.removeEventListener('pointermove', onWindowMove)
  window.removeEventListener('pointerup',   onWindowUp)
}

function onUp() {
  onWindowUp()
}

onUnmounted(onWindowUp)
</script>

<style scoped>
.cie-diag {
  display: block;
  width: 100%;
  height: 100%;
  cursor: default;
  user-select: none;
}

.handle {
  cursor: grab;
}

.diag-axis-label {
  font: 0.04px sans-serif;
  fill: #888;
  text-anchor: middle;
}
</style>
