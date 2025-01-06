import random
from datetime import datetime

import dspy
import numpy as np
from sentence_transformers import SentenceTransformer

from arxplorer.agent.arxiv_searcher import ArxivApiQueryGenerator
from arxplorer.common.arxiv_api import ArxivCrawler
from arxplorer.common.common import instrument_telemetry
from arxplorer.fix_dspy import update_dsp_lm_call

update_dsp_lm_call(time_in_seconds=62, max_tokens=25)

instrument_telemetry()
arxiv_crawler = ArxivCrawler()
MAX_RESULT_SET_SIZE = 50


def rank_by_size(query: str, abstracts: list[str]):
    res = -1 if not abstracts else float(len(abstracts)) / MAX_RESULT_SET_SIZE
    return res


def rank_by_embeddings_distance(query: str, abstracts: list[str]):
    if not abstracts:
        return -1
    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device="cuda:0",
        trust_remote_code=True,
    )

    query_embeddings = model.encode(query)
    res1 = query_embeddings / np.linalg.norm(query_embeddings)

    document_embeddings = model.encode(abstracts)
    res2 = document_embeddings / np.linalg.norm(document_embeddings, axis=1, keepdims=True)

    scores = res1 @ res2.T
    res = np.min(scores)
    return res


# Function to generate synthetic user queries
def generate_synthetic_query():
    topics = [
        "quantum computing",
        "machine learning",
        "climate change",
        "astrophysics",
        "neuroscience",
        "genetics",
        "artificial intelligence",
        "renewable energy",
        "particle physics",
        "bioinformatics",
    ]

    query_templates = [
        "What are the latest developments in {}?",
        "How does {} impact {}?",
        "What are the applications of {} in {}?",
        "What is the relationship between {} and {}?",
        "What are the challenges in {} research?",
        "How has {} evolved in the past decade?",
        "What are the future prospects of {}?",
        "How does {} contribute to advancements in {}?",
        "What are the ethical implications of {} in {}?",
        "How is {} used to solve problems in {}?",
    ]

    topic = random.choice(topics)
    template = random.choice(query_templates)

    if "{}" in template:
        if template.count("{}") == 1:
            return template.format(topic)
        else:
            return template.format(topic, random.choice(topics))
    else:
        return template


# Generate synthetic dataset
num_examples = 10
synthetic_dataset = [
    dspy.Example(
        user_query=generate_synthetic_query(),
        current_date=str(datetime.now()),
        arxiv_query="",  # We don't have predefined correct queries
    ).with_inputs("user_query", "current_date")
    for _ in range(num_examples)
]

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm investigating the use of transformer architectures in computer vision tasks, particularly for image classification and object detection. I'm looking for papers that explore:
- Novel adaptations of transformer models for vision tasks
- Comparisons between CNN-based and transformer-based approaches in various vision benchmarks
- Techniques for improving efficiency and reducing computational costs of vision transformers
- Self-supervised learning methods using transformers for visual representations
- Theoretical analyses of why transformers work well for vision tasks
- Hybrid approaches combining CNNs and transformers
Any recent advancements, benchmark results, or theoretical insights in this area would be valuable.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm researching the intersection of reinforcement learning and natural language processing, particularly in the context of language model fine-tuning. I'm interested in:
- Methods for using RL to optimize language models for specific tasks
- Techniques for reward modeling in language-based RL tasks
- Applications of inverse reinforcement learning in NLP
- Challenges and solutions for sparse reward signals in language tasks
- Comparisons between RL-based and traditional supervised fine-tuning approaches
- Theoretical frameworks for understanding the RL-NLP interface
Both practical implementations and theoretical analyses are relevant to my research.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm exploring recent advancements in few-shot and zero-shot learning, particularly in the context of large language models. I'm seeking information on:
- Novel architectures or training paradigms for improving few-shot performance
- Techniques for enhancing zero-shot generalization in language models
- Theoretical explanations for the emergent few-shot abilities of large models
- Benchmarks and evaluation methodologies for few-shot and zero-shot tasks
- The role of pre-training data and model scale in few-shot capabilities
- Comparisons between few-shot learning and traditional transfer learning approaches
Both empirical studies and theoretical frameworks are of interest.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm investigating the phenomenon of lottery tickets in neural networks and its implications for model pruning and efficient architecture design. I'm looking for research on:
- Extensions of the lottery ticket hypothesis to different model architectures and tasks
- Techniques for identifying winning tickets more efficiently
- Theoretical analyses of why lottery tickets exist and their properties
- Applications of lottery ticket findings in model compression and acceleration
- Connections between lottery tickets and other concepts in deep learning theory
- Empirical studies on the transferability of winning tickets across tasks
Both recent developments and foundational papers in this area are relevant.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm researching the use of diffusion models in various generative tasks, beyond image generation. I'm particularly interested in:
- Applications of diffusion models in audio synthesis, 3D object generation, and video generation
- Theoretical analyses of diffusion models and their comparison to other generative approaches (e.g., GANs, VAEs)
- Techniques for improving the efficiency and speed of diffusion models
- Methods for controlling and steering the generation process in diffusion models
- Approaches for combining diffusion models with other AI techniques (e.g., transformers, reinforcement learning)
- Evaluating the quality and diversity of samples from diffusion models
Recent advancements and state-of-the-art results are especially relevant.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm exploring the concept of neural tangent kernels (NTK) and its implications for understanding deep learning dynamics. I'm seeking information on:
- Theoretical foundations of NTK and its connections to infinite-width networks
- Applications of NTK in analyzing convergence and generalization in deep networks
- Empirical studies validating or challenging NTK predictions in practical settings
- Extensions of NTK to different network architectures (e.g., CNNs, transformers)
- Relationships between NTK and other theoretical frameworks in deep learning
- Practical implications of NTK for network design and training strategies
Both theoretical papers and empirical investigations are of interest.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm investigating the use of meta-learning techniques for improving few-shot learning and rapid adaptation in AI systems. I'm particularly interested in:
- Novel meta-learning algorithms and their theoretical foundations
- Applications of meta-learning in various domains (e.g., computer vision, NLP, robotics)
- Comparisons between different meta-learning approaches (e.g., MAML, Prototypical Networks, Relation Networks)
- Techniques for improving the efficiency and scalability of meta-learning
- Theoretical analyses of why meta-learning works and its limitations
- Connections between meta-learning and other learning paradigms (e.g., transfer learning, continual learning)
Recent advancements and benchmark results are especially relevant.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm researching the intersection of causal inference and machine learning, particularly in the context of improving model robustness and generalization. I'm looking for information on:
- Techniques for incorporating causal knowledge into deep learning models
- Methods for learning causal structures from observational data
- Applications of causal ML in decision-making systems and policy evaluation
- Theoretical frameworks for understanding causality in the context of ML
- Empirical studies demonstrating the benefits of causal approaches in ML tasks
- Challenges and potential solutions in scaling causal inference to high-dimensional data
Both theoretical developments and practical applications are of interest.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm exploring recent advancements in self-supervised learning, particularly in the context of computer vision. I'm seeking information on:
- Novel self-supervised pretext tasks and their effectiveness
- Comparative studies between different self-supervised approaches (e.g., contrastive learning, masked autoencoding)
- Theoretical analyses of why self-supervised learning works
- Applications of self-supervised learning in downstream tasks and transfer learning
- Techniques for improving the efficiency and scalability of self-supervised training
- Integration of self-supervised learning with other paradigms (e.g., semi-supervised learning, few-shot learning)
Recent benchmark results and state-of-the-art techniques are particularly relevant.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

