from logging import getLogger
from gql import Client

from companion.endpoint.readit.core import Blackboard
from companion.endpoint.readit.core import Step
from companion.endpoint.readit.github import ListProjectV2ItemFieldValues
from companion.endpoint.readit.github import SearchIssuesByBody

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


class PersonalArchive:
    REPOS = ["parjong/readit-others", "parjong/readit-papers"]

    def __init__(self, client: Client):
        self._client = client

    def find_issue_urls(self, url: str) -> list[str]:
        """Returns the URLs of archived issues whose body contains `url`."""
        hits = SearchIssuesByBody(repos=self.REPOS, text=url).execute(self._client)
        # Search tokenizes URLs loosely, so confirm the exact URL is in the body.
        return [hit.url for hit in hits if url in hit.body.split()]


class AlreadyArchivedError(Exception):
    """Raised when the URL has already been registered in the personal archive."""

    pass


class EnsureNotArchivedStep(Step):
    """Pipeline step that checks if the URL was registered in the personal archive before.

    Complements EnsureStep: the evaluation queue only remembers recent URLs,
    while the archive issues keep every registered URL.
    """

    def __init__(self, client: Client):
        self._client = client

    def __call__(self, bb: Blackboard) -> Blackboard:
        """
        Raises:
            AlreadyArchivedError: If an archived issue already contains the URL.
        """
        url_to_check = str(bb.url)
        logger.info("Checking archive for URL: %s", url_to_check)

        issue_urls = PersonalArchive(self._client).find_issue_urls(url_to_check)
        if issue_urls:
            raise AlreadyArchivedError(
                f"URL '{url_to_check}' is already archived: {', '.join(issue_urls)}"
            )

        return bb
