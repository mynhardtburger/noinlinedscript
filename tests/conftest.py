from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def jenkinsfile_fixtures():
    return FIXTURES_DIR / "jenkinsfiles"


@pytest.fixture
def shellscript_fixtures():
    return FIXTURES_DIR / "shellscripts"
