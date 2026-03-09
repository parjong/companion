import arxiv
import json
from logging import getLogger
import os
from urllib.parse import urlparse

import click

from endpoint.readit.core import Page
from endpoint.readit.core import page_of_


logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("url")
def main(output_path: str, url: str) -> None:
    logger.info("Summarize '%s'", url)

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
        page = page_of_(url)

    logger.info("Result: '%s'", page)

    with open(output_path, "w") as f:
        json.dump(page.asdict(), f, indent=4)

    logger.info("Check '%s'", output_path)
