# UI Implementation Plan

## Architecture Summary

- **Python server** (FastAPI + uvicorn): file I/O, cylindrical map computation, downloadable export via matplotlib. Started by `cgt ui`, blocks the terminal (Ctrl-C to stop), opens browser automatically. Serves Vite `dist/` as static files.
- **JS client** (Vite + Vue 3 + PrimeVue Aura + Pinia): rendering, interactive compute. WebGL rings renderer used only in the synthetic gamut builder (live preview while dragging primaries). TresJS surface renderer for the main surface view.
- **Rings view**: server-rendered PNG via matplotlib, displayed in an `<img>` tag with CSS zoom. Round-trip ~200–400 ms; acceptable for a semi-static standards-compliant plot. Scale options are constrained by standard: emissive ±1250 C*, reflective 150/300/600.
- **Synthetic gamuts during interactive dragging**: computed and rendered client-side in JS (zero latency). When saved to session, reconstructed server-side in Python for official rendering.
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
Sign is implicit from position within cell: even index = outward (+1), odd = inward (−1).
This matches the storage format on the Python `Gamut` object (`_cylmap_counts`, `_cylmap_chroma`).
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

## Stage 0 — Fix cylindrical map representation ✓ COMPLETE

Two correctness fixes landed together; full test suite passes.

### Fix 1 — Reflective display white point

`Gamut.from_xyz()` now checks CGATS metadata for
`ILLUMINATION_PERFECT_DIFFUSE_REFLECTOR_XYZ` and uses it as the white point
when present, overriding the RGB=(255,255,255) row.  Without this fix,
reflective displays (e-paper, print) had their L* values inflated by ~2× and
volume by ~4× (e.g. E Ink Sample 4: Python 6,934 → correct 1,776, matching
MATLAB).  Covered by `TestReflectiveGamut`.

### Fix 2 — Variable-length cylindrical map

**Storage format** (cached on `Gamut` as `_cylmap_counts`, `_cylmap_chroma`,
`_cylmap_offsets`):
```
counts:  uint8   (l_steps, h_steps)      # parity-filtered count per cell
chroma:  float32 [sum(counts)]           # distances, outside-in per cell, row-major
offsets: int32   [l_steps × h_steps]     # prefix-sum for O(1) cell access
```
Sign implicit: even position within cell = outward (+1), odd = inward (−1).
This is the same binary layout as the UI transfer format above.

**Computation format** (unpacked on demand by `get_cylindrical_map()`):
```
cylmap:  float64  (l_steps, h_steps, max_k, 2)   # [sign, distance], max_k = counts.max()
counts:  int64    (l_steps, h_steps)
```
`max_k` is data-driven; all existing vectorised NumPy operations are unchanged.
Unpack is O(sum(counts)), < 1 ms.

**No fixed intersection limit.**  `_process_hue_loop_nb` working buffer is
`h_steps × n_tri` (absolute pre-filter maximum).  `_intersect_all_cells_nb`
output depth is `max_k_a + max_k_b` (tight post-filter upper bound).

**Parity invariant check** (`_check_cylmap_parity`): all 360 counts in each
L* slice must share the same parity — they originate from the same point,
which is either inside or outside the gamut.  `RuntimeError` on violation.

---

## Stage 1 — Python server foundation ✓ COMPLETE

FastAPI server at `src/cielab_gamut_tools/ui/server.py`, `cgt ui` CLI command,
and full test coverage in `tests/test_ui_server.py`. All tests pass.

### Implementation notes

- `fastapi>=0.100`, `uvicorn[standard]>=0.22`, `python-multipart>=0.0.7` added
  to core dependencies in `pyproject.toml`.
- In-memory `_registry: dict[str, GamutEntry]`; 5 standard `SyntheticGamut`
  references pre-built in `lifespan()` (geometries only — no cylmaps on startup).
- Standard gamuts are `protected=True`; `DELETE` returns 403.
- `volume` field in list response is `null` until first `/volume` request;
  cached on the `Gamut` object thereafter and appears in subsequent list calls.
- Binary cylmap wire format exactly matches the planned spec (uint32 header +
  uint8 counts + 4-byte-aligned padding + float32 chroma). For the standard
  100×360 grid the padding is always 0 bytes (36008 is divisible by 4).
