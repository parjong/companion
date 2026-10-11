import pytest

from companion.endpoint.readit.core import Blackboard
from companion.endpoint.readit.steps.add_queue import AddQueueStep

URL = "https://example.com/post?id=1"


class FakeQueue:
    def __init__(self):
        self.added = []

    def add(self, *, title, url):
        self.added.append((title, url))


def test_adds_title_and_url():
    queue = FakeQueue()
    bb = Blackboard(url=URL, title="A title")
    assert AddQueueStep(queue)(bb) is bb
    assert queue.added == [("A title", URL)]


def test_missing_title_raises():
    queue = FakeQueue()
    with pytest.raises(ValueError):
        AddQueueStep(queue)(Blackboard(url=URL))
    assert queue.added == []
