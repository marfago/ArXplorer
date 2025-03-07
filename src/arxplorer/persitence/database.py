import hashlib
import json
import time
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine.row import RowProxy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from arxplorer.configuration import ConfigurationManager


class QueryStatus(Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    TO_DELETE = "TO_DELETE"


@lru_cache
def _get_query_key(query_text: str) -> str:
    return hashlib.md5(query_text.encode()).hexdigest()


def _row_to_dict(row):
    row = row._asdict() if isinstance(row, RowProxy) else row
    if "created_at" in row:
        row["created_at"] = datetime.fromtimestamp(row["created_at"] / 1_000).isoformat()
    if "updated_at" in row:
        row["updated_at"] = datetime.fromtimestamp(row["updated_at"] / 1_000).isoformat()
    return row


def now_utc_millis() -> int:
    return int(time.time_ns() // 1_000_000)


class DbManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DbManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self, db_url=None):
        if db_url is None:
            db_name = ConfigurationManager().get_db_name()
            db_url = f"sqlite:///{db_name}"
        self.engine = create_engine(db_url, poolclass=QueuePool)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()


class DbContext:
    def __init__(self):
        self.db_manager = DbManager()
        self.session = None

    def __enter__(self):
        self.session = self.db_manager.get_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()


def db_operation(func):
    def wrapper(*args, **kwargs):
        with DbContext() as db:
            return func(db, *args, **kwargs)

    return wrapper


class DbOperations:

    @staticmethod
    @db_operation
    def create_or_update_tables(db):
        db.session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS query (
                query_id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """
            )
        )

        db.session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS paper (
                paper_id TEXT PRIMARY KEY,
                published TEXT,
                title TEXT,
                authors TEXT,
                published_first_time TEXT,
                comment TEXT,
                journal_ref TEXT,
                doi TEXT,
                primary_category TEXT,
                categories TEXT,
                links TEXT,
                github_links TEXT,
                abstract TEXT,
                content TEXT,
                citations INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """
            )
        )

        db.session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS query_paper (
                query_id TEXT,
                paper_id TEXT,
                relevance_score REAL,
                relevance_score_brief_explanation TEXT,
                relevance_score_explanation TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (query_id, paper_id),
                FOREIGN KEY (query_id) REFERENCES query (query_id),
                FOREIGN KEY (paper_id) REFERENCES paper (paper_id)
            )
        """
            )
        )

        db.session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS paper_references (
                source_id TEXT,
                reference_id TEXT,
                PRIMARY KEY (source_id, reference_id),
                FOREIGN KEY (source_id) REFERENCES paper (paper_id),
                FOREIGN KEY (reference_id) REFERENCES paper (paper_id)
            )
        """
            )
        )

        db.session.execute(text("VACUUM"))

    @staticmethod
    @db_operation
    def add_query(db, query_text):
        query_id = _get_query_key(query_text=query_text)
        now = now_utc_millis()
        db.session.execute(
            text(
                """
            INSERT OR IGNORE INTO query (query_id, query_text, status, created_at, updated_at)
            VALUES (:query_id, :query_text, :status, :created_at, :updated_at)
        """
            ),
            {
                "query_id": query_id,
                "query_text": query_text,
                "status": QueryStatus.RUNNING.value,
                "created_at": now,
                "updated_at": now,
            },
        )
        return query_id

    @staticmethod
    @db_operation
    def add_paper(
        db,
        query_text,
        paper_dict,
        relevance_score=None,
        relevance_score_brief_explanation=None,
        relevance_score_explanation=None,
        github_links=None,
    ):
        query_id = _get_query_key(query_text=query_text)
        now = now_utc_millis()

        db.session.execute(
            text(
                """
            INSERT OR IGNORE INTO query (query_id, query_text, status, created_at, updated_at)
            VALUES (:query_id, :query_text, :status, :created_at, :updated_at)
        """
            ),
            {
                "query_id": query_id,
                "query_text": query_text,
                "status": QueryStatus.RUNNING.value,
                "created_at": now,
                "updated_at": now,
            },
        )

        paper_dict["created_at"] = now
        paper_dict["updated_at"] = now
        paper_dict["github_links"] = json.dumps(github_links) if github_links else "{}"

        columns = ", ".join(paper_dict.keys())
        placeholders = ", ".join(f":{key}" for key in paper_dict.keys())

        db.session.execute(
            text(
                f"""
            INSERT OR REPLACE INTO paper ({columns})
            VALUES ({placeholders})
        """
            ),
            paper_dict,
        )

        db.session.execute(
            text(
                """
                INSERT OR REPLACE INTO query_paper
                (query_id, paper_id, relevance_score, relevance_score_brief_explanation, relevance_score_explanation, created_at, updated_at)
                VALUES (:query_id, :paper_id, :relevance_score, :relevance_score_brief_explanation, :relevance_score_explanation, :created_at, :updated_at)
                """  # noqa: B950
            ),
            {
                "query_id": query_id,
                "paper_id": paper_dict["paper_id"],
                "relevance_score": relevance_score,
                "relevance_score_brief_explanation": relevance_score_brief_explanation,
                "relevance_score_explanation": relevance_score_explanation,
                "created_at": now,
                "updated_at": now,
            },
        )

    @staticmethod
    @db_operation
    def get_queries(db, status=None):
        query = "SELECT * FROM query"
        params = {}

        if status:
            query += " WHERE status = :status"
            params["status"] = status.value

        query += " ORDER BY created_at DESC"

        result = db.session.execute(text(query), params)
        return [_row_to_dict(row) for row in result]

    @staticmethod
    @db_operation
    def get_query(db, id):
        result = db.session.execute(text("SELECT * FROM query WHERE query_id = :id"), {"id": id})
        row = result.fetchone()
        return _row_to_dict(row) if row else None

    @staticmethod
    @db_operation
    def get_papers(db, query_id: str, relevance_score: int = None):
        query = """
            SELECT p.*, qp.relevance_score,
                   qp.relevance_score_brief_explanation, qp.relevance_score_explanation
            FROM paper p
            JOIN query_paper qp ON p.paper_id = qp.paper_id
            WHERE qp.query_id = :query_id AND qp.relevance_score IS NOT NULL
        """
        params = {"query_id": query_id}

        if relevance_score is not None:
            query += " AND qp.relevance_score >= :relevance_score"
            params["relevance_score"] = relevance_score

        query += " ORDER BY qp.relevance_score DESC, p.created_at DESC"

        result = db.session.execute(text(query), params)
        return [_row_to_dict(row) for row in result]

    @staticmethod
    @db_operation
    def paper_exists(db, query_text: str, paper_id: str) -> bool:
        query_id = _get_query_key(query_text)
        result = db.session.execute(
            text(
                """
            SELECT 1
            FROM query_paper
            WHERE query_id = :query_id AND paper_id = :paper_id
            LIMIT 1
        """
            ),
            {"query_id": query_id, "paper_id": paper_id},
        )
        return result.fetchone() is not None

    @staticmethod
    @db_operation
    def get_query_stats(db, query_id: str) -> dict:
        total_papers = db.session.execute(
            text(
                """
            SELECT COUNT(*) as total_papers
            FROM query_paper
            WHERE query_id = :query_id
        """
            ),
            {"query_id": query_id},
        ).scalar()

        relevance_scores = db.session.execute(
            text(
                """
            SELECT relevance_score, COUNT(*) as count
            FROM query_paper
            WHERE query_id = :query_id AND relevance_score IS NOT NULL
            GROUP BY relevance_score
            ORDER BY relevance_score DESC
        """
            ),
            {"query_id": query_id},
        ).fetchall()

        query_times = db.session.execute(
            text(
                """
            SELECT created_at, updated_at
            FROM query
            WHERE query_id = :query_id
        """
            ),
            {"query_id": query_id},
        ).fetchone()

        if query_times:
            created_at = datetime.fromtimestamp(query_times[0] / 1_000).isoformat()
            updated_at = datetime.fromtimestamp(query_times[1] / 1_000).isoformat()
        else:
            created_at = updated_at = None

        return {
            "total_papers": total_papers,
            "papers_by_relevance_score": {row[0]: row[1] for row in relevance_scores},
            "query_created_at": created_at,
            "query_last_updated_at": updated_at,
        }

    @staticmethod
    @db_operation
    def delete_query(db, query_id):
        db.session.execute(text("DELETE FROM query_paper WHERE query_id = :query_id"), {"query_id": query_id})
        db.session.execute(text("DELETE FROM query WHERE query_id = :query_id"), {"query_id": query_id})

    @staticmethod
    @db_operation
    def _update_query_status(db, query_id, new_status):
        now = now_utc_millis()
        result = db.session.execute(
            text(
                """
            UPDATE query
            SET status = :status, updated_at = :updated_at
            WHERE query_id = :query_id
        """
            ),
            {"status": new_status.value, "updated_at": now, "query_id": query_id},
        )
        return result.rowcount > 0

    @classmethod
    def set_running_query(cls, query_id):
        return cls._update_query_status(query_id=query_id, new_status=QueryStatus.RUNNING)

    @classmethod
    def set_stop_query(cls, query_id):
        return cls._update_query_status(query_id=query_id, new_status=QueryStatus.STOPPED)

    @classmethod
    def set_to_delete_query(cls, query_id):
        return cls._update_query_status(query_id=query_id, new_status=QueryStatus.TO_DELETE)

    @staticmethod
    @db_operation
    def update_citations(db, paper_citations: List[Tuple[str, int]]):
        now = now_utc_millis()
        db.session.execute(
            text(
                """
            UPDATE paper
            SET citations = :citations, updated_at = :updated_at
            WHERE paper_id = :paper_id
        """
            ),
            [{"citations": citations, "updated_at": now, "paper_id": paper_id} for paper_id, citations in paper_citations],
        )

    @staticmethod
    @db_operation
    def get_all_paper_ids(db) -> List[str]:
        result = db.session.execute(text("SELECT DISTINCT paper_id FROM paper"))
        return [row[0] for row in result]

    @staticmethod
    @db_operation
    def add_references(db, references: List[Tuple[str, str]]):
        db.session.execute(
            text(
                """
            INSERT OR IGNORE INTO paper_references (source_id, reference_id)
            VALUES (:source_id, :reference_id)
        """
            ),
            [{"source_id": source_id, "reference_id": reference_id} for source_id, reference_id in references],
        )