- `GET /api/gamuts/:id/cylmap` imports `get_cylindrical_map` at module level,
  so Numba JIT warm-up runs at server start (not first request).
- SPA fallback: if `ui/dist/` exists, `/assets/*` served as static files and
  all other non-API GETs return `index.html`. If `dist/` is absent, `GET /`
  returns a 404 JSON with build instructions.
- Endpoints:
  - `GET  /api/gamuts` → `[{id, name, source, volume, colour, protected}]`
  - `POST /api/gamuts/upload` — multipart CGATS file upload
  - `POST /api/gamuts/synthetic` — `{primaries_xy, white_xy, gamma, name?}`
  - `DELETE /api/gamuts/:id`
  - `GET  /api/gamuts/:id/cylmap` → binary (format above)
  - `GET  /api/gamuts/:id/surface` → JSON `{vertices: [[L,a,b]×726], faces: [[i,j,k]×~1400]}`
  - `GET  /api/gamuts/:id/volume` → JSON `{volume: float}`
  - `POST /api/gamuts/coverage` — `{dut_id, reference_id}` → `{coverage, intersection_volume}`
  - `POST /api/gamuts/matrix` — `{ids: [...]}` → `{matrix: [[float]]}` (symmetric, diagonal=100)
  - `POST /api/render/rings` — options body → PNG bytes (same path used for both display and export)

---

## Stage 2 — Frontend scaffold ✓ COMPLETE

- Vite + Vue 3 + PrimeVue (Aura theme) + Pinia + TresJS (`@tresjs/core`, `three`) in
  `package.json`; `pinia-plugin-persistedstate` for localStorage persistence
- `vite.config.js`: proxy `/api` → `localhost:8000`; `build.outDir` → `../dist`
- `npm run dev` launches both the Python API server and Vite together via `concurrently`
- Pinia stores (all in `src/stores/`):
  - `gamutStore`: `{id, name, label, source, volume, colour, protected, cylmap, surface}`;
    `cylmap` stored as decoded `{lSteps, hSteps, counts, chroma, offsets}` typed arrays (not
    raw `ArrayBuffer`); lazy `ensureCylmap()`, `ensureSurface()`, `ensureVolume()` actions
  - `selectionStore`: `{dutId, referenceIds[]}`; `setDut`, `toggleReference`, `removeGamut`
  - `uiStore`: `{activeView, exportOptions}` — persisted to localStorage
- `api.js`: typed `fetch` wrappers for all Stage 1 endpoints; `getCylmap()` decodes the binary
  wire format and builds the prefix-sum offset table client-side
- Shell layout: `AppHeader`, `GamutSidebar`, `MainPanel` with `[Rings | Surface | Analysis]`
  tab switcher; active tab persisted via `uiStore`

---

## Stage 3 — Gamut management (partially done)

### Done
- `GamutItem`: colour swatch, editable label, volume badge, DUT/ref toggle, remove button ✓
- `GamutSidebar`: populated from `gamutStore` on mount; standard references present
  immediately; loading/error states ✓
- `AddGamutModal` **file tab**: drag-and-drop zone + native file picker,
  `POST /api/gamuts/upload`, error display ✓
- Colour assignment: fixed palette on the server, assigned round-robin ✓
- Selection logic in `selectionStore` ✓

### Still needed
- `AddGamutModal` **synthetic tab**: primaries/white/gamma inputs (port `ChromaticityEditor`
  from `gamut-rings-app`), `POST /api/gamuts/synthetic`; WebGL rings preview inside this tab
  for zero-latency live feedback while editing

---

## Stage 4 — Rings view ✓ COMPLETE

- `POST /api/render/rings` server endpoint and `renderRings()` JS wrapper in `api.js` ✓
- `RingsView` rewritten: fetches server PNG, displays in `<img>` tag; CSS width-based zoom
  (100% × zoom factor, container scrolls on overflow); debounced re-render (400ms) on any
  selection or options change; race-condition safe via render token ✓
- Zoom toolbar: − / % / + / reset buttons; zoom state persisted in `uiStore` ✓
- `RingsPropertiesPanel`: collapsible panel at bottom of sidebar (always visible, independent
  of list scroll); scale select (Auto / Emissive ±1250 / Reflective 150/300/600), intersection
  toggle (disabled when no reference), auto-title toggle + custom title input, Render button ✓
