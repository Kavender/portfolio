# Tech Interview Assistant

A multi-agent system built with LangChain and LangGraph to assist candidates in preparing for data science technical interviews.

## Overview and Use Cases

The Tech Interview Assistant is designed to help with technical interview preparation by:

1. **Collecting Interview Questions** - Gather data science interview questions from subscribed newsletters in Gmail (e.g., from interviewquery.com)
2. **Generating Solutions** - Create high-quality solutions using LLM-based solvers with reflection capabilities
3. **Knowledge Management** - Store questions and solutions in a vector database for semantic search
4. **Retrieval** - Find similar questions and solutions when needed
5. **Question Classification** - Automatically classify questions as coding or conceptual
6. **Mock Interview Prep** - Under Development

The system uses LangGraph to create a sophisticated workflow that connects these components.

## Components

### Core Components

- **EmailProcessor**: Extracts questions from emails
- **WorkflowManager**: Orchestrates the solution generation process with specialized solvers
- **SolutionGenerator**: Generates solutions using a LLM-based solver
- **SolutionReflector**: Reflects on and improves solutions
- **VectorStoreManager**: Manages the vector database for storing and retrieving solutions
- **DocumentProcessor**: Processes questions and solutions into documents for vector storage
- **WebScraper**: Scrapes questions and solutions from web pages
- **JobTracker**: Tracks job runs and metrics for monitoring and incremental processing

### Service Modules

The system uses a service-oriented architecture:

- **EmailService**: Handles email collection and processing functionality
- **QuestionProcessingService**: Handles question processing and solution generation
- **VectorStoreService**: Handles vector database operations
- **DataService**: Handles data management functionality
- **JobTrackingService**: Handles job tracking and metrics

### Jobs Directory

The system now includes a dedicated jobs directory for job-related functionality:

- **main_agentic_flow.py**: Implements the main workflow as a class
- **run_incremental_update.py**: Handles incremental updates with enhanced error handling

## Installation and Setup

### Environment Setup

1. Fork and clone this repository
2. Set up a virtual environment using one of these methods:
   
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

3. Install the package in development mode for simplified imports:
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
   - Export OpenAI API key: `export OPENAI_API_KEY=your_key_here`
   - Export Anthropic API key: `export ANTHROPIC_API_KEY=your_key_here`
   - Export LangSmith API key (optional): `export LANGSMITH_API_KEY=your_key_here`

