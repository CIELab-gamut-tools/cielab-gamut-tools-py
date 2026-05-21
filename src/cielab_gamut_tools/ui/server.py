"""
FastAPI server for the CIELab gamut tools web UI.

In-memory gamut registry pre-populated with 5 standard synthetic references.
All cylmap / volume computations are lazy (built on first request, then cached
on the Gamut object).
"""

from __future__ import annotations

import io
import os
import struct
import tempfile
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

# Must be set before any pyplot import; server always renders off-screen.
matplotlib.use("Agg")

from cielab_gamut_tools.gamut import Gamut

# Importing this module triggers Numba JIT warm-up at server start.
from cielab_gamut_tools.geometry.volume import get_cylindrical_map
from cielab_gamut_tools.synthetic import SyntheticGamut

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PALETTE = [
    "#2196F3",  # blue
    "#F44336",  # red
    "#4CAF50",  # green
    "#FF9800",  # orange
    "#9C27B0",  # purple
    "#00BCD4",  # cyan
    "#FFEB3B",  # yellow
    "#795548",  # brown
]

_STANDARDS: list[tuple[str, object]] = [
    ("sRGB", SyntheticGamut.srgb),
    ("BT.2020", SyntheticGamut.bt2020),
    ("DCI-P3", SyntheticGamut.dci_p3),
    ("Display P3", SyntheticGamut.display_p3),
    ("Adobe RGB (1998)", SyntheticGamut.adobe_rgb),
]


@dataclass
class GamutEntry:
    id: str
    name: str
    source: str
    colour: str
    gamut: Gamut
    protected: bool = False


_registry: dict[str, GamutEntry] = {}
_palette_counter: int = 0


def _next_colour() -> str:
    global _palette_counter
    colour = _PALETTE[_palette_counter % len(_PALETTE)]
    _palette_counter += 1
    return colour


def _add_entry(
    name: str, source: str, gamut: Gamut, *, protected: bool = False
) -> GamutEntry:
    entry = GamutEntry(
        id=str(uuid.uuid4()),
        name=name,
        source=source,
        colour=_next_colour(),
        gamut=gamut,
        protected=protected,
    )
    _registry[entry.id] = entry
    return entry


def _entry_dict(entry: GamutEntry) -> dict:  # type: ignore[type-arg]
    return {
        "id": entry.id,
        "name": entry.name,
        "source": entry.source,
        "volume": entry.gamut._volume,
        "colour": entry.colour,
        "protected": entry.protected,
    }


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager  # type: ignore[arg-type]
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    _registry.clear()
    global _palette_counter
    _palette_counter = 0
    for name, factory in _STANDARDS:
        sg = factory()  # type: ignore[call-arg]
        _add_entry(name, "synthetic", sg.gamut, protected=True)
    yield


