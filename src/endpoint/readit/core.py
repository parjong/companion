from typing import Annotated, Any, Literal, Union

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field
from pydantic import TypeAdapter
import trafilatura
import urllib.request
from urllib.parse import urlparse
from urllib.parse import urlunparse


class Summary(BaseModel):
    title: str = Field(
        description="The title of concise main title of the article or page"
    )
    date: str = Field(
        description="The issue or publication date as YYYY/MM/DD format (????/??/?? if unknown)"
    )


class BasePage(BaseModel):
    url: str
    title: str

    def url_as_str(self) -> str:
        return self.url


class ArxivPage(BasePage):
    kind: Literal["arxiv"] = "arxiv"
    date: str = Field(pattern=r"^\d{4}$")
    paper_id: str
    abstract: str


class OtherPage(BasePage):
    kind: Literal["other"] = "other"
    date: str = Field(pattern=r"^(\d{4}/\d{2}/\d{2}|\?\?\?\?/\?\?/\?\?)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


Page = Annotated[Union[ArxivPage, OtherPage], Field(discriminator="kind")]


def page_fromdict(d: dict) -> Page:
    return TypeAdapter(Page).validate_python(d)


def page_of_(url: str) -> OtherPage:
    with urllib.request.urlopen(url, timeout=60) as response:
        page_html = response.read()

        page_url = urlparse(response.geturl())

    if page_url.netloc == "www.linkedin.com":
        if page_url.path.startswith("/posts/"):
            page_url = page_url._replace(query="")

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

    return OtherPage(url=urlunparse(page_url), title=summary.title, date=summary.date)
