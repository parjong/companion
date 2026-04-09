from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import TypeAdapter
from pydantic import BeforeValidator
from typing import Any, Literal, Annotated, Union


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
