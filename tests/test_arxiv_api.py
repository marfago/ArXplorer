import os
import shutil
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from arxiv import SortCriterion, SortOrder, Result


@pytest.fixture
def temp_dir():
    # Create a temporary directory for the test
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up the directory after tests
    shutil.rmtree(temp_dir)


def do_nothing(*args, **kwargs):
    return "Extracted content"


@pytest.fixture
def arxiv_crawler(temp_dir):
    from arxplorer.common.arxiv_api import ArxivCrawler

    return ArxivCrawler(cache_folder=temp_dir, converter=do_nothing)


@pytest.fixture
def mock_arxiv_result():
    author1 = Mock()
    author1.name = "John Doe"

    author2 = Mock()
    author2.name = "Jane Smith"

    mock_result = Mock(spec=Result)
    mock_result.get_short_id.return_value = "2101.12345"
    mock_result.updated = datetime(2021, 1, 1)
    mock_result.title = "Test Paper"
    mock_result.authors = [author1, author2]
    mock_result.published = datetime(2021, 1, 1)
    mock_result.comment = "Test comment"
    mock_result.journal_ref = "Test Journal"
    mock_result.doi = "10.1234/test.doi"
    mock_result.primary_category = "cs.AI"
    mock_result.categories = ["cs.AI", "cs.LG"]
    mock_result.links = [Mock(href="http://arxiv.org/abs/2101.12345")]
    mock_result.summary = "Test abstract"
    mock_result._get_default_filename.return_value = "2101.12345.pdf"
    mock_result.pdf_url = "http://arxiv.org/pdf/2101.12345"
    return mock_result


def test_arxiv_crawler_init(temp_dir):
    from arxplorer.common.arxiv_api import ArxivCrawler

    crawler = ArxivCrawler(cache_folder=temp_dir)
    assert crawler._cache_folder == temp_dir
    assert os.path.exists(temp_dir)


@patch("arxplorer.common.arxiv_api.Client")
def test_retrieve_by_ids(mock_client, arxiv_crawler, mock_arxiv_result):
    mock_client.return_value.results.return_value = [mock_arxiv_result]

    result = arxiv_crawler.retrieve_by_ids(["2101.12345"])

    assert len(result) == 1
    assert result[0]["paper_id"] == "2101.12345"
    assert result[0]["title"] == "Test Paper"
    assert result[0]["content"] == "Extracted content"


@patch("arxplorer.common.arxiv_api.Client")
def test_search(mock_client, arxiv_crawler, mock_arxiv_result):
    mock_client.return_value.results.return_value = [mock_arxiv_result]

    result = arxiv_crawler.search("test query", max_results=5)

    assert len(result) == 1
    assert result[0]["paper_id"] == "2101.12345"
    mock_client.return_value.results.assert_called_once()


def test_to_dict(mock_arxiv_result):
    from arxplorer.common.arxiv_api import ArxivCrawler

    result = ArxivCrawler._to_dict(mock_arxiv_result)

    assert result["paper_id"] == "2101.12345"
    assert result["title"] == "Test Paper"
    assert result["authors"] == "John Doe, Jane Smith"
    assert result["primary_category"] == "cs.AI"
    assert result["categories"] == "cs.AI, cs.LG"


@patch("arxplorer.common.arxiv_api.Client")
def test_search_with_sort_options(mock_client, arxiv_crawler):
    arxiv_crawler.search("test", sort_by=SortCriterion.Relevance, sort_order=SortOrder.Ascending)

    mock_client.return_value.results.assert_called_once()
    call_args = mock_client.return_value.results.call_args[1]["search"]
    assert call_args.sort_by == SortCriterion.Relevance
    assert call_args.sort_order == SortOrder.Ascending


@patch("arxplorer.common.arxiv_api.Client")
def test_error_handling(mock_client, arxiv_crawler, caplog):
    mock_client.return_value.results.side_effect = Exception("Test Error")
    result = arxiv_crawler.retrieve_by_ids(["2101.12345"])
    assert len(result) == 0
    assert "An error occurred" in caplog.text


if __name__ == "__main__":
    pytest.main()
