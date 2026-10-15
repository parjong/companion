from companion.connectors.github.pagination import paginate


class PagedClient:
    """Serves pages of nodes and records the variables of every request."""

    def __init__(self, pages):
        self._pages = pages
        self.requests = []

    def execute(self, query, variable_values):
        self.requests.append(variable_values)
        index = len(self.requests) - 1
        last = index == len(self._pages) - 1
        return {
            "conn": {
                "pageInfo": {
                    "hasNextPage": not last,
                    "endCursor": None if last else f"cursor-{index}",
                },
                "nodes": self._pages[index],
            }
        }


def select(result):
    return result["conn"]


def test_follows_cursors_and_yields_nodes_of_every_page():
    client = PagedClient([[1, 2], [3], [4, 5]])

    nodes = list(paginate(client, "Q", {"id": "X"}, connection=select))

    assert nodes == [1, 2, 3, 4, 5]
    assert [r["after"] for r in client.requests] == [None, "cursor-0", "cursor-1"]


def test_passes_the_given_variables_on_every_request():
    client = PagedClient([[1], [2]])

    list(paginate(client, "Q", {"id": "X"}, connection=select))

    assert [r["id"] for r in client.requests] == ["X", "X"]


def test_fetches_pages_lazily():
    client = PagedClient([[1], [2], [3]])

    nodes = paginate(client, "Q", {}, connection=select)
    assert next(nodes) == 1
    assert len(client.requests) == 1


def test_single_page_makes_one_request():
    client = PagedClient([[]])

    assert list(paginate(client, "Q", {}, connection=select)) == []
    assert len(client.requests) == 1
