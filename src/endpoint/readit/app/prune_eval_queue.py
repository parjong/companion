import logging
import os

import click
from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport

from endpoint.readit.steps.prune import PruneQueueStep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("endpoint").setLevel(
    os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper()
)


@click.command()
@click.option(
    "--max-age-days",
    type=click.IntRange(min=0),
    default=30,
    show_default=True,
    help="Remove items added more than this many days ago.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum number of items to remove in a single run (oldest first).",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=not os.environ.get("CI"),
    help="Default is True unless CI environment variable is set.",
)
def main(max_age_days: int, limit: int, dry_run: bool) -> None:
    github_graphql_url = os.environ["GITHUB_GRAPHQL_URL"]
    owner_token = os.environ["OWNER_TOKEN"]

    client = Client(
        transport=HTTPTransport(
            url=github_graphql_url,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    )

    step = PruneQueueStep(client, max_age_days=max_age_days, limit=limit)
    count = step(dry_run=dry_run)

    logger.info("Done (%s %d items)", "would remove" if dry_run else "removed", count)


if __name__ == "__main__":
    main()
