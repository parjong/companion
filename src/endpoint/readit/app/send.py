import click
import os
import logging
import functools

from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step
from endpoint.readit.app.send_to_personal import send_to_personal
from endpoint.readit.app.send_to_queue_v2 import send_to_queue_v2

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


def safe_execute(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> dict:
        try:
            func(*args, **kwargs)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    return wrapper


safe_send_to_personal = safe_execute(send_to_personal)
safe_send_to_queue_v2 = safe_execute(send_to_queue_v2)


class SendStep(Step):
    """Pipeline step that sends the summary to the personal archive and queue v2."""

    def __init__(self, dry_run: bool):
        self._dry_run = dry_run

    def __call__(self, bb: Blackboard) -> Blackboard:
        res_personal = safe_send_to_personal(bb, dry_run=self._dry_run)
        logger.info("send_to_personal result: %s", res_personal)

        res_queue = safe_send_to_queue_v2(bb, dry_run=self._dry_run)
        logger.info("send_to_queue_v2 result: %s", res_queue)

        return bb


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
