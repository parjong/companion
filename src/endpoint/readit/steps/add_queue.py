from datetime import datetime
from datetime import timedelta
from datetime import timezone
from logging import getLogger

from gql import Client

from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step
from endpoint.readit.github import ProjectItemID
from endpoint.readit.github import AddProjectV2DraftIssue
from endpoint.readit.github import UpdateTextFieldValue
from endpoint.readit.github import UpdateDateFieldValue

logger = getLogger(__name__)


class EvalQueue:
    # This Project ID can be verified by running the following GitHub CLI command:
    # gh api graphql -f query='
    #   query { node(id: "PVT_kwHOAOPA3c4BSAfY") { ... on ProjectV2 { number title } } }
    # '
    PROJECT_ID = "PVT_kwHOAOPA3c4BSAfY"

    # Field IDs can be verified by running the following GitHub CLI command:
    # gh api graphql -f query='
    #   query { node(id: "FIELD_ID") { ... on ProjectV2Field { name project { ... on ProjectV2 { number } } } } }
    # '
    TITLE_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_qtdo"
    URL_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_quM8"
    ADDED_AT_FIELD_ID = "PVTF_lAHOAOPA3c4BSAfYzg_subk"

    def __init__(self, client: Client):
        self._client = client

    def add(self, bb: Blackboard):
        item_id: ProjectItemID = AddProjectV2DraftIssue(
            projectId=self.PROJECT_ID, title=bb.title, body=bb.url_as_str()
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.TITLE_FIELD_ID,
            value=bb.title,
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.URL_FIELD_ID,
            value=bb.url_as_str(),
        ).execute(self._client)

        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst).strftime("%Y-%m-%d")

        UpdateDateFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.ADDED_AT_FIELD_ID,
            value=now_kst,
        ).execute(self._client)


class AddQueueStep(Step):
    """Pipeline step that adds the Blackboard summary into the GitHub Project evaluation queue."""

    def __init__(self, client: Client):
        self._client = client

    def __call__(self, bb: Blackboard) -> Blackboard:
        queue = EvalQueue(self._client)
        queue.add(bb)
        return bb
