import os
from logging import getLogger

import click

from endpoint.readit.core import Blackboard
from endpoint.readit.steps.fetch import FetchStep

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("url")
def main(output_path: str, url: str) -> None:
    bb = Blackboard(url=url)
    fetch_step = FetchStep()
    bb = fetch_step(bb)

    # Write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bb.model_dump_json(indent=2))

    logger.info("Saved raw data to '%s'", output_path)


if __name__ == "__main__":
    main()
