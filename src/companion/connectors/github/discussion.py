from gql import gql
from logging import getLogger

logger = getLogger(__name__)


class CreateDiscussion:
    QUERY = gql("""
    mutation ($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {
          repositoryId: $repositoryId,
          categoryId: $categoryId,
          title: $title,
          body: $body
      }) { discussion { id } }
    }
    """)

    def __init__(self, *, repositoryId: str, categoryId: str, title: str, body: str):
        self._values = {
            "repositoryId": repositoryId,
            "categoryId": categoryId,
            "title": title,
            "body": body,
        }

    def execute(self, client):
        result = client.execute(self.QUERY, variable_values=self._values)
        logger.debug(result)
        pass
