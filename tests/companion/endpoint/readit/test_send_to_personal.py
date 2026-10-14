from unittest.mock import patch
from companion.endpoint.readit.core import Blackboard
from companion.endpoint.readit.core import OtherMetadata
from companion.endpoint.readit.app.send_to_personal import CONTENT_COMMENT_MARKER
from companion.endpoint.readit.app.send_to_personal import CONTENT_COMMENT_MAX_LENGTH
from companion.endpoint.readit.app.send_to_personal import (
    build_original_content_comment,
)
from companion.endpoint.readit.app.send_to_personal import send_to_personal
from companion.connectors.github import AddIssueCommentResponse
from companion.connectors.github import CreateIssueResponse


def test_send_to_personal_other_article(monkeypatch):
    """Test send_to_personal for 'other' kind with dry_run."""
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    bb = Blackboard(
        url="https://example.com/some-article",
        kind="other",
        title="Some Test Article",
        date="2026/05/18",
        trafilatura={"text": "This is the body content of the test article."},
        other=OtherMetadata(
            takeaways_sentences=["Key sentence 1", "Key sentence 2"],
        ),
    )

    # Let's call send_to_personal with dry_run=True
    send_to_personal(bb, dry_run=True)

    # Verify that the personal archive metadata is populated
    assert bb.personal_archive.issue_oid == "DUMMY_ISSUE_ID"
    assert bb.personal_archive.issue_url == "https://github.com/dummy/issue/1"
    assert bb.personal_archive.takeaways_comment_oid == "DUMMY_COMMENT_ID"
    assert (
        bb.personal_archive.takeaways_comment_url
        == "https://github.com/dummy/issue/1#issuecomment-1"
    )
    assert bb.personal_archive.content_comment_oid == "DUMMY_COMMENT_ID"
    assert (
        bb.personal_archive.content_comment_url
        == "https://github.com/dummy/issue/1#issuecomment-1"
    )


def _patch_github(bodies, fail_on=None):
    def mock_create_issue(self, client):
        return CreateIssueResponse(
            id="DUMMY_ISSUE_ID", url="https://github.com/dummy/issue/1"
        )

    def mock_add_comment(self, client):
        if fail_on is not None and len(bodies) == fail_on:
            raise RuntimeError("boom")
        bodies.append(self._values["body"])
        n = len(bodies)
        return AddIssueCommentResponse(
            id=f"COMMENT_{n}", url=f"https://github.com/dummy/issue/1#issuecomment-{n}"
        )

    return (
        patch("companion.connectors.github.CreateIssue.execute", mock_create_issue),
        patch("companion.connectors.github.AddIssueComment.execute", mock_add_comment),
    )


def test_send_to_personal_skips_too_long_content(monkeypatch):
    """Content over the limit is not recorded, but archiving still succeeds."""
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    bb = Blackboard(
        url="https://example.com/long-article",
        kind="other",
        title="Long Test Article",
        date="2026/05/18",
        trafilatura={"text": "A" * (CONTENT_COMMENT_MAX_LENGTH + 1)},
    )
    bodies: list[str] = []
    create, comment = _patch_github(bodies)
    with create, comment:
        send_to_personal(bb, dry_run=False)

    assert bodies == []
    assert bb.personal_archive.issue_oid == "DUMMY_ISSUE_ID"
    assert bb.personal_archive.content_comment_oid is None


def test_send_to_personal_records_content_at_limit(monkeypatch):
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    bb = Blackboard(
        url="https://example.com/a",
        kind="other",
        title="T",
        date="2026/05/18",
        trafilatura={"text": "A" * CONTENT_COMMENT_MAX_LENGTH},
    )
    bodies: list[str] = []
    create, comment = _patch_github(bodies)
    with create, comment:
        send_to_personal(bb, dry_run=False)

    assert len(bodies) == 1
    assert len(bodies[0]) < 65536
    assert bodies[0].startswith(CONTENT_COMMENT_MARKER)
    assert bb.personal_archive.content_comment_oid == "COMMENT_1"


def test_send_to_personal_content_failure_is_tolerated(monkeypatch):
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    bb = Blackboard(
        url="https://example.com/a",
        kind="other",
        title="T",
        date="2026/05/18",
        trafilatura={"text": "body"},
    )
    create, comment = _patch_github([], fail_on=0)
    with create, comment:
        send_to_personal(bb, dry_run=False)

    assert bb.personal_archive.issue_oid == "DUMMY_ISSUE_ID"
    assert bb.personal_archive.content_comment_oid is None


def test_build_original_content_comment_empty():
    assert build_original_content_comment(None) is None
    assert build_original_content_comment("") is None
