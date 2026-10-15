from datetime import datetime
from datetime import timedelta
from datetime import timezone

from gql import Client

from companion.connectors.github.project import AddProjectV2DraftIssue
from companion.connectors.github.project import DeleteProjectV2Item
from companion.connectors.github.project import ListProjectV2ItemDateValues
from companion.connectors.github.project import ListProjectV2ItemFieldValues
from companion.connectors.github.project import ProjectItemDate
from companion.connectors.github.project import ProjectItemID
from companion.connectors.github.project import UpdateDateFieldValue
from companion.connectors.github.project import UpdateTextFieldValue


class EvalQueue:
    """The evaluation queue, backed by a GitHub Project.

    Steps declare the part of the queue they need as a Protocol; this class is the one
    implementation that the apps bind to them.
    """

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

    def get_urls(self) -> list[str]:
        return ListProjectV2ItemFieldValues(
            projectId=self.PROJECT_ID, fieldId=self.URL_FIELD_ID
        ).execute(self._client)

    def add(self, *, title: str, url: str) -> None:
        item_id: ProjectItemID = AddProjectV2DraftIssue(
            projectId=self.PROJECT_ID, title=title, body=url
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.TITLE_FIELD_ID,
            value=title,
        ).execute(self._client)

        UpdateTextFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.URL_FIELD_ID,
            value=url,
        ).execute(self._client)

        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst).strftime("%Y-%m-%d")

        UpdateDateFieldValue(
            projectId=self.PROJECT_ID,
            itemId=item_id,
            fieldId=self.ADDED_AT_FIELD_ID,
            value=now_kst,
        ).execute(self._client)

    def list_items(self) -> list[ProjectItemDate]:
        return ListProjectV2ItemDateValues(
            projectId=self.PROJECT_ID, fieldId=self.ADDED_AT_FIELD_ID
        ).execute(self._client)

    def remove(self, item: ProjectItemDate) -> None:
        DeleteProjectV2Item(projectId=self.PROJECT_ID, itemId=item.id).execute(
            self._client
        )
