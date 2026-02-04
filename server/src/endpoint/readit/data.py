from typing import Annotated
from typing import Literal
from typing import Union
# from urllib.parse import ParseResult as URL
# from urllib.parse import urlparse
# from urllib.parse import urlunparse


from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl


class ARXIVMetadata(BaseModel):
    doctype: Literal["arxiv"] = "arxiv"

    title: str = Field(description="arXiv paper title")
    date: str = Field(description="arXiv paper issue date in YYYY format")

    # See https://info.arxiv.org/help/arxiv_identifier.html
    identifier: str = Field(description="arXiv paper identifier")


class EXTRAMetadata(BaseModel):
    doctype: Literal["extra"] = "extra"

    title: str = Field(description="The concise title of the article or page")
    date: str = Field(
        description="The issue date as YYYY/MM/DD format (????/??/?? if unknown)"
    )


PageMetadata = Annotated[
    Union[ARXIVMetadata, EXTRAMetadata], Field(discriminator="doctype")
]


class Page(BaseModel):
    url: HttpUrl
    metadata: PageMetadata
