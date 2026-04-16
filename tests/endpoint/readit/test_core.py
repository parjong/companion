from urllib.parse import urlparse
from endpoint.readit.core import Page


def test_page_fromdict_other():
    """Test parsing an 'other' Page from a dictionary payload."""
    payload = {
        "url": "https://example.com/foo",
        "title": "Example Title",
        "date": "2026/04/10",
        "kind": "other",
        "metadata": {"key_sentences": ["First sentence.", "Second sentence."]},
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
    We also expect summary and year in metadata.
    """
    payload = {
        "url": "https://arxiv.org/abs/2602.04118",
        "title": "Some Paper Title",
        "date": "2026",
        "kind": "arxiv",
        "metadata": {"summary": "This is a great paper.", "year": "2026"},
    }

    page = Page.fromdict(payload)

    assert page.kind == "arxiv"
    assert page.title == "Some Paper Title"
    assert page.date == "2026"
    assert page.url_as_str() == "https://arxiv.org/abs/2602.04118"
    assert page.asdict() == payload
    assert page.metadata["summary"] == "This is a great paper."
    assert page.metadata["year"] == "2026"


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


def test_blackboard_from_pipeline_file(tmp_path):
    """Test loading Blackboard from both legacy and new formats."""
    import json
    from endpoint.readit.core import Blackboard

    # 1. New Format
    bb_path = tmp_path / "bb.json"
    bb_data = {
        "url": "https://example.com",
        "kind": "other",
        "title": "BB Title",
    }
    bb_path.write_text(json.dumps(bb_data))

    bb = Blackboard.from_pipeline_file(str(bb_path))
    assert str(bb.url).rstrip("/") == "https://example.com"
    assert bb.kind == "other"
    assert bb.title == "BB Title"

    # 2. Legacy Format (FetchResult)
    legacy_path = tmp_path / "legacy.json"
    legacy_data = {
        "url": "https://example.com/legacy",
        "html": "<html></html>",
        "trafilatura": {"text": "hello"},
    }
    legacy_path.write_text(json.dumps(legacy_data))

    bb_legacy = Blackboard.from_pipeline_file(str(legacy_path))
    assert str(bb_legacy.url).rstrip("/") == "https://example.com/legacy"
    assert bb_legacy.html == "<html></html>"
    assert bb_legacy.trafilatura == {"text": "hello"}
    assert bb_legacy.kind == "other"  # default

    # 3. File-like object
    with open(bb_path, "r") as f:
        bb_from_file = Blackboard.from_pipeline_file(f)
    assert bb_from_file.title == "BB Title"
