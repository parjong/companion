from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field
from pydantic import AnyHttpUrl
from pydantic import TypeAdapter
import trafilatura
from typing import Any, Literal, Union, Annotated
import urllib.request


class Summary(BaseModel):
    title: str = Field(
        description="The title of concise main title of the article or page"
    )
    date: str = Field(
        description="The issue or publication date as YYYY/MM/DD format (????/??/?? if unknown)"
    )


class ArxivPage(BaseModel):
    kind: Literal["arxiv"] = "arxiv"
    url: AnyHttpUrl
    title: str
    date: str = Field(pattern=r"^\d{4}$")
    paper_id: str
    abstract: str


class OtherPage(BaseModel):
    kind: Literal["other"] = "other"
    url: AnyHttpUrl
    title: str
    date: str = Field(pattern=r"^\d{4}/\d{2}/\d{2}$|^\?\?\?\?/\?\?/\?\?$")
    metadata: dict[str, Any] = Field(default_factory=dict)


Page = Annotated[Union[ArxivPage, OtherPage], Field(discriminator="kind")]
page_adapter = TypeAdapter(Page)


def page_from_dict(d: dict[str, Any]) -> Page:
    return page_adapter.validate_python(d)


def page_to_dict(page: Page) -> dict[str, Any]:
    # We use mode='json' to ensure AnyHttpUrl is serialized to string
    return page_adapter.dump_python(page, mode="json")


def page_of_(url: str) -> OtherPage:
    with urllib.request.urlopen(url, timeout=60) as response:
        page_html = response.read()
        page_url = response.geturl()

    # Try to extract content using trafilatura
    content = trafilatura.extract(page_html, with_metadata=True)
    if not content:
        content = page_html

    prompt = ChatPromptTemplate.from_template("""
    Analyze the following content from a webpage and extract two pieces of information:
    1. The concise main title of the article or page.
    2. The issue or publication date as YYYY/MM/DD format (if available).
       - If not available, state "????/??/??".

    Format your answer as a JSON object with keys "date" and "title".

    Content: {content}
    """)
    structured_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash"
    ).with_structured_output(Summary)

    chain = prompt | structured_llm

    summary = chain.invoke({"content": content})

    return OtherPage(url=page_url, title=summary.title, date=summary.date)
