from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field
import urllib.request
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


@dataclass
class Page:
    url: URL
    title: str
    date: str

    def url_as_str(self) -> str:
        return urlunparse(self.url)

    def asdict(self):
        return {
            "url": urlunparse(self.url),
            "title": self.title,
            "date": self.date,
        }

    @classmethod
    def fromdict(cls, d):
        return cls(url=urlparse(d["url"]), title=d["title"], date=d["date"])


def page_of_(url: str) -> Page:
    with urllib.request.urlopen(url) as response:
        page_html = response.read()

        page_url = urlparse(response.geturl())

    if page_url.netloc == "www.linkedin.com":
        if page_url.path.startswith("/posts/"):
            page_url = page_url._replace(query="")

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

    summary = chain.invoke({"content": page_html})

    return Page(url=page_url, title=summary.title, date=summary.date)
