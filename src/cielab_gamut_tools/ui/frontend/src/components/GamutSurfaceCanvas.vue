<template>
  <div ref="container" class="surface-canvas" />
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { labVerticesToColors } from '../gamut/labToRgb.js'
import { useCanvasCapture } from '../composables/useCanvasCapture.js'

const capture = useCanvasCapture()

const props = defineProps({
  // Array of { id, colour, surface, visible, alpha, wireframe, chroma, lightness, edgeColour }
  gamuts: { type: Array, default: () => [] },
  // 0 = isometric (narrow FOV), 1 = perspective (normal FOV)
  perspectiveBlend: { type: Number, default: 1 },
  // Degrees above the horizontal (a*b*) plane — syncs with the panel inputs
  cameraElev: { type: Number, default: 12 },
  // Degrees around the L* axis from +a* direction — syncs with the panel inputs
  cameraAzim: { type: Number, default: 9 },
  // Distance from camera to orbit target — syncs with the panel inputs
  cameraDistance: { type: Number, default: 331 },
  // Colour space for Lab→RGB vertex colour conversion ('srgb' | 'display-p3')
  colourSpace: { type: String, default: 'srgb' },
})

const emit = defineEmits(['camera-change'])

const container = ref(null)

let renderer, scene, camera, perspCamera, orthoCamera, controls, animId, ro
// id → { solidMesh, edgesMesh, solidGeo, edgesGeo, solidMat, edgesMat }
const meshMap = new Map()
let axisGroup = null
let tickGroup  = null
let currentTickState = null

// Tracks the last camera state we emitted so we can break the prop-watch feedback loop.
let lastEmittedElev = null
let lastEmittedAzim = null
let lastEmittedDist = null

// ── Projection blend — perspective (blend>0) ↔ true isometric (blend=0) ─────
const FOV_PERSPECTIVE = 45   // degrees at blend=1; FOV = 45*blend for blend>0

function applyPerspectiveBlend(blend) {
  if (!perspCamera || !controls) return

  if (blend === 0) {
    if (camera !== orthoCamera) {
      const dist = perspCamera.position.distanceTo(controls.target)
      const halfH = dist * Math.tan(perspCamera.fov / 2 * Math.PI / 180)
      const aspect = perspCamera.aspect
      orthoCamera.left   = -halfH * aspect
      orthoCamera.right  =  halfH * aspect
      orthoCamera.top    =  halfH
      orthoCamera.bottom = -halfH
      orthoCamera.near   = dist - 400
      orthoCamera.far    = dist + 400
      orthoCamera.zoom   = 1
      orthoCamera.position.copy(perspCamera.position)
      orthoCamera.quaternion.copy(perspCamera.quaternion)
      orthoCamera.up.copy(perspCamera.up)
      orthoCamera.updateProjectionMatrix()
      camera = orthoCamera
      controls.object = orthoCamera
      controls.update()
    }
    return
  }

  if (camera === orthoCamera) {
    const halfH = orthoCamera.top / orthoCamera.zoom
    const newFovRad = FOV_PERSPECTIVE * blend * Math.PI / 180
    const newDist = halfH / Math.tan(newFovRad / 2)
    const dir = new THREE.Vector3().subVectors(orthoCamera.position, controls.target).normalize()
    perspCamera.fov = FOV_PERSPECTIVE * blend
    perspCamera.updateProjectionMatrix()
    perspCamera.position.copy(controls.target).addScaledVector(dir, newDist)
    perspCamera.quaternion.copy(orthoCamera.quaternion)
    perspCamera.up.copy(orthoCamera.up)
    camera = perspCamera
    controls.object = perspCamera
    controls.update()
    return
  }

  // Perspective-only path: vary FOV and compensate distance to preserve viewHeight.
  const newFov = FOV_PERSPECTIVE * blend
  const dir = new THREE.Vector3().subVectors(perspCamera.position, controls.target).normalize()
  const currentDist = perspCamera.position.distanceTo(controls.target)
  const oldFovRad = perspCamera.fov * Math.PI / 180
  const newFovRad = newFov * Math.PI / 180
  const newDist = currentDist * Math.tan(oldFovRad / 2) / Math.tan(newFovRad / 2)
  perspCamera.fov = newFov
  perspCamera.updateProjectionMatrix()
  perspCamera.position.copy(controls.target).addScaledVector(dir, newDist)
}

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

