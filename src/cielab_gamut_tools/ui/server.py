"""
FastAPI server for the CIELab gamut tools web UI.

In-memory gamut registry pre-populated with 5 standard synthetic references.
All cylmap / volume computations are lazy (built on first request, then cached
on the Gamut object).
"""

from __future__ import annotations

import os
import struct
import tempfile
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

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


@app.post("/api/gamuts/synthetic", status_code=201)
def create_synthetic(req: SyntheticRequest) -> dict:  # type: ignore[type-arg]
    try:
        sg = SyntheticGamut(
            np.array(req.primaries_xy),
            np.array(req.white_xy),
            gamma=req.gamma,
        )
        gamut = sg.gamut
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    entry = _add_entry(req.name or "Custom gamut", "synthetic", gamut)
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
