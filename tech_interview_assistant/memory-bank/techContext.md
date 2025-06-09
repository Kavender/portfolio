# Technical Context: Tech Interview Assistant

## Technologies Used

### Core Frameworks and Libraries
1. **LangChain**: Framework for building applications with language models
   - Used for creating chains of operations with LLMs
   - Provides components for document processing and vector stores

2. **LangGraph**: Framework for building stateful, multi-actor applications with LLMs
   - Used to create the workflow graph
   - Manages state transitions between components
   - Enables visualization of the workflow
   - Supports conditional routing based on question type

3. **Python**: Primary programming language (Python 3.11)
   - Used for all components and services
   - Leverages modern Python features and type hints

### Language Models and Embeddings
1. **Claude 3 Sonnet**: Primary LLM for solution generation
   - Used in the WorkflowManager for generating solutions
   - Provides high-quality reasoning and code generation
   - Supports specialized handling for different question types

2. **OpenAI Embeddings**: Used for vector embeddings
   - Powers the vector store for semantic search
   - Enables finding similar questions and solutions

### Data Storage and Retrieval
1. **ChromaDB**: Vector database for storing embeddings
   - Stores questions and solutions for retrieval
   - Supports semantic search and filtering
   - Configured with telemetry disabled for better reliability

2. **SQLite**: Used for job tracking
   - Stores metadata about job runs
   - Enables incremental processing

3. **Pandas**: Used for data manipulation
   - Processes question data in DataFrame format
   - Facilitates data transformation and storage

### External APIs and Services
1. **Gmail API**: Used to access email data
   - Extracts questions from email newsletters
   - Requires OAuth2.0 authentication
   - Implements circuit breaker pattern for reliability

2. **Google Drive API**: Optional integration for storage
   - Can be used to store and retrieve questions and solutions
   - Requires OAuth2.0 authentication

### Web Interaction
1. **Puppeteer/Selenium**: Used for web scraping
   - Extracts questions and solutions from web pages
   - Handles login and navigation on websites

## Development Environment