# Usage example
if __name__ == "__main__":  # pragma: no cover
    db_file = "research_db.sqlite"

    DbManager().initialize(f"sqlite:///{db_file}")

    # Create tables
    DbOperations.create_or_update_tables()

    # Add a paper (which also adds a query)
    paper_attributes = {
        "paper_id": "2305.1234",
        "published": "2023-05-01",
        "title": "Advanced ML Techniques",
        "authors": "John Doe, Jane Smith",
        "published_first_time": "2023-04-15",
        "comment": "Groundbreaking research",
        "journal_ref": "Journal of AI, Vol. 5",
        "doi": "10.1234/ai.2023.001",
        "primary_category": "cs.AI",
        "categories": json.dumps(["cs.AI", "cs.LG"]),
        "links": "https://example.com/paper",
        "abstract": "This paper presents advanced ML techniques.",
        "content": "Full paper content...",
    }
    DbOperations.add_paper("Machine Learning", paper_attributes, relevance_score=95)

    # Get queries
    print("All queries:")
    print(json.dumps(DbOperations.get_queries(), indent=2))

    # Get papers for a query
    query_id = hashlib.md5("Machine Learning".encode()).hexdigest()
    print("\nPapers for query_id:")
    print(json.dumps(DbOperations.get_papers(query_id), indent=2))

    # Update citations for multiple papers
    paper_citations = [("2305.1234", 10), ("2305.5678", 5), ("2305.9012", 15)]
    DbOperations.update_citations(paper_citations)

    # Get all paper IDs
    all_paper_ids = DbOperations.get_all_paper_ids()
    print("\nAll paper IDs:")
    print(json.dumps(all_paper_ids, indent=2))

    # Get papers for a query (now including citations)
    # Get papers for a query (now including citations)
    print("\nPapers for query_id (including citations):")
    print(json.dumps(DbOperations.get_papers(query_id), indent=2))

    # Add references
    references = [
        ("2305.1234", "2305.5678"),
        ("2305.1234", "2305.9012"),
        ("2305.5678", "2305.9012"),
    ]
    DbOperations.add_references(references)

    # Get query stats
    print("\nQuery stats:")
    print(json.dumps(DbOperations.get_query_stats(query_id), indent=2))

    # Update query status
    DbOperations.set_stop_query(query_id)
    print("\nUpdated query status:")
    print(json.dumps(DbOperations.get_query(query_id), indent=2))

    # Delete query
    DbOperations.delete_query(query_id)
    print("\nRemaining queries after deletion:")
    print(json.dumps(DbOperations.get_queries(), indent=2))
