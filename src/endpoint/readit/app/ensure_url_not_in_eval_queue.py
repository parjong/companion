import click
from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from logging import getLogger
import os
import sys

from endpoint.readit.core import Blackboard
from endpoint.readit.steps.ensure import EnsureStep
from endpoint.readit.steps.ensure import AlreadyInQueueError

logger = getLogger(__name__)


@click.command()
@click.argument("input_path")
def main(input_path: str) -> None:
    logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

    github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]
    owner_token = os.environ["OWNER_TOKEN"]

    client = Client(
        transport=HTTPTransport(
            url=github_graphql_url,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    )

    with open(input_path, "r") as f:
        bb = Blackboard.from_pipeline_file(f)

    ensure_step = EnsureStep(client)
    try:
        ensure_step(bb)
    except AlreadyInQueueError:
        print("already in queue")
        sys.exit(1)

    print("not in queue")


if __name__ == "__main__":
    main()
