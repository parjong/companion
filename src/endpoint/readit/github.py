from gql import gql
from typing import NewType
from logging import getLogger

logger = getLogger(__name__)

ProjectItemID = NewType("ProjectItemID", str)


class AddProjectV2DraftIssue:
    QUERY = gql("""
    mutation ($projectId: ID!, $title: String!, $body: String!) {
      op: addProjectV2DraftIssue(input: {
        projectId: $projectId,
        title: $title,
        body: $body,
      }) { item: projectItem { id } }
    }
    """)

    def __init__(self, *, projectId: str, title: str, body: str):
        self._values = {
            "projectId": projectId,
            "title": title,
            "body": body,
        }

    def execute(self, client) -> ProjectItemID:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return result["op"]["item"]["id"]


class UpdateTextFieldValue:
    QUERY = gql("""
    mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { text: $value }
      }) { item: projectV2Item { id } }
    }
    """)

    def __init__(
        self, *, projectId: str, itemId: ProjectItemID, fieldId: str, value: str
    ):
        self._values = {
            "projectId": projectId,
            "itemId": str(itemId),
            "fieldId": fieldId,
            "value": value,
        }

    def execute(self, client) -> None:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
