from unittest.mock import patch
from endpoint.readit.core import Blackboard
from endpoint.readit.core import PersonalArchiveMetadata
from endpoint.readit.github import ProjectItemID
from endpoint.readit.app.send_to_queue_v2 import send_to_queue_v2


def test_send_to_queue_v2_other(monkeypatch):
    """Test send_to_queue_v2 for other article kind with original content fields."""
    monkeypatch.setenv("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    monkeypatch.setenv("OWNER_TOKEN", "dummy-token")

    bb = Blackboard(
        url="https://example.com/other-article",
        kind="other",
        title="Test Other Queue Article",
        date="2026/05/18",
        personal_archive=PersonalArchiveMetadata(
            issue_oid="DUMMY_ISSUE_ID",
            issue_url="https://github.com/dummy/issue/1",
            comment_oid="DUMMY_COMMENT_ID",
            comment_url="https://github.com/dummy/issue/1#issuecomment-1",
            content_comment_oid="DUMMY_CONTENT_COMMENT_ID",
            content_comment_url="https://github.com/dummy/issue/1#issuecomment-2",
        ),
    )

    # Capture the fields updated
    updated_fields = {}

    def mock_add_project_v2_execute(self, client):
        return ProjectItemID("DUMMY_ITEM_ID")

    def mock_add_project_v2_item_execute(self, client):
        return ProjectItemID("DUMMY_ITEM_ID")

    def mock_update_text_field(self, client):
        field_id = self._values["fieldId"]
        value = self._values["value"]
        updated_fields[field_id] = value

    with patch(
        "endpoint.readit.app.send_to_queue_v2.AddProjectV2DraftIssue.execute",
        mock_add_project_v2_execute,
    ):
        with patch(
            "endpoint.readit.github.AddProjectV2ItemById.execute",
            mock_add_project_v2_item_execute,
        ):
            with patch(
                "endpoint.readit.app.send_to_queue_v2.UpdateTextFieldValue.execute",
                mock_update_text_field,
            ):
                send_to_queue_v2(bb, dry_run=False)

    # Verify that the original content fields are updated on the project item!
    # OTHER_CONTENT_URL_FIELD_ID = "PVTF_lAHOAOPA3c4BWG6ZzhTMTCA"
    # OTHER_CONTENT_ID_FIELD_ID = "PVTF_lAHOAOPA3c4BWG6ZzhTMTDk"
    assert (
        updated_fields["PVTF_lAHOAOPA3c4BWG6ZzhTMTCA"]
        == "https://github.com/dummy/issue/1#issuecomment-2"
    )
    assert updated_fields["PVTF_lAHOAOPA3c4BWG6ZzhTMTDk"] == "DUMMY_CONTENT_COMMENT_ID"
