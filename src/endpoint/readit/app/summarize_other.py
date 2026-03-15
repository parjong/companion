import arxiv
import json
from logging import getLogger
import os
from urllib.parse import urlparse

import click

from endpoint.readit.core import Page
from endpoint.readit.core import FetchResult
from endpoint.readit.core import summarize_fetch_result


logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("fetch_result_path")
def main(output_path: str, fetch_result_path: str) -> None:
    logger.info("Summarize from '%s'", fetch_result_path)

    with open(fetch_result_path, "r", encoding="utf-8") as f:
        fetch_result = FetchResult.model_validate_json(f.read())

    url = str(fetch_result.url)
    parsed_url = urlparse(url)

    if parsed_url.netloc == "arxiv.org":
        arxiv_id = parsed_url.path.split("/")[-1]
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(search.results())
        paper = results[0]

        page = Page(
            url=parsed_url,
            title=paper.title,
            date=paper.published.strftime("%Y/%m/%d"),
            kind="arxiv",
            metadata={
                "summary": paper.summary,
                "year": str(paper.published.year),
            },
        )
    else:
        page = summarize_fetch_result(fetch_result)

    logger.info("Result: '%s'", page)

    with open(output_path, "w") as f:
        json.dump(page.asdict(), f, indent=4)

    logger.info("Check '%s'", output_path)


if __name__ == "__main__":
    main()
