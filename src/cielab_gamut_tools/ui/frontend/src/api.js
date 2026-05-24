const BASE = '/api'

async function req(method, path, body) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? res.statusText)
  }
  return res
}

export async function getAbout() {
  return (await req('GET', '/about')).json()
}

export async function keepalive() {
  return (await req('GET', '/keepalive')).json()
}

export async function closeKeepalive() {
  // Use fetch directly with keepalive:true so the request survives tab close.
  await fetch('/api/keepalive', { method: 'DELETE', keepalive: true })
}

export async function listGamuts() {
  return (await req('GET', '/gamuts')).json()
}

export async function uploadGamut(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(BASE + '/gamuts/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? res.statusText)
  }
  return res.json()
}

/**
 * Decode the combined binary response from POST/PATCH synthetic endpoints.
 * Wire format: uint32 json_len + UTF-8 JSON + padding + packed cylmap binary.
 */
function decodeSynthResponse(buf) {
  const view = new DataView(buf)
  const jsonLen = view.getUint32(0, true)
  const entry = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, jsonLen)))

  const cylmapOffset = Math.ceil((4 + jsonLen) / 4) * 4
  const lSteps = view.getUint32(cylmapOffset, true)
  const hSteps = view.getUint32(cylmapOffset + 4, true)
  const nCells = lSteps * hSteps
  const counts = new Uint8Array(buf, cylmapOffset + 8, nCells)
  const chromaByteStart = Math.ceil((cylmapOffset + 8 + nCells) / 4) * 4
  const chroma = new Float32Array(buf, chromaByteStart)

  const offsets = new Uint32Array(nCells)
  let acc = 0
  for (let i = 0; i < nCells; i++) { offsets[i] = acc; acc += counts[i] }

  return { entry, packed: { lSteps, hSteps, counts, chroma, offsets } }
}

export async function createSynthetic(payload) {
  const res = await req('POST', '/gamuts/synthetic', payload)
  return decodeSynthResponse(await res.arrayBuffer())
}

export async function updateSynthetic(id, payload) {
  const res = await req('PATCH', `/gamuts/${id}/synthetic`, payload)
  return decodeSynthResponse(await res.arrayBuffer())
}

export async function deleteGamut(id) {
  await req('DELETE', `/gamuts/${id}`)
}

export async function renameGamut(id, name) {
  return (await req('PATCH', `/gamuts/${id}`, { name })).json()
}

export async function getVolume(id) {
  return (await req('GET', `/gamuts/${id}/volume`)).json()
}

export async function getSurface(id) {
  return (await req('GET', `/gamuts/${id}/surface`)).json()
}

export async function getCoverage(dutId, referenceId) {
  return (await req('POST', '/gamuts/coverage', { dut_id: dutId, reference_id: referenceId })).json()
}

export async function getMatrix(ids) {
  return (await req('POST', '/gamuts/matrix', { ids })).json()
}

export async function renderRings(options) {
  const res = await req('POST', '/render/rings', options)
  return res.blob()
}

function triggerDownload(blob, filename) {
  // Wrap as octet-stream to prevent Firefox's PDF viewer from intercepting
  // application/pdf blobs and opening them inline instead of downloading.
  const safe = new Blob([blob], { type: 'application/octet-stream' })
  const url = URL.createObjectURL(safe)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function downloadRings(options) {
  const res = await req('POST', '/render/rings', options)
  triggerDownload(await res.blob(), `rings.${options.format || 'png'}`)
}

export async function downloadSurface(options) {
  const res = await req('POST', '/export/surface', options)
  triggerDownload(await res.blob(), `surface.${options.format || 'png'}`)
}

/**
 * Fetch and decode the binary cylmap for a gamut.
 *
 * Wire format:
 *   uint32  l_steps
 *   uint32  h_steps
 *   uint8[] counts[l_steps × h_steps]   (row-major)
 *   uint8[] padding to 4-byte boundary
 *   float32[] chroma[sum(counts)]
 *
 * Returns { lSteps, hSteps, counts: Uint8Array, chroma: Float32Array, offsets: Uint32Array }
 * where offsets[i] is the index into chroma[] for cell i (prefix-sum of counts).
 */
export async function getCylmap(id) {
  const res = await req('GET', `/gamuts/${id}/cylmap`)
  const buf = await res.arrayBuffer()
  const view = new DataView(buf)

  const lSteps = view.getUint32(0, true)
  const hSteps = view.getUint32(4, true)
  const nCells = lSteps * hSteps

  const counts = new Uint8Array(buf, 8, nCells)

  const countsByteEnd = 8 + nCells
  const chromaByteStart = Math.ceil(countsByteEnd / 4) * 4
  const chroma = new Float32Array(buf, chromaByteStart)

  // Build prefix-sum offset table for O(1) cell access
  const offsets = new Uint32Array(nCells)
  let acc = 0
  for (let i = 0; i < nCells; i++) {
    offsets[i] = acc
    acc += counts[i]
  }

  return { lSteps, hSteps, counts, chroma, offsets }
}
