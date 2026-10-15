from collections.abc import Callable
from collections.abc import Iterator
from typing import Any


def paginate(
    client,
    query,
    variables: dict[str, Any],
    *,
    connection: Callable[[dict[str, Any]], dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Yields every node of a cursor-paginated GraphQL connection, fetching pages lazily.

    'query' must take an '$after: String' variable and pass it to the connection; this function
    supplies it. 'connection' picks the {"pageInfo": ..., "nodes": ...} object out of a response.
    """
    after = None
    while True:
        result = client.execute(query, variable_values={**variables, "after": after})
        page = connection(result)
        yield from page["nodes"]

        page_info = page["pageInfo"]
        if not page_info["hasNextPage"]:
            return
        after = page_info["endCursor"]
