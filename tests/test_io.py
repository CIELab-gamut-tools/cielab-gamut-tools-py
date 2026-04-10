"""
Tests for file I/O functions.
"""

from pathlib import Path

import numpy as np
import pytest

from gamut_volume.io.cgats import read_cgats


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
        rgb, xyz, metadata = read_cgats(SAMPLES_DIR / "sRGB.txt")

        # Check shapes
        assert rgb.ndim == 2
        assert xyz.ndim == 2
        assert rgb.shape[1] == 3
        assert xyz.shape[1] == 3
        assert rgb.shape[0] == xyz.shape[0]

        # Check value ranges
        assert np.all(rgb >= 0)
        assert np.all(xyz >= 0)

    @pytest.mark.skipif(
        not (SAMPLES_DIR / "lcd.txt").exists(),
        reason="Sample file not available",
    )
    def test_read_lcd_sample(self):
        """Test reading the LCD sample file."""
        rgb, xyz, metadata = read_cgats(SAMPLES_DIR / "lcd.txt")

        assert rgb.shape[0] > 0
        assert xyz.shape[0] == rgb.shape[0]


class TestCgatsParser:
    """Tests for CGATS parsing edge cases."""

    def test_parse_minimal_file(self, tmp_path):
        """Test parsing a minimal valid CGATS file."""
        content = """
BEGIN_DATA_FORMAT
SAMPLE_ID RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT
BEGIN_DATA
1 0 0 0 0.1 0.1 0.1
2 255 255 255 95.0 100.0 109.0
END_DATA
"""
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        rgb, xyz, metadata = read_cgats(file_path)

        assert rgb.shape == (2, 3)
        assert xyz.shape == (2, 3)
        np.testing.assert_array_equal(rgb[0], [0, 0, 0])
        np.testing.assert_array_equal(rgb[1], [255, 255, 255])

    def test_parse_with_comments(self, tmp_path):
        """Test that comments are ignored."""
        content = """
# This is a comment
BEGIN_DATA_FORMAT
RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT
# Another comment
BEGIN_DATA
0 0 0 0.1 0.1 0.1
END_DATA
"""
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        rgb, xyz, metadata = read_cgats(file_path)
        assert rgb.shape == (1, 3)

    def test_parse_with_keywords(self, tmp_path):
        """Test parsing keyword/value pairs."""
        content = """
ORIGINATOR "Test"
NUMBER_OF_SETS 1
BEGIN_DATA_FORMAT
RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT
BEGIN_DATA
128 128 128 20.0 21.0 23.0
END_DATA
"""
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        rgb, xyz, metadata = read_cgats(file_path)

        assert metadata.get("ORIGINATOR") == "Test"
        assert metadata.get("NUMBER_OF_SETS") == "1"

    def test_missing_required_columns(self, tmp_path):
        """Test error when required columns are missing."""
        content = """
BEGIN_DATA_FORMAT
RGB_R RGB_G RGB_B
END_DATA_FORMAT
BEGIN_DATA
0 0 0
END_DATA
"""
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        with pytest.raises(ValueError, match="Missing required columns"):
            read_cgats(file_path)

    def test_empty_data(self, tmp_path):
        """Test error when no data rows present."""
        content = """
BEGIN_DATA_FORMAT
RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT
BEGIN_DATA
END_DATA
"""
        file_path = tmp_path / "test.txt"
        file_path.write_text(content)

        with pytest.raises(ValueError, match="No data rows"):
            read_cgats(file_path)
