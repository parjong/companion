from logging import getLogger
from gql import Client

from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step
from endpoint.readit.github import ListProjectV2ItemFieldValues
from endpoint.readit.app.send_to_personal import PersonalStorage
from endpoint.readit.app.send_to_personal import AlreadyInArchiveError

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


# TODO: Consider relocating domain exceptions (e.g. AlreadyInQueueError, AlreadyInArchiveError)
# to a dedicated common exceptions module (e.g. exn.py or exceptions.py) in the future
# to prevent potential circular dependencies and keep core modules clean.
class AlreadyInQueueError(Exception):
    """Raised when the URL is already present in the evaluation queue."""

    pass


class EnsureStep(Step):
    """Pipeline step that checks if the URL is already present in the evaluation queue or personal archive."""

    def __init__(self, client: Client):
        self._client = client

    def __call__(self, bb: Blackboard) -> Blackboard:
        """Pipeline step that checks if the URL is already present in the evaluation queue or personal archive.

        Args:
            bb: The current blackboard state containing the URL to check.

        Returns:
            The unmodified Blackboard state if the URL is not in the queue or archive.

        Raises:
            AlreadyInQueueError: If the URL is already present in the queue.
            AlreadyInArchiveError: If the URL is already present in the personal archive.
        """
        url_to_check = str(bb.url)
        logger.info("Checking URL: %s", url_to_check)

        # 1. 단기 체크: 평가 대기열에 있는지 확인
        queue = EvalQueue(self._client)
        urls_in_queue = queue.get_urls()

        if url_to_check in urls_in_queue:
            raise AlreadyInQueueError(
                f"URL '{url_to_check}' is already in the evaluation queue."
            )

        # 2. 장기 체크: 개인 아카이브(Issues)에 이미 등록되었는지 선제 검증 (비용 최적화)
        storage = PersonalStorage()
        if storage.has_article(url_to_check):
            raise AlreadyInArchiveError(
                f"URL '{url_to_check}' is already in the personal archive."
            )

        return bb
