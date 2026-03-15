from dataclasses import dataclass
from dataclasses import field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from typing import Any
from urllib.parse import ParseResult as URL
from urllib.parse import urlparse
from urllib.parse import urlunparse


class Summary(BaseModel):
    title: str = Field(
        description="The title of concise main title of the article or page"
    )
    date: str = Field(
        description="The issue or publication date as YYYY/MM/DD format (????/??/?? if unknown)"
    )


class FetchResult(BaseModel):
    url: HttpUrl
    html: str
    trafilatura: dict[str, Any]


@dataclass
class Page:
    url: URL
    title: str
    date: str
    kind: str = "other"
    metadata: dict[str, Any] = field(default_factory=dict)

    def url_as_str(self) -> str:
        return urlunparse(self.url)

    def asdict(self):
        return {
            "url": urlunparse(self.url),
            "title": self.title,
            "date": self.date,
            "kind": self.kind,
            "metadata": self.metadata,
        }

    @classmethod
    def fromdict(cls, d):
        return cls(
            url=urlparse(d["url"]),
            title=d["title"],
            date=d["date"],
            kind=d.get("kind", "other"),
            metadata=d.get("metadata", {}),
        )


_PROMPT = ChatPromptTemplate.from_template("""
    Analyze the following content from a webpage and extract two pieces of information:
    1. The concise main title of the article or page.
    2. The issue or publication date as YYYY/MM/DD format (if available).
       - If not available, state "????/??/??".

    Format your answer as a JSON object with keys "date" and "title".

    Content: {content}
    """)
_STRUCTURED_LLM = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
).with_structured_output(Summary)
_CHAIN = _PROMPT | _STRUCTURED_LLM


def summarize_fetch_result(fetch_result: FetchResult) -> Page:
    summary = _CHAIN.invoke({"content": fetch_result.html})

    return Page(
        url=urlparse(str(fetch_result.url)),
        title=summary.title,
        date=summary.date,
    )
