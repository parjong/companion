import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from logging import getLogger
from typing import Protocol

from companion.connectors.github import ProjectItemDate

logger = getLogger(__name__)

# Pause between delete requests to stay clear of GitHub's secondary rate limit.
DELETE_INTERVAL_SECONDS = 1.0


class EvalQueueContract(Protocol):
    """What this step requires of the evaluation queue: only the methods it uses."""

    def list_items(self) -> list[ProjectItemDate]: ...

    def remove(self, item: ProjectItemDate) -> None: ...


def today_kst() -> date:
    return datetime.now(timezone(timedelta(hours=9))).date()


def select_expired(
    items: list[ProjectItemDate], *, today: date, max_age_days: int, limit: int
) -> list[ProjectItemDate]:
    """Returns up to `limit` items older than `max_age_days`, oldest first.

    Items without an 'Added At' date are never selected.
    """
    cutoff = today - timedelta(days=max_age_days)
    expired = [i for i in items if i.date and date.fromisoformat(i.date) < cutoff]
    expired.sort(key=lambda i: i.date)
    return expired[:limit]


class PruneQueueStep:
    """Removes items from the evaluation queue that were added more than `max_age_days` ago."""

    def __init__(self, queue: EvalQueueContract, *, max_age_days: int, limit: int):
        self._queue = queue
        self._max_age_days = max_age_days
        self._limit = limit

    def __call__(self, *, dry_run: bool = False) -> int:
        items = self._queue.list_items()
        targets = select_expired(
            items,
            today=today_kst(),
            max_age_days=self._max_age_days,
            limit=self._limit,
        )
        logger.info(
            "Selected %d of %d items older than %d days (limit=%d)",
            len(targets),
            len(items),
            self._max_age_days,
            self._limit,
        )

        for index, item in enumerate(targets):
            if dry_run:
                logger.info(
                    "[dry-run] Would remove %s (added at %s)", item.id, item.date
                )
                continue
            if index:
                time.sleep(DELETE_INTERVAL_SECONDS)
            self._queue.remove(item)
            logger.info("Removed %s (added at %s)", item.id, item.date)

        return len(targets)
