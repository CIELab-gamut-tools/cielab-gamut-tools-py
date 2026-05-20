<template>
  <div class="rings-wrap">
    <svg :viewBox="`-${LIM} -${LIM} ${LIM*2} ${LIM*2}`" class="rings-svg">
      <!-- border -->
      <path :d="`M-${LIM},-${LIM}H${LIM}V${LIM}H-${LIM}Z`" stroke="black" stroke-width="10" fill="none"/>
      <!-- axes -->
      <path :d="`M-${LIM-TICK},0H${LIM-TICK}`" stroke="#888" stroke-width="3" fill="none"/>
      <path :d="`M0,-${LIM-TICK}V${LIM-TICK}`" stroke="#888" stroke-width="3" fill="none"/>
      <!-- x ticks (top + bottom) -->
      <line v-for="i in TICK_N" :key="`xt${i}`"
            :x1="i*TICK-LIM" :x2="i*TICK-LIM" :y1="-LIM" :y2="-LIM+20" stroke-width="3" stroke="black"/>
      <line v-for="i in TICK_N" :key="`xb${i}`"
            :x1="i*TICK-LIM" :x2="i*TICK-LIM" :y1="LIM" :y2="LIM-20" stroke-width="3" stroke="black"/>
      <!-- y ticks (left + right) -->
      <line v-for="i in TICK_N" :key="`yl${i}`"
            :y1="i*TICK-LIM" :y2="i*TICK-LIM" :x1="-LIM" :x2="-LIM+20" stroke-width="3" stroke="black"/>
      <line v-for="i in TICK_N" :key="`yr${i}`"
            :y1="i*TICK-LIM" :y2="i*TICK-LIM" :x1="LIM" :x2="LIM-20" stroke-width="3" stroke="black"/>
      <!-- x labels -->
      <text v-for="i in LABEL_X_N" :key="`lx${i}`"
            :x="i*LABEL_STEP-LABEL_X_END" :y="LIM-30" class="lbl-x">{{ i*LABEL_STEP-LABEL_X_END }}</text>
      <text v-for="i in LABEL_X_N" :key="`lxt${i}`"
            :x="i*LABEL_STEP-LABEL_X_END" :y="80-LIM" class="lbl-x">{{ i*LABEL_STEP-LABEL_X_END }}</text>
      <!-- y labels -->
      <text v-for="i in LABEL_Y_N" :key="`ly${i}`"
            :y="i*LABEL_STEP-LABEL_Y_END+25" :x="30-LIM" class="lbl-y">{{ LABEL_Y_END-i*LABEL_STEP }}</text>
      <text v-for="i in LABEL_Y_N" :key="`lyr${i}`"
            :y="i*LABEL_STEP-LABEL_Y_END+25" :x="LIM-30" class="lbl-y lbl-y--r">{{ LABEL_Y_END-i*LABEL_STEP }}</text>
      <!-- axis labels -->
      <text :x="-250" :y="LIM-160" class="lbl-axis">a</text>
      <text :x="-200" :y="LIM-180" class="lbl-sup">*</text>
      <text :x="-200" :y="LIM-120" class="lbl-sub">RSS</text>
      <text :x="100-LIM" :y="100" class="lbl-axis">b</text>
      <text :x="150-LIM" :y="80" class="lbl-sup">*</text>
      <text :x="150-LIM" :y="140" class="lbl-sub">RSS</text>
    </svg>
    <canvas ref="canvasEl" class="rings-canvas" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as wgl from '../webgl/wgl.js'
import { computeRings } from '../gamut/rings.js'
import { intersect } from '../gamut/intersect.js'

const props = defineProps({
  gamut:    { type: Object, default: null },
  refGamut: { type: Object, default: null },
})
const emit = defineEmits(['volume'])

// --- Layout constants (match gamut-rings-app) ---
const LIM       = 1100
const TICK      = 100
const TICK_N    = 2 * LIM / TICK - 1
const LABEL_STEP = 200
const LABEL_X_N  = 2 * Math.floor(LIM / LABEL_STEP) - 1
const LABEL_Y_N  = 2 * Math.floor(LIM / LABEL_STEP) + 1
const LABEL_X_END = LIM - (LIM % LABEL_STEP)
const LABEL_Y_END = LIM + (LIM % LABEL_STEP)

