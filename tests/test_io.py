"""
Tests for file I/O functions.
"""

from pathlib import Path

import numpy as np
import pytest

from cielab_gamut_tools.io.cgats import CgatsData, read_cgats, write_cgats


SAMPLES_DIR = Path(__file__).parent / "data"


class TestReadCgats:
    """Tests for CGATS file reading."""

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            read_cgats("/nonexistent/path/file.txt")

    @pytest.mark.skipif(
        not (SAMPLES_DIR / "sRGB.txt").exists(),
        reason="Sample file not available",
    )
    def test_read_srgb_sample(self):
        """Test reading the sRGB sample file."""
        data = read_cgats(SAMPLES_DIR / "sRGB.txt")

        assert data.rgb is not None
        assert data.xyz is not None
        assert data.rgb.ndim == 2 and data.rgb.shape[1] == 3
        assert data.xyz.ndim == 2 and data.xyz.shape[1] == 3
        assert data.rgb.shape[0] == data.xyz.shape[0]
        assert np.all(data.rgb >= 0)
        assert np.all(data.xyz >= 0)

    @pytest.mark.skipif(
        not (SAMPLES_DIR / "lcd.txt").exists(),
        reason="Sample file not available",
    )
    def test_read_lcd_sample(self):
        """Test reading the LCD sample file."""
        data = read_cgats(SAMPLES_DIR / "lcd.txt")

        assert data.rgb is not None
        assert data.rgb.shape[0] > 0
        assert data.xyz is not None
        assert data.xyz.shape[0] == data.rgb.shape[0]

    def test_returns_cgats_data(self, tmp_path):
        """read_cgats should return a CgatsData instance."""
        content = (
            "BEGIN_DATA_FORMAT\n"
            "SAMPLE_ID RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "1 0 0 0 0.1 0.1 0.1\n"
            "END_DATA\n"
        )
        f = tmp_path / "test.txt"
        f.write_text(content)
        data = read_cgats(f)
        assert isinstance(data, CgatsData)


class TestCgatsParser:
    """Tests for CGATS parsing edge cases."""

    def test_parse_minimal_file(self, tmp_path):
        """Test parsing a minimal valid CGATS file."""
        content = (
            "BEGIN_DATA_FORMAT\n"
            "SAMPLE_ID RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "1 0 0 0 0.1 0.1 0.1\n"
            "2 255 255 255 95.0 100.0 109.0\n"
            "END_DATA\n"
        )
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        data = read_cgats(file_path)

        assert data.rgb is not None and data.rgb.shape == (2, 3)
        assert data.xyz is not None and data.xyz.shape == (2, 3)
        np.testing.assert_array_equal(data.rgb[0], [0, 0, 0])
        np.testing.assert_array_equal(data.rgb[1], [255, 255, 255])

    def test_parse_with_comments(self, tmp_path):
        """Test that comments are ignored."""
        content = (
            "# This is a comment\n"
            "BEGIN_DATA_FORMAT\n"
            "RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z\n"
            "END_DATA_FORMAT\n"
            "# Another comment\n"
            "BEGIN_DATA\n"
            "0 0 0 0.1 0.1 0.1\n"
            "END_DATA\n"
        )
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        data = read_cgats(file_path)
        assert data.rgb is not None and data.rgb.shape == (1, 3)

    def test_parse_with_keywords(self, tmp_path):
        """Test parsing keyword/value pairs."""
        content = (
            'ORIGINATOR "Test"\n'
            "NUMBER_OF_SETS 1\n"
            "BEGIN_DATA_FORMAT\n"
            "RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "128 128 128 20.0 21.0 23.0\n"
            "END_DATA\n"
        )
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        data = read_cgats(file_path)

        assert data.metadata.get("ORIGINATOR") == "Test"
        assert data.metadata.get("NUMBER_OF_SETS") == "1"

    def test_missing_xyz_returns_none(self, tmp_path):
        """Missing XYZ columns should yield xyz=None, not raise."""
        content = (
            "BEGIN_DATA_FORMAT\n"
            "RGB_R RGB_G RGB_B\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "0 0 0\n"
            "END_DATA\n"
        )
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        data = read_cgats(file_path)
        assert data.xyz is None
        assert data.lab is None

    def test_empty_data(self, tmp_path):
        """Test error when no data rows present."""
        content = (
            "BEGIN_DATA_FORMAT\n"
            "RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "END_DATA\n"
        )
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        with pytest.raises(ValueError, match="No data rows"):
            read_cgats(file_path)


