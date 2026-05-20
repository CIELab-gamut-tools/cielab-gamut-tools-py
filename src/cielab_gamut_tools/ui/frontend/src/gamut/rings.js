/**
 * Compute C*_RSS rings from a cylmap gamut object.
 *
 * Rewrite of gamut-rings-app/src/gamut/rings.js without t-matrix.
 *
 * @param {Object} g            - { lSteps, hSteps, cylmap[l][h] }
 * @param {Float64Array|null} refCssC - if set, apply the reference offset
 *   (pass cssC from a prior computeRings call on the reference gamut)
 * @returns {{ cssA, cssB, cssC, totalVol }}
 *   All arrays are Float64Array of length nRings * hSteps (row-major, ring first).
 *   totalVol is the gamut volume (same formula as Python volume()).
 */

const N_RINGS = 10
const L_VALUES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

export function computeRings(g, refCssC = null) {
  const { lSteps, hSteps, cylmap } = g
  const dH = 2 * Math.PI / hSteps
  const dL = 100 / lSteps
  const c = dL * dH / 2

  // Step 1: volMap[l * hSteps + h] = Σ sign * dist² * c for each cell
  const volMap = new Float64Array(lSteps * hSteps)
  for (let l = 0; l < lSteps; l++) {
    const row = cylmap[l]
    const base = l * hSteps
    for (let h = 0; h < hSteps; h++) {
      const cell = row[h]
      let v = 0
      for (let k = 0; k < cell.length; k++) v += cell[k][0] * cell[k][1] * cell[k][1] * c
      volMap[base + h] = v
    }
  }

  // Step 2: cumulative sum over L* axis, prepend zero row → cssChromAll[(lSteps+1) * hSteps]
  // cssChromAll[(l+1)*hSteps + h] = sqrt(2 * cumsum_0..l(volMap[h]) / dH)
  const cssChromAll = new Float64Array((lSteps + 1) * hSteps)  // row 0 = zeros
  for (let h = 0; h < hSteps; h++) {
    let acc = 0
    for (let l = 0; l < lSteps; l++) {
      acc += volMap[l * hSteps + h]
      cssChromAll[(l + 1) * hSteps + h] = Math.sqrt(2 * acc / dH)
    }
  }

  // Step 3: sample cssChromAll at L_VALUES (which equal row indices since dL=1)
  const cssC = new Float64Array(N_RINGS * hSteps)
  for (let r = 0; r < N_RINGS; r++) {
    const srcBase = L_VALUES[r] * hSteps
    const dstBase = r * hSteps
    for (let h = 0; h < hSteps; h++) cssC[dstBase + h] = cssChromAll[srcBase + h]
  }

  // Step 4: apply reference offset (parallel update — snapshot original first)
  if (refCssC) {
    const orig = cssC.slice()
    for (let r = 1; r < N_RINGS; r++) {
      const base = r * hSteps
      const prevBase = (r - 1) * hSteps
      for (let h = 0; h < hSteps; h++) {
        const n = orig[base + h]
        const p = orig[prevBase + h]
        const rp = refCssC[prevBase + h]
        cssC[base + h] = Math.sqrt(Math.max(0, n * n - p * p + rp * rp))
      }
    }
  }

  // Step 5: cssA[r,h] = sin(ang_h) * cssC[r,h],  cssB[r,h] = cos(ang_h) * cssC
  const cssA = new Float64Array(N_RINGS * hSteps)
  const cssB = new Float64Array(N_RINGS * hSteps)
  for (let h = 0; h < hSteps; h++) {
    const ang = (h + 0.5) * dH
    const sa = Math.sin(ang)
    const cb = Math.cos(ang)
    for (let r = 0; r < N_RINGS; r++) {
      const i = r * hSteps + h
      cssA[i] = sa * cssC[i]
      cssB[i] = cb * cssC[i]
    }
  }

  let totalVol = 0
  for (let i = 0; i < volMap.length; i++) totalVol += volMap[i]

  return { cssA, cssB, cssC, totalVol }
}
