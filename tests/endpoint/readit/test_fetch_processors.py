from endpoint.readit.steps.fetch import DefaultProcessor
from endpoint.readit.steps.fetch import GeekNewsProcessor
from endpoint.readit.steps.fetch import LinkedInProcessor
from endpoint.readit.steps.fetch import get_processor
from endpoint.readit.steps.fetch import merge_broken_lines

MARKDOWN = (
    "## Intro\nthe following is code:\n\n```\nimport os\nimport re\n```\n\n"
    "Paragraph one\nstarts here."
)


def test_default_processor_is_noop():
    assert DefaultProcessor().postprocess_text(MARKDOWN) == MARKDOWN


def test_merge_keeps_headings_and_code_fences():
    merged = merge_broken_lines(MARKDOWN)
    assert "## Intro\nthe following is code:" in merged
    assert "```\nimport os\nimport re\n```" in merged
    assert "Paragraph one starts here." in merged


def test_merge_joins_inline_code_and_broken_sentences():
    assert merge_broken_lines("use `foo`\n함수를 호출") == "use `foo` 함수를 호출"


def test_site_processors_merge_broken_lines():
    text = "hello\nworld"
    assert GeekNewsProcessor().postprocess_text(text) == "hello world"
    assert LinkedInProcessor().postprocess_text(text) == "hello world"


def test_get_processor_matches_hostname_only():
    assert isinstance(
        get_processor("https://news.hada.io/topic?id=1"), GeekNewsProcessor
    )
    assert isinstance(
        get_processor("https://www.linkedin.com/posts/x"), LinkedInProcessor
    )
    assert isinstance(
        get_processor("https://example.com/?ref=linkedin.com"), DefaultProcessor
    )
