from unittest.mock import patch
from endpoint.readit.core import Blackboard
from endpoint.readit.core import OtherMetadata
from endpoint.readit.app.send_to_personal import send_to_personal
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


def test_send_to_personal_other_article_truncated(monkeypatch):
    """Test send_to_personal truncation logic for very long content."""
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    # Body text longer than 60,000 characters
    long_body = "A" * 65000
    bb = Blackboard(
        url="https://example.com/long-article",
        kind="other",
        title="Long Test Article",
        date="2026/05/18",
        trafilatura={"text": long_body},
    )

    # We want to intercept CreateIssue and AddIssueComment execute call to inspect the body that was sent!
    original_execute = []

    def mock_create_issue(self, client):
        return CreateIssueResponse(
            id="DUMMY_ISSUE_ID", url="https://github.com/dummy/issue/1"
        )

    # We patch AddIssueComment.execute so we can capture the comment body
    def mock_add_comment(self, client):
        original_execute.append(self._values["body"])
        return AddIssueCommentResponse(
            id="TRUNCATED_COMMENT_ID",
            url="https://github.com/dummy/issue/1#issuecomment-truncated",
        )

    with patch("endpoint.readit.github.CreateIssue.execute", mock_create_issue):
        with patch("endpoint.readit.github.AddIssueComment.execute", mock_add_comment):
            send_to_personal(bb, dry_run=False)

    # There should be exactly 1 comment since key_sentences is empty, which is the original content comment
    assert len(original_execute) == 1
    comment_body = original_execute[0]
    assert comment_body.startswith("## Original Content\n\n")
    assert "truncated because it exceeded the character limit" in comment_body
    # The actual truncated body should be exactly 60,000 "A"s
    truncated_content = comment_body.split("\n\n")[1]
    assert len(truncated_content) == 60000
    assert bb.personal_archive.content_comment_oid == "TRUNCATED_COMMENT_ID"
    assert (
        bb.personal_archive.content_comment_url
        == "https://github.com/dummy/issue/1#issuecomment-truncated"
    )
