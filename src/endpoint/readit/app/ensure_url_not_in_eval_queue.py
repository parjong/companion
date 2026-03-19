import click
from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from logging import getLogger
import os
import sys

from endpoint.readit.core import FetchResult
from endpoint.readit.github import ListProjectV2ItemFieldValues

logger = getLogger(__name__)


class EvalQueue:
    PROJECT_ID = "PVT_kwHOAOPA3c4BSAfY"
    URL_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_quM8"

    def __init__(self, client: Client):
        self._client = client

    def get_urls(self) -> list[str]:
        return ListProjectV2ItemFieldValues(
            projectId=self.PROJECT_ID, fieldId=self.URL_FIELD_ID
        ).execute(self._client)


@click.command()
@click.argument("fetch_result_path")
def main(fetch_result_path: str) -> None:
    logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

    github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]
    owner_token = os.environ["OWNER_TOKEN"]

    client = Client(
        transport=HTTPTransport(
            url=github_graphql_url,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    )

    with open(fetch_result_path, "r") as f:
        fetch_result = FetchResult.model_validate_json(f.read())

    url_to_check = str(fetch_result.url)
    logger.info("Checking URL: %s", url_to_check)

    queue = EvalQueue(client)
    urls_in_queue = queue.get_urls()

    if url_to_check in urls_in_queue:
        print("already in queue")
        sys.exit(1)

    print("not in queue")


if __name__ == "__main__":
    main()
