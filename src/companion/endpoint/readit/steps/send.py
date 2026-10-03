import logging
import functools

from companion.endpoint.readit.core import Blackboard
from companion.endpoint.readit.core import Step
from companion.endpoint.readit.app.send_to_personal import send_to_personal

logger = logging.getLogger(__name__)


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


class SendStep(Step):
    """Pipeline step that sends the summary to the personal archive."""

    def __init__(self, dry_run: bool):
        self._dry_run = dry_run

    def __call__(self, bb: Blackboard) -> Blackboard:
        res_personal = safe_send_to_personal(bb, dry_run=self._dry_run)
        logger.info("send_to_personal result: %s", res_personal)

        return bb
