import sys
import os
import json
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src')))

mock_modules = {
    'pydantic': MagicMock(),
    'langchain_google_genai': MagicMock(),
    'langchain_core': MagicMock(),
    'langchain_core.prompts': MagicMock(),
    'arxiv': MagicMock(),
    'gql': MagicMock(),
    'gql.transport.requests': MagicMock(),
}

with patch.dict('sys.modules', mock_modules):
    import endpoint.readit.app.summarize_other
    from endpoint.readit.app.summarize_other import main

def test_summarize_other_success(tmp_path):
    runner = CliRunner()
    output_path = tmp_path / "output.json"

    with patch.object(endpoint.readit.app.summarize_other, "page_of_") as mock_page_of:
        mock_page = MagicMock()
        mock_page.asdict.return_value = {"title": "Test Title", "date": "2023/10/01"}
        mock_page_of.return_value = mock_page

        result = runner.invoke(main, ["-o", str(output_path), "http://example.com"])

        assert result.exit_code == 0
        assert os.path.exists(output_path)
        with open(output_path) as f:
            data = json.load(f)
            assert data == {"title": "Test Title", "date": "2023/10/01"}

def test_summarize_other_error(tmp_path):
    runner = CliRunner()
    output_path = tmp_path / "output.json"

    with patch.object(endpoint.readit.app.summarize_other, "page_of_") as mock_page_of:
        mock_page_of.side_effect = Exception("Simulated fetch error")

        result = runner.invoke(main, ["-o", str(output_path), "http://non-existent-domain.test"])

        assert result.exit_code != 0
        assert "Simulated fetch error" in str(result.exception) or "Simulated fetch error" in result.output
        assert not os.path.exists(output_path)
