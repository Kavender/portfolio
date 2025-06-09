# Tech Interview Assistant

Tech Interview Assistant is an AI-powered multi-agent system built with LangChain and LangGraph to help candidates prepare for data science technical interviews through intelligent question collection, solution generation, and knowledge management.

## Table of Contents

- [Overview](#overview)
- [General Setup](#general-setup)
  - [Environment Setup](#environment-setup)
  - [Credentials Setup](#credentials-setup)
  - [Configuration](#configuration)
- [Run Locally](#run-locally)
  - [Setup Tech Interview Assistant](#setup-tech-interview-assistant)
  - [LangGraph Studio Integration](#langgraph-studio-integration)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [Python API](#python-api)
  - [Incremental Updates](#incremental-updates)
- [Advanced Features](#advanced-features)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Documentation](#documentation)
- [License](#license)

## Overview

The Tech Interview Assistant is designed to help with technical interview preparation by:

1. **Collecting Interview Questions** - Gather data science interview questions from subscribed newsletters in Gmail (e.g., from interviewquery.com)
2. **Generating Solutions** - Create high-quality solutions using LLM-based solvers with reflection capabilities
3. **Knowledge Management** - Store questions and solutions in a vector database for semantic search
4. **Retrieval** - Find similar questions and solutions when needed
5. **Question Classification** - Automatically classify questions as coding or conceptual
6. **Mock Interview Prep** - Under Development

The system uses LangGraph to create a sophisticated workflow that connects these components with specialized solvers for different question types.

### Core Components

- **EmailProcessor**: Extracts questions from emails
- **WorkflowManager**: Orchestrates the solution generation process with specialized solvers
- **SolutionGenerator**: Generates solutions using a LLM-based solver
- **SolutionReflector**: Reflects on and improves solutions
- **VectorStoreManager**: Manages the vector database for storing and retrieving solutions
- **DocumentProcessor**: Processes questions and solutions into documents for vector storage
- **WebScraper**: Scrapes questions and solutions from web pages
- **JobTracker**: Tracks job runs and metrics for monitoring and incremental processing

### Service Architecture

The system uses a service-oriented architecture:

- **EmailService**: Handles email collection and processing functionality
- **QuestionProcessingService**: Handles question processing and solution generation
- **VectorStoreService**: Handles vector database operations
- **DataService**: Handles data management functionality
- **JobTrackingService**: Handles job tracking and metrics

## General Setup

### Environment Setup

1. Fork and clone this repository
2. Create a Python virtualenv and activate it (e.g. `pyenv virtualenv 3.11.1 tech-interview-assistant`, `pyenv activate tech-interview-assistant`)
3. Install dependencies using one of these methods:
   
   **Option 1: Using Poetry (recommended)**
   ```bash
   # Install Poetry if you don't have it
   pip install poetry
   
   # Install dependencies
   poetry install
   
   # Activate the virtual environment
   poetry shell
   
   # If you encounter "Virtual environment already activated" error, use:
   source "$( poetry env list --full-path | grep Activated | cut -d' ' -f1 )/bin/activate"
   ```
   
   **Option 2: Using pip**
   ```bash
   # Create a virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

4. Install the package in development mode for simplified imports:
   ```bash
   # From the project root directory
   pip install -e .
   ```
   
   This allows you to use imports without the `src.` prefix:
   ```python
   # Instead of
   from src.vector_store.document_processor import DocumentProcessor
   
   # You can use
   from vector_store.document_processor import DocumentProcessor
   ```

### Credentials Setup

1. **API Keys**
   ```bash
   export OPENAI_API_KEY=your_key_here
   export ANTHROPIC_API_KEY=your_key_here
   export LANGSMITH_API_KEY=your_key_here  # Optional
   ```

2. **Google Authentication Setup**
   - Get OAuth2.0 Credentials from [Google Cloud Console](https://cloud.google.com/docs/authentication/getting-started)
   - Save your credentials as `credentials.json` in the `src/config/` directory
   - Set the following environment variables in your `.env` file:
     ```
     GOOGLE_APP_CREDENTIALS=./src/config/credentials.json
     GOOGLE_APP_TOKEN=./src/config/gmail_token.json
     ```
   - The authentication token will be generated automatically when you first run the application

> **Note**: If you're using a personal email (non-Google Workspace), select "External" as the User Type in the OAuth consent screen. With "External" selected, you must add your email as a test user in the Google Cloud Console under "OAuth consent screen" > "Test users" to avoid the "App has not completed verification" error.

### Configuration

The system automatically handles most configuration, but you can customize:

- **Email Processing**: Configure sender lists and processing limits
- **Vector Store**: Adjust embedding models and search parameters
- **Solution Generation**: Customize LLM models and prompts
- **Workflow**: Modify retry logic and evaluation criteria

## Run Locally

### Setup Tech Interview Assistant

1. Install LangGraph CLI: `pip install -U "langgraph-cli[inmem]"`
2. Run development server: `langgraph dev`

This will start the LangGraph development server with:
- 🚀 **API**: http://127.0.0.1:2024
- 🎨 **Studio UI**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 **API Docs**: http://127.0.0.1:2024/docs

### LangGraph Studio Integration

This project is fully compatible with LangGraph Studio for workflow visualization and debugging:

1. **Automatic Configuration**: The `langgraph.json` is pre-configured to work with Studio
2. **Real Database Integration**: Studio uses your actual vector store and retrieval system
3. **Workflow Visualization**: See the complete workflow: classify → draft → retrieve → solve → evaluate
4. **Interactive Debugging**: Test different question types and debug workflow logic

The configuration in `langgraph.json`:
```json
{
  "python_version": "3.11",
  "dependencies": ["."],
  "graphs": {
    "main": "./src/graph/workflow_manager.py:graph"
  },
  "store": {
    "index": {
      "embed": "openai:text-embedding-3-small",
      "dims": 1536,
      "api_key": "OPENAI_API_KEY"
    },
    "env": ".env"
  }
}
```

## Usage

### Command Line Interface

The system includes a comprehensive command-line interface:

```bash
# Process questions from emails
./tech_interview_assistant.py process --senders interviewquery.com --limit 5

# Query for similar questions
./tech_interview_assistant.py query "How would you implement a recommendation system?" --k 3

# Scrape questions from URLs
./tech_interview_assistant.py scrape "https://www.interviewquery.com/questions/example1" --batch-size 5

# Store questions from a CSV file
./tech_interview_assistant.py store path/to/questions.csv --batch-size 10

# Run incremental update to process new emails
./tech_interview_assistant.py incremental --default-days 7 --email-limit 100
```

### Python API

```python
from jobs.main_agentic_flow import TechInterviewAssistant

# Initialize the assistant
assistant = TechInterviewAssistant()

# Process questions from emails
result = assistant.process_email_questions(
    sender_lists=["interviewquery.com"],
    limit=5
)

# Retrieve similar questions
query = "How would you implement a recommendation system for an e-commerce website?"
similar = assistant.retrieve_similar_questions(query, k=3)

# Run the full workflow
result = assistant.run_full_workflow(
    email_collection=True,
    web_scraping=True,
    vector_storage=True
)
```

### Incremental Updates

The system supports incremental updates to process new emails since the last run:

```bash
# Run incremental update with default settings
python -m jobs.run_incremental_update

# Run with custom settings
python -m jobs.run_incremental_update --sender-lists interviewquery.com --default-days 7 --email-limit 50

# Force collection of emails regardless of last run timestamp
python -m jobs.run_incremental_update --force-collection --default-days 7

# Skip vector storage but generate solutions
python -m jobs.run_incremental_update --default-days 7 --force-collection --skip-vector-storage

# Set timeout for API requests
python -m jobs.run_incremental_update --default-days 7 --timeout 1200
```

## Advanced Features

### Question Classification and Specialized Solvers

The system automatically classifies questions as either "coding" or "conceptual" and uses specialized solvers:

```python
from graph.workflow_manager import WorkflowManager

# Initialize the workflow manager
workflow_manager = WorkflowManager()

# Create and run the workflow
workflow = workflow_manager.create_workflow()
graph = workflow_manager.return_graph(show_workflow=True)

# Invoke with a question
result = graph.invoke({
    "messages": [HumanMessage(content="How would you implement a recommendation system?")]
})
```

### Hybrid Retrieval System

Combines BM25 (keyword-based) and vector search (semantic) for better results:

```python
hybrid_retriever = assistant.setup_hybrid_retriever(documents, alpha=0.5, k=3)
similar_docs = hybrid_retriever.get_relevant_documents(query)
```

### Circuit Breaker Pattern

Prevents cascading failures in critical components:

```python
# Create a circuit breaker
email_circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=300)

# Use with operations
if email_circuit_breaker.can_execute():
    try:
        result = perform_operation()
        email_circuit_breaker.record_success()
    except Exception as e:
        email_circuit_breaker.record_failure()
        handle_error(e)
```

### Batch Processing

Process multiple questions efficiently:

```python
questions = [
    "How would you implement a recommendation system?", 
    "Explain the bias-variance tradeoff."
]
results = assistant.process_questions_batch(questions, batch_size=10)
```

### Multi-Question Processing

Process sequences with state management:

```python
# Process a batch of questions with state tracking
result = assistant.process_email_questions(
    sender_lists=["interviewquery.com"],
    limit=10
)
```

The system will:
1. Extract questions from emails
2. Process each question in sequence
3. Maintain state between questions
4. Track progress through the batch

## Project Structure

The project is organized for modularity and maintainability:

```
src/
├── services/           # Service modules providing core functionality
├── email_processor/    # Email processing components
├── graph/             # LangGraph workflow definitions
│   ├── workflow_manager.py  # Main workflow orchestration
│   ├── retrieval.py         # Retrieval of similar examples
│   └── solver.py           # Specialized solvers for question types
├── jobs/              # Job-related functionality
│   ├── main_agentic_flow.py     # Main workflow implementation
│   └── run_incremental_update.py # Incremental update script
├── solution_generator/ # Solution generation components
├── vector_store/      # Vector database components
├── utils/             # Utility functions and helpers
└── main.py           # Main entry point

scripts/               # Utility scripts
tech_interview_assistant.py  # CLI entry point
langgraph.json        # LangGraph configuration
```

## Testing

Run the tests to verify system functionality:

```bash
./tests/test_tech_interview_assistant.py
```

For more detailed testing:

```bash
# Test solution generator
python scripts/test_solution_generator.py

# Test tech interview assistant
python scripts/test_tech_interview_assistant.py
```

## Documentation

For more detailed documentation, see:

- [Tech Interview Workflow](docs/tech_interview_workflow.md): Detailed workflow description
- [Workflow Diagram](docs/workflow_diagram.md): Visual workflow representation
- [Scripts README](scripts/README.md): Detailed script documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.