// --- WebGL state ---
const canvasEl = ref(null)
let gl = null
let progs = {}
let bufs = {}
let arrays = {}
let rendering = false
let pendingRender = false
let cachedRefGamut = null
let cachedRefRings = null

onMounted(() => {
  const canvas = canvasEl.value
  gl = canvas.getContext('webgl')
  canvas.width = canvas.height = 1024

  progs.fixedColour = wgl.makeProgram(gl, 'fixedColour')
  progs.varColour   = wgl.makeProgram(gl, 'varColour')

  // Vertex buffers
  bufs.rings  = gl.createBuffer()
  bufs.iRings = gl.createBuffer()
  arrays.rings  = new Float32Array(7202)   // origin + 10*360 points
  arrays.iRings = new Float32Array(14402)  // origin + 10*360*2 points (DUT+ref interleaved)

  // 20 index buffers: rings 0..19 (for reference mode: 10 DUT + 10 ref interleaved)
  bufs.lines = []
  bufs.areas = []
  for (let n = 0; n < 20; n++) {
    // LINE_LOOP: 360 indices for ring n
    const la = new Uint16Array(360)
    for (let i = 0; i < 360; i++) la[i] = n * 360 + i + 1
    const lb = gl.createBuffer()
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, lb)
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, la, gl.STATIC_DRAW)
    bufs.lines.push(lb)

    // TRIANGLE_STRIP/FAN: annular region between ring n-1 and ring n
    let aa
    if (n === 0) {
      aa = new Uint16Array(362)
      for (let i = 0; i < 361; i++) aa[i] = i
      aa[361] = 1
    } else {
      aa = new Uint16Array(722)
      for (let i = 0; i < 360; i++) {
        aa[i * 2]     = i + n * 360 - 359
        aa[i * 2 + 1] = i + n * 360 + 1
      }
      aa[720] = n * 360 - 359
      aa[721] = n * 360 + 1
    }
    const ab = gl.createBuffer()
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ab)
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, aa, gl.STATIC_DRAW)
    bufs.areas.push(ab)
  }

  if (props.gamut) scheduleRender()
})

onUnmounted(() => {
  if (gl) {
    // Release WebGL resources
    Object.values(bufs.lines || []).forEach(b => gl.deleteBuffer(b))
    Object.values(bufs.areas || []).forEach(b => gl.deleteBuffer(b))
    gl.deleteBuffer(bufs.rings)
    gl.deleteBuffer(bufs.iRings)
  }
})

watch([() => props.gamut, () => props.refGamut], () => {
  if (props.gamut) scheduleRender()
})

function scheduleRender() {
  if (rendering) { pendingRender = true; return }
  doRender()
}

async function doRender() {
  rendering = true
  pendingRender = false

  const { gamut, refGamut } = props

  if (refGamut) {
    if (cachedRefGamut !== refGamut) {
      cachedRefRings = computeRings(refGamut)
      cachedRefGamut = refGamut
    }
    const iGamut = intersect(gamut, refGamut)
    const dutRings = computeRings(iGamut, cachedRefRings.cssC)
    renderWithRef(dutRings, cachedRefRings)
    emit('volume', dutRings.totalVol)
  } else {
    cachedRefGamut = null
    cachedRefRings = null
    const ringData = computeRings(gamut)
    renderSingle(ringData)
    emit('volume', ringData.totalVol)
  }

  gl.flush()
  await new Promise(requestAnimationFrame)
  rendering = false
  if (pendingRender) doRender()
}

