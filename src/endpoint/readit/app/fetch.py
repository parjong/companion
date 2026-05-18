import json
import os
import re
import time
from logging import getLogger
from urllib.parse import urlparse
from urllib.parse import urlunparse

import click
import trafilatura
from curl_cffi import requests

from endpoint.readit.core import Blackboard

logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


def preprocess_html(html_bytes: bytes, url: str) -> bytes:
    """Preprocess HTML to preserve list item separation and newlines in trafilatura specifically for Geek News."""
    if "news.hada.io" not in url:
        return html_bytes

    try:
        html = html_bytes.decode("utf-8", errors="replace")
        # Replace list items with paragraph tags to preserve list item separation and newlines
        html = re.sub(r"<li>", "<p>- ", html, flags=re.IGNORECASE)
        html = re.sub(r"</li>", "</p>", html, flags=re.IGNORECASE)
        # Replace br tags with paragraph boundaries to preserve single line breaks
        html = re.sub(r"<br\s*/?>", "</p><p>", html, flags=re.IGNORECASE)
        return html.encode("utf-8")
    except Exception:
        return html_bytes


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


@click.command()
@click.option("-o", "output_path", required=True)
@click.argument("url")
def main(output_path: str, url: str) -> None:
    logger.info("Fetching '%s'", url)

    try:
        page_html_bytes, final_url = fetch_with_retry(url)
        # We need the HTML as a string for the output JSON
        page_html = page_html_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error("All attempts failed for '%s': %s", url, e)
        raise click.ClickException(f"Failed to fetch {url}: {e}")

    # Normalize the URL
    normalized_url = normalize_url(final_url)

    # Preprocess html to preserve list items and newlines specifically for Geek News
    preprocessed_bytes = preprocess_html(page_html_bytes, final_url)

    # Extract content using trafilatura
    # output_format="json" with with_metadata=True gives a JSON string with metadata
    trafilatura_json_str = trafilatura.extract(
        preprocessed_bytes, output_format="json", with_metadata=True
    )
    if trafilatura_json_str:
        trafilatura_data = json.loads(trafilatura_json_str)
        # Extract content with markdown formatting and without comments
        formatted_text = trafilatura.extract(
            preprocessed_bytes,
            include_comments=False,
            include_formatting=True,
            include_links=True,
        )
        if formatted_text:
            # Strip comments section from GeekNews
            for delimiter in ["## 댓글과 토론", "## 댓글"]:
                if delimiter in formatted_text:
                    formatted_text = formatted_text.split(delimiter)[0].strip()
            trafilatura_data["text"] = formatted_text
    else:
        trafilatura_data = {}

    # Prepare final output using Pydantic
    result = Blackboard(
        url=normalized_url, html=page_html, trafilatura=trafilatura_data
    )

    # Write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    logger.info("Saved raw data to '%s'", output_path)


if __name__ == "__main__":
    main()
