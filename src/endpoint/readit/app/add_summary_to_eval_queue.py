import click
from gql import Client

import json
from logging import getLogger
import os

from endpoint.readit.core import Page
from endpoint.readit.github import ProjectItemID
from endpoint.readit.github import AddProjectV2DraftIssue
from endpoint.readit.github import UpdateTextFieldValue

from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


class EvalQueue:
    PROJECT_ID = "PVT_kwHOAOPA3c4BSAfY"

    TITLE_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_qtdo"
    URL_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_quM8"

    def __init__(self):
        github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]

        owner_token = os.environ["OWNER_TOKEN"]

        self._client = Client(
            transport=HTTPTransport(
                url=github_graphql_url,
                headers={"Authorization": f"Bearer {owner_token}"},
            )
        )

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


@click.command()
@click.argument("summary_path")
def main(summary_path: str) -> None:
    with open(summary_path, "r") as f:
        page = Page.fromdict(json.load(f))

    logger.info("page = '%s'", page)

    queue = EvalQueue()

    queue.add(page)

    logger.info("Done")


if __name__ == "__main__":
    main()
