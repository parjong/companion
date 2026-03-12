import json
from unittest.mock import patch
from click.testing import CliRunner
from endpoint.readit.app.send_to_personal import main

def test_main_arxiv(tmp_path):
    # Prepare dummy page data
    page_data = {
        "url": "https://arxiv.org/abs/1234.5678",
        "title": "Arxiv Paper",
        "date": "2023/01/01",
        "kind": "arxiv",
        "metadata": {"summary": "summary", "year": "2023"}
    }
    summary_file = tmp_path / "summary_arxiv.json"
    summary_file.write_text(json.dumps(page_data))

    with patch("endpoint.readit.app.send_to_personal.PersonalStorage") as MockStorage:
        mock_storage_instance = MockStorage.return_value
        runner = CliRunner()
        result = runner.invoke(main, [str(summary_file)])

        assert result.exit_code == 0
        mock_storage_instance.add_arXiv_article.assert_called_once()
        mock_storage_instance.add_other_article.assert_not_called()

def test_main_other(tmp_path):
    # Prepare dummy page data
    page_data = {
        "url": "https://example.com",
        "title": "Other Page",
        "date": "2023/01/01",
        "kind": "other",
        "metadata": {}
    }
    summary_file = tmp_path / "summary_other.json"
    summary_file.write_text(json.dumps(page_data))

    with patch("endpoint.readit.app.send_to_personal.PersonalStorage") as MockStorage:
        mock_storage_instance = MockStorage.return_value
        runner = CliRunner()
        result = runner.invoke(main, [str(summary_file)])

        assert result.exit_code == 0
        mock_storage_instance.add_other_article.assert_called_once()
        mock_storage_instance.add_arXiv_article.assert_not_called()

def test_main_fallback(tmp_path):
    # Prepare dummy page data with unknown kind
    page_data = {
        "url": "https://example.com/unknown",
        "title": "Unknown Kind Page",
        "date": "2023/01/01",
        "kind": "unknown",
        "metadata": {}
    }
    summary_file = tmp_path / "summary_unknown.json"
    summary_file.write_text(json.dumps(page_data))

    with patch("endpoint.readit.app.send_to_personal.PersonalStorage") as MockStorage:
        mock_storage_instance = MockStorage.return_value
        runner = CliRunner()
        result = runner.invoke(main, [str(summary_file)])

        assert result.exit_code == 0
        # Should fallback to add_other_article
        mock_storage_instance.add_other_article.assert_called_once()
        mock_storage_instance.add_arXiv_article.assert_not_called()
