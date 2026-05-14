# UI Implementation Plan

## Architecture Summary

- **Python server** (FastAPI + uvicorn): file I/O, cylindrical map computation, downloadable export via matplotlib. Started by `cgt ui`, blocks the terminal (Ctrl-C to stop), opens browser automatically. Serves Vite `dist/` as static files.
- **JS client** (Vite + Vue 3 + PrimeVue Aura + Pinia): rendering, interactive compute. WebGL rings renderer (ported from `gamut-rings-app`), TresJS surface renderer.
- **Synthetic gamuts during interactive dragging**: computed client-side in JS (zero latency). When saved to session or exported, reconstructed server-side in Python.
- **Downloadable output**: always via Python matplotlib — identical to CLI output.

### Cylmap transfer format

Binary, self-describing:
```
uint32     l_steps
uint32     h_steps
uint8[]    counts[l_steps × h_steps], row-major   (~36 KB)
uint8[]    padding to 4-byte boundary
float32[]  chroma[sum(counts)], outside-in per cell  (~288 KB typical)
```
Direction is implicit: index 0 within each cell is outward-facing, alternating thereafter.
JS builds a prefix-sum offset table on receipt for O(1) cell access.

### Stack

- Backend: FastAPI + uvicorn
- Frontend: Vite + Vue 3 + PrimeVue (Aura theme) + Pinia + TresJS
- Rings rendering: hand-coded WebGL (ported from `gamut-rings-app`)
- Surface rendering: TresJS (Three.js for Vue 3)
- No Tailwind

### Frontend location

`src/cielab_gamut_tools/ui/frontend/` — Vite project  
`src/cielab_gamut_tools/ui/dist/` — build output, served as static files

### Dev workflow

Run both servers in parallel:
- `uvicorn cielab_gamut_tools.ui.server:app --reload` on port 8000
- `npm run dev` (in `ui/frontend/`) on port 5173, proxies `/api` to port 8000

---

## Stage 0 — Fix cylindrical map representation (correctness prerequisite)

Must land before any UI work. Correctness fix to core computation.

**The bug:** `MAX_K=4` in `_process_hue_loop_nb` truncates intersections before the parity
filter runs. Duplicate/bad entries from tile boundaries eat into the budget, silently
dropping real intersections for non-convex gamuts (print, reflective). MATLAB uses cell
arrays with no such limit.

**Fix in `geometry/volume.py`:**
- Increase working buffer inside `_process_hue_loop_nb` to `MAX_K=64` (Numba
  pre-allocated, never exposed outside the JIT)
- Within the JIT: collect all hits into the working buffer, sort **descending by t**
  (outside-in, largest chroma first), apply parity filter, write post-filter values to output
- Replace the dense `(l_steps, h_steps, MAX_K, 2)` cylmap with two arrays:
  - `counts`: `uint8 (l_steps, h_steps)` — post-filter intersection count per cell
  - `chroma`: `float32 [sum(counts)]` — flat, outside-in ordered, one contiguous block
    per cell in row-major order
- Direction is implicit and must never be stored — convention: index 0 = outward-facing,
  alternating inward/outward thereafter. Outside-in ordering is enforced here to avoid
  the sign-tracking headaches of inside-out ordering.
- Precompute prefix-sum offset table alongside counts for O(1) cell access
- Add assertion: `counts.max() <= MAX_K_WORKING` with a clear error message if triggered
- Update `volume()` and `intersect()` to consume the new format
- Update Numba warm-up calls at module load

**Verification (must all pass):**
- `SyntheticGamut.srgb().volume()` remains ~830,807
- BT.2020 volume > sRGB
- Intersection commutativity: A∩B == B∩A
- Self-intersection: A∩A == A
- Full test suite passes

Update `CLAUDE.md` with new cylmap format, outside-in convention, and rationale.

---

## Stage 1 — Python server foundation

- Add `fastapi` and `uvicorn` to dependencies in `pyproject.toml`
- `cgt ui` CLI command: starts uvicorn on `localhost:8000` (blocking), opens browser
- FastAPI app at `src/cielab_gamut_tools/ui/server.py`
- In-memory gamut registry, pre-populated on startup with 5 standard references:
  `srgb`, `bt.2020`, `dci-p3`, `display-p3`, `adobe-rgb`
