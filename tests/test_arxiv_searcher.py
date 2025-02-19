from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest

from arxplorer.agent.arxiv_searcher import (
    ArxivSearcher,
    ArxivPaper,
    ArxivApiQueryGenerator,
    to_pydantic_model,
)


@pytest.fixture
def arxiv_searcher():
    with patch("arxplorer.agent.arxiv_searcher.dspy.ChainOfThought") as mock_predict:
        # Mock the predictor to return a consistent result
        mock_predictor = Mock()
        mock_predictor.return_value = Mock(arxiv_query="mocked_query")
        mock_predict.return_value = mock_predictor

        yield ArxivSearcher(llm_model="mock_model", num_retries=3, max_tokens=8192)


@pytest.fixture
def sample_paper():
    return {
        "paper_id": "2101.12345",
        "published": "2021-01-01",
        "title": "Sample Paper Title",
        "authors": "John Doe, Jane Smith",
        "published_first_time": "2021-01-01",
        "primary_category": "cs.AI",
        "categories": "cs.AI, cs.LG",
        "links": "http://arxiv.org/abs/2101.12345",
        "abstract": "This is a sample paper abstract.",
    }


def test_arxiv_searcher_initialization(arxiv_searcher):
    assert isinstance(arxiv_searcher, ArxivSearcher)
    assert arxiv_searcher.llm_model == "mock_model"


@patch("arxplorer.agent.arxiv_searcher.ArxivCrawler")
@patch("arxplorer.agent.arxiv_searcher.dspy.LM")
def test_arxiv_searcher_forward(mock_lm, mock_arxiv_crawler, arxiv_searcher, sample_paper):
    mock_crawler_instance = Mock()
    mock_crawler_instance.search.return_value = [sample_paper for x in range(30)]
    mock_arxiv_crawler.return_value = mock_crawler_instance

    result = arxiv_searcher("test user query")

    mock_crawler_instance.search.assert_called_once_with("mocked_query", max_results=50)
    assert len(result) == 30
    assert isinstance(result[0], ArxivPaper)


def test_to_pydantic_model(sample_paper):
    paper = to_pydantic_model(sample_paper)
    assert isinstance(paper, ArxivPaper)
    assert paper.paper_id == "2101.12345"
    assert paper.published == date(2021, 1, 1)
    assert paper.title == "Sample Paper Title"
    assert paper.authors == "John Doe, Jane Smith"
    assert paper.primary_category == "cs.AI"
    assert paper.categories == "cs.AI, cs.LG"


def test_arxiv_api_query_generator():
    # Create a mock input
    mock_input = {
        "user_query": "Sample user query",
        "query_title": "A query title",
        "arxiv_query": "cat:cs.AI AND all:neural networks",
        "current_date": str(datetime.now()),
    }

    # Create the generator with mock input
    generator = ArxivApiQueryGenerator(**mock_input)

    # Check if all required fields are present
    assert hasattr(generator, "user_query")
    assert hasattr(generator, "arxiv_query")

    # Verify the values
    assert generator.user_query == "Sample user query"
    assert generator.arxiv_query == "cat:cs.AI AND all:neural networks"


@pytest.mark.parametrize(
    "input_query, expected_categories",
    [
        ("Machine learning papers", ["cs.LG"]),
        ("Artificial intelligence and robotics", ["cs.AI", "cs.RO"]),
        ("Computer vision and natural language processing", ["cs.CV", "cs.CL"]),
    ],
)
def test_arxiv_searcher_category_selection(arxiv_searcher, input_query, expected_categories, sample_paper):
    with patch("arxplorer.agent.arxiv_searcher.ArxivCrawler") as mock_crawler:
        mock_crawler_instance = Mock()
        mock_crawler_instance.search.return_value = [sample_paper for x in range(30)]  # Return a non-empty list
        mock_crawler.return_value = mock_crawler_instance

        with patch.object(arxiv_searcher.predictor, "return_value") as mock_prediction:
            mock_prediction.arxiv_query = f"cat:{' '.join(expected_categories)}"
            arxiv_searcher(input_query)

        called_query = mock_crawler_instance.search.call_args[0][0]
        for category in expected_categories:
            assert f"{category}" in called_query


@pytest.mark.parametrize(
    "input_query, expected_keywords",
    [
        ("Neural network calibration", ["neural network", "calibration"]),
        ("Activation functions", ["activation", "functions"]),
        ("Transformer architecture", ["transformer", "architecture"]),
    ],
)
def test_arxiv_searcher_keyword_inclusion(arxiv_searcher, input_query, expected_keywords, sample_paper):
    with patch("arxplorer.agent.arxiv_searcher.ArxivCrawler") as mock_crawler:
        mock_crawler_instance = Mock()
        mock_crawler_instance.search.return_value = [sample_paper for x in range(30)]  # Return a non-empty list
        mock_crawler.return_value = mock_crawler_instance

        with patch.object(arxiv_searcher.predictor, "return_value") as mock_prediction:
            mock_prediction.arxiv_query = " AND ".join(expected_keywords)
            arxiv_searcher(input_query)

        called_query = mock_crawler_instance.search.call_args[0][0]
        for keyword in expected_keywords:
            assert keyword.lower() in called_query.lower()


def test_arxiv_searcher_empty_result_handling(arxiv_searcher):
    with (
        patch("arxplorer.agent.arxiv_searcher.ArxivCrawler") as mock_crawler,
        patch("arxplorer.agent.arxiv_searcher.dspy.Suggest") as mock_suggest,
    ):
        mock_crawler_instance = Mock()
        mock_crawler_instance.search.return_value = []
        mock_crawler.return_value = mock_crawler_instance

        arxiv_searcher("Query with no results")

        mock_suggest.assert_called_once()


def test_arxiv_paper_model():
    paper_data = {
        "paper_id": "2101.12345",
        "published": "2021-01-01",
        "title": "Test Paper",
        "authors": "John Doe",
        "published_first_time": "2021-01-01",
        "primary_category": "cs.AI",
        "categories": "cs.AI",
        "links": "http://arxiv.org/abs/2101.12345",
        "abstract": "Test abstract",
        "comment": "Test comment",
        "journal_ref": "Test Journal, 2021",
        "doi": "10.1234/test.doi",
    }
    paper = ArxivPaper(**paper_data)
    assert paper.paper_id == "2101.12345"
    assert paper.published == date(2021, 1, 1)
    assert paper.title == "Test Paper"
    assert paper.authors == "John Doe"
    assert paper.primary_category == "cs.AI"
    assert paper.comment == "Test comment"
    assert paper.journal_ref == "Test Journal, 2021"
    assert paper.doi == "10.1234/test.doi"


if __name__ == "__main__":
    pytest.main()
