from typing import IO

import arxiv
import datetime
import json
from logging import getLogger
import os
from urllib.parse import urlparse

import click
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field

from endpoint.readit.core import Blackboard
from endpoint.readit.core import FetchResult


logger = getLogger(__name__)
logger.setLevel(os.environ.get("ENTRYPOINT_LOG_LEVEL", "INFO").upper())


class Summary(BaseModel):
    title: str = Field(
        description="The title of concise main title of the article or page"
    )
    date: str = Field(
        description="The issue or publication date as YYYY/MM/DD format (????/??/?? if unknown)"
    )
    key_sentences: list[str] = Field(
        description="Up to 3 most important sentences extracted exactly from the content"
    )


# --- Inference Models & Chains ---

_STRUCTURED_LLM = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
).with_structured_output(Summary)

# Stage 1: Standard Summarization (Cleaned Text)
_PROMPT = ChatPromptTemplate.from_template("""
    Analyze the provided content and extract the following information:
    1. **Title**: The concise main title of the article or page.
    2. **Date**: The publication or issue date in YYYY/MM/DD format.
    3. **Key Sentences**: Identify up to 3 most important sentences that represent the core message of the content.

    **Date Recognition Guidelines:**
    - Current Date (Today): {today} (KST)
    - Metadata Date Hint: {date_hint} (Use this if available and applicable)
    - If the content uses relative dates (e.g., "2 days ago", "last week"), calculate the absolute date based on the Current Date.
    - If the body text lacks a clear date, try to infer it from the Metadata Date Hint or potential date slugs in the page structure.
    - If the date cannot be determined, use "????/??/??".

    **Critical Constraints for Key Sentences:**
    - Each sentence MUST be extracted EXACTLY as it appears in the original content.
    - Do NOT summarize or rephrase the sentences.
    - Provide them as a list of strings.

    Format your answer as a JSON object with keys "date", "title", and "key_sentences".

    Content: {content}
    """)
_CHAIN = _PROMPT | _STRUCTURED_LLM

# Stage 2: Fallback Extraction (Raw HTML)
_FALLBACK_PROMPT = ChatPromptTemplate.from_template("""
    Identify the publication date from the provided raw HTML.
    Specifically look for relative time patterns (e.g., "1 day ago", "3시간 전") and meta tags.

    **Guidelines:**
    - Today: {today} (KST)
    - Calculate absolute dates from relative expressions.
    - Return "????/??/??" if not found.

    Format: JSON object with "date", "title" (use current: {current_title}), and "key_sentences" (provide empty list []).

    Raw HTML: {html}
    """)
_FALLBACK_CHAIN = _FALLBACK_PROMPT | _STRUCTURED_LLM


def page_of_(bb: Blackboard) -> Blackboard:
    if not bb.html:
        raise ValueError(f"No HTML content available for summarization: {bb.url}")

    # Use 'or {}' for safe access in case bb.trafilatura is None (per Blackboard model definition)
    content = (bb.trafilatura or {}).get("text") or bb.html

    # Calculate current date in KST (UTC+9)
    # TODO: Move 'today' calculation to the fetch stage in the future to ensure temporal consistency
    kst = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(kst).strftime("%Y/%m/%d")

    # Get date hint from trafilatura metadata
    date_hint = (bb.trafilatura or {}).get("date") or "Unknown"

    summary = _CHAIN.invoke(
        {
            "content": content,
            "today": today,
            "date_hint": date_hint,
        }
    )

    # Fallback stage: if date is unknown, try parsing raw HTML
    if summary.date == "????/??/??" or "??" in summary.date:
        logger.info(
            "First inference failed to find date. Triggering fallback with raw HTML..."
        )
        fallback_res = _FALLBACK_CHAIN.invoke(
            {
                "html": bb.html,
                "today": today,
                "current_title": summary.title,
            }
        )
        logger.info(f"Fallback result: {fallback_res.date}")
        summary.date = fallback_res.date

    return bb.model_copy(
        update={
            "title": summary.title,
            "date": summary.date,
            "metadata": {"key_sentences": summary.key_sentences},
        }
    )


def load_blackboard(f: IO) -> Blackboard:
    """Input Adapter: Loads either a legacy FetchResult or a Blackboard from JSON."""
    data = json.load(f)

    try:
        # Try as Blackboard first
        return Blackboard.model_validate(data)
    except Exception:
        # Fallback to legacy FetchResult and convert
        fr = FetchResult.model_validate(data)
        return Blackboard(
            url=fr.url,
            html=fr.html,
            trafilatura=fr.trafilatura,
        )


@click.command()
@click.option("-o", "output_path", required=True)
# TODO: Rename to input_path in Phase 3
@click.argument("fetch_result_path")
def main(output_path: str, fetch_result_path: str) -> None:
    logger.info("Summarize from '%s'", fetch_result_path)

    with open(fetch_result_path, "r", encoding="utf-8") as f:
        bb = load_blackboard(f)

    url = str(bb.url)
    parsed_url = urlparse(url)

    if parsed_url.netloc == "arxiv.org":
        arxiv_id = parsed_url.path.split("/")[-1]
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(search.results())
        paper = results[0]

        bb = bb.model_copy(
            update={
                "title": paper.title,
                "date": paper.published.strftime("%Y/%m/%d"),
                "kind": "arxiv",
                "metadata": {
                    "summary": paper.summary,
                    "year": str(paper.published.year),
                },
            }
        )
    else:
        bb = page_of_(bb)

    logger.info("Result: '%s'", bb.model_dump(exclude={"html", "trafilatura"}))

    with open(output_path, "w") as f:
        json.dump(bb.model_dump(mode="json"), f, indent=4)

    logger.info("Check '%s'", output_path)


if __name__ == "__main__":
    main()
