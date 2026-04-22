import pytest
from endpoint.readit.core import Blackboard
from endpoint.readit.core import ArxivMetadata


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


def test_blackboard_url_as_str():
    """Test the url_as_str method of Blackboard."""
    bb = Blackboard(url="https://example.com/foo")
    assert bb.url_as_str() == "https://example.com/foo"
