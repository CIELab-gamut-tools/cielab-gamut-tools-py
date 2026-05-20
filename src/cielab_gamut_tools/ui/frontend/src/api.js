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

export async function createSynthetic(payload) {
  return (await req('POST', '/gamuts/synthetic', payload)).json()
}

export async function deleteGamut(id) {
  await req('DELETE', `/gamuts/${id}`)
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
