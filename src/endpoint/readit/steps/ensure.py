from logging import getLogger
from gql import Client

from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step
from endpoint.readit.github import ListProjectV2ItemFieldValues

logger = getLogger(__name__)


class EvalQueue:
    PROJECT_ID = "PVT_kwHOAOPA3c4BSAfY"
    URL_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_quM8"

    def __init__(self, client: Client):
        self._client = client

    def get_urls(self) -> list[str]:
        return ListProjectV2ItemFieldValues(
            projectId=self.PROJECT_ID, fieldId=self.URL_FIELD_ID
        ).execute(self._client)


class AlreadyInQueueError(Exception):
    """Raised when the URL is already present in the evaluation queue."""

    pass


class EnsureStep(Step):
    """Pipeline step that checks if the URL is already present in the evaluation queue."""

    def __init__(self, client: Client):
        self._client = client

    def __call__(self, bb: Blackboard) -> Blackboard:
        """Pipeline step that checks if the URL is already present in the evaluation queue.

        Args:
            bb: The current blackboard state containing the URL to check.

        Returns:
            The unmodified Blackboard state if the URL is not in the queue.

        Raises:
            AlreadyInQueueError: If the URL is already present in the queue.
        """
        url_to_check = str(bb.url)
        logger.info("Checking URL: %s", url_to_check)

        queue = EvalQueue(self._client)
        urls_in_queue = queue.get_urls()

        if url_to_check in urls_in_queue:
            raise AlreadyInQueueError(
                f"URL '{url_to_check}' is already in the evaluation queue."
            )

        return bb
