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


class BaseProcessor:
    """Base class for HTML and text pre/postprocessing."""

    def preprocess_html(self, html_bytes: bytes) -> bytes:
        return html_bytes

    def postprocess_text(self, text: str) -> str:
        return text


class DefaultProcessor(BaseProcessor):
    """Default processor that performs no modifications."""

    pass


class GeekNewsProcessor(BaseProcessor):
    """Geek News specific HTML and text pre/postprocessor."""

    def preprocess_html(self, html_bytes: bytes) -> bytes:
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

    def _merge_link_and_header(self, text: str) -> str:
        """Merge the top link and the title header into a single unified clickable header."""
        link_match = re.search(r"^\[([^\]]+)\]\((https?://[^\)]+)\)", text.strip())
        if link_match:
            link_text, link_url = link_match.groups()
            header_match = re.search(r"#\s+([^\n]+)", text)
            if header_match:
                header_text = header_match.group(1).strip()
                # Remove the top link and its trailing spaces/newlines
                cleaned_text = re.sub(r"^\[[^\]]+\]\([^\)]+\)\s*", "", text.strip())
                # Replace '# Title' with '# [Title](URL)'
                return re.sub(
                    r"#\s+" + re.escape(header_text),
                    f"# [{header_text}]({link_url})",
                    cleaned_text,
                    count=1,
                )
        return text

    def postprocess_text(self, text: str) -> str:
        # Strip comments section from GeekNews
        for delimiter in ["## 댓글과 토론", "## 댓글"]:
            if delimiter in text:
                text = text.split(delimiter)[0].strip()

        # Merge the top link and title header for GeekNews into a single unified clickable header
        text = self._merge_link_and_header(text)

        # Merge inline code backticks followed by newlines and a lowercase/Korean character
        pattern_backtick = r"`([^`\n]+)`\s*\n+\s*([가-힣a-z,.?!~])"
        text = re.sub(pattern_backtick, r"`\1` \2", text)

        # Merge general accidental newlines inside sentences
        lines = text.splitlines()
        merged_lines = []
        for line in lines:
            if merged_lines and merged_lines[-1].strip() and line.strip():
                prev_line = merged_lines[-1].rstrip()
                curr_line = line.strip()
                if not prev_line.endswith(
                    (".", "!", "?", ":", "#", "-", "*")
                ) and re.match(r"^[가-힣a-z]", curr_line):
                    merged_lines[-1] = prev_line + " " + curr_line
                    continue
            merged_lines.append(line)
        text = "\n".join(merged_lines)

        # Remove empty lines between consecutive list items to keep list blocks compact
        lines = text.splitlines()
        new_lines = []
        for i, line in enumerate(lines):
            if line.strip().startswith("- ") and i > 0:
                last_non_empty = None
                for prev in reversed(new_lines):
                    if prev.strip():
                        last_non_empty = prev.strip()
                        break
                if last_non_empty and (
                    last_non_empty.startswith("- ") or last_non_empty.startswith("* ")
                ):
                    while new_lines and not new_lines[-1].strip():
                        new_lines.pop()
            new_lines.append(line)
        text = "\n".join(new_lines)
        return text


class LinkedInProcessor(BaseProcessor):
    """LinkedIn specific HTML and text pre/postprocessor."""

    def postprocess_text(self, text: str) -> str:
        # Match markdown links containing comments or comment_actor in their target and strip everything from there
        pattern = re.compile(
            r"\[[^\]]+\]\([^\)]*(?:comment_actor|see-more-comments)[^\)]*\)"
        )
        match = pattern.search(text)
        if match:
            text = text[: match.start()].strip()
        return text


def get_processor(url: str) -> BaseProcessor:
    """Return the appropriate HTML/text processor for the given URL."""
    if "news.hada.io" in url:
        return GeekNewsProcessor()
    if "linkedin.com" in url:
        return LinkedInProcessor()
    return DefaultProcessor()


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

    # Get the appropriate HTML/text processor based on the URL
    processor = get_processor(final_url)

    # Preprocess html to preserve list items and newlines specifically for Geek News
    preprocessed_bytes = processor.preprocess_html(page_html_bytes)

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
            # Postprocess text based on domain specific rules
            formatted_text = processor.postprocess_text(formatted_text)
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
