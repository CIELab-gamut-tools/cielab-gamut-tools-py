# UI Architecture

Architecture notes for the planned web UI application for `cielab-gamut-tools`.

## Goal

Provide non-expert users (metrologists) with a simple single-command launcher that opens
a browser-based tool for exploring and publishing gamut data from CGATS measurement files.

```bash
cielab-tools ui        # subcommand of the main CLI entry point; launches app in browser
```

## Deployment Model

A local web server launched by the CLI entry point. The Python process has full filesystem
access — no browser sandboxing constraints. The user's browser connects to `localhost` and
is purely a rendering surface.

```
cielab-tools ui (subcommand of main CLI)
  → starts FastAPI server on localhost:8000
  → opens browser automatically
  → Vue.js frontend talks to /api/* endpoints
  → server reads/writes CGATS files and renders publication output with full OS permissions
```

## Stack

| Layer | Technology | Rationale |
|---|---|---|
| CLI entry point | Python `console_scripts` | Standard pip-installed executable, no `python -m` needed |
| Backend | FastAPI + uvicorn | Lightweight, async, easy to serve both API and static files |
| Interactive visualisation | Plotly.js (via Vue component) | WebGL 3D, smooth rotation, single figure spec shared with export path |
| Publication export | Matplotlib (existing) | True vector output (EPS, SVG, PDF), TIFF, no heavy renderer deps |
| Frontend framework | Vue 3 | User preference, component model suits the control-heavy UI |
| Component library | Element Plus | Bootstrap-inspired aesthetics, clean, good form controls, tree-shakeable |

No Tailwind. No Vuetify.

## Separation of Concerns

### Python computes, JavaScript renders

The expensive algorithmic work (tesselation, cylindrical map, intersection) stays in Python.
The output is geometry data (vertices, faces, ring contours) serialised to JSON and sent to
the frontend. Plotly.js renders it interactively in WebGL.

This means there is **no duplicate rendering logic** — the same computed geometry feeds
both the interactive view and the publication export path.

```
Gamut.from_cgats() / SyntheticGamut.*()
  → compute_geometry()           # existing Python algorithms
  → geometry JSON                # vertices, faces, ring contours, etc.
      │
      ├─→ Plotly figure spec → plotly.js → interactive WebGL in browser
      │
      └─→ matplotlib_render()   → EPS / SVG / PDF / TIFF / PNG (served as file download)
```

### Why not Plotly for all export?

Plotly can export via kaleido (headless Chromium). Rejected because:
- kaleido is ~150 MB and pulls Chromium into a scientific CLI tool
- 3D "vector" output from kaleido is rasterized (a bitmap in a vector container)
- Matplotlib produces genuine vector paths for all output including 3D projections
- Matplotlib is already a dependency; keeping export there adds nothing new

### Why not matplotlib for interactive display?

Matplotlib's browser 3D requires either sending images on every camera move (laggy) or
running a native GUI event loop (not suitable for a web app). Plotly.js handles this
natively with WebGL.

## API Endpoints

```
GET  /                        → serve Vue app (index.html)
GET  /static/*                → Vue build assets

POST /api/scan-folder         → { path } → [{ filename, size, modified }, ...]
POST /api/load-cgats          → { path } → { metadata, white_point, primary_count, ... }
POST /api/compute-figure      → { paths, settings } → Plotly figure JSON
POST /api/export              → { paths, settings, format, dpi } → file download
GET  /api/reference-gamuts    → [{ id, name }, ...]   (sRGB, BT.2020, DCI-P3, Display P3, Adobe RGB)
```

## Frontend Structure

```
ui/
├── server.py                 # FastAPI app, mounts static/, registers routes
├── routes/
│   ├── files.py              # scan-folder, load-cgats
│   ├── figure.py             # compute-figure
│   └── export.py             # export endpoint, calls matplotlib
├── geometry.py               # converts Gamut objects → Plotly figure spec
└── static/                   # Vue build output (dist/ copied here at build time)
    └── index.html
```

```
frontend/                     # Vue project (separate build step)
├── src/
│   ├── App.vue
│   ├── components/
│   │   ├── FileBrowser.vue   # folder path input + file list
│   │   ├── PlotView.vue      # Plotly.js wrapper
│   │   ├── ControlPanel.vue  # reference gamut, ring options, primary vectors
│   │   └── ExportPanel.vue   # format, DPI, download button
│   └── api.js                # thin wrapper around fetch calls to /api/*
└── vite.config.js
```

## CLI Entry Point

```python
# src/cielab_gamut_tools/ui/server.py
def main():
    import webbrowser, threading
    import uvicorn
    threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8000")).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

```toml
# pyproject.toml — the UI is a subcommand of the main CLI, not a separate entry point
# See CLI_DESIGN.md for the entry point definition
[project.scripts]
cielab-gamut-tools = "cielab_gamut_tools.cli:main"
cielab-tools       = "cielab_gamut_tools.cli:main"
```

Users can also run `python -m cielab_gamut_tools` if preferred (add `__main__.py`).

## File Access Pattern

Target users have a folder of CGATS files. The UI workflow is:

1. User enters (or pastes) a folder path
2. `/api/scan-folder` returns the file list — server reads the filesystem directly
3. User selects one or more files
4. Settings panel: reference gamut, intersection mode, ring options, primary vectors
5. Plot updates via `/api/compute-figure`
6. Export: user picks format + DPI, clicks download, server renders via matplotlib and
   returns the file

No browser file upload needed. No sandboxing issues.

## Build / Distribution

The Vue build (`dist/`) is committed to the repo (or generated as part of the release
process) and included in the Python wheel under `ui/static/`. Hatchling includes it via:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/cielab_gamut_tools"]
artifacts = ["src/cielab_gamut_tools/ui/static"]
```

End users do not need Node.js — they just `pip install cielab-gamut-tools`.

## Additional Dependencies (UI only)

These are added as an optional extra to avoid burdening pure-library users:

```toml
[project.optional-dependencies]
ui = [
    "fastapi>=0.100",
    "uvicorn>=0.23",
]
```

Install with: `pip install cielab-gamut-tools[ui]`

Plotly.js is loaded by the Vue frontend from the npm bundle — it is not a Python
dependency. Matplotlib is already a core dependency so no addition needed for export.
