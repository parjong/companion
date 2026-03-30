from dataclasses import dataclass
from dataclasses import field

from pydantic import BaseModel
from pydantic import HttpUrl
from typing import Any
from urllib.parse import ParseResult as URL
from urllib.parse import urlparse
from urllib.parse import urlunparse


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