function renderSingle({ cssA, cssB }) {
  const data = arrays.rings
  const H = 360
  for (let i = 0, j = 2; i < 3600; i++) {
    data[j++] = cssA[i] / LIM
    data[j++] = cssB[i] / LIM
  }

  wgl.clear(gl)

  // Filled areas (CIELab-coloured)
  const { program: vp, attributes: { a_position: va }, uniforms: { u_lightness, u_chroma } } = progs.varColour
  gl.useProgram(vp)
  gl.bindBuffer(gl.ARRAY_BUFFER, bufs.rings)
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW)
  gl.enableVertexAttribArray(va)
  gl.vertexAttribPointer(va, 2, gl.FLOAT, false, 0, 0)
  for (let i = 0; i < 10; i++) {
    gl.uniform1f(u_chroma, 15 + Math.sqrt(i) * 12)
    gl.uniform1f(u_lightness, 30 + i * 60 / 9)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.areas[i])
    gl.drawElements(i ? gl.TRIANGLE_STRIP : gl.TRIANGLE_FAN, i ? 722 : 362, gl.UNSIGNED_SHORT, 0)
  }

  // Outlines
  const { program: fp, attributes: { a_position: fa }, uniforms: { u_col } } = progs.fixedColour
  gl.useProgram(fp)
  gl.bindBuffer(gl.ARRAY_BUFFER, bufs.rings)
  gl.enableVertexAttribArray(fa)
  gl.vertexAttribPointer(fa, 2, gl.FLOAT, false, 0, 0)
  for (let i = 0; i < 10; i++) {
    gl.uniform4f(u_col, 0, 0, 0, 1)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.lines[i])
    gl.drawElements(gl.LINE_LOOP, 360, gl.UNSIGNED_SHORT, 0)
  }
}

function renderWithRef({ cssA, cssB }, { cssA: rx, cssB: ry }) {
  const data = arrays.iRings
  for (let i = 0, j = 2; i < 3600; i += 360) {
    for (let k = i; k < i + 360; k++) { data[j++] = cssA[k] / LIM; data[j++] = cssB[k] / LIM }
    for (let k = i; k < i + 360; k++) { data[j++] = rx[k] / LIM;   data[j++] = ry[k] / LIM }
  }

  wgl.clear(gl)

  // Filled areas
  const { program: vp, attributes: { a_position: va }, uniforms: { u_lightness, u_chroma } } = progs.varColour
  gl.useProgram(vp)
  gl.bindBuffer(gl.ARRAY_BUFFER, bufs.iRings)
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW)
  gl.enableVertexAttribArray(va)
  gl.vertexAttribPointer(va, 2, gl.FLOAT, false, 0, 0)
  for (let i = 0; i < 10; i++) {
    gl.uniform1f(u_chroma, 15 + Math.sqrt(i) * 12)
    gl.uniform1f(u_lightness, 30 + i * 60 / 9)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.areas[i * 2])
    gl.drawElements(i ? gl.TRIANGLE_STRIP : gl.TRIANGLE_FAN, i ? 722 : 362, gl.UNSIGNED_SHORT, 0)
    gl.uniform1f(u_chroma, 0)
    gl.uniform1f(u_lightness, 50 + i * 48 / 9)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.areas[i * 2 + 1])
    gl.drawElements(gl.TRIANGLE_STRIP, 722, gl.UNSIGNED_SHORT, 0)
  }

  // Outlines on reference rings only
  const { program: fp, attributes: { a_position: fa }, uniforms: { u_col } } = progs.fixedColour
  gl.useProgram(fp)
  gl.bindBuffer(gl.ARRAY_BUFFER, bufs.iRings)
  gl.enableVertexAttribArray(fa)
  gl.vertexAttribPointer(fa, 2, gl.FLOAT, false, 0, 0)
  for (let i = 0; i < 10; i++) {
    gl.uniform4f(u_col, 0, 0, 0, 1)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.lines[i * 2 + 1])
    gl.drawElements(gl.LINE_LOOP, 360, gl.UNSIGNED_SHORT, 0)
  }
}
</script>

<style scoped>
.rings-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
}

.rings-svg,
.rings-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.lbl-x    { font: 60px serif; text-anchor: middle; }
.lbl-y    { font: 60px serif; }
.lbl-y--r { text-anchor: end; }
.lbl-axis { font: bold italic 100px serif; }
.lbl-sup  { font: bold italic 60px serif; }
.lbl-sub  { font: bold italic 60px serif; }
</style>
