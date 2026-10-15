from dataclasses import dataclass
from enum import StrEnum
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


class _TolerantStrEnum(StrEnum):
    """A string enum that maps values GitHub adds later to UNKNOWN instead of failing."""

    @classmethod
    def _missing_(cls, value):
        logger.warning("Unknown %s value: %r", cls.__name__, value)
        return cls["UNKNOWN"]


class ProjectItemKind(_TolerantStrEnum):
    # https://docs.github.com/en/graphql/reference/unions#projectv2itemcontent
    ISSUE = "Issue"
    PULL_REQUEST = "PullRequest"
    DRAFT_ISSUE = "DraftIssue"
    # GitHub returns no content for items the token cannot read.
    REDACTED = "Redacted"
    UNKNOWN = "Unknown"


class ProjectItemState(_TolerantStrEnum):
    # https://docs.github.com/en/graphql/reference/enums#issuestate
    # https://docs.github.com/en/graphql/reference/enums#pullrequeststate
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"
    # Draft and redacted items have no state.
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProjectItem:
    id: ProjectItemID
    kind: ProjectItemKind
    # None for redacted items.
    title: str | None
    # None for draft and redacted items.
    url: str | None
    state: ProjectItemState


class ProjectNotFoundError(Exception):
    """Raised when GitHub returns no Project for the ID, e.g. a wrong ID or no access."""


class ListProjectV2Items:
    # https://docs.github.com/en/graphql/reference/objects#projectv2itemconnection
    QUERY = gql("""
    query ($projectId: ID!, $after: String, $query: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $after, query: $query) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              id
              content {
                __typename
                ... on Issue { title state url }
                ... on PullRequest { title state url }
                ... on DraftIssue { title }
              }
            }
          }
        }
      }
    }
    """)

    # 'query' uses the Project filter syntax (e.g. "is:closed"). None lists every item.
    def __init__(self, *, projectId: str, query: str | None = None):
        self._projectId = projectId
        self._query = query

    def execute(self, client) -> list[ProjectItem]:
        items = []
        after = None
        has_next_page = True

        while has_next_page:
            result = client.execute(
                self.QUERY,
                variable_values={
                    "projectId": self._projectId,
                    "after": after,
                    "query": self._query,
                },
            )
            if result["node"] is None:
                raise ProjectNotFoundError(
                    f"Project {self._projectId} was not found or is not accessible "
                    "with this token."
                )
            items_data = result["node"]["items"]
            for node in items_data["nodes"]:
                content = node["content"] or {}
                items.append(
                    ProjectItem(
                        id=ProjectItemID(node["id"]),
                        kind=ProjectItemKind(content.get("__typename", "Redacted")),
                        title=content.get("title"),
                        url=content.get("url"),
                        state=ProjectItemState(content.get("state", "NONE")),
                    )
                )

            page_info = items_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            after = page_info["endCursor"]

        return items


@dataclass(frozen=True)
class ProjectItemDate:
    id: ProjectItemID
    date: str | None


class ListProjectV2ItemDateValues:
    # https://docs.github.com/en/graphql/reference/objects#projectv2itemfielddatevalue
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
              id
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldDateValue {
                    date
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

    def execute(self, client) -> list[ProjectItemDate]:
        items = []
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
                date = None
                for field_value in item["fieldValues"]["nodes"]:
                    if not field_value:
                        continue
                    if field_value.get("field", {}).get("id") == self._fieldId:
                        date = field_value.get("date")
                items.append(ProjectItemDate(id=ProjectItemID(item["id"]), date=date))

            page_info = items_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            after = page_info["endCursor"]

        return items


class DeleteProjectV2Item:
    # https://docs.github.com/en/graphql/reference/mutations#deleteprojectv2item
    QUERY = gql("""
    mutation ($projectId: ID!, $itemId: ID!) {
      op: deleteProjectV2Item(input: {
        projectId: $projectId,
        itemId: $itemId,
      }) { deletedItemId }
    }
    """)

    def __init__(self, *, projectId: str, itemId: ProjectItemID):
        self._values = {
            "projectId": projectId,
            "itemId": str(itemId),
        }

    def execute(self, client) -> None:
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
