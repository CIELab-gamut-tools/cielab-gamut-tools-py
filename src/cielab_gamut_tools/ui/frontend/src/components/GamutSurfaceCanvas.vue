<template>
  <div ref="container" class="surface-canvas" />
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const props = defineProps({
  // Array of { id, colour, surface: {vertices, faces} | null, visible, alpha }
  gamuts: { type: Array, default: () => [] },
})

const container = ref(null)

let renderer, scene, camera, controls, animId, ro
const meshMap = new Map()  // id → { mesh, geo, mat }
let axisGroup = null
let tickGroup  = null
let currentTickState = null

// ── Coordinate constants (Three.js: X=b*, Y=L*, Z=a*) ──────────────────────
const X0 = -128, X1 = 128   // b* extent
const Y0 =    0, Y1 = 100   // L* extent
const Z0 = -128, Z1 = 128   // a* extent

// The 4 vertical edges with their outward tick directions.
const V_EDGES = [
  { x: X0, z: Z0, dx: -1, dz: -1 },
  { x: X1, z: Z0, dx:  1, dz: -1 },
  { x: X1, z: Z1, dx:  1, dz:  1 },
  { x: X0, z: Z1, dx: -1, dz:  1 },
]

// ── Gamut geometry ──────────────────────────────────────────────────────────

// vertices: [[L*, a*, b*], ...] → mapped to [b*, L*, a*] (X, Y, Z).
function buildGeometry({ vertices, faces }) {
  const positions = new Float32Array(vertices.length * 3)
  for (let i = 0; i < vertices.length; i++) {
    const [L, a, b] = vertices[i]
    positions[i * 3 + 0] = b
    positions[i * 3 + 1] = L
    positions[i * 3 + 2] = a
  }
  const flatIdx = new Uint16Array(faces.length * 3)
  for (let i = 0; i < faces.length; i++) {
    flatIdx[i * 3 + 0] = faces[i][0]
    flatIdx[i * 3 + 1] = faces[i][1]
    flatIdx[i * 3 + 2] = faces[i][2]
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setIndex(new THREE.BufferAttribute(flatIdx, 1))
  geo.computeVertexNormals()
  return geo
}

function syncMeshes(gamuts) {
  const activeIds = new Set(gamuts.map(g => g.id))

  for (const [id, entry] of meshMap) {
    if (!activeIds.has(id)) {
      scene.remove(entry.mesh)
      entry.geo.dispose()
      entry.mat.dispose()
      meshMap.delete(id)
    }
  }

  for (const g of gamuts) {
    if (!g.surface) continue
    const alpha   = g.alpha   ?? 0.75
    const visible = g.visible ?? true

    if (meshMap.has(g.id)) {
      const { mesh, mat } = meshMap.get(g.id)
      mat.color.set(g.colour)
      mat.opacity = alpha
      mat.transparent = alpha < 1.0
      mat.needsUpdate = true
      mesh.visible = visible
    } else {
      const geo = buildGeometry(g.surface)
      const mat = new THREE.MeshPhongMaterial({
        color: new THREE.Color(g.colour),
        opacity: alpha,
        transparent: alpha < 1.0,
        side: THREE.DoubleSide,
        shininess: 30,
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.visible = visible
      scene.add(mesh)
      meshMap.set(g.id, { mesh, geo, mat })
    }
  }
}

// ── Axis box — static parts (panes + edges) ─────────────────────────────────
// Panes: inward-pointing normals + FrontSide — the 3 panes facing the camera
// are automatically hidden by Three.js backface culling, no per-frame logic.
// Grid lines are baked into each pane's canvas texture so they hide with it.

function makeGridTexture(texW, texH, hMin, hMax, vMin, vMax) {
  const canvas = document.createElement('canvas')
  canvas.width = texW; canvas.height = texH
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#d8dde2'
  ctx.fillRect(0, 0, texW, texH)
  ctx.strokeStyle = '#9faab4'
  ctx.lineWidth = 1
  const STEP = 20
  const hStart = Math.ceil(hMin / STEP) * STEP
  for (let v = hStart; v <= hMax; v += STEP) {
    const x = Math.round((v - hMin) / (hMax - hMin) * texW) + 0.5
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, texH); ctx.stroke()
  }
  const vStart = Math.ceil(vMin / STEP) * STEP
  for (let v = vStart; v <= vMax; v += STEP) {
    const y = Math.round(texH - (v - vMin) / (vMax - vMin) * texH) + 0.5
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(texW, y); ctx.stroke()
  }
  return new THREE.CanvasTexture(canvas)
}

function buildAxisBox() {
  const group = new THREE.Group()

  // Panes — [cx, cy, cz, rotX, rotY, planeW, planeH, texW, texH, hMin, hMax, vMin, vMax]
  const paneConfigs = [
    [X0,  50,   0,  0,          Math.PI/2,  256, 100, 512, 200,  -128, 128,    0, 100],
    [X1,  50,   0,  0,         -Math.PI/2,  256, 100, 512, 200,  -128, 128,    0, 100],
    [0,   Y0,   0, -Math.PI/2,  0,          256, 256, 512, 512,  -128, 128, -128, 128],
    [0,   Y1,   0,  Math.PI/2,  0,          256, 256, 512, 512,  -128, 128, -128, 128],
    [0,   50,  Z0,  0,          0,          256, 100, 512, 200,  -128, 128,    0, 100],
    [0,   50,  Z1,  0,          Math.PI,    256, 100, 512, 200,  -128, 128,    0, 100],
  ]
  for (const [cx, cy, cz, rx, ry, pw, ph, tw, th, hMin, hMax, vMin, vMax] of paneConfigs) {
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(pw, ph),
      new THREE.MeshBasicMaterial({
        map: makeGridTexture(tw, th, hMin, hMax, vMin, vMax),
        side: THREE.FrontSide, transparent: true, opacity: 0.45, depthWrite: false,
      })
    )
    mesh.position.set(cx, cy, cz)
    mesh.rotation.set(rx, ry, 0)
    group.add(mesh)
  }

  // Edges
  const corners = [
    [X0,Y0,Z0],[X1,Y0,Z0],[X1,Y1,Z0],[X0,Y1,Z0],
    [X0,Y0,Z1],[X1,Y0,Z1],[X1,Y1,Z1],[X0,Y1,Z1],
  ]
  const edgePairs = [
    [0,1],[1,2],[2,3],[3,0],
    [4,5],[5,6],[6,7],[7,4],
    [0,4],[1,5],[2,6],[3,7],
  ]
  group.add(new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(
      edgePairs.flatMap(([a, b]) => [
        new THREE.Vector3(...corners[a]),
        new THREE.Vector3(...corners[b]),
      ])
    ),
    new THREE.LineBasicMaterial({ color: 0x777777 })
  ))

  return group
}

