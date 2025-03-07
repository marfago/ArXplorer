"""
This module provides functionality for assessing the relevance of arXiv papers to a given query.

It includes classes for generating relevance assessments and a main ArxivAssessor class that
uses a language model to predict the relevance of a paper to a query.
"""

import logging
from textwrap import dedent
from typing import Optional

import dspy
from pydantic import Field, BaseModel

from arxplorer.common.arxiv_api import ArxivCrawler
from arxplorer.common.common import instrument_telemetry, load_env
from arxplorer.configuration import ConfigurationManager
from arxplorer.fix_dspy.custom_adapter import CustomJSONAdapter


class ArxivRelevanceAssessment(BaseModel):
    relevance_score: int = Field(description="Relevance score from 0 to 5")
    relevance_score_brief_explanation: str = Field(
        description=""""
A brief explanation of the assigned relevance score.
Should also briefly list the major claims in the paper and the most relevant numerical results.
        """
    )
    relevance_score_explanation: str = Field(
        description=dedent(
            """
A detailed explanation of the assigned relevance score.
Write a markdown with at least 500 words accordingly to the following template (the comments are explanations of what
the corresponding section is about, dont report the comments).

**Major claims and relevant numerical results**
[comment]: <> (This section lists in details the major claims in the paper and the most relevant numerical results.)

**Specific Alignments with the Query**
[comment]: <> (This section covers all the aspect discussed in the paper that are relevant for the query.
Here are also reported all the sections from the paper relevant to the query.)

**Areas of Divergence**
[comment]: <> (This section describes in detail what is missing/not covered in the paper that is required/relevant for the query.)
```
"""
        )
    )

    github_links: Optional[list[str]] = dspy.OutputField(desc="A list of link to github code/repositories.")


class PaperAssessmentGenerator(dspy.Signature):
    """
    Read the paper and assess the relevance with respect to the user provided topic/query using the following scale:

    0 = Not relevant at all
    1 = Marginally relevant
    2 = Somewhat relevant
    3 = Moderately relevant
    4 = Highly relevant
    5 = Fully relevant

    To ensure consistency in your grading, please review these examples:

    Example Query: "What are the effects of climate change on coral reef ecosystems?"

    Example for grade 0 (Not relevant at all):
    Title: "Advancements in Quantum Computing Algorithms"
    Relevance: 0
    Explanation: This paper focuses entirely on quantum computing and has no connection to climate change or coral
    reef ecosystems. It is completely unrelated to the given query.

    Example for grade 1 (Marginally relevant):
    Title: "Global Warming: A Comprehensive Review of Temperature Changes"
    Relevance: 1
    Explanation: While this paper discusses global warming, which is related to climate change, it doesn't
    specifically address coral reef ecosystems. The connection to the query is minimal and indirect.

    Example for grade 2 (Somewhat relevant):
    Title: "The Impact of Rising Ocean Temperatures on Marine Biodiversity"
    Relevance: 2
    Explanation: This paper discusses the effects of rising temperatures on marine life, which is related to
    the query. However, it likely doesn't focus specifically on coral reef ecosystems and may only briefly mention them.

    Example for grade 3 (Moderately relevant):
    Title: "Coral Bleaching Events: Causes and Consequences"
    Relevance: 3
    Explanation: This paper directly addresses coral reef health, which is relevant to the query.
    However, it may focus more on the immediate causes of coral bleaching rather than the broader effects of climate
    change on coral reef ecosystems.

    Example for grade 4 (Highly relevant):
    Title: "Climate Change and Coral Reefs: Ecosystem Responses and Adaptation Strategies"
    Relevance: 4
    Explanation: This paper directly addresses the effects of climate change on coral reef ecosystems,
    covering multiple aspects of the query. It likely provides in-depth analysis but may not cover all possible
    effects or the most recent data.

    Example for grade 5 (Fully relevant):
    Title: "Comprehensive Assessment of Climate Change Impacts on Coral Reef Ecosystems: Current State, Future Projections,
    and Mitigation Strategies"
    Relevance: 5
    Explanation: This paper fully addresses the query by providing a comprehensive analysis of climate change
    effects on coral reef ecosystems. It likely includes current data, future projections, various impact factors,
    and potential mitigation strategies.
    """

    query = dspy.InputField(desc="A user provided topic or query")
    paper = dspy.InputField(desc="A provided paper")
    assessed_relevance: ArxivRelevanceAssessment = dspy.OutputField()


class ArxivAssessor(dspy.Module):
    """
    A module for assessing the relevance of arXiv papers to a given query.

    This class uses a language model to predict the relevance of a paper to a query,
    based on the PaperAssessmentGenerator signature.

    Attributes:
        llm_model (str): The name of the language model to use.
        predictor (dspy.Predict): A predictor object for generating assessments.
        num_retries (int): The number of times to retry failed API calls.
    """

    def __init__(self, llm_model: str, num_retries: int, max_tokens: int):
        """
        Initialize the ArxivAssessor.

        Args:
            llm_model (str): The name of the language model to use.
            num_retries (int): The number of times to retry failed API calls.
            max_tokens (int): The maximum number of tokens for the language model output.
        """
        super().__init__()
        self.llm_model = llm_model
        self.predictor = dspy.Predict(PaperAssessmentGenerator)
        self.num_retries = num_retries
        self.max_tokens = max_tokens

    def forward(self, paper: str, query: str, temperature=0) -> ArxivRelevanceAssessment:
        """
        Generate a relevance assessment for a given paper and query.

        Args:
            paper (str): The content of the paper to assess.
            query (str): The query to assess the paper against.
            temperature (float): The temperature parameter for the language model.

        Returns:
            ArxivRelevanceAssessment: The generated relevance assessment.
        """
        lm = dspy.LM(
            model=self.llm_model,
            max_tokens=self.max_tokens,
            num_retries=self.num_retries,
            retry_strategy=ConfigurationManager.get_llm_client_max_num_retries(),
        )
        with dspy.settings.context(lm=lm, temperature=temperature, adapter=CustomJSONAdapter()):
            prediction = self.predictor(paper=paper, query=query)
            return prediction.assessed_relevance


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    instrument_telemetry()
    load_env()

    papers = ArxivCrawler().retrieve_by_ids(["2409.18836v2"])

    res = ArxivAssessor()(
        query="""
        I am interested in mitigating self-confidence in neural network. You should look in ML, CS and AI space.
        """,
        paper=papers[0]["content"],
    )
    print(res)
