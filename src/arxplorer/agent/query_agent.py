"""
This module implements an ArXiv query agent that orchestrates the process of searching,
retrieving, assessing, and extracting references from arXiv papers.
"""

import concurrent.futures
import json
import logging
import threading
import time
from queue import PriorityQueue
from typing import Callable

from arxplorer.agent.arxiv_searcher import ArxivSearcher, ArxivPaper
from arxplorer.agent.assessor import ArxivAssessor, ArxivRelevanceAssessment
from arxplorer.agent.references_extractor import ArxivReferenceExtractor, ArxivReference
from arxplorer.common.arxiv_api import (
    ArxivCrawler,
    extract_arxiv_id,
    html_converter,
    pdf_converter,
)
from arxplorer.common.common import catch_errors
from arxplorer.configuration import ConfigurationManager
from arxplorer.fix_dspy import update_dsp_lm_call
from arxplorer.persitence.database import DbOperations

update_dsp_lm_call(max_tokens=ConfigurationManager.get_max_queries_per_minute(), time_in_seconds=60)


class PriorityTask:
    """
    Represents a task with a priority level for use in a priority queue.

    Attributes:
        priority (int): The priority level of the task.
        func (Callable): The function to be executed.
        order (int): A unique identifier for the task (used for tie-breaking).
        args (tuple): Positional arguments for the function.
        kwargs (dict): Keyword arguments for the function.
    """

    def __init__(self, priority: int, func: Callable, order: int, *args, **kwargs):
        self.priority = priority
        self.func = func
        self.order = order
        self.args = args
        self.kwargs = kwargs

    def __lt__(self, other: "PriorityTask") -> bool:
        """Define the less-than operation for priority queue ordering."""
        return (-self.priority, self.order) < (-other.priority, other.order)

    def __repr__(self):
        """String representation of the PriorityTask."""
        return f"{self.priority} - {self.order}"


