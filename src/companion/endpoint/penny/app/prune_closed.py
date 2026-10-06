import logging
import os
import click

from companion.connectors.github import ProjectNotFoundError
from companion.connectors.github import make_client
from companion.endpoint.penny.steps.prune import PruneClosedStep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


@click.command()
@click.option(
    "--dry-run/--no-dry-run",
    default=not os.environ.get("CI"),
    help="Default is True unless CI environment variable is set.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=0),
    default=None,
    help="Delete at most this many closed items. Default is no limit.",
)
def main(dry_run: bool, limit: int | None) -> None:
    # Pre-flight environment variables check
    missing_vars = [
        var for var in ["OWNER_TOKEN", "GITHUB_GRAPHQL_URL"] if not os.environ.get(var)
    ]
    if missing_vars:
        raise click.UsageError(
            f"Missing required environment variable(s): {', '.join(missing_vars)}. "
            "Please ensure they are defined in your environment."
        )

    client = make_client(
        url=os.environ["GITHUB_GRAPHQL_URL"], token=os.environ["OWNER_TOKEN"]
    )
    step = PruneClosedStep(
        client,
        limit=limit,
        dry_run=dry_run,
    )

    try:
        result = step()
    except ProjectNotFoundError as e:
        raise click.ClickException(str(e))

    if result.failed:
        raise click.ClickException(
            f"Failed to delete {len(result.failed)} item(s); "
            f"{len(result.deleted)} deleted."
        )

    if dry_run:
        logger.info("Dry run: would delete %d item(s).", len(result.skipped))
        return

    logger.info("Done. Deleted %d item(s).", len(result.deleted))


if __name__ == "__main__":
    main()
