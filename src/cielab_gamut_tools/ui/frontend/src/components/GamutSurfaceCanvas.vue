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
    const alpha = g.alpha ?? 0.75
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

// ── Axis box ────────────────────────────────────────────────────────────────
// Three.js axes: X = b*, Y = L*, Z = a*
// Six panes use inward-pointing normals + FrontSide culling — the 3 panes
// facing away from the camera are automatically hidden each frame with no
// per-frame visibility logic needed.

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
  const aspect = cw / ch
  const h = text.length > 3 ? 12 : 10
  sprite.scale.set(h * aspect, h, 1)
  return sprite
}

function buildAxisBox() {
  const X0 = -128, X1 = 128   // b* world extent
  const Y0 = 0,   Y1 = 100    // L* world extent
  const Z0 = -128, Z1 = 128   // a* world extent
  const group = new THREE.Group()

  // ── Panes ────────────────────────────────────────────────────────────────
  // Each PlaneGeometry's default normal is +Z (local).  We rotate it so the
  // normal points inward (toward the box centre).  Three.js FrontSide culling
  // then hides whichever 3 panes face the camera.
  const paneMat = new THREE.MeshBasicMaterial({
    color: 0xd8dde2,
    side: THREE.FrontSide,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
  })
  // [cx, cy, cz, rotX, rotY,  planeW, planeH]
  const paneConfigs = [
    [X0,  50,   0,  0,          Math.PI/2,  256, 100],  // b*=min  normal→+X
    [X1,  50,   0,  0,         -Math.PI/2,  256, 100],  // b*=max  normal→-X
    [0,   Y0,   0, -Math.PI/2,  0,          256, 256],  // L*=0    normal→+Y
    [0,   Y1,   0,  Math.PI/2,  0,          256, 256],  // L*=100  normal→-Y
    [0,   50,  Z0,  0,          0,          256, 100],  // a*=min  normal→+Z
    [0,   50,  Z1,  0,          Math.PI,    256, 100],  // a*=max  normal→-Z
  ]
  for (const [cx, cy, cz, rx, ry, w, h] of paneConfigs) {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), paneMat)
    mesh.position.set(cx, cy, cz)
    mesh.rotation.set(rx, ry, 0)
    group.add(mesh)
  }

  // ── Edges ────────────────────────────────────────────────────────────────
  const corners = [
    [X0,Y0,Z0],[X1,Y0,Z0],[X1,Y1,Z0],[X0,Y1,Z0],
    [X0,Y0,Z1],[X1,Y0,Z1],[X1,Y1,Z1],[X0,Y1,Z1],
  ]
  const edgePairs = [
    [0,1],[1,2],[2,3],[3,0],   // back face (a*=min)
    [4,5],[5,6],[6,7],[7,4],   // front face (a*=max)
    [0,4],[1,5],[2,6],[3,7],   // connecting edges
  ]
  const ePts = edgePairs.flatMap(([a, b]) => [
    new THREE.Vector3(...corners[a]),
    new THREE.Vector3(...corners[b]),
  ])
  group.add(new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(ePts),
    new THREE.LineBasicMaterial({ color: 0x777777 })
  ))

  // ── Tick marks ───────────────────────────────────────────────────────────
  // L* on front-left edge (X=X0, Z=Z1), b* on bottom-front (Y=Y0, Z=Z1),
  // a* on bottom-left (Y=Y0, X=X0).
  const T = 5
  const tPts = []
  for (let l = 0; l <= 100; l += 20) {
    tPts.push(new THREE.Vector3(X0, l, Z1), new THREE.Vector3(X0 - T, l, Z1 + T))
  }
  for (let b = -100; b <= 100; b += 50) {
    tPts.push(new THREE.Vector3(b, Y0, Z1), new THREE.Vector3(b, Y0 - T, Z1 + T))
  }
  for (let a = -100; a <= 100; a += 50) {
    tPts.push(new THREE.Vector3(X0, Y0, a), new THREE.Vector3(X0 - T, Y0 - T, a))
  }
  group.add(new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(tPts),
    new THREE.LineBasicMaterial({ color: 0x555555 })
  ))

  // ── Tick labels ──────────────────────────────────────────────────────────
  for (let l = 0; l <= 100; l += 20) {
    const s = makeTextSprite(String(l))
    s.position.set(X0 - 20, l, Z1 + 16)
    group.add(s)
  }
  for (let b = -100; b <= 100; b += 50) {
    const s = makeTextSprite(String(b))
    s.position.set(b, Y0 - 14, Z1 + 16)
    group.add(s)
  }
  for (let a = -100; a <= 100; a += 50) {
    const s = makeTextSprite(String(a))
    s.position.set(X0 - 20, Y0 - 14, a)
    group.add(s)
  }

  // Axis name labels
  const lb = makeTextSprite('b*', 32); lb.position.set(0, Y0 - 26, Z1 + 26); group.add(lb)
  const la = makeTextSprite('a*', 32); la.position.set(X0 - 28, Y0 - 26, 0); group.add(la)
  const ll = makeTextSprite('L*', 32); ll.position.set(X0 - 32, 50, Z1 + 32); group.add(ll)

  return group
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

  syncMeshes(props.gamuts)
})

watch(
  () => props.gamuts.map(g => `${g.id}:${g.colour}:${g.visible}:${g.alpha}:${!!g.surface}`).join('|'),
  () => { if (scene) syncMeshes(props.gamuts) },
)

onUnmounted(() => {
  cancelAnimationFrame(animId)
  ro?.disconnect()
  controls?.dispose()
  axisGroup?.traverse(obj => {
    obj.geometry?.dispose()
    if (obj.material) { obj.material.map?.dispose(); obj.material.dispose() }
  })
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
