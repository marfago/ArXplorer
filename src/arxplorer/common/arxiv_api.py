import logging
import os
import os.path
import re
import tempfile
import threading
import time

from arxiv import Client, Search, SortCriterion, SortOrder, Result
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.datamodel.pipeline_options import (
    AcceleratorOptions,
    AcceleratorDevice,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

NANOS_IN_SEC = 1_000_000_000
SECS_IN_MINUTE = 60

NUM_CPUS = os.cpu_count()


def extract_arxiv_id(text: str):
    if not text:
        return None
    pattern = r"(arxiv:)?[\s:]*([a-z]+(?:\.[a-z]+)?\/\d{7}|\d{4}\.\d{4,5}(?:v\d+)?)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return matches[-1][1] if len(matches) > 0 else None


def pdf_converter(arxiv_id, num_threads) -> str:
    start_time = time.time_ns()

    logging.info(f">>>>>>> Converting {arxiv_id} to markdown.")

    accelerator_options = AcceleratorOptions(num_threads=num_threads, device=AcceleratorDevice.AUTO)

    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = accelerator_options
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.document_timeout = 5 * SECS_IN_MINUTE

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )

    result = converter.convert(f"https://arxiv.org/pdf/{arxiv_id}")
    if result.status != ConversionStatus.SUCCESS:
        logging.warning(f"{arxiv_id} conversion failed with {result.status}")
        raise ValueError("The PDF conversion was partial or unsuccessful.")

    content = result.document.export_to_markdown()
    conversion_time = (time.time_ns() - start_time) // NANOS_IN_SEC
    logging.info(f"<<<<<<<< {arxiv_id} converted to markdown in {conversion_time} secs")
    return content


def html_converter(arxiv_id, num_threads) -> str:
    start_time = time.time_ns()

    converter = DocumentConverter()
    try:
        result = converter.convert(f"https://ar5iv.org/html/{arxiv_id}")
    except Exception:
        logging.exception(f"An error occurred when converting {arxiv_id} from ar5iv.org.")
        try:
            result = converter.convert(f"https://arxiv.org/html/{arxiv_id}")
        except Exception:
            logging.exception(f"An error occurred when converting {arxiv_id} from arxiv.org/html")
            return pdf_converter(arxiv_id, num_threads)

    if result.status != ConversionStatus.SUCCESS:
        logging.warning(f"{arxiv_id} conversion failed with {result.status}")
        raise ValueError("The PDF conversion was partial or unsuccessful.")

    content = result.document.export_to_markdown()
    conversion_time = (time.time_ns() - start_time) // NANOS_IN_SEC
    logging.info(f"<<<<<<<< {arxiv_id} converted to markdown in {conversion_time} secs")
    return content


class ArxivCrawler:
    """
    A component fetching a paper from arxiv.org
    """

    def __init__(
        self,
        cache_folder=tempfile.gettempdir(),  # noqa: B008
        converter=html_converter,
        max_parallel_converters=2,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache_folder = cache_folder
        self._semaphore = threading.Semaphore(max_parallel_converters)
        self._max_parallel_threads = NUM_CPUS // max_parallel_converters
        self._converter = converter
        self.logger.info(f"Using {self._max_parallel_threads} parallel threads for conversion.")

    def retrieve_by_ids(self, ids: list[str] = ()) -> list[dict]:
        self.logger.info(f"Retrieving ids: {ids}")
        documents = []
        try:
            papers = Client().results(search=Search(id_list=ids))
            for paper in papers:
                try:
                    md_file_name = paper._get_default_filename()[0:-4] + ".md"
                    file_folder = self._cache_folder

                    md_file_path = os.path.join(file_folder, md_file_name)

                    if not os.path.exists(md_file_path):
                        with self._semaphore:
                            content = self._converter(paper.get_short_id(), self._max_parallel_threads)
                        with open(md_file_path, "w", encoding="utf8") as f:
                            f.write(content)
                    else:
                        with open(md_file_path, "r", encoding="utf8") as f:
                            content = f.read()
                        self.logger.debug(f"File {md_file_path} read from cache.")

                    documents.append(self._to_dict(paper, content=content))
                except Exception:
                    self.logger.exception(f"An error occurred when processing {paper}")
        except Exception:
            self.logger.exception("An error occurred.")
        return documents

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: SortCriterion = SortCriterion.Relevance,
        sort_order: SortOrder = SortOrder.Descending,
    ) -> list[dict]:
        self.logger.info(f"Searching query: {query}")
        client = Client(page_size=max_results, num_retries=7)
        # client.query_url_format = "https://www.arxiv.org/api/query?{}"
        results = client.results(
            search=Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )
        documents = [self._to_dict(paper) for paper in results]
        return documents

    @classmethod
    def _to_dict(cls, paper: Result, content: str = None) -> dict:
        return {
            "paper_id": paper.get_short_id(),
            "published": str(paper.updated.date()),
            "title": paper.title,
            "authors": ", ".join(a.name for a in paper.authors),
            "published_first_time": str(paper.published.date()),
            "comment": paper.comment,
            "journal_ref": paper.journal_ref,
            "doi": paper.doi,
            "primary_category": paper.primary_category,
            "categories": ", ".join(category for category in paper.categories),
            "links": ", ".join(link.href for link in paper.links),
            "abstract": paper.summary,
            "content": content,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    docs = ArxivCrawler().search(
        'cat:(cs.LG OR cs.AI OR cs.CC) AND (abs:"neural network" AND (abs:"self-confidence" OR abs:"calibration"))',
        max_results=10,
        sort_by=SortCriterion.Relevance,
        sort_order=SortOrder.Descending,
    )
    print(docs)
    ids = [doc["paper_id"] for doc in docs]
    print(ids)
    new_documents = ArxivCrawler().retrieve_by_ids([ids[0]])
    print(new_documents[0]["content"])