// ── Camera angle helpers ────────────────────────────────────────────────────
// Convention: elev = degrees above the horizontal (XZ / a*b*) plane (0=side, 90=top).
// azim = degrees in the XZ plane measured from +Z (a*), counterclockwise looking down.
// Matches the Three.js Spherical: phi from +Y, theta from +Z.

function getCameraAngles() {
  if (!controls || !camera) return null
  const sp = new THREE.Spherical()
  const rel = new THREE.Vector3().subVectors(camera.position, controls.target)
  sp.setFromCartesianCoords(rel.x, rel.y, rel.z)
  let azim = sp.theta * 180 / Math.PI
  while (azim >  180) azim -= 360
  while (azim < -180) azim += 360
  return {
    elev: Math.round(90 - sp.phi * 180 / Math.PI),
    azim: Math.round(azim),
    dist: Math.round(sp.radius),
  }
}

function setCameraFromAngles(elev, azim, dist = null) {
  if (!controls || !camera) return
  const sp = new THREE.Spherical()
  const rel = new THREE.Vector3().subVectors(camera.position, controls.target)
  sp.setFromCartesianCoords(rel.x, rel.y, rel.z)
  // Keep phi just off the poles so the position vector retains an x/z component.
  // At exactly phi=0 the position is (0,r,0) and atan2(0,0)=0 — OrbitControls'
  // next update() would silently reset theta (azimuth) to 0.
  const EPS = 1e-4
  sp.phi   = Math.max(EPS, Math.min(Math.PI - EPS, (90 - elev) * Math.PI / 180))
  sp.theta = azim * Math.PI / 180
  if (dist !== null) sp.radius = dist
  camera.position.copy(
    new THREE.Vector3().setFromSpherical(sp).add(controls.target)
  )
  camera.lookAt(controls.target)
  controls.update()
  updateTicks()
  updateRenderOrder()
}

// ── Gamut geometry ──────────────────────────────────────────────────────────
// vertices: [[L*, a*, b*], …] → Three.js [b*, L*, a*] (X, Y, Z)
// Vertex colours are computed from Lab values using the current colourSpace.

function buildGeometry({ vertices, faces }, colourSpace, chroma = 1.0, lightness = null) {
  const n = vertices.length
  const positions = new Float32Array(n * 3)
  for (let i = 0; i < n; i++) {
    const [L, a, b] = vertices[i]
    positions[i * 3 + 0] = b
    positions[i * 3 + 1] = L
    positions[i * 3 + 2] = a
  }
  const flatIdx = new Uint16Array(faces.length * 3)
  for (let i = 0; i < faces.length; i++) {
    // Reverse winding so normals point outward in Three.js (X=b*, Y=L*, Z=a*).
    // The Python tessellation winding is designed for matplotlib's (a*, b*, L*)
    // axis order; the coordinate remapping changes handedness, so normals are
    // flipped here to restore outward-facing fronts and correct Phong shading.
    flatIdx[i * 3 + 0] = faces[i][0]
    flatIdx[i * 3 + 1] = faces[i][2]
    flatIdx[i * 3 + 2] = faces[i][1]
  }
  const colors = labVerticesToColors(vertices, colourSpace, chroma, lightness)

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('color',    new THREE.BufferAttribute(colors, 3))
  geo.setIndex(new THREE.BufferAttribute(flatIdx, 1))
  geo.computeVertexNormals()
  return geo
}

