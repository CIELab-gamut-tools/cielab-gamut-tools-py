"""
Pytest configuration and fixtures.
"""

from pathlib import Path

import pytest


@pytest.fixture
def samples_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def matlab_samples_dir() -> Path:
    """Return the path to the MATLAB project samples directory."""
    return Path(__file__).parent.parent.parent / "gamut-volume-m" / "samples"
