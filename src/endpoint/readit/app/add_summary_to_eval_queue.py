import click
from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from logging import getLogger
import os

from endpoint.readit.core import Blackboard
from endpoint.readit.steps.add_queue import AddQueueStep

logger = getLogger(__name__)


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
        bb = Blackboard.from_pipeline_file(f)

    logger.info("blackboard = '%s'", bb)

    add_queue_step = AddQueueStep(client)
    add_queue_step(bb)

    logger.info("Done")


if __name__ == "__main__":
    main()
