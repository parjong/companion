import logging


from companion.endpoint.penny.steps import prune
from companion.endpoint.penny.steps.prune import PruneClosedStep

PROJECT_ID = PruneClosedStep.PROJECT_ID


def node(item_id, kind, state=None):
    if kind == "DraftIssue":
        content = {"__typename": kind, "title": f"title {item_id}"}
    elif kind is None:
        content = None
    else:
        content = {
            "__typename": kind,
            "title": f"title {item_id}",
            "url": f"https://example.com/{item_id}",
            "state": state,
        }
    return {"id": item_id, "content": content}


def closed_node(n):
    content = n["content"]
    return bool(content) and content.get("state") in ("CLOSED", "MERGED")


class FakeClient:
    """Serves the given nodes in pages of 'page_size' and records deletions."""

    def __init__(self, nodes, *, page_size=100, failing=()):
        self._nodes = nodes
        self.queries = []
        self._page_size = page_size
        self._failing = set(failing)
        self.deleted = []
        self.list_calls = 0

    def execute(self, query, variable_values):
        if "itemId" in variable_values:
            item_id = variable_values["itemId"]
            assert variable_values["projectId"] == PROJECT_ID
            if item_id in self._failing:
                raise RuntimeError("boom")
            self.deleted.append(item_id)
            return {"op": {"deletedItemId": item_id}}

        self.list_calls += 1
        assert variable_values["projectId"] == PROJECT_ID
        self.queries.append(variable_values["query"])
        nodes = self._nodes
        if variable_values["query"] == "is:closed":
            nodes = [n for n in nodes if closed_node(n)]
        start = int(variable_values["after"] or 0)
        end = start + self._page_size
        return {
            "node": {
                "items": {
                    "pageInfo": {
                        "hasNextPage": end < len(nodes),
                        "endCursor": str(end),
                    },
                    "nodes": nodes[start:end],
                }
            }
        }


def make_step(client, *, limit=None, dry_run=False):
    return PruneClosedStep(client, limit=limit, dry_run=dry_run)


def test_deletes_only_closed_issues_and_pull_requests():
    client = FakeClient(
        [
            node("closed_issue", "Issue", "CLOSED"),
            node("open_issue", "Issue", "OPEN"),
            node("merged_pr", "PullRequest", "MERGED"),
            node("closed_pr", "PullRequest", "CLOSED"),
            node("open_pr", "PullRequest", "OPEN"),
            node("draft", "DraftIssue"),
            node("redacted", None),
        ]
    )

    result = make_step(client)()

    assert client.deleted == ["closed_issue", "merged_pr", "closed_pr"]
    assert [item.id for item in result.deleted] == client.deleted
    assert result.failed == []


def test_dry_run_deletes_nothing():
    client = FakeClient([node("closed_issue", "Issue", "CLOSED")])

    result = make_step(client, dry_run=True)()

    assert client.deleted == []
    assert result.deleted == []
    assert result.failed == []
    assert [item.id for item in result.skipped] == ["closed_issue"]


def test_limit_deletes_only_the_first_closed_items():
    client = FakeClient([node(f"closed_{i}", "Issue", "CLOSED") for i in range(3)])

    result = make_step(client, limit=2)()

    assert client.deleted == ["closed_0", "closed_1"]
    assert [item.id for item in result.deleted] == client.deleted


def test_limit_counts_only_closed_items():
    client = FakeClient(
        [
            node("open_1", "Issue", "OPEN"),
            node("closed_1", "Issue", "CLOSED"),
            node("open_2", "Issue", "OPEN"),
            node("closed_2", "Issue", "CLOSED"),
        ]
    )

    make_step(client, limit=1)()

    assert client.deleted == ["closed_1"]


def test_logs_every_candidate_before_deleting(caplog):
    caplog.set_level("INFO")
    client = FakeClient([node(f"closed_{i}", "Issue", "CLOSED") for i in range(3)])

    make_step(client, limit=1)()

    messages = [record.getMessage() for record in caplog.records]
    candidates = [i for i, m in enumerate(messages) if "Candidate" in m]
    first_delete = next(i for i, m in enumerate(messages) if "Deleted" in m)
    assert len(candidates) == 3
    assert max(candidates) < first_delete
    assert "https://example.com/closed_2" in messages[candidates[2]]


def test_lists_only_closed_items_with_the_query():
    client = FakeClient([node("open", "Issue", "OPEN")])

    make_step(client)()

    assert client.queries == ["is:closed"]


def test_step_logs_at_info_level_by_default():
    assert prune.logger.isEnabledFor(logging.INFO)


def test_follows_pagination():
    client = FakeClient(
        [node(f"closed_{i}", "Issue", "CLOSED") for i in range(5)], page_size=2
    )

    make_step(client)()

    assert client.list_calls == 3
    assert client.deleted == [f"closed_{i}" for i in range(5)]


def test_failure_is_reported_and_remaining_items_are_deleted():
    client = FakeClient(
        [node(f"closed_{i}", "Issue", "CLOSED") for i in range(3)],
        failing={"closed_1"},
    )

    result = make_step(client)()

    assert client.deleted == ["closed_0", "closed_2"]
    assert [item.id for item in result.failed] == ["closed_1"]
