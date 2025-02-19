import logging
from textwrap import dedent
from typing import Optional

import dspy
from pydantic import BaseModel, Field, field_validator

from arxplorer.common.arxiv_api import ArxivCrawler
from arxplorer.common.common import instrument_telemetry, load_env
from arxplorer.configuration import ConfigurationManager
from arxplorer.fix_dspy.custom_adapter import CustomJSONAdapter


class ArxivReference(BaseModel):
    arxiv_id: Optional[str] = Field(
        description="The arXiv id formatted as one of arch-ive/YYMMNNNN or arXiv:YYMM.number or YYMM.number."
    )
    title: Optional[str] = Field(description="The document title.")
    relevance_score: int = Field(
        description=dedent(
            """
    A relevance score with respect to the query/topic.
    0 = Not relevant at all
    1 = Marginally relevant
    2 = Somewhat relevant
    3 = Moderately relevant
    4 = Highly relevant
    5 = Fully relevant

    To ensure consistency in your grading, please review these examples:

    Example Query: "What are the effects of climate change on coral reef ecosystems?"

    Title: "Advancements in Quantum Computing Algorithms"
    Relevance: 0
    Explanation: This paper focuses entirely on quantum computing and has no connection to climate change or coral
    reef ecosystems. It is completely unrelated to the given query.

    Title: "Global Warming: A Comprehensive Review of Temperature Changes"
    Relevance: 1
    Explanation: While this paper discusses global warming, which is related to climate change, it doesn't
    specifically address coral reef ecosystems. The connection to the query is minimal and indirect.

    Title: "The Impact of Rising Ocean Temperatures on Marine Biodiversity"
    Relevance: 2
    Explanation: This paper discusses the effects of rising temperatures on marine life, which is related to
    the query. However, it likely doesn't focus specifically on coral reef ecosystems and may only briefly mention them.

    Title: "Coral Bleaching Events: Causes and Consequences"
    Relevance: 3
    Explanation: This paper directly addresses coral reef health, which is relevant to the query.
    However, it may focus more on the immediate causes of coral bleaching rather than the broader effects of climate
    change on coral reef ecosystems.

    Title: "Climate Change and Coral Reefs: Ecosystem Responses and Adaptation Strategies"
    Relevance: 4
    Explanation: This paper directly addresses the effects of climate change on coral reef ecosystems,
    covering multiple aspects of the query. It likely provides in-depth analysis but may not cover all possible
    effects or the most recent data.

    Title: "Comprehensive Assessment of Climate Change Impacts on Coral Reef Ecosystems: Current State, Future Projections,
    and Mitigation Strategies"
    Relevance: 5
    Explanation: This paper fully addresses the query by providing a comprehensive analysis of climate change
    effects on coral reef ecosystems. It likely includes current data, future projections, various impact factors,
    and potential mitigation strategies.
    """
        )
    )
    relevance_score_explanation: str = Field(description="An explanation of the assigned relevance score.")

    @classmethod
    @field_validator("relevance_score")
    def validate_relevance_score(cls, v: int) -> int:
        if v not in range(6):
            raise ValueError("relevance_score must be between 0 and 5")
        return v


class ArxivReferencesGenerator(dspy.Signature):
    """
    Read the paper and extract all the arXiv references. Only return arXiv references.
    """

    query: str = dspy.InputField(desc="A user topic or query.")
    paper: str = dspy.InputField(desc="A paper.")
    references: list[ArxivReference] = dspy.OutputField(desc="A list of references extracted from the paper.")


class ArxivReferenceExtractor(dspy.Module):
    def __init__(self, llm_model: str, num_retries: int, max_tokens: int):
        super().__init__()
        self.llm_model = llm_model
        self.predictor = dspy.Predict(ArxivReferencesGenerator)
        self.num_retries = num_retries
        self.max_tokens = max_tokens

    def forward(self, paper: str, query: str, temperature=0) -> list[ArxivReference]:
        lm = dspy.LM(
            model=self.llm_model,
            max_tokens=self.max_tokens,
            num_retries=self.num_retries,
            retry_strategy=ConfigurationManager.get_llm_client_retry_strategy(),
        )

        with dspy.settings.context(lm=lm, temperature=temperature, adapter=CustomJSONAdapter()):
            prediction = self.predictor(paper=paper, query=query)
            return prediction.references


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    instrument_telemetry()
    load_env()

    papers = ArxivCrawler().retrieve_by_ids(["1412.6572"])
    print(papers)

    references = ArxivReferenceExtractor()(
        query="""
        I am interested in adversarial examples.
        """,
        paper=papers[0]["content"],
    )
    for reference in references:
        if reference.arxiv_id:
            print(reference)
    print(f"Found {len(references)} items")
