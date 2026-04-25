from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def list_page_html() -> str:
    return (FIXTURES_DIR / "list_page.html").read_text()


@pytest.fixture
def detail_page_html() -> str:
    return (FIXTURES_DIR / "detail_page.html").read_text()
