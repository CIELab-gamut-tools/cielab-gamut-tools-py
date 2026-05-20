/**
 * Convert the packed binary cylmap from the API into the
 * { lSteps, hSteps, cylmap[l][h] } format expected by rings.js and intersect.js.
 *
 * Each cell is an array of [sign, dist] pairs sorted ASCENDING by dist
 * (innermost/smallest first, outermost/largest last).
 *
 * Wire format (outside-in, outermost first, even-index=+1):
 *   cell[0] = [+1, d_outer], cell[1] = [-1, d_next], ...
 *
 * After reversing (inside-out):
 *   cell[0] = [sign_inner, d_inner], ..., cell[n-1] = [+1, d_outer]
 *
 * This matches what fix() in intersect.js enforces: working from the last
 * element backward it expects sign=+1 at the outermost crossing.
 */
export function unpackCylmap({ lSteps, hSteps, counts, chroma, offsets }) {
  const cylmap = new Array(lSteps)
  for (let l = 0; l < lSteps; l++) {
    const row = new Array(hSteps)
    for (let h = 0; h < hSteps; h++) {
      const idx = l * hSteps + h
      const n = counts[idx]
      const off = offsets[idx]
      const cell = new Array(n)
      // Reverse order so innermost is at index 0, outermost at index n-1.
      // Original sign: even original index → +1, odd → -1.
      for (let k = 0; k < n; k++) {
        const origIdx = n - 1 - k
        cell[k] = [(origIdx % 2 === 0) ? 1 : -1, chroma[off + origIdx]]
      }
      row[h] = cell
    }
    cylmap[l] = row
  }
  return { lSteps, hSteps, cylmap }
}
