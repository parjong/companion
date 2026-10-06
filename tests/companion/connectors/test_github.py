import pytest

from companion.connectors.github import ListProjectV2Items
from companion.connectors.github import ProjectNotFoundError
from companion.connectors.github import ProjectItemKind
from companion.connectors.github import ProjectItemState


class FakeClient:
    def __init__(self, nodes):
        self._nodes = nodes

    def execute(self, query, variable_values):
        return {
            "node": {
                "items": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": self._nodes,
                }
            }
        }


def list_items(nodes):
    return ListProjectV2Items(projectId="PVT_project").execute(FakeClient(nodes))


def test_parses_kind_and_state_into_enums():
    [item] = list_items(
        [
            {
                "id": "I",
                "content": {
                    "__typename": "PullRequest",
                    "title": "t",
                    "url": "u",
                    "state": "MERGED",
                },
            }
        ]
    )

    assert item.kind is ProjectItemKind.PULL_REQUEST
    assert item.state is ProjectItemState.MERGED


def test_draft_and_redacted_items_have_no_state():
    draft, redacted = list_items(
        [
            {"id": "D", "content": {"__typename": "DraftIssue", "title": "t"}},
            {"id": "R", "content": None},
        ]
    )

    assert draft.kind is ProjectItemKind.DRAFT_ISSUE
    assert draft.state is ProjectItemState.NONE
    assert redacted.kind is ProjectItemKind.REDACTED
    assert redacted.state is ProjectItemState.NONE


def test_values_added_by_github_later_become_unknown():
    [item] = list_items(
        [
            {
                "id": "I",
                "content": {
                    "__typename": "Discussion",
                    "title": "t",
                    "url": "u",
                    "state": "ANSWERED",
                },
            }
        ]
    )

    assert item.kind is ProjectItemKind.UNKNOWN
    assert item.state is ProjectItemState.UNKNOWN


def test_raises_a_clear_error_when_the_project_is_not_found():
    class NotFoundClient:
        def execute(self, query, variable_values):
            return {"node": None}

    with pytest.raises(ProjectNotFoundError, match="PVT_project"):
        ListProjectV2Items(projectId="PVT_project").execute(NotFoundClient())