// Build a LineSegments geometry for wireframe rendering, carrying vertex colours
// derived from the solid geometry's indexed faces.
// Returns { geo, vertIndices } — vertIndices is kept in meshMap so edge colours
// can be updated in-place without rebuilding positions.
function buildEdgesGeometry(solidGeo) {
  const index  = solidGeo.index.array
  const srcPos = solidGeo.attributes.position
  const srcCol = solidGeo.attributes.color
  const n = index.length  // 3 × numFaces

  // Collect unique undirected edges.
  const seen = new Set()
  const vertIndices = []   // flat list: [u0, v0, u1, v1, …]
  for (let i = 0; i < n; i += 3) {
    const a = index[i], b = index[i + 1], c = index[i + 2]
    for (const [u, v] of [[a, b], [b, c], [c, a]]) {
      const key = u < v ? u * 65536 + v : v * 65536 + u
      if (!seen.has(key)) {
        seen.add(key)
        vertIndices.push(u, v)
      }
    }
  }

  const ne = vertIndices.length
  const positions = new Float32Array(ne * 3)
  const colors    = new Float32Array(ne * 3)
  for (let i = 0; i < ne; i++) {
    const vi = vertIndices[i]
    positions[i * 3]     = srcPos.getX(vi)
    positions[i * 3 + 1] = srcPos.getY(vi)
    positions[i * 3 + 2] = srcPos.getZ(vi)
    colors[i * 3]         = srcCol.getX(vi)
    colors[i * 3 + 1]     = srcCol.getY(vi)
    colors[i * 3 + 2]     = srcCol.getZ(vi)
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('color',    new THREE.BufferAttribute(colors, 3))
  return { geo, vertIndices }
}

// Copy Lab-derived colours from the solid geometry into the edge geometry,
// using the stored vertex index list.
function updateEdgeColorsFromSolid(edgesGeo, solidGeo, vertIndices) {
  const srcCol = solidGeo.attributes.color
  const arr    = edgesGeo.attributes.color.array
  for (let i = 0; i < vertIndices.length; i++) {
    const vi = vertIndices[i]
    arr[i * 3]     = srcCol.getX(vi)
    arr[i * 3 + 1] = srcCol.getY(vi)
    arr[i * 3 + 2] = srcCol.getZ(vi)
  }
  edgesGeo.attributes.color.needsUpdate = true
}

// Fill the edge geometry colour buffer with a single flat colour.
function fillEdgeColour(edgesGeo, hexColour) {
  const c   = new THREE.Color(hexColour)
  const arr = edgesGeo.attributes.color.array
  const n   = arr.length / 3
  for (let i = 0; i < n; i++) {
    arr[i * 3]     = c.r
    arr[i * 3 + 1] = c.g
    arr[i * 3 + 2] = c.b
  }
  edgesGeo.attributes.color.needsUpdate = true
}

function syncMeshes(gamuts) {
  const activeIds = new Set(gamuts.map(g => g.id))

  for (const [id, entry] of meshMap) {
    if (!activeIds.has(id)) {
      scene.remove(entry.solidMesh)
      scene.remove(entry.edgesMesh)
      entry.solidGeo.dispose()
      entry.edgesGeo.dispose()
      entry.solidMat.dispose()
      entry.edgesMat.dispose()
      meshMap.delete(id)
    }
  }

  for (const g of gamuts) {
    if (!g.surface) continue
    const alpha      = g.alpha      ?? 0.75
    const visible    = g.visible    ?? true
    const wireframe  = g.wireframe  ?? false
    const chroma     = g.chroma     ?? 1.0
    const lightness  = g.lightness  ?? null
    const edgeColour = g.edgeColour ?? null

    if (meshMap.has(g.id)) {
      const entry = meshMap.get(g.id)
      const { solidMesh, edgesMesh, solidMat, edgesMat } = entry
      let { solidGeo, edgesGeo, vertIndices } = entry

      if (entry.surface !== g.surface) {
        // Surface geometry changed — dispose old and rebuild.
        entry.solidGeo.dispose()
        entry.edgesGeo.dispose()
        solidGeo = buildGeometry(g.surface, props.colourSpace, chroma, lightness)
        const built = buildEdgesGeometry(solidGeo)
        edgesGeo = built.geo
        vertIndices = built.vertIndices
        solidMesh.geometry = solidGeo
        edgesMesh.geometry = edgesGeo
        entry.solidGeo    = solidGeo
        entry.edgesGeo    = edgesGeo
        entry.vertIndices = vertIndices
        entry.surface     = g.surface
      } else {
        // Recompute vertex colours in-place (chroma/lightness/colourSpace may have changed).
        const newColors = labVerticesToColors(g.surface.vertices, props.colourSpace, chroma, lightness)
        solidGeo.attributes.color.set(newColors)
        solidGeo.attributes.color.needsUpdate = true
      }

      // Propagate to edges — either Lab-derived or a flat override.
      if (edgeColour) {
        fillEdgeColour(edgesGeo, edgeColour)
      } else {
        updateEdgeColorsFromSolid(edgesGeo, solidGeo, vertIndices)
      }

      solidMat.opacity     = alpha
      solidMat.transparent = alpha < 1.0
      solidMat.depthWrite  = alpha >= 1.0
      solidMat.needsUpdate = true
      edgesMat.opacity     = alpha
      edgesMat.transparent = alpha < 1.0
      edgesMat.needsUpdate = true

      solidMesh.visible = !wireframe && visible
      edgesMesh.visible =  wireframe && visible
    } else {
      const solidGeo = buildGeometry(g.surface, props.colourSpace, chroma, lightness)
      const { geo: edgesGeo, vertIndices } = buildEdgesGeometry(solidGeo)

      if (edgeColour) fillEdgeColour(edgesGeo, edgeColour)

      const solidMat = new THREE.MeshPhongMaterial({
        vertexColors: true,
        color: 0xffffff,   // white so vertex colours are unmodulated
        opacity: alpha,
        transparent: alpha < 1.0,
        depthWrite: alpha >= 1.0,
        side: THREE.FrontSide,
        shininess: 30,
      })
      const edgesMat = new THREE.LineBasicMaterial({
        vertexColors: true,
        opacity: alpha,
        transparent: alpha < 1.0,
      })
      const solidMesh = new THREE.Mesh(solidGeo, solidMat)
      const edgesMesh = new THREE.LineSegments(edgesGeo, edgesMat)
      solidMesh.visible = !wireframe && visible
      edgesMesh.visible =  wireframe && visible
      scene.add(solidMesh)
      scene.add(edgesMesh)
      meshMap.set(g.id, { solidMesh, edgesMesh, solidGeo, edgesGeo, solidMat, edgesMat, vertIndices, surface: g.surface })
    }
  }
  updateRenderOrder()
}

// ── Axis box — static parts (panes + edges) ─────────────────────────────────

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

function computeTickState() {
  const cp = camera.position

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
  const hDy  = state.hPlane === Y0 ? -1 : 1
  const bDz  = state.bEdge === Z1  ?  1 : -1
  const aDx  = state.aEdge === X0  ? -1 :  1

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

function updateRenderOrder() {
  if (!camera || meshMap.size < 2) return
  const entries = []
  for (const [, entry] of meshMap) {
    const geo = entry.solidGeo
    if (!geo.boundingSphere) geo.computeBoundingSphere()
    const dist = camera.position.distanceTo(geo.boundingSphere.center)
    entries.push({ entry, nearDist: dist - geo.boundingSphere.radius })
  }
  entries.sort((a, b) => b.nearDist - a.nearDist)
  entries.forEach(({ entry }, i) => {
    entry.solidMesh.renderOrder = i
    entry.edgesMesh.renderOrder = i
  })
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  const el = container.value
  const w = el.clientWidth || 600
  const h = el.clientHeight || 400

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf0f2f5)

  perspCamera = new THREE.PerspectiveCamera(FOV_PERSPECTIVE, w / h, 1, 10000)
  perspCamera.position.set(50, 120, 320)
  perspCamera.lookAt(0, 50, 0)
  orthoCamera = new THREE.OrthographicCamera(0, 0, 0, 0, -5000, 5000)
  camera = perspCamera

  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
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

  // Apply stored camera angle and distance (overrides the hardcoded initial position above).
  setCameraFromAngles(props.cameraElev, props.cameraAzim, props.cameraDistance)

  // Apply initial projection blend.
  applyPerspectiveBlend(props.perspectiveBlend)

  controls.addEventListener('change', () => {
    updateTicks()
    updateRenderOrder()
    const angles = getCameraAngles()
    if (angles) {
      lastEmittedElev = angles.elev
      lastEmittedAzim = angles.azim
      lastEmittedDist = angles.dist
      emit('camera-change', angles)
    }
  })

  ro = new ResizeObserver(entries => {
    const { width, height } = entries[0].contentRect
    if (width === 0 || height === 0) return
    perspCamera.aspect = width / height
    perspCamera.updateProjectionMatrix()
    if (camera === orthoCamera) {
      const halfH = orthoCamera.top
      orthoCamera.left  = -halfH * (width / height)
      orthoCamera.right =  halfH * (width / height)
      orthoCamera.updateProjectionMatrix()
    }
    renderer.setSize(width, height)
  })
  ro.observe(el)

  function animate() {
    animId = requestAnimationFrame(animate)
    controls.update()
    {
      const dist = camera.position.distanceTo(controls.target)
      const near = (camera === orthoCamera) ? dist - 400 : Math.max(0.1, dist - 300)
      const far  = dist + 400
      if (camera.near !== near || camera.far !== far) {
        camera.near = near
        camera.far  = far
        camera.updateProjectionMatrix()
      }
    }
    renderer.render(scene, camera)
  }
  animate()

  camera.updateMatrixWorld()
  updateTicks()

  syncMeshes(props.gamuts)

  capture.register(() => {
    renderer.render(scene, camera)
    return new Promise(resolve => {
      renderer.domElement.toBlob(b => resolve(b), 'image/png')
    })
  })
})

