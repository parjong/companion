import click
import os
import logging

from endpoint.readit.core import Blackboard
from endpoint.readit.steps.send import SendStep

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--dry-run/--no-dry-run",
    default=not os.environ.get("CI"),
    help="Default is True unless CI environment variable is set.",
)
@click.argument("summary_path")
def main(summary_path: str, dry_run: bool) -> None:
    logging.basicConfig(level=logging.INFO)

    bb = Blackboard.from_pipeline_file(summary_path)

    logger.info("Blackboard = '%s'", bb)

    send_step = SendStep(dry_run=dry_run)
    send_step(bb)

    logger.info("Done")


if __name__ == "__main__":
    main()
