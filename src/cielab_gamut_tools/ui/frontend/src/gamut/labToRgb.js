// CIELab D50 → display RGB conversion, parameterised by colour space.
//
// The colourSpace parameter is the architectural hook for future wide-gamut
// rendering (display-p3, rec2020). Currently 'srgb' and 'display-p3' are
// implemented; switching the canvas renderer to display-p3 additionally
// requires setting renderer.outputColorSpace = THREE.DisplayP3ColorSpace and
// creating the WebGL context with { colorSpace: 'display-p3' }.

// D50 reference white (CIE 1931 2° observer, normalised Y=1)
const D50 = [0.9642, 1.0000, 0.8251]

// Lab → XYZ D50 (CIE standard, IEC 61966-2-1 §A.2)
function labToXyz(L, a, b) {
  const k = 24389 / 27   // 903.296…
  const e = 216 / 24389  // 0.008856…

  const fy = (L + 16) / 116
  const fx = a / 500 + fy
  const fz = fy - b / 200

  const fx3 = fx * fx * fx
  const fz3 = fz * fz * fz

  const X = D50[0] * (fx3 > e ? fx3 : (116 * fx - 16) / k)
  const Y = D50[1] * (L > k * e ? Math.pow((L + 16) / 116, 3) : L / k)
  const Z = D50[2] * (fz3 > e ? fz3 : (116 * fz - 16) / k)

  return [X, Y, Z]
}

// Bradford D50 → D65 chromatic adaptation (CSS Color 4 / ICC values)
const M_D50_TO_D65 = [
  [ 0.9554734527042182,  -0.023038981542500950,  0.0632593657361014  ],
  [-0.028369706963208136, 1.009296438986404,      0.021041398966943008],
  [ 0.012314001688319899,-0.020507696433477912,   1.3303659366080753  ],
]

// XYZ D65 → linear RGB matrices, indexed by colour space name
const M_TO_LINEAR = {
  srgb: [
    [ 3.2404542, -1.5371385, -0.4985314],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0556434, -0.2040259,  1.0572252],
  ],
  'display-p3': [
    [ 2.4934969, -0.9313836, -0.4027108],
    [-0.8294890,  1.7626641,  0.0236247],
    [ 0.0358458, -0.0761724,  0.9568845],
  ],
}

function mat3Mul(m, v) {
  return [
    m[0][0]*v[0] + m[0][1]*v[1] + m[0][2]*v[2],
    m[1][0]*v[0] + m[1][1]*v[1] + m[1][2]*v[2],
    m[2][0]*v[0] + m[2][1]*v[1] + m[2][2]*v[2],
  ]
}

// sRGB / Display P3 share the same piecewise gamma (IEC 61966-2-1)
function gammaEncode(c) {
  if (c <= 0.0031308) return 12.92 * c
  return 1.055 * Math.pow(c, 1 / 2.4) - 0.055
}

/**
 * Convert a single CIELab value to [r, g, b] in [0, 1], clipped at gamut boundary.
 * @param {number} L       - L* (0–100)
 * @param {number} a       - a* (approx –128–128)
 * @param {number} b       - b* (approx –128–128)
 * @param {string} colourSpace - 'srgb' (default) | 'display-p3'
 * @param {number} chroma  - scale factor for a* and b* before conversion (default 1.0)
 * @param {number|null} lightness - override L* before conversion; null = use actual L*
 * @returns {number[]} [r, g, b] each in [0, 1]
 */
export function labToRgb(L, a, b, colourSpace = 'srgb', chroma = 1.0, lightness = null) {
  const Leff = lightness ?? L
  const xyz50 = labToXyz(Leff, a * chroma, b * chroma)
  const xyz65 = mat3Mul(M_D50_TO_D65, xyz50)
  const linear = mat3Mul(M_TO_LINEAR[colourSpace] ?? M_TO_LINEAR.srgb, xyz65)
  return linear.map(c => Math.max(0, Math.min(1, gammaEncode(c))))
}

/**
 * Build a Float32Array of per-vertex RGB colours from a Lab vertex array.
 * @param {Array<number[]>} vertices  - [[L, a, b], …]
 * @param {string} colourSpace        - passed to labToRgb
 * @param {number} chroma             - a* and b* scale factor (default 1.0)
 * @param {number|null} lightness     - L* override, null = per-vertex L* (default)
 * @returns {Float32Array} interleaved [r,g,b, r,g,b, …]
 */
export function labVerticesToColors(vertices, colourSpace = 'srgb', chroma = 1.0, lightness = null) {
  const n = vertices.length
  const colors = new Float32Array(n * 3)
  for (let i = 0; i < n; i++) {
    const [r, g, b] = labToRgb(
      vertices[i][0], vertices[i][1], vertices[i][2],
      colourSpace, chroma, lightness,
    )
    colors[i * 3]     = r
    colors[i * 3 + 1] = g
    colors[i * 3 + 2] = b
  }
  return colors
}
