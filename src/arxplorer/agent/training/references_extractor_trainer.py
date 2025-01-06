import json
import logging
from typing import List

import dspy
from dotenv import load_dotenv, find_dotenv

from arxplorer.agent.references_extractor import ArxivReferencesGenerator
from arxplorer.common.arxiv_api import ArxivCrawler
from arxplorer.common.common import instrument_telemetry


def evaluate_samples():
    def extraction_correctness_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
        set1 = {(reference.arxiv_id, reference.title, reference.relevance_score) for reference in prediction.references}
        set2 = {(reference["arxiv_id"], reference["title"], reference["relevance_score"]) for reference in example.references}

        return float(len(set1.intersection(set2))) / float(len(set2))

    def prepare_dataset(dataset) -> List[dspy.Example]:
        return [dspy.Example(sample).with_inputs("document", "query") for sample in dataset]

    with open("train_dataset.json", "r") as f:
        evaluation_set = json.load(f)

    lm = dspy.LM(model="gemini/gemini-2.0-flash", max_tokens=100_000)
    dspy.settings.configure(lm=lm)
    predictor = dspy.Predict(ArxivReferencesGenerator)

    train_set = prepare_dataset(evaluation_set)
    # evaluate_correctness = dspy.Evaluate(
    #     devset=train_set,
    #     metric=extraction_correctness_metric,
    #     num_threads=24,
    #     display_progress=True,
    #     display_table=True
    # )

    # evaluate_correctness(predictor, devset=train_set)

    mipro_optimizer = dspy.MIPROv2(
        metric=extraction_correctness_metric,
        auto="medium",
    )

    optimized_relevance_extractor = mipro_optimizer.compile(
        predictor,
        trainset=train_set,
        max_bootstrapped_demos=4,
        requires_permission_to_run=False,
        minibatch=False,
    )
    optimized_relevance_extractor.save("optimized_relevance_extractor.json")
    print(optimized_relevance_extractor)


def generate_samples(ids: List[str], queries: List[str]):
    records = []
    lm = dspy.LM(model="gemini/gemini-2.0-flash", max_tokens=100_000)
    dspy.settings.configure(lm=lm)

    for id, query in zip(ids, queries):
        papers = ArxivCrawler().retrieve_by_ids(
            [id],
        )

        predictor = dspy.Predict(ArxivReferencesGenerator)
        prediction = predictor(document=papers[0].content, query=query)

        records.append(
            {
                "document": papers[0].content,
                "query": query,
                "references": [
                    {
                        "arxiv_id": reference.arxiv_id,
                        "title": reference.title,
                        "relevance_score": reference.relevance_score,
                        "relevance_score_explanation": reference.relevance_score_explanation,
                    }
                    for reference in prediction.references
                ],
            }
        )

    with open("train_dataset_new.json", "w") as f:
        json.dump(records, f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv(find_dotenv(), override=True)
    instrument_telemetry()

    evaluate_samples()
    # generate_samples(ids=["1807.03888v2"],
    #                  queries=["I am interested in finding articles about identify out of distribution samples in neural networks training"])
