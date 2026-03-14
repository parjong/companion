import json
import os
import urllib.request
from urllib.parse import urlparse, urlunparse
from logging import getLogger

import click
import trafilatura

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())

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
        page_url = urlparse(response.geturl())

    # Normalize the URL (matching logic in core.py)
    if page_url.netloc == "www.linkedin.com":
        if page_url.path.startswith("/posts/"):
            page_url = page_url._replace(query="")

    normalized_url = urlunparse(page_url)

    # Extract content using trafilatura
    # output_format="json" with with_metadata=True gives a JSON string with metadata
    trafilatura_json_str = trafilatura.extract(page_html_bytes, output_format="json", with_metadata=True)
    if trafilatura_json_str:
        trafilatura_data = json.loads(trafilatura_json_str)
    else:
        trafilatura_data = {}

    # Prepare final output
    result = {
        "url": normalized_url,
        "html": page_html,
        "trafilatura": trafilatura_data
    }

    # Write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info("Saved raw data to '%s'", output_path)

if __name__ == "__main__":
    main()