// ── Axis ticks and labels — rebuilt when camera orientation changes ──────────

function makeTextSprite(text, fontSize = 28) {
  const cw = 128, ch = 48
  const canvas = document.createElement('canvas')
  canvas.width = cw; canvas.height = ch
  const ctx = canvas.getContext('2d')
  ctx.font = `${fontSize}px Arial,sans-serif`
  ctx.fillStyle = '#444'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, cw / 2, ch / 2)
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true })
  )
  const h = text.length > 3 ? 12 : 10
  sprite.scale.set(h * (cw / ch), h, 1)
  return sprite
}

// Determine which edges to place ticks on based on current camera position.
// Returns { lEdge, hPlane, bEdge, aEdge }.
//
// lEdge  — index into V_EDGES for L* ticks: the leftmost vertical edge in NDC.
// hPlane — Y coordinate of the horizontal plane for a*/b* ticks:
//   L*=0 when camera is above it (camera.y ≥ 0), L*=100 when camera is below.
//   With inward normals, both planes are simultaneously visible when the camera
//   is between them (0 < y < 100) — the user's rule is to use L*=0 in that case,
//   which this implements.
// bEdge  — Z coordinate of the closer b*-axis edge (Z=±128).
// aEdge  — X coordinate of the closer a*-axis edge (X=±128).
function computeTickState() {
  const cp = camera.position

  // Leftmost vertical edge in screen space
  let minNdcX = Infinity, lEdge = 0
  for (let i = 0; i < V_EDGES.length; i++) {
    const ndc = new THREE.Vector3(V_EDGES[i].x, 50, V_EDGES[i].z).project(camera)
    if (ndc.x < minNdcX) { minNdcX = ndc.x; lEdge = i }
  }

  const hPlane = cp.y < Y0 ? Y1 : Y0
  const bEdge  = Math.abs(cp.z - Z1) <= Math.abs(cp.z - Z0) ? Z1 : Z0
  const aEdge  = Math.abs(cp.x - X0) <= Math.abs(cp.x - X1) ? X0 : X1

  return { lEdge, hPlane, bEdge, aEdge }
}

function stateEqual(a, b) {
  return a && b &&
    a.lEdge === b.lEdge && a.hPlane === b.hPlane &&
    a.bEdge === b.bEdge && a.aEdge === b.aEdge
}