### Environment Setup
1. **Virtual Environment**: Using either Poetry or venv
   ```bash
   # Option 1: Using Poetry
   pip install poetry
   poetry install
   poetry shell
   
   # Option 2: Using pip
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **API Keys and Credentials**:
   - OpenAI API key: `export OPENAI_API_KEY=your_key_here`
   - Anthropic API key: `export ANTHROPIC_API_KEY=your_key_here`
   - LangSmith API key (optional): `export LANGSMITH_API_KEY=your_key_here`
   - Google OAuth2.0 credentials: Stored in `src/config/credentials.json`

3. **Environment Variables**:
   ```
   GOOGLE_APP_CREDENTIALS=./src/config/credentials.json
   GOOGLE_APP_TOKEN=./src/config/gmail_token.json
   ```

### Project Structure
```
tech_interview_assistant/
├── docs/                      # Documentation
├── scripts/                   # Utility scripts
├── src/                       # Main source code
│   ├── config/                # Configuration files
│   ├── data/                  # Data storage
│   ├── data_manager/          # Data management components
│   ├── email_processor/       # Email processing components
│   ├── graph/                 # LangGraph workflow definitions
│   ├── jobs/                  # Job-related functionality
│   │   ├── main_agentic_flow.py  # Main workflow implementation
│   │   └── run_incremental_update.py  # Incremental update script
│   ├── services/              # Service modules
│   ├── solution_generator/    # Solution generation components
│   ├── utils/                 # Utility functions
│   ├── vector_store/          # Vector database components
│   ├── web_scraper/           # Web scraping components
│   └── main.py                # Main application entry point
├── tech_interview_assistant.py # CLI entry point
├── requirements.txt           # Dependencies for pip
└── pyproject.toml             # Dependencies for Poetry
```

## Technical Constraints

### Performance Constraints
1. **API Rate Limits**:
   - Gmail API has usage quotas and rate limits
   - LLM APIs (Anthropic, OpenAI) have rate limits and costs
   - Web scraping should be rate-limited to avoid blocking

2. **Processing Time**:
   - Solution generation with LLMs can take several seconds per question
   - Batch processing is recommended for multiple questions
   - Incremental processing helps manage large volumes of emails

3. **Memory Usage**:
   - Processing large batches of questions can consume significant memory
   - State management for multiple questions requires careful memory handling
   - Consider batch size limitations for optimal performance

### Security Constraints
1. **API Authentication**:
   - Gmail API requires OAuth2.0 authentication
   - Token refresh is needed when tokens expire
   - API keys should be stored securely (not in version control)

2. **Data Privacy**:
   - Email content may contain sensitive information
   - Local storage is used to maintain privacy
   - No user data is sent to external services except as needed for API calls

### Scalability Constraints
1. **Vector Store Size**:
   - Vector databases have practical limits on size
   - Consider partitioning or pruning for very large collections

2. **Batch Processing**:
   - Processing large batches of questions requires memory management
   - Default batch sizes are configured for typical use cases
   - Consider parallel processing for larger workloads

## Dependencies

### Core Dependencies
```
langchain==0.3.9
langchain-core==0.3.21
langchain-community==0.3.9
langchain-text-splitters==0.3.2
langchain-google-community==2.0.3
langgraph==0.0.x
anthropic==0.x.x
openai==1.x.x
chromadb==0.x.x
```

### API Integration Dependencies
```
google-api-python-client==2.154.0
google-auth==2.36.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
```

### Data Processing Dependencies
```
pandas==2.x.x
numpy==1.26.4
pydantic==2.x.x
sqlalchemy==2.0.36
```

### Web Scraping Dependencies
```
selenium==4.x.x
beautifulsoup4==4.x.x
```

## Tool Usage Patterns

### Command Line Interface
The system provides a command-line interface for common operations:

```bash
# Process questions from emails
./tech_interview_assistant.py process --senders interviewquery.com --limit 5

# Query for similar questions
./tech_interview_assistant.py query "How would you implement a recommendation system?" --k 3

# Run incremental update
./tech_interview_assistant.py incremental --default-days 7 --force-collection --timeout 900
```

### Python API
The system can also be used as a Python library:

```python
from src.jobs.main_agentic_flow import TechInterviewAssistant

# Initialize the assistant
assistant = TechInterviewAssistant()

# Process questions from emails
result = assistant.process_email_questions(
    sender_lists=["interviewquery.com"],
    limit=5
)

# Retrieve similar questions
query = "How would you implement a recommendation system?"
similar = assistant.retrieve_similar_questions(query, k=3)
```

### Incremental Processing
The system supports incremental processing to handle new emails efficiently:

```python
# Process questions since the last run
questions = assistant.collect_questions_since_last_run(
    sender_lists=["interviewquery.com"],
    default_minutes=60,
    limit=100
)
```

### Batch Processing
For processing multiple questions at once:

```python
questions = ["How would you implement a recommendation system?", 
             "Explain the bias-variance tradeoff."]
results = assistant.process_questions_batch(questions, batch_size=10)
```

### Workflow Management
The system uses a workflow manager for solution generation:

```python
from src.graph.workflow_manager import WorkflowManager

# Initialize the workflow manager
workflow_manager = WorkflowManager()

# Create the workflow
workflow = workflow_manager.create_workflow()

# Get the compiled graph
graph = workflow_manager.return_graph(show_workflow=True)

# Invoke the workflow
result = graph.invoke({
    "messages": [HumanMessage(content="How would you implement a recommendation system?")]
})
```

### Circuit Breaker Pattern
The system uses circuit breakers for critical components:

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
else:
    # Skip operation due to circuit breaker
    log_skipped_operation()
```

## Langraph Studio Compatibility
The project is compatible with Langraph Studio for visualization:

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
