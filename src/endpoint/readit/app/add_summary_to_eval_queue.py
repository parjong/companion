import click
from gql import Client

from datetime import datetime
from datetime import timedelta
from datetime import timezone
import json
from logging import getLogger
import os

from endpoint.readit.core import Page
from endpoint.readit.github import ProjectItemID
from endpoint.readit.github import AddProjectV2DraftIssue
from endpoint.readit.github import UpdateTextFieldValue
from endpoint.readit.github import UpdateDateFieldValue

from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

logger = getLogger(__name__)


class EvalQueue:
    # This Project ID can be verified by running the following GitHub CLI command:
    # gh api graphql -f query='
    #   query { node(id: "PVT_kwHOAOPA3c4BSAfY") { ... on ProjectV2 { number title } } }
    # '
    PROJECT_ID = "PVT_kwHOAOPA3c4BSAfY"

    # Field IDs can be verified by running the following GitHub CLI command:
    # gh api graphql -f query='
    #   query { node(id: "FIELD_ID") { ... on ProjectV2Field { name project { ... on ProjectV2 { number } } } } }
    # '
    TITLE_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_qtdo"
    URL_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_quM8"
    ADDED_AT_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_subk"

    def __init__(self, client: Client):
        self._client = client

    def add(self, page: Page):
        item_id: ProjectItemID = AddProjectV2DraftIssue(
            projectId=self.PROJECT_ID, title=page.title, body=page.url_as_str()
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.TITLE_FIELD_ID,
            value=page.title,
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.URL_FIELD_ID,
            value=page.url_as_str(),
        ).execute(self._client)

        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst).strftime("%Y-%m-%d")

        UpdateDateFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.ADDED_AT_FIELD_ID,
            value=now_kst,
        ).execute(self._client)


@click.command()
@click.argument("summary_path")
def main(summary_path: str) -> None:
    logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

    github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]
    owner_token = os.environ["OWNER_TOKEN"]

    client = Client(
        transport=HTTPTransport(
            url=github_graphql_url,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    )

    with open(summary_path, "r") as f:
        page = Page.fromdict(json.load(f))

    logger.info("page = '%s'", page)

    queue = EvalQueue(client)

    queue.add(page)

    logger.info("Done")


if __name__ == "__main__":
    main()
