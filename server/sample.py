from pprint import pp

from endpoint.readit.data import ARXIVMetadata

# from endpoint.readit.data import EXTRAMetadata
from endpoint.readit.data import Page

d1 = Page(
    url="http://arxiv.org/C",
    metadata=ARXIVMetadata(title="A", date="2026", identifier="C"),
)

pp(d1)

# if url.netloc is arxiv
#   Create Summary with arXiv URL
# Otherwise
#   Create Summary with LLM & Trafilatura