class PriorityLimitedThreadExecutor:
    """
    Manages a group of tasks with priority and limits on concurrent execution.

    Attributes:
        _task_queue (PriorityQueue): Queue for storing tasks ordered by priority.
        _thread_pool_executor (ThreadPoolExecutor): Executor for running tasks.
        _stop_event (threading.Event): Event for signaling the executor to stop.
        _semaphore (threading.Semaphore): Semaphore for limiting concurrent tasks.
    """

    def __init__(self, max_tasks: int = 10):
        """
        Initialize the PriorityLimitedThreadExecutor.

        Args:
            max_tasks (int): Maximum number of concurrent tasks allowed.
        """
        self._task_queue = PriorityQueue()
        self._thread_pool_executor = concurrent.futures.ThreadPoolExecutor()
        self._stop_event = threading.Event()
        self._semaphore = threading.Semaphore(max_tasks)

    def create_thread(self, func: Callable, priority: int = 0, *args, **kwargs) -> None:
        """
        Creates a new task with the given priority and adds it to the queue.

        Args:
            func (Callable): The function to be executed.
            priority (int): The priority of the task (default is 0).
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        logging.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> QUEUE SIZE: {self._task_queue.qsize()}")
        if self._stop_event.is_set():
            logging.warning("Queue is shutting down. Ignoring submitted task.")
            return

        task = PriorityTask(priority, func, time.time_ns(), *args, **kwargs)

        self._task_queue.put(task)
        self._thread_pool_executor.submit(self._run_next_task)

    def _run_next_task(self) -> None:
        """Runs the next task from the queue."""
        with self._semaphore:
            priority_task = self._task_queue.get_nowait()
            logging.info(f"Executing task with priority {priority_task.priority}. Queue size is {self._task_queue.qsize()}")
            try:
                if self._stop_event.is_set():
                    logging.warning("Queue is shutting down. Ignoring retrieved task.")
                    return
                priority_task.func(*priority_task.args, **priority_task.kwargs)
            finally:
                self._task_queue.task_done()

    def stop(self) -> None:
        """Signals the task group to stop processing new tasks."""
        self._stop_event.set()
        self._thread_pool_executor.shutdown()
        self._task_queue.join()


class ArxivQueryAgent:
    """
    Orchestrates the process of searching, retrieving, assessing, and extracting references from arXiv papers.

    Attributes:
        _logger (logging.Logger): Logger for this class.
        _llm_model (str): The language model to use for various tasks.
        _thread_executor (PriorityLimitedThreadExecutor): Executor for managing concurrent tasks.
        _crawler (ArxivCrawler): Crawler for retrieving papers from arXiv.
        _query_searcher (ArxivSearcher): Searcher for querying arXiv.
        _reference_extractor (ArxivReferenceExtractor): Extractor for finding references in papers.
        _assessor (ArxivAssessor): Assessor for evaluating paper relevance.
    """

    def __init__(self):
        """Initialize the ArxivQueryAgent with necessary components and configurations."""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._llm_model = ConfigurationManager.get_llm_model()
        self._thread_executor = PriorityLimitedThreadExecutor(ConfigurationManager.get_max_parallel_tasks())
        self._crawler = ArxivCrawler(
            cache_folder=ConfigurationManager.get_cache_folder(),
            max_parallel_converters=ConfigurationManager.get_max_parallel_convert_processes(),
            converter=(html_converter if ConfigurationManager.is_fast_conversion() else pdf_converter),
        )
        self._query_searcher = ArxivSearcher(
            llm_model=self._llm_model, num_retries=ConfigurationManager.get_llm_client_max_num_retries()
        )
        self._reference_extractor = ArxivReferenceExtractor(
            llm_model=self._llm_model, num_retries=ConfigurationManager.get_llm_client_max_num_retries()
        )
        self._assessor = ArxivAssessor(
            llm_model=self._llm_model, num_retries=ConfigurationManager.get_llm_client_max_num_retries()
        )

    @catch_errors()
    def _search_for_papers(self, user_query: str) -> None:
        """
        Searches for papers based on the user query and creates retrieve tasks for each paper found.

        Args:
            user_query (str): The user's search query.
        """
        papers: list[ArxivPaper] = self._query_searcher(user_query=user_query, temperature=0, max_results=300)
        for paper in papers:
            self._logger.info(f"Adding a retrieve task for paper {paper}")
            self._thread_executor.create_thread(self._retrieve_papers, 1, 3, paper.paper_id, user_query)

    @catch_errors()
    def _retrieve_papers(self, relevance: int, paper_id: str, user_query: str) -> None:
        """
        Retrieves a paper and creates tasks for assessment and reference extraction.

        Args:
            relevance (int): The relevance score of the paper.
            paper_id (str): The ID of the paper to retrieve.
            user_query (str): The original user query.
        """
        if DbOperations.paper_exists(user_query, paper_id):
            self._logger.debug(f"Paper {paper_id} already processed")
            return

        self._logger.info(f"Retrieving paper id: {paper_id} with relevance {relevance}")
        crawler = self._crawler
        retrieved_papers: list[dict] = crawler.retrieve_by_ids([paper_id])
        self._logger.info(f"Paper id: {paper_id} retrieved")

        if retrieved_papers:
            for retrieved_paper in retrieved_papers:
                self._thread_executor.create_thread(self._assess_papers, relevance, retrieved_paper, user_query)
                self._thread_executor.create_thread(self._extract_references, relevance, retrieved_paper, user_query)

    @catch_errors()
    def _assess_papers(self, paper: dict, user_query: str) -> None:
        """
        Assesses the relevance of a paper to the user query.

        Args:
            paper (dict): The paper to assess.
            user_query (str): The original user query.
        """
        if DbOperations.paper_exists(user_query, paper["paper_id"]):
            self._logger.debug(f"Paper {paper['paper_id']} already processed")
            return

        self._logger.debug(f"Assessing paper id: {paper['paper_id']}")

        assessment: ArxivRelevanceAssessment = self._assessor(query=user_query, paper=paper)
        self._logger.info(f"Paper id: {paper['paper_id']} assessed")
        self._logger.debug(
            f"arxiv: {paper['paper_id']} - "
            f"relevance: {assessment.relevance_score} - "
            f"last retrieved paper title: {paper['title']} - "
            f"paper relevance: {assessment.relevance_score_explanation}"
        )

        self._logger.info(f"Found paper {paper['paper_id']} - {assessment.relevance_score} - {paper['title']}")
        self._persist_assessed_paper(paper, assessment, user_query)

    @catch_errors()
    def _extract_references(self, paper: dict, user_query: str) -> None:
        """
        Extracts references from a paper and creates retrieve tasks for relevant references.

        Args:
            paper (dict): The paper from which to extract references.
            user_query (str): The original user query.
        """
        if DbOperations.paper_exists(user_query, paper["paper_id"]):
            self._logger.debug(f"Paper {paper['paper_id']} already processed")
            return

        self._logger.info(f"Extracting references from paper with id: {paper['paper_id']}")

        references: list[ArxivReference] = self._reference_extractor(query=user_query, paper=paper["content"])
        self._logger.info(f"Extracted {len(references)} reference(s) from paper with id: {paper['paper_id']}")
        counter = 0
        for reference in references:
            ref_arxiv_id = extract_arxiv_id(reference.arxiv_id)
            if ref_arxiv_id:
                counter += 1
                self._logger.debug(
                    f"Added reference to the queue: {ref_arxiv_id} - {reference.relevance_score} - {reference.title}"
                )
                self._thread_executor.create_thread(
                    self._retrieve_papers,
                    reference.relevance_score,
                    reference.relevance_score,
                    ref_arxiv_id,
                    user_query,
                )
        if not counter:
            self._logger.warning(f"No references found in paper with id: {paper['paper_id']}")

    @catch_errors()
    def _persist_assessed_paper(self, paper: dict, assessment: ArxivRelevanceAssessment, user_query: str) -> None:
        """
        Persists the assessed paper to the database.

        Args:
            paper (dict): The paper to persist.
            assessment (ArxivRelevanceAssessment): The assessment of the paper.
            user_query (str): The original user query.
        """
        DbOperations.add_paper(
            query_text=user_query,
            relevance_score=assessment.relevance_score,
            relevance_score_explanation=assessment.relevance_score_explanation,
            relevance_score_brief_explanation=assessment.relevance_score_brief_explanation,
            github_links=json.dumps(assessment.github_links),
            paper_dict=paper,
        )

    def search(self, user_query: str) -> str:
        """
        Initiates the search process for the given user query.

        Args:
            user_query (str): The user's search query.

        Returns:
            str: The query ID assigned by the database.
        """
        query_id = DbOperations.add_query(user_query)
        self._thread_executor.create_thread(self._search_for_papers, 5, user_query)
        return query_id

    def stop(self) -> None:
        """Stops the orchestrator by signaling the task group to stop processing new tasks."""
        self._logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Stopping orchestrator <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        self._thread_executor.stop()
        self._logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Orchestrator stopped <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
