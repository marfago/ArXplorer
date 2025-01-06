import time
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import text

from arxplorer.persitence import database
from arxplorer.persitence.database import (
    QueryStatus,
    DbOperations,
    DbManager,
    _get_query_key,
    db_operation,
    _row_to_dict,
    now_utc_millis,
)

# Mock constant for timestamp
MOCK_TIMESTAMP = 1735689600000  # 2025-01-01 00:00:00 UTC in milliseconds
MOCK_DATE = datetime.fromtimestamp(MOCK_TIMESTAMP / 1_000).isoformat()  # localized date


@pytest.fixture(scope="function")
def db_manager():
    # Use an in-memory database for testing
    with patch("arxplorer.configuration.ConfigurationManager") as mock_config:
        mock_config().get_db_name.return_value = ":memory:"
        DbManager().initialize("sqlite:///:memory:")
        DbOperations.create_or_update_tables()
        yield DbManager()
    DbManager().engine.dispose()


@pytest.fixture(scope="function")
def mock_now():
    with patch("arxplorer.persitence.database.now_utc_millis", return_value=MOCK_TIMESTAMP):
        yield


def test_get_query(db_manager, mock_now):
    query_text = "Test Query"
    query_id = DbOperations.add_query(query_text)

    query = DbOperations.get_query(query_id)

    assert query["query_id"] == query_id
    assert query["query_text"] == query_text
    assert query["created_at"] == MOCK_DATE
    assert query["updated_at"] == MOCK_DATE


def test_add_query(db_manager, mock_now):
    query_text = "Test Query"
    query_id = DbOperations.add_query(query_text)

    result = DbOperations.get_query(query_id)

    assert result is not None
    assert result["query_text"] == query_text
    assert result["status"] == QueryStatus.RUNNING.value
    assert result["created_at"] == MOCK_DATE
    assert result["updated_at"] == MOCK_DATE


def test_add_paper(db_manager, mock_now):
    query_text = "Test Query"
    paper_dict = {"paper_id": "test123", "title": "Test Paper", "authors": "Test Author", "abstract": "Test Abstract"}

    DbOperations.add_paper(query_text, paper_dict, relevance_score=0.8)

    papers = DbOperations.get_papers(database._get_query_key(query_text))
    assert len(papers) == 1
    assert papers[0]["paper_id"] == paper_dict["paper_id"]
    assert papers[0]["relevance_score"] == 0.8
    assert papers[0]["created_at"] == MOCK_DATE
    assert papers[0]["updated_at"] == MOCK_DATE


def test_get_queries(db_manager, mock_now):
    DbOperations.add_query("Query 1")
    time.sleep(0.1)  # Make sure we have a different timestamp
    DbOperations.add_query("Query 2")

    queries = DbOperations.get_queries()

    assert len(queries) == 2
    assert {queries[0]["query_text"], queries[1]["query_text"]} == {"Query 1", "Query 2"}
    assert all(query["created_at"] == MOCK_DATE for query in queries)
    assert all(query["updated_at"] == MOCK_DATE for query in queries)


def test_update_query_status(db_manager, mock_now):
    query_text = "Test Query"
    query_id = DbOperations.add_query(query_text)

    DbOperations.set_stop_query(query_id)

    query = DbOperations.get_query(query_id)
    assert query["status"] == QueryStatus.STOPPED.value
    assert query["updated_at"] == MOCK_DATE


def test_update_citations(db_manager, mock_now):
    paper_dict = {"paper_id": "test123", "title": "Test Paper", "authors": "Test Author", "abstract": "Test Abstract"}
    DbOperations.add_paper("Test Query", paper_dict, relevance_score=5)

    DbOperations.update_citations([("test123", 10)])

    papers = DbOperations.get_papers(_get_query_key("Test Query"))
    assert papers[0]["citations"] == 10
    assert papers[0]["updated_at"] == MOCK_DATE


def test_get_all_paper_ids(db_manager):
    paper_dict1 = {"paper_id": "test1", "title": "Test Paper 1"}
    paper_dict2 = {"paper_id": "test2", "title": "Test Paper 2"}

    DbOperations.add_paper("Test Query", paper_dict1)
    DbOperations.add_paper("Test Query", paper_dict2)

    paper_ids = DbOperations.get_all_paper_ids()

    assert set(paper_ids) == {"test1", "test2"}


def test_add_references(db_manager):
    references = [("paper1", "paper2"), ("paper1", "paper3")]

    DbOperations.add_references(references)

    with db_manager.get_session() as session:
        result = session.execute(text("SELECT * FROM paper_references"))
        results = [result._asdict() for result in result.fetchall()]

    assert len(results) == 2
    assert (results[0]["source_id"], results[0]["reference_id"]) == references[0]
    assert (results[1]["source_id"], results[1]["reference_id"]) == references[1]
