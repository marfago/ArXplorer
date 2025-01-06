import logging
from typing import List, Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


def _remove_version(arxiv_id: str) -> str:
    if arxiv_id[-2].lower() == "v":
        return arxiv_id[:-2]
    elif arxiv_id[-3].lower() == "v":
        return arxiv_id[:-3]
    return arxiv_id


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def fetch_citation_counts(arxiv_ids: List[str]) -> List[int]:
    base_url = "https://api.semanticscholar.org/graph/v1/paper/batch"
    params = {"fields": "citationCount"}
    formatted_ids = [f"ARXIV:{_remove_version(id)}" for id in arxiv_ids]

    response = requests.post(base_url, params=params, json={"ids": formatted_ids}, timeout=10)
    response.raise_for_status()

    data = response.json()
    return [paper["citationCount"] if paper else None for paper in data]


def get_citation_counts(arxiv_ids: List[str]) -> list[tuple[Any, Any]]:
    try:
        counts = fetch_citation_counts(arxiv_ids)
    except Exception as e:
        logging.warning(f"Failed to fetch citation counts after multiple retries: {e}")
        counts = [None] * len(arxiv_ids)
    return [(id, count) for (id, count) in zip(arxiv_ids, counts)]


if __name__ == "__main__":
    # Example usage:
    arxiv_ids = ["2104.08653", "2106.15928", "2104.08653", "2106.15928"]
    citation_counts = get_citation_counts(arxiv_ids)
    print("Citation counts:", citation_counts)
