import pytest
from urllib.parse import urlparse
from endpoint.readit.core import Page
from endpoint.readit.core import Blackboard
from endpoint.readit.core import ArxivMetadata


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


def test_blackboard_arxiv_validation():
    """Test that kind='arxiv' requires arxiv metadata."""
    # Valid arxiv
    bb = Blackboard(
        url="https://arxiv.org/abs/1234.5678",
        kind="arxiv",
        arxiv=ArxivMetadata(summary="Summary", year="2024"),
    )
    assert bb.arxiv.year == "2024"

    # Invalid arxiv (missing arxiv field)
    with pytest.raises(ValueError, match="arxiv metadata is required"):
        Blackboard(url="https://arxiv.org/abs/1234.5678", kind="arxiv")


def test_blackboard_metadata_migration():
    """Test that legacy 'metadata' in input is migrated to specialized fields."""
    # 1. Arxiv migration
    data_arxiv = {
        "url": "https://arxiv.org/abs/1234.5678",
        "kind": "arxiv",
        "metadata": {"summary": "Migrated summary", "year": "2024"},
    }
    bb_arxiv = Blackboard.model_validate(data_arxiv)
    assert bb_arxiv.arxiv is not None
    assert bb_arxiv.arxiv.summary == "Migrated summary"
    # Ensure metadata was popped
    assert "metadata" not in bb_arxiv.model_dump(exclude_unset=True)

    # 2. Other migration
    data_other = {
        "url": "https://example.com",
        "kind": "other",
        "metadata": {"key_sentences": ["Sentence A"]},
    }
    bb_other = Blackboard.model_validate(data_other)
    assert bb_other.other is not None
    assert bb_other.other.key_sentences == ["Sentence A"]


def test_page_bridge_logic():
    """Test that Page class can load from new Blackboard format (without metadata key)."""
    # Blackboard format (using 'other' instead of 'metadata')
    bb_data = {
        "url": "https://example.com",
        "title": "New Format Title",
        "date": "2024/04/21",
        "kind": "other",
        "other": {"key_sentences": ["Sentence 1", "Sentence 2"]},
    }

    # Should load correctly into Page despite missing 'metadata' key in local dict
    page = Page.fromdict(bb_data)

    assert page.kind == "other"
    assert page.metadata["key_sentences"] == ["Sentence 1", "Sentence 2"]

    # Arxiv case
    arxiv_data = {
        "url": "https://arxiv.org/abs/1234.5678",
        "title": "Arxiv Paper",
        "date": "2024",
        "kind": "arxiv",
        "arxiv": {"summary": "Paper summary", "year": "2024"},
    }
    page_arxiv = Page.fromdict(arxiv_data)
    assert page_arxiv.kind == "arxiv"
    assert page_arxiv.metadata["summary"] == "Paper summary"
