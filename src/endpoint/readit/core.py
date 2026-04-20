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
from pydantic import model_validator


class OtherMetadata(BaseModel):
    key_sentences: list[str] = Field(default_factory=list)


class ArxivMetadata(BaseModel):
    summary: str
    year: str


class Blackboard(BaseModel):
    url: HttpUrl
    html: str | None = None
    trafilatura: dict[str, Any] | None = None
    title: str | None = None
    date: str | None = None
    # TODO: Consider allowing None to represent 'not yet categorized' state
    kind: str = "other"

    arxiv: ArxivMetadata | None = Field(None)
    other: OtherMetadata | None = Field(default_factory=OtherMetadata)

    @model_validator(mode="before")
    @classmethod
    def migrate_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            metadata = data.pop("metadata", None)
            if metadata is not None:
                kind = data.get("kind", "other")
                if kind == "arxiv":
                    data["arxiv"] = metadata
                else:
                    data["other"] = metadata
        return data

    @model_validator(mode="after")
    def validate_kind_metadata(self) -> "Blackboard":
        if self.kind == "arxiv" and self.arxiv is None:
            raise ValueError("arxiv metadata is required when kind is 'arxiv'")
        if self.kind == "other" and self.other is None:
            raise ValueError("other metadata is required when kind is 'other'")
        return self

    @classmethod
    # TODO: To be applied to other modules (e.g. summarize_other.py) in Phase 4
    def from_pipeline_file(cls, path_or_file: Any) -> "Blackboard":
        import json
        from pathlib import Path

        if hasattr(path_or_file, "read"):
            data = json.load(path_or_file)
        else:
            data = json.loads(Path(path_or_file).read_text())

        return cls.model_validate(data)


class OtherPageModel(BaseModel):
    url: str
    title: str
    date: str
    kind: Literal["other"] = "other"
    metadata: OtherMetadata = Field(default_factory=OtherMetadata)


class ArxivPageModel(BaseModel):
    url: str
    title: str
    date: str
    kind: Literal["arxiv"] = "arxiv"
    metadata: ArxivMetadata

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        # If it looks like a full date (e.g. 2026/04/10), extract the year
        if "/" in v or "-" in v:
            v = v.split("/")[0].split("-")[0]

        if v == "UNKNOWN" or not v.isdigit() or len(v) != 4:
            raise ValueError("Arxiv date must be a 4-digit year (YYYY), not UNKNOWN.")
        return v


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
        """Returns metadata as a dictionary for backward compatibility."""
        if isinstance(self._inner.metadata, BaseModel):
            return self._inner.metadata.model_dump()
        return self._inner.metadata

    def url_as_str(self) -> str:
        return str(self._inner.url)

    def asdict(self) -> dict[str, Any]:
        return self._inner.model_dump()

    @classmethod
    def fromdict(cls, d: dict[str, Any]) -> "Page":
        # Bridge logic: If metadata is missing but arxiv/other is present,
        # move it to metadata for PageModel compatibility.
        if "metadata" not in d:
            kind = d.get("kind", "other")
            if kind == "arxiv" and "arxiv" in d:
                d["metadata"] = d["arxiv"]
            elif kind == "other" and "other" in d:
                d["metadata"] = d["other"]

        return cls(
            url=urlparse(d["url"]),
            title=d["title"],
            date=d["date"],
            kind=d.get("kind", "other"),
            metadata=d.get("metadata"),
        )

    @classmethod
    def from_pipeline_file(cls, path_or_file: Any) -> "Page":
        import json
        from pathlib import Path

        if hasattr(path_or_file, "read"):
            data = json.load(path_or_file)
        else:
            data = json.loads(Path(path_or_file).read_text())

        # Simple detection: if it has required Page fields, use it.
        # If it's a Blackboard, it must at least have title and date to be converted to Page.
        # For Phase 1, we assume the data is sufficient.
        return cls.fromdict(data)