watch(
  () => props.gamuts.map(g =>
    `${g.id}:${g.visible}:${g.alpha}:${g.wireframe}:${g.chroma}:${g.lightness}:${g.edgeColour}:${!!g.surface}:${g._sv ?? 0}`
  ).join('|'),
  () => { if (scene) syncMeshes(props.gamuts) },
)

watch(
  () => props.perspectiveBlend,
  (blend) => { if (perspCamera && controls) applyPerspectiveBlend(blend) },
)

// When camera angles are changed from outside (panel inputs), reposition the
// camera. Guard skips the update if the values match what we just emitted from
// an orbit event, preventing the prop-watch feedback loop.
watch(
  () => [props.cameraElev, props.cameraAzim, props.cameraDistance],
  ([elev, azim, dist]) => {
    if (!camera || !controls) return
    if (lastEmittedElev !== null &&
        Math.abs(elev - lastEmittedElev) < 1 &&
        Math.abs(azim - lastEmittedAzim) < 1 &&
        lastEmittedDist !== null && Math.abs(dist - lastEmittedDist) < 1) return
    setCameraFromAngles(elev, azim, dist)
  },
)

// Rebuild all geometries when the colour space changes (future: display-p3 toggle).
watch(
  () => props.colourSpace,
  () => {
    if (!scene) return
    for (const { solidMesh, edgesMesh, solidGeo, edgesGeo, solidMat, edgesMat } of meshMap.values()) {
      scene.remove(solidMesh)
      scene.remove(edgesMesh)
      solidGeo.dispose()
      edgesGeo.dispose()
      solidMat.dispose()
      edgesMat.dispose()
    }
    meshMap.clear()
    syncMeshes(props.gamuts)
  },
)

onUnmounted(() => {
  capture.unregister()
  cancelAnimationFrame(animId)
  ro?.disconnect()
  controls?.dispose()
  disposeGroup(axisGroup)
  disposeGroup(tickGroup)
  for (const { solidGeo, edgesGeo, solidMat, edgesMat } of meshMap.values()) {
    solidGeo.dispose()
    edgesGeo.dispose()
    solidMat.dispose()
    edgesMat.dispose()
  }
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