- Endpoints:
  - `GET  /api/gamuts` → `[{id, name, source, volume, colour}]`
  - `POST /api/gamuts/upload` — multipart CGATS file upload
  - `POST /api/gamuts/synthetic` — `{primaries_xy, white_xy, gamma}`
  - `DELETE /api/gamuts/:id`
  - `GET  /api/gamuts/:id/cylmap` → binary (format above)
  - `GET  /api/gamuts/:id/surface` → JSON `{vertices: [[L,a,b]×726], faces: [[i,j,k]×~1400]}`
  - `GET  /api/gamuts/:id/volume` → JSON `{volume: float}`
  - `POST /api/gamuts/coverage` — `{dut_id, reference_id}` → `{coverage, intersection_volume}`
  - `POST /api/gamuts/matrix` — `{ids: [...]}` → `{matrix: [[float]]}`
- Static file serving of `ui/dist/`, SPA fallback to `index.html`
- Fully testable with curl before any frontend exists

---

## Stage 2 — Frontend scaffold

- Vite + Vue 3 + PrimeVue (Aura theme) + Pinia + TresJS project under `ui/frontend/`
- `vite.config.js`: proxy `/api` → `localhost:8000`
- Pinia stores:
  - `gamutStore`: `{id, name, label, source, volume, colour, cylmap: ArrayBuffer, offsets: Uint32Array, surfaceMesh}`
  - `selectionStore`: `{dutId, referenceIds[]}`
  - `uiStore`: `{activeView, exportOptions}` — persisted to localStorage
- API client (`api.js`): typed `fetch` wrappers; binary cylmap response unpacked to counts +
  chroma typed arrays + prefix-sum offset table
- Shell layout: `AppHeader`, `GamutSidebar` (empty list), `MainPanel` with
  `[Rings | Surface | Analysis]` tab switcher
- No real functionality yet — skeleton renders without errors, tabs switch

---

## Stage 3 — Gamut management

- `GamutItem`: colour swatch, editable label, volume badge, DUT/ref toggle (radio for DUT,
  checkbox for ref), remove button
- Sidebar populated from `gamutStore` on mount — standard references present immediately
- `AddGamutModal` with two tabs:
  - **File tab**: drag-and-drop zone + native file picker, `POST /api/gamuts/upload`
  - **Synthetic tab**: port `ChromaticityEditor` and primaries/white/gamma inputs from
    `gamut-rings-app`, `POST /api/gamuts/synthetic`
- Colour assignment: small fixed palette, assigned round-robin on add
- Selection logic enforced in `selectionStore`: exactly one DUT, any number of references

---

## Stage 4 — Rings view

- Port `GamutRingsCanvas` WebGL component from `gamut-rings-app`, rewired to read cylmap
  from `gamutStore`
- Client-side rings computation from cylmap typed arrays (outside-in convention throughout)
- Client-side intersection via `intersect.js` logic (two cylmaps → intersection cylmap → render)
- `RingsView`: reacts to `selectionStore` changes, fetches cylmaps on first use (cached in
  store), triggers re-render
- `RingsOptions` panel: L\* label set, plot title, legend toggle

---

## Stage 5 — Surface view

- `GamutSurfaceCanvas`: TresJS component, `BufferGeometry` built from surface mesh JSON
- Fetch `GET /api/gamuts/:id/surface` on first use, cached in store
- Orbit controls, per-gamut colour + alpha
- Multiple gamuts overlaid (DUT + all selected references)
- `SurfaceOptions` panel: alpha slider, per-gamut visibility toggle

---

## Stage 6 — Analysis view

- `VolumeTable`: all loaded gamuts, volume column, sortable
- `CoverageMatrix`: DUT rows × reference columns, calls `POST /api/gamuts/matrix`
- Client-side CSV export of table
- Copy-to-clipboard for individual cells

---

## Stage 7 — Downloadable export

- Server endpoints: `POST /api/export/rings`, `POST /api/export/surface`
  — call existing matplotlib render path with options matching CLI flags, return PNG or PDF bytes
- `ExportPanel`: format picker (PNG/PDF), DPI, title/legend options mirroring CLI
- Triggered from `AppHeader` export button; active view determines which endpoint is called
- Downloaded via blob URL — output is identical to `cgt plot rings` / `cgt plot surface`

---

## Stage 8 — Build integration and packaging

- `npm run build` → `ui/dist/`; `Makefile` target or `hatchling` build hook
- Include `ui/dist/` in Python package via `tool.hatch.build.include` in `pyproject.toml`
- `cgt ui` detects missing `dist/` and prints a clear message directing the user to build
- Update `README.md` and `CLAUDE.md` with dev workflow