2. **Google Authentication Setup**
   - Get OAuth2.0 Credentials from [Google Cloud Console](https://cloud.google.com/docs/authentication/getting-started)
   - Save your credentials as `credentials.json` in the `src/config/` directory
   - Set the following environment variables in your `.env` file:
     ```
     GOOGLE_APP_CREDENTIALS=./src/config/credentials.json
     GOOGLE_APP_TOKEN=./src/config/gmail_token.json
     ```
   - The authentication token will be generated automatically when you first run the application
   - If you need to manually generate or refresh the token, you can use the `get_auth_token` function from `src/utils/gmail_utils.py`:
     ```python
     from utils.gmail_utils import get_auth_token
     
     # Generate a new token
     get_auth_token(
         credential_file_path="./src/config/credentials.json",
         token_file_path="./src/config/gmail_token.json"
     )
     ```
   - If the token expires, you'll see an error like: `google.auth.exceptions.RefreshError: ('invalid_grant: Token has been expired or revoked.', {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})`. The system will automatically attempt to regenerate the token, or you can manually delete the token file and regenerate it.
   - Make sure grant the same set of scopes on the page `GmailReader wants access to your Google Account`, otherwise token files cannot be re-generated properly.Instead it will raise `Warning: Scope has changed from X to Y`

## Usage

### Command Line Interface

The system includes a command-line interface for easy usage:

```bash
# Process questions from emails
./tech_interview_assistant.py process --senders interviewquery.com --limit 5

# Query for similar questions
./tech_interview_assistant.py query "How would you implement a recommendation system?" --k 3

# Scrape questions from URLs
./tech_interview_assistant.py scrape "https://www.interviewquery.com/questions/example1" "https://www.interviewquery.com/questions/example2" --batch-size 5

# Store questions from a CSV file in the vector database
./tech_interview_assistant.py store path/to/questions.csv --batch-size 10

# Run incremental update to process new emails
./tech_interview_assistant.py incremental --default-days 7 --email-limit 100
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

For more details on the incremental update script, see [Scripts README](scripts/README.md).

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

## Advanced Features

### Question Classification

The system now automatically classifies questions as either "coding" or "conceptual" and uses specialized solvers for each type:

```python
from graph.workflow_manager import WorkflowManager

# Initialize the workflow manager
workflow_manager = WorkflowManager()

# Create the workflow
workflow = workflow_manager.create_workflow()

# Get the compiled graph
graph = workflow_manager.return_graph(show_workflow=True)

# Invoke the workflow with a question
result = graph.invoke({
    "messages": [HumanMessage(content="How would you implement a recommendation system?")]
})
```

### Multi-Question Processing

Process multiple questions in sequence with state management:

```python
# Process a batch of questions
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

### Circuit Breaker Pattern

The system uses circuit breakers for critical components to prevent cascading failures:

```python
# Create a circuit breaker
email_circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=300)

# Check if operation can be executed
if email_circuit_breaker.can_execute():
    try:
        # Perform operation
        result = perform_operation()
        
        # Record success
        email_circuit_breaker.record_success()
    except Exception as e:
        # Record failure
        email_circuit_breaker.record_failure()
        
        # Handle error
        handle_error(e)
```

### Batch Processing

Process multiple questions at once:

```python
questions = ["How would you implement a recommendation system?", "Explain the bias-variance tradeoff."]
results = assistant.process_questions_batch(questions, batch_size=10)
```

### Hybrid Retrieval

The system uses a hybrid retrieval approach that combines BM25 (keyword-based) and vector search (semantic) for better results:

```python
hybrid_retriever = assistant.setup_hybrid_retriever(documents, alpha=0.5, k=3)
similar_docs = hybrid_retriever.get_relevant_documents(query)
```

## Langraph Studio Compatibility

This project is compatible with Langraph Studio, allowing you to visualize and interact with the workflow graph.

### Setup for Langraph Studio

1. Ensure you have the correct configuration in `langgraph.json`:
   ```json
   {
     "python_version": "3.11",
     "dependencies": ["."],
     "graphs": {
       "main": "./src/graph/workflow_manager.py:WorkflowManager.return_graph"
     },
     "store": {
       "index": {
         "embed": "openai:text-embedding-3-small",
         "dims": 1536,
         "api_key": "your_openai_api_key"
       },
       "env": ".env"
     }
   }
   ```

2. Open the project in Langraph Studio to visualize and interact with the workflow graph.

## Project Structure

The project has been reorganized for better modularity:

- `src/`: Main source code directory
  - `services/`: Service modules that provide core functionality
  - `email_processor/`: Email processing components
  - `graph/`: LangGraph workflow definitions
    - `workflow_manager.py`: Manages the solution generation workflow
    - `retrieval.py`: Handles retrieval of similar examples
    - `solver.py`: Specialized solvers for different question types
  - `jobs/`: Job-related functionality
    - `main_agentic_flow.py`: Main workflow implementation
    - `run_incremental_update.py`: Incremental update script
  - `solution_generator/`: Solution generation components
  - `vector_store/`: Vector database components
  - `web_scraper/`: Web scraping components
  - `utils/`: Utility functions and helpers
  - `main.py`: Main entry point for the application
- `scripts/`: Utility scripts
- `tech_interview_assistant.py`: CLI entry point

## Testing

Run the tests to verify that the system works correctly:

```bash
./tests/test_tech_interview_assistant.py
```

## Documentation

For more detailed documentation, see:

- [Tech Interview Workflow](docs/tech_interview_workflow.md): Detailed description of the workflow
- [Workflow Diagram](docs/workflow_diagram.md): Visual representation of the workflow

## License

This project is licensed under the MIT License - see the LICENSE file for details.
