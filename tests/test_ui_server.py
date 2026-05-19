"""
Tests for the FastAPI UI server (Stage 1).

Module-scoped client fixture so the Numba JIT warm-up and gamut builds are
paid once for the entire module, not per test.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from cielab_gamut_tools.ui.server import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def standard_ids(client: TestClient) -> dict[str, str]:
    """Return {name: id} for all standard gamuts."""
    resp = client.get("/api/gamuts")
    assert resp.status_code == 200
    return {g["name"]: g["id"] for g in resp.json()}


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_returns_five_standards(client: TestClient) -> None:
    resp = client.get("/api/gamuts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    names = {g["name"] for g in data}
    assert names == {"sRGB", "BT.2020", "DCI-P3", "Display P3", "Adobe RGB (1998)"}


def test_list_entry_shape(client: TestClient) -> None:
    resp = client.get("/api/gamuts")
    entry = resp.json()[0]
    assert set(entry.keys()) == {"id", "name", "source", "volume", "colour", "protected"}
    assert entry["source"] == "synthetic"
    assert entry["volume"] is None  # lazy — not computed yet
    assert entry["protected"] is True
    assert entry["colour"].startswith("#")


# ---------------------------------------------------------------------------
# Synthetic create / delete
# ---------------------------------------------------------------------------


def test_create_synthetic(client: TestClient) -> None:
    payload = {
        "primaries_xy": [[0.64, 0.33], [0.30, 0.60], [0.15, 0.06]],
        "white_xy": [0.3127, 0.3290],
        "gamma": 2.2,
        "name": "Test gamut",
    }
    resp = client.post("/api/gamuts/synthetic", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test gamut"
    assert data["source"] == "synthetic"
    assert data["protected"] is False

    # Should appear in list
    ids = {g["id"] for g in client.get("/api/gamuts").json()}
    assert data["id"] in ids

    # Clean up
    del_resp = client.delete(f"/api/gamuts/{data['id']}")
    assert del_resp.status_code == 204


def test_delete_standard_forbidden(client: TestClient, standard_ids: dict[str, str]) -> None:
    srgb_id = standard_ids["sRGB"]
    resp = client.delete(f"/api/gamuts/{srgb_id}")
    assert resp.status_code == 403


def test_delete_nonexistent(client: TestClient) -> None:
    resp = client.delete("/api/gamuts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def test_upload_cgats(client: TestClient) -> None:
    data_file = Path(__file__).parent / "data" / "sRGB.txt"
    with data_file.open("rb") as f:
        resp = client.post("/api/gamuts/upload", files={"file": ("sRGB.txt", f, "text/plain")})
    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "file"
    assert data["name"] == "sRGB"

    # Clean up
    client.delete(f"/api/gamuts/{data['id']}")


def test_upload_invalid_file(client: TestClient) -> None:
    resp = client.post(
        "/api/gamuts/upload",
        files={"file": ("bad.txt", b"not a CGATS file", "text/plain")},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Surface  (fast — no cylmap computation)
# ---------------------------------------------------------------------------


def test_surface_shape(client: TestClient, standard_ids: dict[str, str]) -> None:
    srgb_id = standard_ids["sRGB"]
    resp = client.get(f"/api/gamuts/{srgb_id}/surface")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["vertices"]) == 726
    assert all(len(v) == 3 for v in data["vertices"])
    assert len(data["faces"]) > 1000
    assert all(len(f) == 3 for f in data["faces"])


# ---------------------------------------------------------------------------
# Volume  (triggers cylmap build — pays Numba warm-up once)
# ---------------------------------------------------------------------------


def test_volume_srgb(client: TestClient, standard_ids: dict[str, str]) -> None:
    srgb_id = standard_ids["sRGB"]
    resp = client.get(f"/api/gamuts/{srgb_id}/volume")
    assert resp.status_code == 200
    vol = resp.json()["volume"]
    assert isinstance(vol, float)
    # sRGB volume ~830 000; allow generous tolerance for CI
    assert 700_000 < vol < 1_000_000


def test_volume_cached_in_list(client: TestClient) -> None:
    # After calling /volume above, _volume should be set and appear in list.
    resp = client.get("/api/gamuts")
    srgb = next(g for g in resp.json() if g["name"] == "sRGB")
    assert srgb["volume"] is not None


def test_volume_not_found(client: TestClient) -> None:
    resp = client.get("/api/gamuts/00000000-0000-0000-0000-000000000000/volume")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cylmap binary  (reuses cached cylmap from volume test above)
# ---------------------------------------------------------------------------


def test_cylmap_binary_format(client: TestClient, standard_ids: dict[str, str]) -> None:
    srgb_id = standard_ids["sRGB"]
    resp = client.get(f"/api/gamuts/{srgb_id}/cylmap")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"

    body = resp.content
    l_steps, h_steps = struct.unpack_from("<II", body, 0)
    assert l_steps == 100
    assert h_steps == 360

    # counts section: l_steps × h_steps bytes after the 8-byte header
    counts_end = 8 + l_steps * h_steps
    counts = list(body[8:counts_end])
    total_hits = sum(counts)

    # padding
    pad = (4 - counts_end % 4) % 4
    chroma_start = counts_end + pad
    chroma_bytes = body[chroma_start:]
    assert len(chroma_bytes) == total_hits * 4  # one float32 per hit


# ---------------------------------------------------------------------------
# Coverage  (builds BT.2020 cylmap too)
# ---------------------------------------------------------------------------


def test_coverage_srgb_vs_bt2020(
    client: TestClient, standard_ids: dict[str, str]
) -> None:
    payload = {"dut_id": standard_ids["sRGB"], "reference_id": standard_ids["BT.2020"]}
    resp = client.post("/api/gamuts/coverage", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert 0 < data["coverage"] < 100
    assert data["intersection_volume"] > 0


def test_coverage_self(client: TestClient, standard_ids: dict[str, str]) -> None:
    srgb_id = standard_ids["sRGB"]
    payload = {"dut_id": srgb_id, "reference_id": srgb_id}
    resp = client.post("/api/gamuts/coverage", json=payload)
    assert resp.status_code == 200
    assert abs(resp.json()["coverage"] - 100.0) < 0.1


def test_coverage_not_found(client: TestClient, standard_ids: dict[str, str]) -> None:
    payload = {
        "dut_id": standard_ids["sRGB"],
        "reference_id": "00000000-0000-0000-0000-000000000000",
    }
    resp = client.post("/api/gamuts/coverage", json=payload)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Matrix  (cylmaps already cached; only intersection is new work)
# ---------------------------------------------------------------------------


def test_matrix_2x2(client: TestClient, standard_ids: dict[str, str]) -> None:
    ids = [standard_ids["sRGB"], standard_ids["BT.2020"]]
    resp = client.post("/api/gamuts/matrix", json={"ids": ids})
    assert resp.status_code == 200
    matrix = resp.json()["matrix"]
    assert len(matrix) == 2
    assert len(matrix[0]) == 2
    # Diagonal must be 100%
    assert matrix[0][0] == pytest.approx(100.0)
    assert matrix[1][1] == pytest.approx(100.0)
    # sRGB is smaller than BT.2020, so sRGB coverage of BT.2020 < 100%
    assert matrix[0][1] < 100.0
    # BT.2020 fully contains sRGB, so BT.2020 coverage of sRGB ≈ 100%
    assert matrix[1][0] > 95.0


def test_matrix_unknown_id(client: TestClient, standard_ids: dict[str, str]) -> None:
    resp = client.post(
        "/api/gamuts/matrix",
        json={"ids": [standard_ids["sRGB"], "00000000-0000-0000-0000-000000000000"]},
    )
    assert resp.status_code == 404
