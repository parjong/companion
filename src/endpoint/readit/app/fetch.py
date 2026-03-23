import json
import os
import urllib.request
from urllib.parse import urlparse, urlunparse
from logging import getLogger

import click
import trafilatura

from endpoint.readit.core import FetchResult

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


def normalize_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.netloc == "www.linkedin.com":
        if parsed_url.path.startswith("/posts/"):
            parsed_url = parsed_url._replace(query="")
    return urlunparse(parsed_url)


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("url")
def main(output_path: str, url: str) -> None:
    logger.info("Fetching '%s'", url)

    # Fetch the URL
    with urllib.request.urlopen(url, timeout=60) as response:
        page_html_bytes = response.read()
        # We need the HTML as a string for the output JSON
        page_html = page_html_bytes.decode("utf-8", errors="replace")
        final_url = response.geturl()

    # Normalize the URL
    normalized_url = normalize_url(final_url)

    # Extract content using trafilatura
    # output_format="json" with with_metadata=True gives a JSON string with metadata
    trafilatura_json_str = trafilatura.extract(
        page_html_bytes, output_format="json", with_metadata=True
    )
    if trafilatura_json_str:
        trafilatura_data = json.loads(trafilatura_json_str)
    else:
        trafilatura_data = {}

    # Prepare final output using Pydantic
    result = FetchResult(
        url=normalized_url, html=page_html, trafilatura=trafilatura_data
    )

    # Write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    logger.info("Saved raw data to '%s'", output_path)


if __name__ == "__main__":
    main()
