import pytest
from endpoint.readit.core import Blackboard
from endpoint.readit.core import ArxivMetadata
from endpoint.readit.core import PersonalArchiveMetadata


def test_blackboard_arxiv_validation():
    """Test that kind='arxiv' requires arxiv metadata."""
    # Valid arxiv
    bb = Blackboard(
        url="https://arxiv.org/abs/1234.5678",
        kind="arxiv",
        arxiv=ArxivMetadata(summary="Summary", year="2024"),
    )
    assert bb.arxiv is not None
    assert bb.arxiv.year == "2024"

    # Invalid arxiv (missing arxiv field)
    with pytest.raises(ValueError, match="arxiv metadata is required"):
        Blackboard(url="https://arxiv.org/abs/1234.5678", kind="arxiv")


def test_blackboard_url_as_str():
    """Test the url_as_str method of Blackboard."""
    bb = Blackboard(url="https://example.com/foo")
    assert bb.url_as_str() == "https://example.com/foo"


def test_personal_archive_metadata_validation():
    """Test PersonalArchiveMetadata validation for comments and issues."""
    meta = PersonalArchiveMetadata(
        issue_oid="ISSUE_OID",
        issue_url="https://github.com/parjong/companion/issues/1",
        comment_oid="COMMENT_OID",
        comment_url="https://github.com/parjong/companion/issues/1#issuecomment-1",
        content_comment_oid="CONTENT_COMMENT_OID",
        content_comment_url="https://github.com/parjong/companion/issues/1#issuecomment-2",
    )
    assert meta.content_comment_oid == "CONTENT_COMMENT_OID"
    assert (
        meta.content_comment_url
        == "https://github.com/parjong/companion/issues/1#issuecomment-2"
    )

    # Invalid URL validation
    with pytest.raises(ValueError):
        PersonalArchiveMetadata(content_comment_url="invalid-url")
