import pytest

from companion.connectors.github.project import ListProjectV2ItemDateValues
from companion.connectors.github.project import ListProjectV2ItemFieldValues
from companion.connectors.github.project import ListProjectV2Items
from companion.connectors.github.project import ProjectNotFoundError
from companion.connectors.github.project import ProjectItemKind
from companion.connectors.github.project import ProjectItemState


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


class NotFoundClient:
    def execute(self, query, variable_values):
        return {"node": None}


@pytest.mark.parametrize(
    "operation",
    [
        ListProjectV2Items(projectId="PVT_project"),
        ListProjectV2ItemFieldValues(projectId="PVT_project", fieldId="F"),
        ListProjectV2ItemDateValues(projectId="PVT_project", fieldId="F"),
    ],
)
def test_every_list_operation_raises_when_the_project_is_not_found(operation):
    with pytest.raises(ProjectNotFoundError, match="PVT_project"):
        operation.execute(NotFoundClient())


class TwoPageClient:
    def __init__(self, pages):
        self._pages = pages
        self._served = 0

    def execute(self, query, variable_values):
        page = self._pages[self._served]
        self._served += 1
        return {
            "node": {
                "items": {
                    "pageInfo": {
                        "hasNextPage": self._served < len(self._pages),
                        "endCursor": "next",
                    },
                    "nodes": page,
                }
            }
        }


def test_list_items_collects_items_of_every_page():
    pages = [
        [{"id": "A", "content": {"__typename": "DraftIssue", "title": "a"}}],
        [{"id": "B", "content": {"__typename": "DraftIssue", "title": "b"}}],
    ]

    items = ListProjectV2Items(projectId="PVT_project").execute(TwoPageClient(pages))

    assert [i.id for i in items] == ["A", "B"]


def test_list_date_values_collects_dates_of_every_page():
    def node(item_id, date):
        value = {"date": date, "field": {"id": "F"}}
        return {"id": item_id, "fieldValues": {"nodes": [None, value]}}

    pages = [[node("A", "2026-01-01")], [node("B", None)]]

    dates = ListProjectV2ItemDateValues(projectId="PVT_project", fieldId="F").execute(
        TwoPageClient(pages)
    )

    assert [(d.id, d.date) for d in dates] == [("A", "2026-01-01"), ("B", None)]


def test_list_field_values_collects_text_of_every_page():
    def node(text):
        value = {"text": text, "field": {"id": "F"}}
        return {"fieldValues": {"nodes": [value]}}

    pages = [[node("a")], [node("b")]]

    texts = ListProjectV2ItemFieldValues(projectId="PVT_project", fieldId="F").execute(
        TwoPageClient(pages)
    )

    assert texts == ["a", "b"]
