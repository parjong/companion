from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from logging import getLogger
import os

from contextlib import ExitStack
from unittest.mock import patch

from endpoint.readit.core import Blackboard
from endpoint.readit.github import CreateIssue
from endpoint.readit.github import CreateIssueResponse
from endpoint.readit.github import AddIssueComment
from endpoint.readit.github import AddIssueCommentResponse

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


class AlreadyInArchiveError(Exception):
    """Raised when the URL is already present in the personal issue archive."""

    pass


class GetRepositoryNameWithOwner:
    QUERY = gql("""
    query ($repositoryId: ID!) {
      node(id: $repositoryId) {
        ... on Repository {
          nameWithOwner
        }
      }
    }
    """)

    def __init__(self, *, repositoryId: str):
        self._values = {"repositoryId": repositoryId}

    def execute(self, client) -> str:
        result = client.execute(self.QUERY, variable_values=self._values)
        node = result.get("node")
        if not node:
            raise ValueError(
                f"Repository with ID '{self._values['repositoryId']}' not found."
            )
        return node["nameWithOwner"]


class SearchIssuesByUrl:
    QUERY = gql("""
    query ($query: String!) {
      search(query: $query, type: ISSUE, first: 1) {
        issueCount
      }
    }
    """)

    def __init__(self, *, query: str):
        self._values = {"query": query}

    def execute(self, client) -> int:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return result.get("search", {}).get("issueCount", 0)


def mock_create_issue_execute(self, client) -> CreateIssueResponse:
    title = self._values["title"]
    logger.info(f"  [Dry Run] Would create Issue: '{title}'")
    return CreateIssueResponse(
        id="DUMMY_ISSUE_ID", url="https://github.com/dummy/issue/1"
    )


def mock_add_issue_comment_execute(self, client) -> AddIssueCommentResponse:
    logger.info("  [Dry Run] Would add Issue Comment")
    return AddIssueCommentResponse(
        id="DUMMY_COMMENT_ID", url="https://github.com/dummy/issue/1#issuecomment-1"
    )


def mock_create_discussion_execute(self, client) -> None:
    title = self._values["title"]
    logger.info(f"  [Dry Run] Would create Discussion: '{title}'")


class CreateDiscussion:
    QUERY = gql("""
    mutation ($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {
          repositoryId: $repositoryId,
          categoryId: $categoryId,
          title: $title,
          body: $body
      }) { discussion { id } }
    }
    """)

    def __init__(self, *, repositoryId: str, categoryId: str, title: str, body: str):
        self._values = {
            "repositoryId": repositoryId,
            "categoryId": categoryId,
            "title": title,
            "body": body,
        }

    def execute(self, client):
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        pass


# TODO: Consider renaming this class to ReviewIssueStorage or similar in the future.
class PersonalStorage:
    # Repository IDs for separation
    PAPERS_REPO_ID = "R_kgDOSCdIzw"  # readit-papers
    OTHERS_REPO_ID = "R_kgDOSCdKKw"  # readit-others

    def __init__(self):
        github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]

        owner_token = os.environ["OWNER_TOKEN"]

        self._client = Client(
            transport=HTTPTransport(
                url=github_graphql_url,
                headers={"Authorization": f"Bearer {owner_token}"},
            )
        )

        self._handlers = {
            "arxiv": self.add_arXiv_article,
        }

    _papers_repo_name: str | None = None
    _others_repo_name: str | None = None

    def has_article(self, url: str) -> bool:
        if not PersonalStorage._papers_repo_name:
            PersonalStorage._papers_repo_name = GetRepositoryNameWithOwner(
                repositoryId=self.PAPERS_REPO_ID
            ).execute(self._client)
        if not PersonalStorage._others_repo_name:
            PersonalStorage._others_repo_name = GetRepositoryNameWithOwner(
                repositoryId=self.OTHERS_REPO_ID
            ).execute(self._client)

        papers_repo = PersonalStorage._papers_repo_name
        others_repo = PersonalStorage._others_repo_name

        search_query = f'repo:{papers_repo} repo:{others_repo} "{url}"'
        count = SearchIssuesByUrl(query=search_query).execute(self._client)
        return count > 0

    def add_article(self, bb: Blackboard):
        if self.has_article(bb.url_as_str()):
            raise AlreadyInArchiveError(
                f"URL '{bb.url_as_str()}' is already in the personal archive."
            )

        if self._add_known_article_if_possible(bb):
            return

        try:
            self.add_other_article(bb)
        except Exception as e:
            logger.error(f"Failed to add article with add_other_article: {e}")
            raise

    def _add_known_article_if_possible(self, bb: Blackboard) -> bool:
        handler = self._handlers.get(bb.kind)
        if not handler:
            return False

        try:
            handler(bb)
            return True
        except Exception as e:
            handler_name = getattr(handler, "__name__", str(handler))
            logger.error(f"Failed to add article with {handler_name}: {e}")
            logger.info("Falling back to add_other_article")
            return False

    def add_arXiv_article(self, bb: Blackboard):
        # Validation ensures bb.arxiv is not None if kind is 'arxiv'
        summary = bb.arxiv.summary if bb.arxiv else ""
        lines = [bb.url_as_str(), "", f"> {summary}"]

        year = bb.arxiv.year if bb.arxiv else "????"
        title = f"[{year}] {bb.title}"
        body = "\n".join(lines)

        issue_resp = CreateIssue(
            repositoryId=self.PAPERS_REPO_ID,
            title=title,
            body=body,
        ).execute(self._client)
        bb.personal_archive.issue_oid = issue_resp.id
        bb.personal_archive.issue_url = issue_resp.url

    def add_other_article(self, bb: Blackboard):
        title = f"[{bb.date}] {bb.title}"
        body = bb.url_as_str()

        issue_resp = CreateIssue(
            repositoryId=self.OTHERS_REPO_ID,
            title=title,
            body=body,
        ).execute(self._client)

        issue_oid = issue_resp.id
        bb.personal_archive.issue_oid = issue_oid
        bb.personal_archive.issue_url = issue_resp.url

        # Add key sentences as a comment if available
        key_sentences = bb.other.key_sentences if bb.other else []
        if key_sentences:
            comment_body = "\n".join([f"- {s}" for s in key_sentences])
            comment_resp = AddIssueComment(
                subjectId=issue_oid,
                body=comment_body,
            ).execute(self._client)
            bb.personal_archive.comment_oid = comment_resp.id
            bb.personal_archive.comment_url = comment_resp.url


def send_to_personal(bb: Blackboard, dry_run: bool) -> None:
    storage = PersonalStorage()

    with ExitStack() as stack:
        if dry_run:
            logger.info("--- DRY RUN MODE ENABLED (Side-effects suppressed) ---")
            stack.enter_context(
                patch.object(CreateIssue, "execute", mock_create_issue_execute)
            )
            stack.enter_context(
                patch.object(AddIssueComment, "execute", mock_add_issue_comment_execute)
            )
            stack.enter_context(
                patch.object(
                    CreateDiscussion, "execute", mock_create_discussion_execute
                )
            )

        storage.add_article(bb)

    logger.info("Done")
