from typing import Annotated
from typing import Any
from typing import Literal
from typing import Union
from urllib.parse import ParseResult as URL
from urllib.parse import urlparse
from urllib.parse import urlunparse

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import TypeAdapter
from pydantic import field_validator


class FetchResult(BaseModel):
    url: HttpUrl
    html: str
    trafilatura: dict[str, Any]


class ArxivPageModel(BaseModel):
    kind: Literal["arxiv"] = "arxiv"
    url: str
    title: str
    date: str
    metadata: dict[str, Any]

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if v == "UNKNOWN" or not v.isdigit() or len(v) != 4:
            raise ValueError("Arxiv date must be a 4-digit year (YYYY), not UNKNOWN.")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        if "paper_id" not in v:
            raise ValueError("Arxiv metadata requires 'paper_id'.")
        if "abstract" not in v:
            raise ValueError("Arxiv metadata requires 'abstract'.")
        return v


class OtherPageModel(BaseModel):
    kind: Literal["other"] = "other"
    url: str
    title: str
    date: str
    metadata: dict[str, Any] = Field(default_factory=dict)


PageModel = Annotated[
    Union[ArxivPageModel, OtherPageModel], Field(discriminator="kind")
]
_PageAdapter = TypeAdapter(PageModel)


class Page:
    """Wrapper class preserving legacy interface while using Pydantic PageModel internally."""

    _inner: PageModel

    def __init__(
        self,
        url: URL,
        title: str,
        date: str,
        kind: str = "other",
        metadata: dict[str, Any] | None = None,
    ):
        if metadata is None:
            metadata = {}
        payload = {
            "url": urlunparse(url),
            "title": title,
            "date": date,
            "kind": kind,
            "metadata": metadata,
        }
        self._inner = _PageAdapter.validate_python(payload)

    @property
    def url(self) -> URL:
        return urlparse(str(self._inner.url))

    @property
    def title(self) -> str:
        return self._inner.title

    @property
    def date(self) -> str:
        return self._inner.date

    @property
    def kind(self) -> str:
        return self._inner.kind

    @property
    def metadata(self) -> dict[str, Any]:
        return self._inner.metadata

    def url_as_str(self) -> str:
        return str(self._inner.url)

    def asdict(self) -> dict[str, Any]:
        return self._inner.model_dump()

    @classmethod
    def fromdict(cls, d: dict[str, Any]) -> "Page":
        return cls(
            url=urlparse(d["url"]),
            title=d["title"],
            date=d["date"],
            kind=d.get("kind", "other"),
            metadata=d.get("metadata", {}),
        )
