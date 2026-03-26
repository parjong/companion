from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import TypeAdapter
from pydantic import BeforeValidator
from typing import Any, Literal, Annotated, Union


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


class BasePage(BaseModel):
    url: HttpUrl
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def url_as_str(self) -> str:
        return str(self.url)

    def asdict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ArxivPage(BasePage):
    kind: Literal["arxiv"] = "arxiv"
    paper_id: str
    abstract: str
    date: str = Field(pattern=r"^\d{4}$")


class OtherPage(BasePage):
    kind: Literal["other"] = "other"
    date: str = Field(pattern=r"^(\d{4}/\d{2}/\d{2}|\?\?\?\?/\?\?/\?\?)$")


Page = Annotated[Union[ArxivPage, OtherPage], Field(discriminator="kind")]


def _default_kind_to_other(v: Any) -> Any:
    if isinstance(v, dict) and "kind" not in v:
        return {**v, "kind": "other"}
    return v


PageAdapter = TypeAdapter(Annotated[Page, BeforeValidator(_default_kind_to_other)])


def parse_page(data: dict[str, Any]) -> Page:
    return PageAdapter.validate_python(data)


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


def page_of_(fetch_result: FetchResult) -> OtherPage:
    summary = _CHAIN.invoke({"content": fetch_result.html})

    return OtherPage(
        url=fetch_result.url,
        title=summary.title,
        date=summary.date,
    )
