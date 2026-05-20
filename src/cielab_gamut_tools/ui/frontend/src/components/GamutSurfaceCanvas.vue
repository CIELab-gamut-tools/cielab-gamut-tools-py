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

// Build a BufferGeometry from surface data.
// vertices: [[L*, a*, b*], ...] → mapped to [a*, L*, b*] (X, Y, Z).
function buildGeometry({ vertices, faces }) {
  const positions = new Float32Array(vertices.length * 3)
  for (let i = 0; i < vertices.length; i++) {
    const [L, a, b] = vertices[i]
    positions[i * 3 + 0] = a
    positions[i * 3 + 1] = L
    positions[i * 3 + 2] = b
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

  // Remove meshes for gamuts no longer in the list
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

  // Lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.55))
  const dl1 = new THREE.DirectionalLight(0xffffff, 0.85)
  dl1.position.set(100, 200, 100)
  scene.add(dl1)
  const dl2 = new THREE.DirectionalLight(0x9999ff, 0.25)
  dl2.position.set(-120, -80, -100)
  scene.add(dl2)

  // Reference grid on the L*=0 plane (a*–b* plane)
  const grid = new THREE.GridHelper(300, 10, 0xaaaaaa, 0xcccccc)
  grid.position.y = 0
  scene.add(grid)

  // L* axis line
  const axisGeo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0, 100, 0),
  ])
  scene.add(new THREE.Line(axisGeo, new THREE.LineBasicMaterial({ color: 0x888888 })))

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

// Watch for gamut list / surface / visibility / alpha changes.
// Avoids deep-watching the large vertices/faces arrays by keying on derived scalars.
watch(
  () => props.gamuts.map(g => `${g.id}:${g.colour}:${g.visible}:${g.alpha}:${!!g.surface}`).join('|'),
  () => { if (scene) syncMeshes(props.gamuts) },
)

onUnmounted(() => {
  cancelAnimationFrame(animId)
  ro?.disconnect()
  controls?.dispose()
  for (const { geo, mat } of meshMap.values()) {
    geo.dispose()
    mat.dispose()
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
