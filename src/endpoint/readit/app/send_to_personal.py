from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from logging import getLogger
import os

from contextlib import ExitStack
from unittest.mock import patch

from endpoint.readit.core import Blackboard
from endpoint.readit.github import CreateIssue
from endpoint.readit.github import AddIssueComment

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


def mock_create_issue_execute(self, client) -> str:
    title = self._values["title"]
    logger.info(f"  [Dry Run] Would create Issue: '{title}'")
    return "DUMMY_ISSUE_ID"


def mock_add_issue_comment_execute(self, client) -> str:
    logger.info("  [Dry Run] Would add Issue Comment")
    return "DUMMY_COMMENT_ID"


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

    def add_article(self, bb: Blackboard):
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

        CreateIssue(
            repositoryId=self.PAPERS_REPO_ID,
            title=title,
            body=body,
        ).execute(self._client)

    def add_other_article(self, bb: Blackboard):
        title = f"[{bb.date}] {bb.title}"
        body = bb.url_as_str()

        issue_id = CreateIssue(
            repositoryId=self.OTHERS_REPO_ID,
            title=title,
            body=body,
        ).execute(self._client)

        # Add key sentences as a comment if available
        key_sentences = bb.other.key_sentences if bb.other else []
        if key_sentences:
            comment_body = "\n".join([f"- {s}" for s in key_sentences])
            AddIssueComment(
                subjectId=issue_id,
                body=comment_body,
            ).execute(self._client)


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
