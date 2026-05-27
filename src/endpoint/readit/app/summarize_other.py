import json
from logging import getLogger
import os

import click

from endpoint.readit.steps.summarize import SummarizeStep
from endpoint.readit.steps.summarize import load_blackboard

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("input_path")
def main(output_path: str, input_path: str) -> None:
    logger.info("Summarize from '%s'", input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        bb = load_blackboard(f)

    summarize_step = SummarizeStep()
    bb = summarize_step(bb)

    logger.info("Result: '%s'", bb.model_dump(exclude={"html", "trafilatura"}))

    with open(output_path, "w") as f:
        json.dump(bb.model_dump(mode="json"), f, indent=4)

    logger.info("Check '%s'", output_path)


if __name__ == "__main__":
    main()
