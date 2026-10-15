from unittest.mock import Mock

import pytest
from pydantic import HttpUrl
from gql import Client

from companion.endpoint.readit.core import Blackboard
from companion.connectors.github.issue import IssueSearchHit
from companion.connectors.github.issue import SearchIssuesByBody
from companion.endpoint.readit.steps.ensure import AlreadyArchivedError
from companion.endpoint.readit.steps.ensure import AlreadyInQueueError
from companion.endpoint.readit.steps.ensure import EnsureStep
from companion.endpoint.readit.steps.ensure import EnsureNotArchivedStep

URL = "https://example.com/post?id=1"
# The search is stubbed out, so the client is never used.
CLIENT = Mock(spec=Client)


class FakeQueue:
    def __init__(self, urls):
        self._urls = urls

    def get_urls(self):
        return self._urls


def test_url_not_in_queue_passes_through():
    bb = Blackboard(url=HttpUrl(URL))
    assert EnsureStep(FakeQueue([]))(bb) is bb


def test_url_in_queue_raises():
    with pytest.raises(AlreadyInQueueError):
        EnsureStep(FakeQueue([URL]))(Blackboard(url=HttpUrl(URL)))


def stub_search(monkeypatch, hits):
    monkeypatch.setattr(SearchIssuesByBody, "execute", lambda self, client: hits)


def test_not_archived_passes_through(monkeypatch):
    stub_search(monkeypatch, [])
    bb = Blackboard(url=HttpUrl(URL))
    assert EnsureNotArchivedStep(client=CLIENT)(bb) is bb


def test_archived_url_raises(monkeypatch):
    stub_search(monkeypatch, [IssueSearchHit(url="https://gh/issues/1", body=URL)])
    with pytest.raises(AlreadyArchivedError):
        EnsureNotArchivedStep(client=CLIENT)(Blackboard(url=HttpUrl(URL)))


def test_archived_url_in_multiline_body_raises(monkeypatch):
    body = f"{URL}\n\n> summary"
    stub_search(monkeypatch, [IssueSearchHit(url="https://gh/issues/2", body=body)])
    with pytest.raises(AlreadyArchivedError):
        EnsureNotArchivedStep(client=CLIENT)(Blackboard(url=HttpUrl(URL)))


def test_fuzzy_search_hit_is_ignored(monkeypatch):
    other = "https://example.com/post?id=12"
    stub_search(monkeypatch, [IssueSearchHit(url="https://gh/issues/3", body=other)])
    bb = Blackboard(url=HttpUrl(URL))
    assert EnsureNotArchivedStep(client=CLIENT)(bb) is bb
