from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
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

    @model_validator(mode="after")
    def validate_kind_metadata(self) -> "Blackboard":
        if self.kind == "arxiv" and self.arxiv is None:
            raise ValueError("arxiv metadata is required when kind is 'arxiv'")
        if self.kind == "other" and self.other is None:
            raise ValueError("other metadata is required when kind is 'other'")
        return self

    def url_as_str(self) -> str:
        return str(self.url)

    @classmethod
    def from_pipeline_file(cls, path_or_file: Any) -> "Blackboard":
        import json
        from pathlib import Path

        if hasattr(path_or_file, "read"):
            data = json.load(path_or_file)
        else:
            data = json.loads(Path(path_or_file).read_text())

        return cls.model_validate(data)
