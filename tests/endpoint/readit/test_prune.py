from datetime import date

from endpoint.readit.github import ProjectItemDate
from endpoint.readit.github import ProjectItemID
from endpoint.readit.steps.prune import select_expired


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
