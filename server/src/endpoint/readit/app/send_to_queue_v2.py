import click

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

import json
from logging import getLogger
import os
from typing import NewType

from endpoint.readit.core import Page


logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

ProjectItemID = NewType("ProjectItemID", str)


class AddProjectV2DraftIssue:
    QUERY = gql("""
    mutation ($projectId: ID!, $title: String!, $body: String!) {
      op: addProjectV2DraftIssue(input: {
        projectId: $projectId,
        title: $title,
        body: $body,
      }) { item: projectItem { id } }
    }
    """)

    def __init__(self, *, projectId: str, title: str, body: str):
        self._values = {
            "projectId": projectId,
            "title": title,
            "body": body,
        }

    def execute(self, client) -> ProjectItemID:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return result["op"]["item"]["id"]


class UpdateTextFieldValue:
    QUERY = gql("""
    mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { text: $value }
      }) { item: projectV2Item { id } }
    }
    """)

    def __init__(
        self, *, projectId: str, itemId: ProjectItemID, fieldId: str, value: str
    ):
        self._values = {
            "projectId": projectId,
            "itemId": str(itemId),
            "fieldId": fieldId,
            "value": value,
        }

    def execute(self, client) -> ProjectItemID:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        pass


class Queue:
    PROJECT_ID = "PVT_kwHOAOPA3c4BNgtr"

    URL_FIELD_ID = "PVTF_lAHOAOPA3c4BNgtrzg9Ovbk"
    ISSUE_DATE_FIELD_ID = "PVTF_lAHOAOPA3c4BNgtrzg9OvdE"

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
            fieldId=self.URL_FIELD_ID,
            value=page.url_as_str(),
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.ISSUE_DATE_FIELD_ID,
            value=page.date,
        ).execute(self._client)


@click.command()
@click.argument("summary_path")
def main(summary_path: str) -> None:
    with open(summary_path, "r") as f:
        page = Page.fromdict(json.load(f))

    logger.info("page = '%s'", page)

    queue = Queue()

    queue.add(page)

    logger.info("Done")
