from logging import getLogger
from typing import Protocol

from companion.endpoint.readit.core import Blackboard
from companion.endpoint.readit.core import Step

logger = getLogger(__name__)


class EvalQueueContract(Protocol):
    """What this step requires of the evaluation queue: only the methods it uses."""

    def add(self, *, title: str, url: str) -> None: ...


class AddQueueStep(Step):
    """Pipeline step that adds the Blackboard summary into the evaluation queue."""

    def __init__(self, queue: EvalQueueContract):
        self._queue = queue

    def __call__(self, bb: Blackboard) -> Blackboard:
        if bb.title is None:
            raise ValueError("Cannot add to the evaluation queue without a title.")
        self._queue.add(title=bb.title, url=bb.url_as_str())
        return bb
