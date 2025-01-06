# ArXplorer Development Guide

This document provides detailed information for developers interested in contributing to or understanding the ArXplorer project.

## System Architecture

The following diagram illustrates the main components and data flow of the ArXplorer system:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#e0e0e0',
    'primaryTextColor': '#333',
    'primaryBorderColor': '#888',
    'lineColor': '#555',
    'secondaryColor': '#f4f4f4',
    'tertiaryColor': '#fff'
  }
}}%%

flowchart TB
%% Node definitions
   A([User Query])
   B[Query Translation]
   C[ArXiv Search]
   D{Results?}
   E[Revise Query]
   F[Paper Retrieval]
   G[Paper Processing]
   H[Paper Assessment]
   I[Reference Extraction]
   J[Reference Processing]
   K[(Data Persistence)]
   L[Citation Retrieval]
   M[Semantic Scholar API]
   N{{Dash-based UI}}

%% Flow connections
   N -->|Create/Start/Stop/Delete Queries| A
   A --> B
   B --> C
   C --> D
   D -->|Empty| E
   E --> B
   D -->|Not Empty| F
   F --> G
   G --> H & I
   I --> J
   J -.-> F
   H -.-> K
   M --> L
   L -.-> K
   K <--->|Navigate Results| N

%% Styling
   classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;
   classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
   classDef process fill:#fff9c4,stroke:#fbc02d,stroke-width:1px;
   classDef decision fill:#ffebee,stroke:#c62828,stroke-width:1px;
   classDef data fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
   classDef external fill:#d1c4e9,stroke:#673ab7,stroke-width:2px,stroke-dasharray: 5 5;
   classDef ui fill:#b2dfdb,stroke:#00796b,stroke-width:2px;

   class A input;
   class B,E,G,H,I,J,L process;
   class C,F,M external;
   class D decision;
   class K data;
   class N ui;

%% Link styling
   linkStyle default stroke:#555,stroke-width:1px;
   linkStyle 5 stroke:#c62828,stroke-width:1px,stroke-dasharray: 3 3;
   linkStyle 9,10,11,13 stroke:#fbc02d,stroke-width:1px,stroke-dasharray: 3 3;
   linkStyle 0,14 stroke:#00796b,stroke-width:2px;
```

## How It Works

### 1. User Query Processing

1. The user inputs a natural language query through the Dash-based UI.
2. The query is passed to the `ArxivApiQueryGenerator`, which translates it into an ArXiv-compatible search string using advanced NLP techniques.
3. If the generated query returns no results, the system suggests a revision, leveraging `dspy.Suggest` for query refinement.

### 2. ArXiv Search and Paper Retrieval

1. The translated query is used to search ArXiv via their API.
2. For each paper found, the system initiates a parallel retrieval process.
3. Papers are fetched using either HTML or PDF conversion methods, depending on availability and configuration.

### 3. Paper Processing and Analysis

1. Retrieved papers undergo parallel processing:
    - **Content Extraction**: Full text is extracted and converted to a standardized format.
    - **Relevance Assessment**: The `ArxivAssessor` uses AI to evaluate the paper's relevance to the original query, assigning a score and providing detailed explanations.
    - **Reference Extraction**: The `ArxivReferenceExtractor` identifies and extracts references from the paper.

2. Each extracted reference is fed back into the retrieval process, creating a recursive exploration of the topic.

### 4. Citation Retrieval

1. In parallel to other processes, the `CitationsRetriever` fetches citation counts for papers using the Semantic Scholar API.
2. Citation data is periodically updated to keep information current.

### 5. Data Management

1. Processed papers, their assessments, extracted references, and citation data are stored in a database managed by `DbManager`.
2. The system supports continuous updates, allowing for refinement of results over time.

### 6. Multi-threaded Execution

1. The `PriorityLimitedThreadExecutor` manages concurrent execution of tasks.
2. Tasks are prioritized to ensure efficient use of resources and timely processing of the most relevant papers.

### 7. User Interface and Result Navigation

1. The Dash-based UI allows users to:
    - Create, start, stop, and delete queries
    - View and navigate through processed results
    - Filter and sort papers based on relevance, citation count, and other metrics
    - Access detailed assessments and explanations for each paper

### 8. Continuous Processing

1. The system continues to process papers and update results until the user stops the query or a predefined limit is reached.
2. New papers and updated citation counts are continuously integrated into the results, providing an evolving view of the research landscape.

### 9. Extensibility and API Integration

1. The system is designed to easily integrate with additional external APIs and data sources.
2. The modular architecture allows for the addition of new analysis tools or processing steps without significant restructuring.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/marfago/arxplorer.git
   cd arxplorer
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up the Google Gemini API key:
   ```bash
   export GOOGLE_API_KEY=your_gemini_api_key_here
   ```

## Running Tests

To run the test suite:

```bash
poetry run pytest
```

To run tests with coverage:

```bash
poetry run pytest --cov=arxplorer --cov-report=term-missing --cov-report=html
```

## Code Style and Linting

We use Black for code formatting and Flake8 for linting.

To check code style:

```bash
poetry run black --check .
```

To run the linter:

```bash
poetry run flake8 .
```

## Contributing Guidelines

1. Fork the repository and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code lints.
5. Issue that pull request!

Please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file for more detailed information on our contribution process.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.