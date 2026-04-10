import arxiv
import json
from logging import getLogger
import os
from urllib.parse import urlparse

import click
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field

from endpoint.readit.core import Page
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


_PROMPT = ChatPromptTemplate.from_template("""
    Analyze the provided content and extract the following information:
    1. **Title**: The concise main title of the article or page.
    2. **Date**: The publication or issue date in YYYY/MM/DD format. Use "????/??/??" if it cannot be determined.
    3. **Key Sentences**: Identify up to 3 most important sentences that represent the core message of the content.

    **Critical Constraints for Key Sentences:**
    - Each sentence MUST be extracted EXACTLY as it appears in the original content. 
    - Do NOT summarize or rephrase the sentences. 
    - Provide them as a list of strings.

    Format your answer as a JSON object with keys "date", "title", and "key_sentences".

    Content: {content}
    """)
_STRUCTURED_LLM = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
).with_structured_output(Summary)
_CHAIN = _PROMPT | _STRUCTURED_LLM


def page_of_(fetch_result: FetchResult) -> Page:
    content = fetch_result.trafilatura.get("text") or fetch_result.html
    summary = _CHAIN.invoke({"content": content})

    return Page(
        url=urlparse(str(fetch_result.url)),
        title=summary.title,
        date=summary.date,
        metadata={
            "key_sentences": summary.key_sentences,
        },
    )


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
        page = page_of_(fetch_result)

    logger.info("Result: '%s'", page)

    with open(output_path, "w") as f:
        json.dump(page.asdict(), f, indent=4)

    logger.info("Check '%s'", output_path)


if __name__ == "__main__":
    main()