synthetic_dataset.append(
    dspy.Example(
        user_query="""
I'm investigating the use of graph neural networks (GNNs) for modeling relational data and learning on graphs. I'm particularly interested in:
- Novel GNN architectures and their theoretical properties
- Applications of GNNs in various domains (e.g., social networks, molecular modeling, recommender systems)
- Techniques for improving the expressive power and scalability of GNNs
- Theoretical analyses of GNNs' capabilities and limitations
- Methods for incorporating external knowledge or features into GNN models
- Comparisons between GNNs and other approaches for graph-structured data
Both theoretical papers and empirical studies showcasing real-world applications are relevant.
        """,  # noqa: B950
        current_date=str(datetime.now()),
        arxiv_query="",
    ).with_inputs("user_query", "current_date")
)

random.Random(0).shuffle(synthetic_dataset)

# Configure DSPy to use a specific language model
lm = dspy.LM(
    model="gemini/gemini-2.0-flash",
    max_tokens=100_000,
    num_retries=5,
    retry_strategy="exponential_backoff_retry",
)

with dspy.settings.context(lm=lm, temperature=0):
    # Define the DSPy module for query generation
    generate_query = dspy.ChainOfThought(ArxivApiQueryGenerator)

    # Define the metric function
    def metric(gold, pred, trace=None):
        results = arxiv_crawler.search(pred.arxiv_query, max_results=MAX_RESULT_SET_SIZE)
        res = rank_by_size(gold.user_query, [result["abstract"] for result in results])
        return res

    # Optimize via BootstrapFewShot
    optimizer = dspy.teleprompt.MIPROv2(
        metric=metric,
        init_temperature=0.5,
        auto="heavy",  # Can choose between light, medium, and heavy optimization runs
    )
    kwargs = dict(num_threads=20, display_progress=True)
    optimized = optimizer.compile(
        generate_query,
        trainset=synthetic_dataset,
        # max_labeled_demos=0,
        # max_bootstrapped_demos=0,
        requires_permission_to_run=False,
    )

    # Save optimize program for future use
    optimized.save("mipro_v2_zeroshot_optimized_size.json")

    # Print the optimized prompt
    print("\nOptimized Prompt:")
    print(optimized)

    for candidate in optimized.candidate_programs:
        print("############################################################")
        print(f"Score: {candidate[0]}\n")
        print(candidate[1].extended_signature.instructions)
        print("############################################################")