function buildTickGroup(state) {
  const group = new THREE.Group()
  const T = 5
  const tPts = []

  const ve   = V_EDGES[state.lEdge]
  const hDy  = state.hPlane === Y0 ? -1 : 1    // outward Y from horizontal plane
  const bDz  = state.bEdge === Z1  ?  1 : -1   // outward Z from b* edge
  const aDx  = state.aEdge === X0  ? -1 :  1   // outward X from a* edge

  // L* ticks on leftmost vertical edge
  for (let l = 0; l <= 100; l += 20) {
    tPts.push(
      new THREE.Vector3(ve.x,            l, ve.z),
      new THREE.Vector3(ve.x + ve.dx*T,  l, ve.z + ve.dz*T),
    )
    const s = makeTextSprite(String(l))
    s.position.set(ve.x + ve.dx*20, l, ve.z + ve.dz*16)
    group.add(s)
  }
  const ll = makeTextSprite('L*', 32)
  ll.position.set(ve.x + ve.dx*32, 50, ve.z + ve.dz*32)
  group.add(ll)

  // b* ticks on closer b*-axis edge of horizontal plane
  for (let b = -100; b <= 100; b += 20) {
    tPts.push(
      new THREE.Vector3(b, state.hPlane,          state.bEdge),
      new THREE.Vector3(b, state.hPlane + hDy*T,  state.bEdge + bDz*T),
    )
    const s = makeTextSprite(String(b))
    s.position.set(b, state.hPlane + hDy*14, state.bEdge + bDz*16)
    group.add(s)
  }
  const lb = makeTextSprite('b*', 32)
  lb.position.set(0, state.hPlane + hDy*26, state.bEdge + bDz*26)
  group.add(lb)

  // a* ticks on closer a*-axis edge of horizontal plane
  for (let a = -100; a <= 100; a += 20) {
    tPts.push(
      new THREE.Vector3(state.aEdge,         state.hPlane,          a),
      new THREE.Vector3(state.aEdge + aDx*T, state.hPlane + hDy*T,  a),
    )
    const s = makeTextSprite(String(a))
    s.position.set(state.aEdge + aDx*20, state.hPlane + hDy*14, a)
    group.add(s)
  }
  const la = makeTextSprite('a*', 32)
  la.position.set(state.aEdge + aDx*32, state.hPlane + hDy*26, 0)
  group.add(la)

  group.add(new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(tPts),
    new THREE.LineBasicMaterial({ color: 0x555555 })
  ))

  return group
}

function disposeGroup(group) {
  group?.traverse(obj => {
    obj.geometry?.dispose()
    if (obj.material) { obj.material.map?.dispose(); obj.material.dispose() }
  })
}

function updateTicks() {
  const state = computeTickState()
  if (stateEqual(state, currentTickState)) return
  currentTickState = state

  if (tickGroup) { scene.remove(tickGroup); disposeGroup(tickGroup) }
  tickGroup = buildTickGroup(state)
  scene.add(tickGroup)
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  const el = container.value
  const w = el.clientWidth || 600
  const h = el.clientHeight || 400

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf0f2f5)

  camera = new THREE.PerspectiveCamera(45, w / h, 1, 2000)
  camera.position.set(50, 120, 320)
  camera.lookAt(0, 50, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(w, h)
  el.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0xffffff, 0.55))
  const dl1 = new THREE.DirectionalLight(0xffffff, 0.85)
  dl1.position.set(100, 200, 100)
  scene.add(dl1)
  const dl2 = new THREE.DirectionalLight(0x9999ff, 0.25)
  dl2.position.set(-120, -80, -100)
  scene.add(dl2)

  axisGroup = buildAxisBox()
  scene.add(axisGroup)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 50, 0)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.update()

  // Rebuild ticks whenever the camera moves; stateEqual guard makes this cheap.
  controls.addEventListener('change', updateTicks)

  ro = new ResizeObserver(entries => {
    const { width, height } = entries[0].contentRect
    if (width === 0 || height === 0) return
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  })
  ro.observe(el)

  function animate() {
    animId = requestAnimationFrame(animate)
    controls.update()
    renderer.render(scene, camera)
  }
  animate()

  // Initial tick placement once camera matrices are valid.
  camera.updateMatrixWorld()
  updateTicks()

  syncMeshes(props.gamuts)
})

watch(
  () => props.gamuts.map(g => `${g.id}:${g.colour}:${g.visible}:${g.alpha}:${!!g.surface}`).join('|'),
  () => { if (scene) syncMeshes(props.gamuts) },
)

onUnmounted(() => {
  cancelAnimationFrame(animId)
  ro?.disconnect()
  controls?.removeEventListener('change', updateTicks)
  controls?.dispose()
  disposeGroup(axisGroup)
  disposeGroup(tickGroup)
  for (const { geo, mat } of meshMap.values()) { geo.dispose(); mat.dispose() }
  meshMap.clear()
  renderer?.dispose()
})
</script>

<style scoped>
.surface-canvas {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.surface-canvas :deep(canvas) {
  display: block;
}
</style>
