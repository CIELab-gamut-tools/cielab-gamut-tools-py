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
