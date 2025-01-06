import logging
from datetime import date, datetime
from typing import List, Optional, Dict

import dspy
from dspy.primitives import assertions
from pydantic import Field, BaseModel

from arxplorer.common.arxiv_api import ArxivCrawler
from arxplorer.common.common import load_env, instrument_telemetry
from arxplorer.configuration import ConfigurationManager


class ArxivApiQueryGenerator(dspy.Signature):
    """
    You are a research scientist tasked with formulating precise arXiv search queries based on user requests.  Your goal is to translate nuanced natural language descriptions of research topics into effective arXiv search strings, leveraging arXiv's advanced search capabilities.

    **Understanding the User's Needs:**  Carefully analyze the user's query to identify the core research areas, specific keywords, and any implicit constraints (e.g., time period, methodology).  Pay close attention to the relationships between different concepts mentioned.

    **Constructing the arXiv Query:** Utilize arXiv's search syntax, including field prefixes (e.g., `ti:` for title, `au:` for author, `abs:` for abstract), Boolean operators (`AND`, `OR`, `ANDNOT`), and phrase searching (using double quotes).  Prioritize accuracy and comprehensiveness in your query construction.  If the user's query is ambiguous, provide a clarifying question to the user before constructing the query.

    **Reasoning and Explanation:**  Provide a clear and concise explanation of your reasoning process for constructing the query, justifying your choice of keywords, operators, and field prefixes.  This explanation should demonstrate your understanding of the user's request and the rationale behind the specific search terms used.

    **Example:**

    **User Query:**  "I'm interested in recent research on the application of graph neural networks (GNNs) to natural language processing (NLP) tasks, focusing on semantic parsing and relation extraction.  I'm particularly interested in papers that compare GNN-based approaches with traditional methods."

    **Arxiv Query:**  `all:(graph neural network OR GNN) AND ("natural language processing" OR NLP) AND (semantic parsing OR "relation extraction") AND ("comparison" OR benchmark)`

    **Reasoning:** The user's query focuses on GNNs applied to NLP, specifically semantic parsing and relation extraction. The query includes both full phrases and individual keywords to capture relevant papers.  The "AND" operator ensures all specified criteria are met.  The inclusion of "comparison" and "benchmark" targets papers explicitly comparing GNN approaches with alternatives.

    **Input Fields:**

    * `user_query`: The user's research question (natural language).
    * `current_date`: The current date (optional, for filtering by publication date).

    **Output Fields:**

    * `arxiv_query`: The generated arXiv search query string.
    * `reasoning`: A detailed explanation of the reasoning behind the constructed query.


    Now, process the following user query: {user_query}
    """  # noqa: B950

    user_query: str = dspy.InputField(desc="A user provided topic or query.")
    current_date: str = dspy.InputField(desc="The current date")
    arxiv_query: str = dspy.OutputField(description="The arxiv search query.")


class ArxivPaper(BaseModel):
    paper_id: str = Field(description="The ArXiv identifier of the paper in short format (e.g., '2101.12345')")
    published: date = Field(description="The date when the latest version of the paper was published on ArXiv")
    title: str = Field(description="The full title of the academic paper")
    authors: str = Field(description="Comma-separated list of author names")
    published_first_time: date = Field(description="The date when the paper was first published on ArXiv")
    comment: Optional[str] = Field(
        default=None,
        description="Additional comments provided by the authors about the paper",
    )
    journal_ref: Optional[str] = Field(
        default=None,
        description="Reference to the journal where the paper was published (if applicable)",
    )
    doi: Optional[str] = Field(
        default=None,
        description="Digital Object Identifier (DOI) for the published paper",
    )
    primary_category: str = Field(description="Primary ArXiv category/subject classification (e.g., 'cs.AI', 'physics.comp-ph')")
    categories: str = Field(description="List of all ArXiv categories/subject classifications applicable to the paper")
    links: str = Field(description="List of URLs associated with the paper (PDF, abstract page, etc.)")
    abstract: str = Field(description="Abstract or summary of the paper's content")
    content: Optional[str] = Field(default=None, description="The complete paper's content")


def to_pydantic_model(paper: Dict) -> ArxivPaper:
    return ArxivPaper.model_validate(paper)


def backtrack_handler(func, bypass_suggest=True, max_backtracks=5):
    return assertions.default_assertion_handler(func, bypass_suggest, max_backtracks)


class ArxivSearcher(dspy.Module):
    def __init__(
        self,
        llm_model: str,
        num_retries: int,
    ):
        super().__init__()
        self.llm_model = llm_model
        self.predictor = dspy.ChainOfThought(ArxivApiQueryGenerator)
        self.num_retries = num_retries
        self.activate_assertions(handler=backtrack_handler)

    def forward(self, user_query: str, temperature=0, max_tokens=200_000, max_results=50) -> List[ArxivPaper]:
        lm = dspy.LM(
            model=self.llm_model,
            max_tokens=max_tokens,
            num_retries=self.num_retries,
            retry_strategy=ConfigurationManager.get_llm_client_retry_strategy(),
        )
        with dspy.settings.context(lm=lm, temperature=temperature):
            prediction = self.predictor(user_query=user_query, current_date=str(datetime.now()))
            arxiv_query = prediction.arxiv_query
            papers = ArxivCrawler().search(arxiv_query, max_results=max_results)
            dspy.Suggest(
                len(papers) > 0,
                "The query returned an empty result set. Try again with a simpler query.",
            )
            return [to_pydantic_model(paper) for paper in papers]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    instrument_telemetry()
    load_env()

    agent = ArxivSearcher()
    res: str = agent(
        user_query="""I am conducting a search about new prompting techniques to instruct LLMs (large language models).
I want to understand the recent developments. I am not interested in general techniques,
but in approaches to increase relevance and accuracy of LLM's answers.
I'd like to find interesting papers published in January 2025."""
    )

    print(len(res))
