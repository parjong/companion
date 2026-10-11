from datetime import date

from companion.endpoint.readit.steps import prune

from companion.connectors.github import ProjectItemDate
from companion.connectors.github import ProjectItemID
from companion.endpoint.readit.steps.prune import PruneQueueStep
from companion.endpoint.readit.steps.prune import select_expired


def item(id: str, d: str | None) -> ProjectItemDate:
    return ProjectItemDate(id=ProjectItemID(id), date=d)


TODAY = date(2026, 10, 1)


def test_select_expired_picks_only_items_older_than_max_age():
    items = [
        item("old", "2026-08-01"),
        item("edge", "2026-09-01"),
        item("new", "2026-09-30"),
    ]
    selected = select_expired(items, today=TODAY, max_age_days=30, limit=10)
    assert [i.id for i in selected] == ["old"]


def test_select_expired_orders_oldest_first_and_applies_limit():
    items = [item("b", "2026-07-02"), item("a", "2026-07-01"), item("c", "2026-07-03")]
    selected = select_expired(items, today=TODAY, max_age_days=30, limit=2)
    assert [i.id for i in selected] == ["a", "b"]


def test_select_expired_skips_items_without_date():
    selected = select_expired([item("x", None)], today=TODAY, max_age_days=30, limit=10)
    assert selected == []


class FakeQueue:
    def __init__(self, items):
        self._items = items
        self.removed = []

    def list_items(self):
        return self._items

    def remove(self, item):
        self.removed.append(item.id)


def run_step(queue, *, dry_run, monkeypatch, limit=10):
    monkeypatch.setattr(prune, "today_kst", lambda: TODAY)
    monkeypatch.setattr(prune.time, "sleep", lambda seconds: None)
    step = PruneQueueStep(queue, max_age_days=30, limit=limit)
    return step(dry_run=dry_run)


def test_step_removes_expired_items_oldest_first(monkeypatch):
    queue = FakeQueue(
        [item("new", "2026-09-30"), item("b", "2026-08-02"), item("a", "2026-08-01")]
    )
    assert run_step(queue, dry_run=False, monkeypatch=monkeypatch) == 2
    assert queue.removed == ["a", "b"]


def test_step_dry_run_removes_nothing(monkeypatch):
    queue = FakeQueue([item("a", "2026-08-01")])
    assert run_step(queue, dry_run=True, monkeypatch=monkeypatch) == 1
    assert queue.removed == []
