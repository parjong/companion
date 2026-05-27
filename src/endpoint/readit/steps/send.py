import logging
import functools

from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step
from endpoint.readit.app.send_to_personal import send_to_personal
from endpoint.readit.app.send_to_queue_v2 import send_to_queue_v2

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
