from dataclasses import dataclass
from gql import gql
from logging import getLogger

logger = getLogger(__name__)


@dataclass(frozen=True)
class CreateIssueResponse:
    id: str
    url: str


@dataclass(frozen=True)
class AddIssueCommentResponse:
    id: str
    url: str


class CreateIssue:
    # https://docs.github.com/en/graphql/reference/mutations#createissue
    QUERY = gql("""
    mutation ($repositoryId: ID!, $title: String!, $body: String!) {
      op: createIssue(input: {
        repositoryId: $repositoryId,
        title: $title,
        body: $body,
      }) { issue { id url } }
    }
    """)

    def __init__(self, *, repositoryId: str, title: str, body: str):
        self._values = {
            "repositoryId": repositoryId,
            "title": title,
            "body": body,
        }

    def execute(self, client) -> CreateIssueResponse:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return CreateIssueResponse(
            id=result["op"]["issue"]["id"],
            url=result["op"]["issue"]["url"],
        )


class AddIssueComment:
    # https://docs.github.com/en/graphql/reference/mutations#addcomment
    QUERY = gql("""
    mutation ($subjectId: ID!, $body: String!) {
      op: addComment(input: {
        subjectId: $subjectId,
        body: $body,
      }) { commentEdge { node { id url } } }
    }
    """)

    def __init__(self, *, subjectId: str, body: str):
        self._values = {
            "subjectId": subjectId,
            "body": body,
        }

    def execute(self, client) -> AddIssueCommentResponse:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return AddIssueCommentResponse(
            id=result["op"]["commentEdge"]["node"]["id"],
            url=result["op"]["commentEdge"]["node"]["url"],
        )


@dataclass(frozen=True)
class IssueSearchHit:
    url: str
    body: str


class SearchIssuesByBody:
    # https://docs.github.com/en/graphql/reference/queries#search
    # 'first: 10' is a margin rather than an expected result count: an exact
    # match yields 0 or 1 hits, but search tokenizes URLs loosely, so inexact
    # hits can rank ahead of the exact one. Callers must verify the hits.
    QUERY = gql("""
    query ($query: String!) {
      search(query: $query, type: ISSUE, first: 10) {
        nodes {
          ... on Issue {
            url
            body
          }
        }
      }
    }
    """)

    def __init__(self, *, repos: list[str], text: str):
        # Quotes inside the text would break the phrase match.
        phrase = text.replace('"', " ")
        repo_qualifiers = " ".join(f"repo:{repo}" for repo in repos)
        self._values = {"query": f'{repo_qualifiers} is:issue in:body "{phrase}"'}

    def execute(self, client) -> list[IssueSearchHit]:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return [
            IssueSearchHit(url=node["url"], body=node["body"])
            for node in result["search"]["nodes"]
            if node
        ]
