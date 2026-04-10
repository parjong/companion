import click

from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

import json
from logging import getLogger
import os

from contextlib import ExitStack
from unittest.mock import patch

from endpoint.readit.core import Page

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


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

        self._handlers = {
            "arxiv": self.add_arXiv_article,
        }

    def add_article(self, page: Page):
        if self._add_known_article_if_possible(page):
            return

        try:
            self.add_other_article(page)
        except Exception as e:
            logger.error(f"Failed to add article with add_other_article: {e}")
            raise

    def _add_known_article_if_possible(self, page: Page) -> bool:
        handler = self._handlers.get(page.kind)
        if not handler:
            return False

        try:
            handler(page)
            return True
        except Exception as e:
            handler_name = getattr(handler, "__name__", str(handler))
            logger.error(f"Failed to add article with {handler_name}: {e}")
            logger.info("Falling back to add_other_article")
            return False

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
@click.option(
    "--dry-run/--no-dry-run",
    default=not os.environ.get("CI"),
    help="Default is True unless CI environment variable is set.",
)
@click.argument("summary_path")
def main(summary_path: str, dry_run: bool) -> None:
    import logging

    logging.basicConfig(level=logging.INFO)
    with open(summary_path, "r") as f:
        page = Page.fromdict(json.load(f))

    storage = PersonalStorage()

    with ExitStack() as stack:
        if dry_run:
            logger.info("--- DRY RUN MODE ENABLED (Side-effects suppressed) ---")
            stack.enter_context(
                patch.object(CreateDiscussion, "execute", mock_create_discussion_execute)
            )

        storage.add_article(page)

    logger.info("Done")
