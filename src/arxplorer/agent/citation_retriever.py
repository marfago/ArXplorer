import logging
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor

from arxplorer.common.semanticscholar import fetch_citation_counts
from arxplorer.persitence.database import DbOperations


class CitationsRetriever:
    """
    A class to retrieve citation counts for papers in batches.

    This class manages the retrieval of citation counts for papers stored in a database.
    It processes papers in batches, fetches their citation counts, and updates the database.

    Attributes:
        logger (logging.Logger): Logger for this class.
        _sleep_time (int): Time to sleep between full processing cycles.
        _stop_event (threading.Event): Event to signal stopping of the retrieval process.
        _executor (ThreadPoolExecutor): Executor for running the retrieval process.
        _batch_size (int): Number of papers to process in each batch.
    """

    def __init__(self, sleep_time: int = 30, batch_size: int = 50):
        """
        Initialize the CitationsRetriever.

        Args:
            sleep_time (int): Time to sleep between full processing cycles (default: 30 seconds).
            batch_size (int): Number of papers to process in each batch (default: 50).
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._sleep_time = sleep_time
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(1)
        self._batch_size = batch_size

    def _run(self):
        """
        Main method to run the citation retrieval process.

        This method fetches paper IDs, processes them in batches, retrieves citation counts,
        and updates the database. It continues running until stopped.
        """
        if self._stop_event.is_set():
            return

        paper_ids = DbOperations.get_all_paper_ids()
        self.logger.debug(f"Retrieved {len(paper_ids)} paper IDs")

        for i in range(0, len(paper_ids), self._batch_size):
            if self._stop_event.is_set():
                break

            batch = paper_ids[i : i + self._batch_size]
            self.logger.info(f"Processing batch {i // self._batch_size + 1}, size: {len(batch)}")

            try:
                citation_counts = fetch_citation_counts(batch)
                self.logger.info(f"Retrieved citation counts for {len(citation_counts)} papers")

                # Prepare data for database update
                citation_data = list(zip(batch, citation_counts))
                self.logger.debug(f"Citations: {citation_data}")

                # Update the database with new citation counts
                DbOperations.update_citations(citation_data)
                self.logger.info("Updated database with new citation counts")

            except Exception as e:
                self.logger.error(f"Error processing batch: {e}")

            # Sleep between batches to avoid overwhelming the API
            time.sleep(5)

        if not self._stop_event.is_set():
            self.logger.info(f"Finished processing all papers. Sleeping for {self._sleep_time} seconds")
            time.sleep(self._sleep_time)
            self._executor.submit(self._run)

    def start(self):
        """
        Start the citation retrieval process.

        This method initiates the citation retrieval process in a separate thread.
        """
        self.logger.info("Starting CitationsRetriever")
        self._executor.submit(self._run)

    def stop(self):
        """
        Stop the citation retrieval process.

        This method signals the citation retrieval process to stop.
        """
        self.logger.info("Stopping CitationsRetriever")
        self._stop_event.set()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    c = CitationsRetriever(sleep_time=60, batch_size=100)  # Run every 60 seconds, process in batches of 50
    c.start()
    try:
        # Run for 10 minutes
        time.sleep(600)
    finally:
        c.stop()
        time.sleep(10)  # Allow time for the current batch to finish