class TestReadCgatsLab:
    """Tests for reading CGATS files with LAB columns."""

    def test_read_lab_columns(self, tmp_path):
        """Should extract LAB_L/A/B into data.lab."""
        content = (
            "CGATS.17\n"
            "FORMAT_VERSION\t2\n"
            "IDMS_FILE_TYPE\tCGE_ENVELOPE\n"
            "BEGIN_DATA_FORMAT\n"
            "SampleID RGB_R RGB_G RGB_B LAB_L LAB_A LAB_B\n"
            "END_DATA_FORMAT\n"
            "NUMBER_OF_SETS\t2\n"
            "BEGIN_DATA\n"
            "1 0 0 0 0 0 0\n"
            "2 255 255 255 100 0 0\n"
            "END_DATA\n"
        )
        f = tmp_path / "envelope.txt"
        f.write_text(content)

        data = read_cgats(f)

        assert data.lab is not None
        assert data.lab.shape == (2, 3)
        np.testing.assert_array_equal(data.lab[0], [0, 0, 0])
        np.testing.assert_array_equal(data.lab[1], [100, 0, 0])

    def test_lab_only_xyz_is_none(self, tmp_path):
        """A LAB-only file should have xyz=None."""
        content = (
            "BEGIN_DATA_FORMAT\n"
            "SampleID RGB_R RGB_G RGB_B LAB_L LAB_A LAB_B\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "1 0 0 0 50 10 -10\n"
            "END_DATA\n"
        )
        f = tmp_path / "lab_only.txt"
        f.write_text(content)

        data = read_cgats(f)

        assert data.xyz is None
        assert data.lab is not None
        assert data.rgb is not None

    def test_read_both_xyz_and_lab(self, tmp_path):
        """A file with both XYZ and LAB columns populates both fields."""
        content = (
            "BEGIN_DATA_FORMAT\n"
            "SampleID RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z LAB_L LAB_A LAB_B\n"
            "END_DATA_FORMAT\n"
            "BEGIN_DATA\n"
            "1 255 255 255 95.0 100.0 109.0 100 0 0\n"
            "END_DATA\n"
        )
        f = tmp_path / "both.txt"
        f.write_text(content)

        data = read_cgats(f)

        assert data.xyz is not None
        assert data.lab is not None
        assert data.xyz.shape == (1, 3)
        assert data.lab.shape == (1, 3)

    def test_read_reference_envelope(self):
        """Read the IDMS reference sRGB CGE_ENVELOPE file."""
        ref = Path(
            "standards/IDMS 5.32-code/"
            "Reference_sRGB_IEC_61966-2-1_cge_envelope.txt"
        )
        if not ref.exists():
            pytest.skip("Reference envelope file not available")

        data = read_cgats(ref)

        assert data.rgb is not None
        assert data.lab is not None
        assert data.xyz is None
        assert data.rgb.shape == (602, 3)
        assert data.lab.shape == (602, 3)
        # Black point — RGB (0,0,0) should be first row
        np.testing.assert_allclose(data.lab[0], [0, 0, 0], atol=0.01)
        # White point — find by RGB value (not position; file is in tesselation order)
        white_mask = np.all(data.rgb == 255, axis=1)
        assert white_mask.any(), "No pure-white row found"
        np.testing.assert_allclose(data.lab[white_mask][0, 0], 100, atol=0.01)


