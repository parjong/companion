from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from logging import getLogger
import os
from urllib.parse import urlparse

from contextlib import ExitStack
from unittest.mock import patch

from endpoint.readit.core import Blackboard
from endpoint.readit.github import AddProjectV2DraftIssue
from endpoint.readit.github import AddProjectV2ItemById
from endpoint.readit.github import ProjectItemID
from endpoint.readit.github import UpdateTextFieldValue

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


def mock_add_project_v2_execute(self, client) -> ProjectItemID:
    title = self._values["title"]
    logger.info(f"  [Dry Run] Would add Project V2 Draft Issue: '{title}'")
    return ProjectItemID("DUMMY_ITEM_ID")


def mock_add_project_v2_item_execute(self, client) -> ProjectItemID:
    logger.info("  [Dry Run] Would add Issue to Project V2")
    return ProjectItemID("DUMMY_ITEM_ID")


def mock_update_text_field_execute(self, client) -> None:
    field_id = self._values["fieldId"]
    value = self._values["value"]
    logger.info(f"  [Dry Run] Would update field '{field_id}' with value: '{value}'")


class Queue:
    # Projects
    # arXiv: readit (No. 7)
    ARXIV_PROJECT_ID = "PVT_kwHOAOPA3c4BVeSc"

    ARXIV_ID_FIELD_ID = "PVTF_lAHOAOPA3c4BVeSczhRdyvc"
    ARXIV_ABSTRACT_FIELD_ID = "PVTF_lAHOAOPA3c4BVeSczhRdywU"
    ARXIV_YEAR_FIELD_ID = "PVTF_lAHOAOPA3c4BVeSczhRdyxM"

    # readit: other (No. 8)
    OTHER_PROJECT_ID = "PVT_kwHOAOPA3c4BWG6Z"

    OTHER_ISSUE_DATE_FIELD_ID = "PVTF_lAHOAOPA3c4BWG6ZzhRdy20"
    OTHER_KEY_SENTENCES_URL_FIELD_ID = "PVTF_lAHOAOPA3c4BWG6ZzhRdy4E"
    OTHER_URL_FIELD_ID = "PVTF_lAHOAOPA3c4BWG6ZzhReQy0"

    def __init__(self):
        github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]

        owner_token = os.environ["OWNER_TOKEN"]

        self._client = Client(
            transport=HTTPTransport(
                url=github_graphql_url,
                headers={"Authorization": f"Bearer {owner_token}"},
            )
        )

    def add(self, bb: Blackboard):
        handlers = {
            "arxiv": self._add_arxiv,
            "other": self._add_other,
        }
        handler = handlers.get(bb.kind)

        if not handler:
            raise ValueError(f"Unknown document kind: {bb.kind}")

        handler(bb)

    def _add_other(self, bb: Blackboard):
        date = bb.date if bb.date else "????/??/??"
        title = f"[{date}] {bb.title}"
        body = bb.url_as_str()

        # Reuse existing issue if already created by personal archive, fallback to Draft Issue
        issue_id = bb.personal_archive.issue_id
        if issue_id:
            item_id = AddProjectV2ItemById(
                projectId=self.OTHER_PROJECT_ID, contentId=issue_id
            ).execute(self._client)
        else:
            item_id = AddProjectV2DraftIssue(
                projectId=self.OTHER_PROJECT_ID, title=title, body=body
            ).execute(self._client)

        # 3. Update Fields
        UpdateTextFieldValue(
            projectId=self.OTHER_PROJECT_ID,
            itemId=item_id,
            fieldId=self.OTHER_URL_FIELD_ID,
            value=bb.url_as_str(),
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.OTHER_PROJECT_ID,
            itemId=item_id,
            fieldId=self.OTHER_ISSUE_DATE_FIELD_ID,
            value=date,
        ).execute(self._client)

        # Use comment_url (where key sentences are) if available
        summary_url = bb.personal_archive.comment_url
        if summary_url:
            UpdateTextFieldValue(
                projectId=self.OTHER_PROJECT_ID,
                itemId=item_id,
                fieldId=self.OTHER_KEY_SENTENCES_URL_FIELD_ID,
                value=str(summary_url),
            ).execute(self._client)

    def _add_arxiv(self, bb: Blackboard):
        # TODO: Move arxiv_id extraction to Blackboard model or fetcher in the future
        parsed_url = urlparse(bb.url_as_str())
        arxiv_id = parsed_url.path.split("/")[-1]

        summary = bb.arxiv.summary if bb.arxiv else ""
        lines = [bb.url_as_str(), "", f"> {summary}"]

        year = bb.arxiv.year if bb.arxiv else "????"
        title = f"[{year}] {bb.title}"
        body = "\n".join(lines)

        # Reuse existing issue if already created by personal archive, fallback to Draft Issue
        issue_id = bb.personal_archive.issue_id
        if issue_id:
            item_id = AddProjectV2ItemById(
                projectId=self.ARXIV_PROJECT_ID, contentId=issue_id
            ).execute(self._client)
        else:
            item_id = AddProjectV2DraftIssue(
                projectId=self.ARXIV_PROJECT_ID, title=title, body=body
            ).execute(self._client)

        # 3. Update Fields
        UpdateTextFieldValue(
            projectId=self.ARXIV_PROJECT_ID,
            itemId=item_id,
            fieldId=self.ARXIV_ID_FIELD_ID,
            value=arxiv_id,
        ).execute(self._client)

        # TODO Pass "Abstract" via "Comment"

        UpdateTextFieldValue(
            projectId=self.ARXIV_PROJECT_ID,
            itemId=item_id,
            fieldId=self.ARXIV_YEAR_FIELD_ID,
            value=year,
        ).execute(self._client)


def send_to_queue_v2(bb: Blackboard, dry_run: bool) -> None:
    queue = Queue()

    with ExitStack() as stack:
        if dry_run:
            logger.info("--- DRY RUN MODE ENABLED (Side-effects suppressed) ---")
            stack.enter_context(
                patch.object(
                    AddProjectV2DraftIssue, "execute", mock_add_project_v2_execute
                )
            )
            stack.enter_context(
                patch.object(
                    UpdateTextFieldValue, "execute", mock_update_text_field_execute
                )
            )
            stack.enter_context(
                patch(
                    "endpoint.readit.github.AddProjectV2ItemById.execute",
                    mock_add_project_v2_item_execute,
                )
            )

        queue.add(bb)

    logger.info("Done")
