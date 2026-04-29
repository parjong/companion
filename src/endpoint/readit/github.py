from dataclasses import dataclass
from gql import gql
from typing import NewType
from logging import getLogger

logger = getLogger(__name__)

ProjectItemID = NewType("ProjectItemID", str)


class AddProjectV2DraftIssue:
    # https://docs.github.com/en/graphql/reference/mutations#addprojectv2draftissue
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


@dataclass(frozen=True)
class CreateIssueResponse:
    id: str
    url: str


@dataclass(frozen=True)
class AddIssueCommentResponse:
    id: str
    url: str


class CreateIssue:
    # https://docs.github.com/en/graphql/reference/mutations#createissue
    QUERY = gql("""
    mutation ($repositoryId: ID!, $title: String!, $body: String!) {
      op: createIssue(input: {
        repositoryId: $repositoryId,
        title: $title,
        body: $body,
      }) { issue { id url } }
    }
    """)

    def __init__(self, *, repositoryId: str, title: str, body: str):
        self._values = {
            "repositoryId": repositoryId,
            "title": title,
            "body": body,
        }

    def execute(self, client) -> CreateIssueResponse:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return CreateIssueResponse(
            id=result["op"]["issue"]["id"],
            url=result["op"]["issue"]["url"],
        )


class AddIssueComment:
    # https://docs.github.com/en/graphql/reference/mutations#addcomment
    QUERY = gql("""
    mutation ($subjectId: ID!, $body: String!) {
      op: addComment(input: {
        subjectId: $subjectId,
        body: $body,
      }) { commentEdge { node { id url } } }
    }
    """)

    def __init__(self, *, subjectId: str, body: str):
        self._values = {
            "subjectId": subjectId,
            "body": body,
        }

    def execute(self, client) -> AddIssueCommentResponse:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return AddIssueCommentResponse(
            id=result["op"]["commentEdge"]["node"]["id"],
            url=result["op"]["commentEdge"]["node"]["url"],
        )


class UpdateTextFieldValue:
    # https://docs.github.com/en/graphql/reference/mutations#updateprojectv2itemfieldvalue
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


class ListProjectV2ItemFieldValues:
    # https://docs.github.com/en/graphql/reference/objects#projectv2itemfieldvalueconnection
    QUERY = gql("""
    query ($projectId: ID!, $after: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    field {
                      ... on ProjectV2FieldCommon {
                        id
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """)

    def __init__(self, *, projectId: str, fieldId: str):
        self._projectId = projectId
        self._fieldId = fieldId

    def execute(self, client) -> list[str]:
        values = []
        after = None
        has_next_page = True

        while has_next_page:
            result = client.execute(
                self.QUERY,
                variable_values={
                    "projectId": self._projectId,
                    "after": after,
                },
            )
            items_data = result["node"]["items"]
            for item in items_data["nodes"]:
                for field_value in item["fieldValues"]["nodes"]:
                    if not field_value:
                        continue
                    if field_value.get("field", {}).get("id") == self._fieldId:
                        text = field_value.get("text")
                        if text is not None:
                            values.append(text)

            page_info = items_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            after = page_info["endCursor"]

        return values


class UpdateDateFieldValue:
    # https://docs.github.com/en/graphql/reference/mutations#updateprojectv2itemfieldvalue
    QUERY = gql("""
    mutation ($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: Date!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { date: $value }
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


class AddProjectV2ItemById:
    # https://docs.github.com/en/graphql/reference/mutations#addprojectv2itembyid
    QUERY = gql("""
    mutation ($projectId: ID!, $contentId: ID!) {
      op: addProjectV2ItemById(input: {
        projectId: $projectId,
        contentId: $contentId,
      }) { item { id } }
    }
    """)

    def __init__(self, *, projectId: str, contentId: str):
        self._values = {
            "projectId": projectId,
            "contentId": contentId,
        }

    def execute(self, client) -> ProjectItemID:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        return ProjectItemID(result["op"]["item"]["id"])
