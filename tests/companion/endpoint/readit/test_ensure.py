import pytest

from companion.endpoint.readit.core import Blackboard
from companion.connectors.github import IssueSearchHit
from companion.connectors.github import SearchIssuesByBody
from companion.endpoint.readit.steps.ensure import AlreadyArchivedError
from companion.endpoint.readit.steps.ensure import EnsureNotArchivedStep

URL = "https://example.com/post?id=1"


def stub_search(monkeypatch, hits):
    monkeypatch.setattr(SearchIssuesByBody, "execute", lambda self, client: hits)


def test_not_archived_passes_through(monkeypatch):
    stub_search(monkeypatch, [])
    bb = Blackboard(url=URL)
    assert EnsureNotArchivedStep(client=None)(bb) is bb


def test_archived_url_raises(monkeypatch):
    stub_search(monkeypatch, [IssueSearchHit(url="https://gh/issues/1", body=URL)])
    with pytest.raises(AlreadyArchivedError):
        EnsureNotArchivedStep(client=None)(Blackboard(url=URL))


def test_archived_url_in_multiline_body_raises(monkeypatch):
    body = f"{URL}\n\n> summary"
    stub_search(monkeypatch, [IssueSearchHit(url="https://gh/issues/2", body=body)])
    with pytest.raises(AlreadyArchivedError):
        EnsureNotArchivedStep(client=None)(Blackboard(url=URL))


def test_fuzzy_search_hit_is_ignored(monkeypatch):
    other = "https://example.com/post?id=12"
    stub_search(monkeypatch, [IssueSearchHit(url="https://gh/issues/3", body=other)])
    bb = Blackboard(url=URL)
    assert EnsureNotArchivedStep(client=None)(bb) is bb