app = FastAPI(title="CIELab Gamut Tools", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Gamut list
# ---------------------------------------------------------------------------


@app.get("/api/gamuts")
def list_gamuts() -> list[dict]:  # type: ignore[type-arg]
    return [_entry_dict(e) for e in _registry.values()]


# ---------------------------------------------------------------------------
# Upload CGATS file
# ---------------------------------------------------------------------------


@app.post("/api/gamuts/upload", status_code=201)
def upload_gamut(file: UploadFile) -> dict:  # type: ignore[type-arg]
    filename = file.filename or "upload.txt"
    suffix = Path(filename).suffix or ".txt"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        gamut = Gamut.from_cgats(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    name = Path(filename).stem
    entry = _add_entry(name, "file", gamut)
    return _entry_dict(entry)


# ---------------------------------------------------------------------------
# Create synthetic gamut
# ---------------------------------------------------------------------------


class SyntheticRequest(BaseModel):
    primaries_xy: list[list[float]]  # [[rx,ry],[gx,gy],[bx,by]]
    white_xy: list[float]  # [x, y]
    gamma: float = 2.2
    name: str | None = None
    clowlo: float = 1.0
    boost_fn: str = "min"


@app.post("/api/gamuts/synthetic", status_code=201)
def create_synthetic(req: SyntheticRequest) -> dict:  # type: ignore[type-arg]
    try:
        sg = SyntheticGamut(
            np.array(req.primaries_xy),
            np.array(req.white_xy),
            gamma=req.gamma,
            clowlo=req.clowlo,
            boost_fn=req.boost_fn,
        )
        gamut = sg.gamut
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    entry = _add_entry(req.name or "Custom gamut", "synthetic", gamut)
    return _entry_dict(entry)


# ---------------------------------------------------------------------------
# Rename gamut
# ---------------------------------------------------------------------------


class RenameRequest(BaseModel):
    name: str


@app.patch("/api/gamuts/{gamut_id}", status_code=200)
def rename_gamut(gamut_id: str, req: RenameRequest) -> dict:  # type: ignore[type-arg]
    entry = _registry.get(gamut_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Gamut not found")
    entry.name = req.name.strip() or entry.name
    return _entry_dict(entry)


# ---------------------------------------------------------------------------
# Delete gamut
# ---------------------------------------------------------------------------


@app.delete("/api/gamuts/{gamut_id}", status_code=204)
def delete_gamut(gamut_id: str) -> None:
    entry = _registry.get(gamut_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Gamut not found")
    if entry.protected:
        raise HTTPException(
            status_code=403, detail="Cannot delete standard reference gamuts"
        )
    del _registry[gamut_id]


# ---------------------------------------------------------------------------
# Cylmap — binary transfer format
#
#   uint32     l_steps
#   uint32     h_steps
#   uint8[]    counts[l_steps × h_steps], row-major
#   uint8[]    padding to 4-byte boundary
#   float32[]  chroma[sum(counts)], outside-in per cell
# ---------------------------------------------------------------------------


@app.get("/api/gamuts/{gamut_id}/cylmap")
def get_cylmap(gamut_id: str) -> Response:
    entry = _registry.get(gamut_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Gamut not found")

    get_cylindrical_map(entry.gamut)  # builds and caches if needed

    counts = entry.gamut._cylmap_counts  # uint8 (l_steps, h_steps)
    chroma = entry.gamut._cylmap_chroma  # float32 flat
    assert counts is not None and chroma is not None

    l_steps, h_steps = counts.shape
    header = struct.pack("<II", l_steps, h_steps)
    counts_bytes = counts.flatten("C").tobytes()
    n = len(header) + len(counts_bytes)
    padding = (4 - n % 4) % 4

    body = header + counts_bytes + b"\x00" * padding + chroma.tobytes()
    return Response(content=body, media_type="application/octet-stream")


# ---------------------------------------------------------------------------
# Surface mesh
# ---------------------------------------------------------------------------


@app.get("/api/gamuts/{gamut_id}/surface")
def get_surface(gamut_id: str) -> dict:  # type: ignore[type-arg]
    entry = _registry.get(gamut_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Gamut not found")
    return {
        "vertices": entry.gamut.lab.tolist(),     # 726 × [L, a*, b*]
        "faces": entry.gamut.triangles.tolist(),  # ~1400 × [i, j, k]
    }


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


@app.get("/api/gamuts/{gamut_id}/volume")
def get_volume(gamut_id: str) -> dict:  # type: ignore[type-arg]
    entry = _registry.get(gamut_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Gamut not found")
    return {"volume": entry.gamut.volume()}


# ---------------------------------------------------------------------------
# Coverage  (DUT ∩ reference) / reference
# ---------------------------------------------------------------------------


class CoverageRequest(BaseModel):
    dut_id: str
    reference_id: str


@app.post("/api/gamuts/coverage")
def compute_coverage(req: CoverageRequest) -> dict:  # type: ignore[type-arg]
    dut = _registry.get(req.dut_id)
    ref = _registry.get(req.reference_id)
    if dut is None:
        raise HTTPException(status_code=404, detail=f"DUT gamut {req.dut_id!r} not found")
    if ref is None:
        raise HTTPException(
            status_code=404, detail=f"Reference gamut {req.reference_id!r} not found"
        )

    intersection = dut.gamut.intersect(ref.gamut)
    ref_volume = ref.gamut.volume()
    int_volume = intersection.volume()
    coverage = int_volume / ref_volume * 100 if ref_volume > 0 else 0.0

    return {"coverage": coverage, "intersection_volume": int_volume}


# ---------------------------------------------------------------------------
# Pairwise coverage matrix
# ---------------------------------------------------------------------------


class MatrixRequest(BaseModel):
    ids: list[str]


@app.post("/api/gamuts/matrix")
def compute_matrix(req: MatrixRequest) -> dict:  # type: ignore[type-arg]
    entries: list[GamutEntry] = []
    for gid in req.ids:
        e = _registry.get(gid)
        if e is None:
            raise HTTPException(status_code=404, detail=f"Gamut {gid!r} not found")
        entries.append(e)

    n = len(entries)
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]

    # Cache intersection volumes: key = (min_idx, max_idx)
    int_cache: dict[tuple[int, int], float] = {}

    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 100.0
                continue
            key = (min(i, j), max(i, j))
            if key not in int_cache:
                inter = entries[key[0]].gamut.intersect(entries[key[1]].gamut)
                int_cache[key] = inter.volume()
            ref_vol = entries[j].gamut.volume()
            matrix[i][j] = (
                int_cache[key] / ref_vol * 100 if ref_vol > 0 else 0.0
            )

    return {"matrix": matrix}


# ---------------------------------------------------------------------------
# Render rings plot  →  PNG or PDF bytes
# ---------------------------------------------------------------------------

_SCALE_LIMITS: dict[str | int, tuple[float, float]] = {
    "emissive": (-1250.0, 1250.0),
    150: (-150.0, 150.0),  300: (-300.0, 300.0),  600: (-600.0, 600.0),
    "150": (-150.0, 150.0), "300": (-300.0, 300.0), "600": (-600.0, 600.0),
}


def _parse_floats(s: str) -> list[float]:
    return [float(x) for x in s.split(",") if x.strip()]


def _parse_band_ls(s: str) -> float | tuple[float, float] | list[float]:
    parts = _parse_floats(s)
    if not parts:
        return (20.0, 90.0)
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return (parts[0], parts[1])
    return parts


def _parse_primary_chroma(s: str) -> float | str:
    stripped = s.strip()
    if not stripped or stripped.lower() == "auto":
        return "auto"
    try:
        return float(stripped)
    except ValueError:
        return "auto"


def _resolve_l_label_indices(
    l_labels: str, effective_l_rings: list[float]
) -> list[int] | None:
    """Convert L* label values (e.g. '10,50') to 0-based indices into [*l_rings, 100].
    Returns None to keep plot_rings default, [] to suppress all labels."""
    stripped = l_labels.strip()
    if not stripped:
        return None  # plot_rings default [0, 4]
    if stripped.lower() == "none":
        return []
    vals = _parse_floats(stripped)
    all_l = effective_l_rings + [100.0]
    result = []
    for lv in vals:
        diffs = [abs(al - lv) for al in all_l]
        best_i = min(range(len(diffs)), key=lambda i: diffs[i])
        if diffs[best_i] < 1.0:
            result.append(best_i)
    return result or None


class RingsRenderRequest(BaseModel):
    dut_id: str
    reference_ids: list[str] = []
    # Axis scale (convenience mapping to xlim/ylim)
    scale: str | int | None = None    # "emissive" | 150 | 300 | 600 | None (auto)
    # Reference options
    intersection: bool = False
    # Ring levels
    l_rings: str = ""                 # "" = default [10,20,...,90]; "20,40,60,80" = custom
    # Colour bands
    show_bands: bool = True
    band_chroma: float = 50.0
    band_ls: str = "20,90"           # single value or "LO,HI"
    # Primary indicators
    primaries: str = "rgb"            # "none" | "rgb" | "all"
    ref_primaries: str = "none"
    primary_color: str = "output"     # "input" | "output"
    primary_origin: str = "centre"    # "centre" | "ring"
    primary_chroma: str = "auto"      # "auto" | numeric string
    show_cent_mark: bool = True
    # L* ring labels
    l_labels: str = "10,50"          # "none" | comma-separated L* values
    l_label_color: str = ""          # "" = default (outer black, inner white)
    # Constant-chroma reference circles
    chroma_rings: str = ""            # "" | "50,100,150"
    # Labels used in auto-title assembly
    dut_label: str = ""              # "" = auto (gamut title or name)
    ref_label: str = ""
    # Title
    title: str | None = "auto"       # "auto" | None (suppress) | custom string
    # Figure
    figsize: str = "8,8"
    dpi: int = 150
    format: str = "png"              # "png" | "pdf"
    download: bool = False


@app.post("/api/render/rings")
def render_rings(req: RingsRenderRequest) -> Response:
    dut = _registry.get(req.dut_id)
    if dut is None:
        raise HTTPException(status_code=404, detail=f"DUT gamut {req.dut_id!r} not found")

    refs: list[Gamut] = []
    for rid in req.reference_ids[:2]:
        ref = _registry.get(rid)
        if ref is None:
            raise HTTPException(status_code=404, detail=f"Reference gamut {rid!r} not found")
        refs.append(ref.gamut)

    lim = _SCALE_LIMITS.get(req.scale) if req.scale is not None else None
    fmt = req.format.lower() if req.format.lower() in ("png", "pdf") else "png"

    # Parse compound string fields
    parsed_l_rings: list[float] | None = (
        _parse_floats(req.l_rings) if req.l_rings.strip() else None
    )
    effective_l_rings = parsed_l_rings if parsed_l_rings is not None else list(range(10, 100, 10))
    parsed_chroma_rings = _parse_floats(req.chroma_rings) if req.chroma_rings.strip() else []
    parsed_figsize_list = _parse_floats(req.figsize)
    parsed_figsize = (
        (parsed_figsize_list[0], parsed_figsize_list[1])
        if len(parsed_figsize_list) == 2 else (8.0, 8.0)
    )
    l_label_indices = _resolve_l_label_indices(req.l_labels, effective_l_rings)

    kwargs: dict = dict(
        intersection_plot=req.intersection,
        show_bands=req.show_bands,
        band_chroma=req.band_chroma,
        band_ls=_parse_band_ls(req.band_ls),
        primaries=req.primaries,
        ref_primaries=req.ref_primaries,
        primary_color=req.primary_color,
        primary_origin=req.primary_origin,
        primary_chroma=_parse_primary_chroma(req.primary_chroma),
        cent_mark="+k" if req.show_cent_mark else None,
        chroma_rings=parsed_chroma_rings,
        figsize=parsed_figsize,
        title=req.title,
        xlim=lim,
        ylim=lim,
    )
    if parsed_l_rings is not None:
        kwargs["l_rings"] = parsed_l_rings
    if l_label_indices is not None:
        kwargs["l_label_indices"] = l_label_indices
    if req.l_label_color.strip():
        kwargs["l_label_colors"] = req.l_label_color.strip()
    if req.dut_label.strip():
        kwargs["dut_label"] = req.dut_label.strip()
    if req.ref_label.strip():
        kwargs["ref_label"] = req.ref_label.strip()

    from cielab_gamut_tools.plotting.rings import plot_rings
    import matplotlib.pyplot as plt

    try:
        fig, _ = plot_rings(
            dut.gamut,
            reference=refs[0] if refs else None,
            reference2=refs[1] if len(refs) > 1 else None,
            **kwargs,
        )
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, dpi=req.dpi, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    mime = "application/pdf" if fmt == "pdf" else "image/png"
    headers: dict[str, str] = {}
    if req.download:
        headers["Content-Disposition"] = f'attachment; filename="rings.{fmt}"'

    return Response(content=buf.read(), media_type=mime, headers=headers)


# ---------------------------------------------------------------------------
# Static files / SPA fallback
# ---------------------------------------------------------------------------

_DIST = Path(__file__).parent / "dist"

if _DIST.is_dir() and (_DIST / "index.html").exists():
    from starlette.staticfiles import StaticFiles

    _assets = _DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="static-assets")

    @app.get("/{path:path}")
    def _spa_fallback(path: str) -> FileResponse:
        return FileResponse(str(_DIST / "index.html"))

else:

    @app.get("/")
    def _no_ui() -> JSONResponse:
        raise HTTPException(
            status_code=404,
            detail="UI not built. Run: cd src/cielab_gamut_tools/ui/frontend && npm run build",
        )
