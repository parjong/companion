import click

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

import json
from logging import getLogger
import os

from endpoint.readit.core import Page


logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


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


class PersonalStorage:
    REPOSITORY_ID = "MDEwOlJlcG9zaXRvcnk4NTc2NDg5Mw=="

    def __init__(self):
        github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]

        owner_token = os.environ["OWNER_TOKEN"]

        self._client = Client(
            transport=HTTPTransport(
                url=github_graphql_url,
                headers={"Authorization": f"Bearer {owner_token}"},
            )
        )

    def add_arXiv_article(self, page: Page):
        summary = page.metadata.get("summary", "")
        lines = [page.url_as_str(), "", f"> {summary}"]

        year = page.metadata.get("year", "????")
        title = f"[{year}] {page.title}"
        body = "\n".join(lines)

        CreateDiscussion(
            repositoryId=self.REPOSITORY_ID,
            categoryId="DIC_kwDOBRyrHc4Cz64i",
            title=title,
            body=body,
        ).execute(self._client)

    def add_other_article(self, page: Page):
        title = f"[{page.date}] {page.title}"
        body = page.url_as_str()

        CreateDiscussion(
            repositoryId=self.REPOSITORY_ID,
            categoryId="DIC_kwDOBRyrHc4Cz61s",
            title=title,
            body=body,
        ).execute(self._client)


@click.command()
@click.argument("summary_path")
def main(summary_path: str) -> None:
    with open(summary_path, "r") as f:
        page = Page.fromdict(json.load(f))

    storage = PersonalStorage()

    if page.kind == "arxiv":
        storage.add_arXiv_article(page)
    else:
        storage.add_other_article(page)

    logger.info("Done")
