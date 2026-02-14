from pathlib import Path

import pytest


@pytest.fixture()
def sample_project() -> Path:
    return Path(__file__).resolve().parent.parent / "sample_project"
