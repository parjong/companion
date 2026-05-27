import json
import os
import time
from logging import getLogger
from urllib.parse import urlparse
from urllib.parse import urlunparse

import click
import trafilatura
from curl_cffi import requests

from endpoint.readit.core import Blackboard
from endpoint.readit.core import Step

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


def normalize_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.netloc == "www.linkedin.com":
        if parsed_url.path.startswith("/posts/"):
            parsed_url = parsed_url._replace(query="")
    return urlunparse(parsed_url)


def fetch_with_retry(url: str, max_retries: int = 3) -> tuple[bytes, str]:
    """Fetch URL with curl_cffi and exponential backoff retry."""
    with requests.Session() as s:
        for attempt in range(max_retries):
            try:
                # Use a browser impersonation to avoid bot detection
                response = s.get(url, impersonate="chrome110", timeout=30)
                response.raise_for_status()
                return response.content, response.url
            except Exception as e:
                logger.warning(
                    "Attempt %d failed to fetch '%s': %s", attempt + 1, url, e
                )
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info("Retrying in %d seconds...", wait_time)
                    time.sleep(wait_time)
                else:
                    raise e
    raise RuntimeError(f"Failed to fetch '{url}' after {max_retries} attempts")


class FetchStep(Step):
    """Pipeline step that fetches page HTML and extracts content using trafilatura."""

    def __call__(self, bb: Blackboard) -> Blackboard:
        """Pipeline step that fetches page HTML and extracts content.

        Args:
            bb: The current blackboard state containing the target URL.

        Returns:
            A new Blackboard state filled with the HTML content and extracted data.

        Raises:
            RuntimeError: If all network fetch attempts fail.
        """
        url_str = bb.url_as_str()
        logger.info("Fetching '%s'", url_str)

        try:
            page_html_bytes, final_url = fetch_with_retry(url_str)
            page_html = page_html_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            logger.error("All attempts failed for '%s': %s", url_str, e)
            raise RuntimeError(f"Failed to fetch {url_str}: {e}")

        # Normalize the URL
        normalized_url = normalize_url(final_url)

        # Extract content using trafilatura
        trafilatura_json_str = trafilatura.extract(
            page_html_bytes, output_format="json", with_metadata=True
        )
        if trafilatura_json_str:
            trafilatura_data = json.loads(trafilatura_json_str)
        else:
            trafilatura_data = {}

        return bb.model_copy(
            update={
                "url": normalized_url,
                "html": page_html,
                "trafilatura": trafilatura_data,
            }
        )


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("url")
def main(output_path: str, url: str) -> None:
    bb = Blackboard(url=url)
    fetch_step = FetchStep()
    bb = fetch_step(bb)

    # Write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bb.model_dump_json(indent=2))

    logger.info("Saved raw data to '%s'", output_path)


if __name__ == "__main__":
    main()
