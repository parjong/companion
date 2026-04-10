from urllib.parse import urlparse
from endpoint.readit.core import Page


def test_page_fromdict_other():
    """Test parsing an 'other' Page from a dictionary payload."""
    payload = {
        "url": "https://example.com/foo",
        "title": "Example Title",
        "date": "2026/04/10",
        "kind": "other",
        "metadata": {"some": "value"},
    }

    page = Page.fromdict(payload)

    assert page.kind == "other"
    assert page.title == "Example Title"
    assert page.date == "2026/04/10"
    assert page.url_as_str() == "https://example.com/foo"
    # asdict shouldn't lose the metadata
    assert page.asdict() == payload
    # Validate inner URL object representation
    assert page.url.netloc == "example.com"


def test_page_fromdict_arxiv():
    """Test parsing an 'arxiv' Page.
    Notes from Issue #28: date format should be YYYY, it can't be UNKNOWN.
    We also expect paper_id and abstract around metadata for now.
    """
    payload = {
        "url": "https://arxiv.org/abs/2602.04118",
        "title": "Some Paper Title",
        "date": "2026",
        "kind": "arxiv",
        "metadata": {"paper_id": "2602.04118", "abstract": "This is a great paper."},
    }

    page = Page.fromdict(payload)

    assert page.kind == "arxiv"
    assert page.title == "Some Paper Title"
    assert page.date == "2026"
    assert page.url_as_str() == "https://arxiv.org/abs/2602.04118"
    assert page.asdict() == payload
    assert page.metadata["paper_id"] == "2602.04118"


def test_page_direct_instantiation():
    """Test creating a Page directly via constructor."""
    page = Page(
        url=urlparse("https://github.com"),
        title="GitHub",
        date="UNKNOWN",
        kind="other",
        metadata={},
    )
    assert page.kind == "other"
    assert page.date == "UNKNOWN"
    assert page.url_as_str() == "https://github.com"
