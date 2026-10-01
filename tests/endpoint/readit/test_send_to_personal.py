from unittest.mock import patch
from endpoint.readit.core import Blackboard
from endpoint.readit.core import OtherMetadata
from endpoint.readit.app.send_to_personal import CONTENT_COMMENT_MARKER
from endpoint.readit.app.send_to_personal import build_original_content_comments
from endpoint.readit.app.send_to_personal import send_to_personal
from endpoint.readit.app.send_to_personal import split_content
from endpoint.readit.github import AddIssueCommentResponse
from endpoint.readit.github import CreateIssueResponse


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
            key_sentences=["Key sentence 1", "Key sentence 2"],
        ),
    )

    # Let's call send_to_personal with dry_run=True
    send_to_personal(bb, dry_run=True)

    # Verify that the personal archive metadata is populated
    assert bb.personal_archive.issue_oid == "DUMMY_ISSUE_ID"
    assert bb.personal_archive.issue_url == "https://github.com/dummy/issue/1"
    assert bb.personal_archive.comment_oid == "DUMMY_COMMENT_ID"
    assert (
        bb.personal_archive.comment_url
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
        patch("endpoint.readit.github.CreateIssue.execute", mock_create_issue),
        patch("endpoint.readit.github.AddIssueComment.execute", mock_add_comment),
    )


def test_send_to_personal_splits_long_content(monkeypatch):
    """Content over the limit is split into several comments rather than dropped."""
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    bb = Blackboard(
        url="https://example.com/long-article",
        kind="other",
        title="Long Test Article",
        date="2026/05/18",
        trafilatura={"text": "A" * 65000},
    )
    bodies: list[str] = []
    create, comment = _patch_github(bodies)
    with create, comment:
        send_to_personal(bb, dry_run=False)

    assert len(bodies) == 2
    assert all(len(b) < 65536 for b in bodies)
    assert all(b.startswith(CONTENT_COMMENT_MARKER) for b in bodies)
    assert "<!-- part: 1/2 -->" in bodies[0]
    assert "<!-- part: 2/2 -->" in bodies[1]
    assert sum(b.count("A") for b in bodies) == 65000
    # The first comment is the one referenced from the project board
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


def test_build_original_content_comments_empty():
    assert build_original_content_comments(None) == []
    assert build_original_content_comments("") == []


def test_split_content_keeps_code_fences_balanced():
    text = "intro\n```\n" + "\n".join(f"line {i}" for i in range(50)) + "\n```\noutro"
    chunks = split_content(text, limit=120)
    assert len(chunks) > 1
    assert all(len(c) <= 120 for c in chunks)
    assert all(c.count("```") % 2 == 0 for c in chunks)
    assert "line 0" in chunks[0] and "outro" in chunks[-1]


def test_split_content_hard_splits_long_line():
    chunks = split_content("x" * 1000, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == "x" * 1000
