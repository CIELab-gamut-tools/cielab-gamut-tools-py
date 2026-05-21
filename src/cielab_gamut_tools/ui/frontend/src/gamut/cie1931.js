import data from './cie1931.json'

// Spectral locus in CIE 1931 xy chromaticity, computed from the 2-degree CMF.
// Each entry is [x, y]; rows with near-zero sum (deep UV/IR) are excluded.
export const spectralLocus = data
  .map(([, xb, yb, zb]) => {
    const s = xb + yb + zb
    return s > 1e-10 ? [xb / s, yb / s] : null
  })
  .filter(Boolean)

export const locusFirst = spectralLocus[0]
export const locusLast  = spectralLocus[spectralLocus.length - 1]