class TestWriteCgats:
    """Tests for CGATS file writing."""

    # ── Helpers ────────────────────────────────────────────────────────────

    def _read_lines(self, path: Path) -> list[str]:
        return path.read_text(encoding="utf-8").splitlines()

    def _read_section(self, path: Path, start: str, end: str) -> list[str]:
        lines = self._read_lines(path)
        inside = False
        result = []
        for line in lines:
            if line.strip() == start:
                inside = True
                continue
            if line.strip() == end:
                break
            if inside:
                result.append(line.strip())
        return result

    # ── Structure tests ────────────────────────────────────────────────────

    def test_creates_file(self, tmp_path):
        """write_cgats should create a file at the target path."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((3, 3)))
        assert out.exists()

    def test_cgats17_header(self, tmp_path):
        """First line must be CGATS.17."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)))
        assert self._read_lines(out)[0] == "CGATS.17"

    def test_format_version_header(self, tmp_path):
        """Second line must be FORMAT_VERSION\\t2."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)))
        assert self._read_lines(out)[1] == "FORMAT_VERSION\t2"

    def test_data_format_section_present(self, tmp_path):
        """BEGIN_DATA_FORMAT / END_DATA_FORMAT must be present."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((2, 3)))
        lines = self._read_lines(out)
        assert "BEGIN_DATA_FORMAT" in lines
        assert "END_DATA_FORMAT" in lines

    def test_data_section_present(self, tmp_path):
        """BEGIN_DATA / END_DATA must be present."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((2, 3)))
        lines = self._read_lines(out)
        assert "BEGIN_DATA" in lines
        assert "END_DATA" in lines

    def test_number_of_sets(self, tmp_path):
        """NUMBER_OF_SETS header must match the number of data rows."""
        n = 7
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((n, 3)))
        lines = self._read_lines(out)
        nos_line = next(l for l in lines if l.startswith("NUMBER_OF_SETS"))
        assert int(nos_line.split()[-1]) == n
        data_rows = self._read_section(out, "BEGIN_DATA", "END_DATA")
        assert len(data_rows) == n

    # ── Field name tests ───────────────────────────────────────────────────

    def test_lab_only_field_names(self, tmp_path):
        """Without rgb/xyz: fields should be SampleID LAB_L LAB_A LAB_B."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)))
        fmt = self._read_section(out, "BEGIN_DATA_FORMAT", "END_DATA_FORMAT")
        assert fmt == ["SampleID LAB_L LAB_A LAB_B"]

    def test_xyz_only_field_names(self, tmp_path):
        """Without rgb/lab: fields should be SampleID XYZ_X XYZ_Y XYZ_Z."""
        out = tmp_path / "out.txt"
        write_cgats(out, xyz=np.zeros((1, 3)))
        fmt = self._read_section(out, "BEGIN_DATA_FORMAT", "END_DATA_FORMAT")
        assert fmt == ["SampleID XYZ_X XYZ_Y XYZ_Z"]

    def test_rgb_lab_field_names(self, tmp_path):
        """With rgb+lab: fields should include RGB then LAB columns."""
        out = tmp_path / "out.txt"
        write_cgats(out, rgb=np.zeros((1, 3)), lab=np.zeros((1, 3)))
        fmt = self._read_section(out, "BEGIN_DATA_FORMAT", "END_DATA_FORMAT")
        assert fmt == ["SampleID RGB_R RGB_G RGB_B LAB_L LAB_A LAB_B"]

    def test_rgb_xyz_lab_field_names(self, tmp_path):
        """With rgb+xyz+lab: fields should be SampleID RGB XYZ LAB."""
        out = tmp_path / "out.txt"
        write_cgats(out, rgb=np.zeros((1, 3)), xyz=np.zeros((1, 3)), lab=np.zeros((1, 3)))
        fmt = self._read_section(out, "BEGIN_DATA_FORMAT", "END_DATA_FORMAT")
        assert fmt == [
            "SampleID RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z LAB_L LAB_A LAB_B"
        ]

    # ── Data value tests ───────────────────────────────────────────────────

    def test_data_values_lab(self, tmp_path):
        """LAB values written should match the input array."""
        lab = np.array([[50.0, 20.0, -30.0], [75.5, -10.0, 5.25]])
        out = tmp_path / "out.txt"
        write_cgats(out, lab=lab)

        data = read_cgats(out)
        assert data.lab is not None
        np.testing.assert_allclose(data.lab, lab, rtol=1e-5)

    def test_data_values_xyz(self, tmp_path):
        """XYZ values written should match the input array."""
        xyz = np.array([[95.0, 100.0, 109.0], [0.0, 0.0, 0.0]])
        out = tmp_path / "out.txt"
        write_cgats(out, xyz=xyz)

        data = read_cgats(out)
        assert data.xyz is not None
        np.testing.assert_allclose(data.xyz, xyz, rtol=1e-5)

    def test_integer_formatting(self, tmp_path):
        """Integer-valued floats should be written without decimal point."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.array([[0.0, 0.0, 0.0]]))
        data_rows = self._read_section(out, "BEGIN_DATA", "END_DATA")
        # All three LAB values and the SampleID should be bare integers
        assert data_rows[0] == "1 0 0 0"

    def test_float_formatting(self, tmp_path):
        """Non-integer floats should use %g formatting (no trailing zeros)."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.array([[50.5, 0.0, -12.125]]))
        data_rows = self._read_section(out, "BEGIN_DATA", "END_DATA")
        parts = data_rows[0].split()
        # 50.5 should not become 50.5000000 etc.
        assert "." not in parts[2] or not parts[2].endswith("0")

    # ── Sample ID tests ────────────────────────────────────────────────────

    def test_auto_sample_ids(self, tmp_path):
        """Sample IDs should default to 1-based sequential integers."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((3, 3)))
        rows = self._read_section(out, "BEGIN_DATA", "END_DATA")
        ids = [int(r.split()[0]) for r in rows]
        assert ids == [1, 2, 3]

    def test_custom_sample_ids(self, tmp_path):
        """Provided sample IDs should appear in the output."""
        out = tmp_path / "out.txt"
        ids = np.array([10, 20, 30])
        write_cgats(out, lab=np.zeros((3, 3)), sample_ids=ids)
        rows = self._read_section(out, "BEGIN_DATA", "END_DATA")
        written_ids = [int(r.split()[0]) for r in rows]
        assert written_ids == [10, 20, 30]

    # ── Header option tests ────────────────────────────────────────────────

    def test_file_type_header(self, tmp_path):
        """IDMS_FILE_TYPE header should appear when file_type is given."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)), file_type="CGE_ENVELOPE")
        lines = self._read_lines(out)
        assert "IDMS_FILE_TYPE\tCGE_ENVELOPE" in lines

    def test_no_file_type_header(self, tmp_path):
        """No IDMS_FILE_TYPE line when file_type=None."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)), file_type=None)
        lines = self._read_lines(out)
        assert not any("IDMS_FILE_TYPE" in l for l in lines)

    def test_description_line(self, tmp_path):
        """Description should appear as a bare line after FORMAT_VERSION."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)), description="My test gamut")
        lines = self._read_lines(out)
        assert "My test gamut" in lines

    def test_created_header(self, tmp_path):
        """CREATED header should appear when created is given."""
        out = tmp_path / "out.txt"
        write_cgats(out, lab=np.zeros((1, 3)), created="Thursday, March 05, 2020")
        lines = self._read_lines(out)
        assert "CREATED\tThursday, March 05, 2020" in lines

    # ── Error condition tests ──────────────────────────────────────────────

    def test_requires_xyz_or_lab(self, tmp_path):
        """Should raise ValueError when neither xyz nor lab is provided."""
        with pytest.raises(ValueError, match="At least one of xyz or lab"):
            write_cgats(tmp_path / "out.txt", rgb=np.zeros((3, 3)))

    def test_array_length_mismatch(self, tmp_path):
        """Should raise ValueError when arrays have different lengths."""
        with pytest.raises(ValueError, match="length mismatch"):
            write_cgats(
                tmp_path / "out.txt",
                rgb=np.zeros((3, 3)),
                lab=np.zeros((5, 3)),
            )

    # ── Round-trip tests ───────────────────────────────────────────────────

    def test_roundtrip_lab(self, tmp_path):
        """Write LAB then read back; values should survive round-trip."""
        lab = np.array([[0.0, 0.0, 0.0], [50.123, -20.5, 35.75], [100.0, 0.0, 0.0]])
        out = tmp_path / "rt_lab.txt"
        write_cgats(out, lab=lab)
        data = read_cgats(out)
        assert data.lab is not None
        np.testing.assert_allclose(data.lab, lab, rtol=1e-5)

    def test_roundtrip_xyz(self, tmp_path):
        """Write XYZ then read back; values should survive round-trip."""
        xyz = np.array([[0.0, 0.0, 0.0], [95.0, 100.0, 108.9]])
        out = tmp_path / "rt_xyz.txt"
        write_cgats(out, xyz=xyz)
        data = read_cgats(out)
        assert data.xyz is not None
        np.testing.assert_allclose(data.xyz, xyz, rtol=1e-5)

    def test_roundtrip_rgb_lab(self, tmp_path):
        """Write RGB+LAB then read back; both should survive round-trip."""
        rgb = np.array([[0.0, 0.0, 0.0], [255.0, 0.0, 0.0]])
        lab = np.array([[0.0, 0.0, 0.0], [54.29, 80.81, 69.89]])
        out = tmp_path / "rt_rgb_lab.txt"
        write_cgats(out, rgb=rgb, lab=lab)
        data = read_cgats(out)
        assert data.rgb is not None and data.lab is not None
        np.testing.assert_allclose(data.rgb, rgb, rtol=1e-5)
        np.testing.assert_allclose(data.lab, lab, rtol=1e-4)
