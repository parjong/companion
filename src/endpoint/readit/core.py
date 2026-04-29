from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import model_validator
from pydantic import TypeAdapter
from pydantic import field_validator


class OtherMetadata(BaseModel):
    key_sentences: list[str] = Field(default_factory=list)


class ArxivMetadata(BaseModel):
    summary: str
    year: str


class PersonalArchiveMetadata(BaseModel):
    # 'str' is used instead of 'HttpUrl' to avoid the complexity of Pydantic's Url objects
    # (e.g., in logging or f-strings) while still ensuring data integrity
    # through validation during assignment.
    issue_url: str | None = None
    comment_url: str | None = None

    @field_validator("issue_url", "comment_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            TypeAdapter(HttpUrl).validate_python(v)
        return v


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

    # Reserved for 'send' step
    personal_archive: PersonalArchiveMetadata = Field(
        default_factory=PersonalArchiveMetadata
    )

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
