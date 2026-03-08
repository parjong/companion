import json
from logging import getLogger
import os

import click

from endpoint.readit.core import page_of_


logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("url")
def main(output_path: str, url: str) -> None:
    logger.info("Summarize '%s'", url)

    page = page_of_(url).asdict()

    logger.info("Result: '%s'", page)

    with open(output_path, "w") as f:
        json.dump(page, f, indent=4)

    logger.info("Check '%s'", output_path)
