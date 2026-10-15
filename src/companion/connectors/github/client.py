from gql import Client
from gql.transport.requests import RequestsHTTPTransport as HTTPTransport


def make_client(*, url: str, token: str) -> Client:
    """Create a GraphQL client that authenticates with the given token."""
    return Client(
        transport=HTTPTransport(
            url=url,
            headers={"Authorization": f"Bearer {token}"},
        )
    )
