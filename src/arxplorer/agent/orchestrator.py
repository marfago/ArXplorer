import logging
import threading
import time

from arxplorer.agent.citation_retriever import CitationsRetriever
from arxplorer.agent.query_agent import ArxivQueryAgent
from arxplorer.common.common import instrument_telemetry, load_env
from arxplorer.persitence.database import QueryStatus, DbOperations


class Orchestrator:

    def __init__(self):
        self._event = threading.Event()
        logging.info("Stopping main orchestrator.")

    def start(self):  # noqa: C901
        """
        Main function to run the ArxivOrchestrator with a timed search.
        """

        citations_retriever = CitationsRetriever(sleep_time=60, batch_size=100)  # Run every 60 seconds, process in batches of 50
        citations_retriever.start()

        active_queries: dict[str, ArxivQueryAgent] = {}

        while not self._event.is_set():
            db_queries = DbOperations.get_queries()

            running_queries = {}
            stopped_queries = {}
            to_delete_queries = {}
            for query in db_queries:
                query_id = query["query_id"]
                if query["status"] == QueryStatus.RUNNING.value:
                    running_queries[query_id] = query
                if query["status"] == QueryStatus.STOPPED.value:
                    stopped_queries[query_id] = query
                if query["status"] == QueryStatus.TO_DELETE.value:
                    to_delete_queries[query_id] = query

            # Remove agents
            for query_id, _ in to_delete_queries.items():
                logging.info(f"Deleting query: {query_id}")
                if query_id in active_queries:
                    active_queries[query_id].stop()
                    del active_queries[query_id]
                DbOperations.delete_query(query_id)

            # Stop agents
            for query_id in set(active_queries.keys()).intersection(set(stopped_queries.keys())):
                logging.info(f"Stopping query: {query_id}")
                active_queries[query_id].stop()
                del active_queries[query_id]

            # Add new agents
            for query_id in set(running_queries.keys()).difference(set(active_queries.keys())):
                if query_id not in active_queries:
                    query = running_queries[query_id]
                    logging.info(f"Adding query {query}")
                    new_orchestrator = ArxivQueryAgent()
                    new_orchestrator.search(query["query_text"])
                    active_queries[query["query_id"]] = new_orchestrator

            time.sleep(2)

        # Stop all agents
        citations_retriever.stop()
        for query_id in active_queries.keys():
            logging.info(f"Stopping query: {query_id}")
            active_queries[query_id].stop()

        logging.info("Main orchestrator stopped")

    def stop(self):
        self._event.set()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    instrument_telemetry()
    load_env()

    Orchestrator().start()