- `uiStore` extended: `ringsOptions {scale, autoTitle, customTitle, intersection}`, `ringsZoom`,
  `ringsRenderCounter` / `forceRender()` action; all persisted to localStorage ✓
- `GamutSidebar` restructured: list area is `flex:1 overflow-y:auto`, panel is `flex-shrink:0`
  so it always sticks below the list without requiring scroll ✓
- `RingsCanvas` (WebGL) kept intact for future use in the synthetic gamut builder tab ✓

---

## Stage 5 — Surface view ✓ COMPLETE

- `GamutSurfaceCanvas`: Three.js component, `BufferGeometry` built from surface mesh JSON ✓
- Fetch `GET /api/gamuts/:id/surface` on first use, cached in store ✓
- Orbit controls, per-gamut alpha + visibility toggle ✓
- Multiple gamuts overlaid (DUT + all selected references) ✓
- `SurfacePropertiesPanel`: collapsible panel at bottom of sidebar ✓

### Implementation notes

- **Lab-derived vertex colours** (`src/gamut/labToRgb.js`): CIELab D50 → XYZ D50 → XYZ D65
  (Bradford CAT) → linear RGB → gamma, parameterised by `colourSpace` ('srgb' | 'display-p3').
  The colour space is an architectural parameter threaded from `uiStore` → `SurfaceView` →
  `GamutSurfaceCanvas` → `labVerticesToColors()`; switching to display-P3 requires only setting
  `colourSpace: 'display-p3'` in the store and enabling `renderer.outputColorSpace` — no rewrite.
- **Wireframe mode** per gamut: `THREE.LineSegments` with a custom edges geometry (unique
  undirected edges only, vertex colours copied from solid geometry). Toggle in panel row.
- **Winding order**: face indices are reversed in `buildGeometry` (swap i[1] and i[2]) to produce
  outward-facing normals in Three.js's (X=b*, Y=L*, Z=a*) coordinate space. The Python
  tessellation winding targets matplotlib's (a*, b*, L*) axis order; the coordinate remapping
  changes handedness, requiring the flip.
- **Projection blend**: orthographic ↔ perspective slider (0–1), preserving view height across
  the transition.
- **Camera angle sync**: `cameraElev` (−90…90°) and `cameraAzim` (−180…180°) stored in
  `uiStore`, displayed and editable in the panel. OrbitControls emits `camera-change` → store;
  panel inputs watch the store → reposition camera. A last-emitted-value guard (< 1° tolerance)
  breaks the orbit → prop-watch feedback loop.
- **Render order**: transparent meshes sorted back-to-front by `nearDist = dist − boundingRadius`
  so nested gamuts (e.g. sRGB inside BT.2020) composite correctly.
- `uiStore.surfaceOptions`: `{ perGamut: {id → {visible, alpha, wireframe}}, perspectiveBlend,
  cameraElev, cameraAzim, colourSpace }` — all persisted to localStorage.

---

## Stage 6 — Analysis view

- `VolumeTable`: all loaded gamuts, volume column, sortable
- `CoverageMatrix`: DUT rows × reference columns, calls `POST /api/gamuts/matrix`
- Client-side CSV export of table
- Copy-to-clipboard for individual cells

---

## Stage 7 — Downloadable export

- Rings export reuses `POST /api/render/rings` — adding `"format": "pdf"` and a higher `"dpi"`
  triggers `Content-Disposition: attachment`; no separate endpoint needed. Output is identical
  to `cgt plot rings`.
- Surface export: `POST /api/export/surface` — calls matplotlib 3D render path, returns PNG or
  PDF bytes. Output is identical to `cgt plot surface`.
- `ExportPanel`: format picker (PNG/PDF), DPI spinner; for rings, options are already set in
  `RingsPropertiesPanel` — export button in `AppHeader` just re-posts with download flag.
- Downloaded via blob URL.

---

## Stage 8 — Build integration and packaging

- `npm run build` → `ui/dist/`; `Makefile` target or `hatchling` build hook
- Include `ui/dist/` in Python package via `tool.hatch.build.include` in `pyproject.toml`
- `cgt ui` detects missing `dist/` and prints a clear message directing the user to build
- Update `README.md` and `CLAUDE.md` with dev workflow
