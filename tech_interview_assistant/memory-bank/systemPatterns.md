# System Patterns: Tech Interview Assistant

## System Architecture
The Tech Interview Assistant is built using a service-oriented architecture with a workflow-based approach. The system is organized into several key components that work together to provide the complete functionality.

### High-Level Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Email Sources  │────▶│ Email Processor │────▶│ Question Queue  │
└─────────────────┘     └─────────────────┘     └─────────┬───────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Retrieval System│◀────│  Vector Store   │◀────│ Workflow Manager│
└─────────────────┘     └─────────────────┘     └─────────┬───────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │    Solvers      │
                                                └─────────────────┘
```

## Component Relationships

### Core Components
1. **TechInterviewAssistant**: The main facade class that coordinates all services
2. **EmailService**: Handles email collection and processing
3. **QuestionProcessingService**: Manages question processing and solution generation
4. **VectorStoreService**: Manages vector database operations
5. **DataService**: Handles data management functionality
6. **JobTrackingService**: Handles job tracking and metrics
7. **WorkflowManager**: Manages the solution generation workflow

### Processing Pipeline
1. **EmailProcessor**: Extracts questions from emails
2. **WorkflowManager**: Orchestrates the solution generation process
3. **Solvers**: Specialized components for different question types
4. **DocumentProcessor**: Processes questions and solutions into documents
5. **VectorStoreManager**: Manages the vector database for storage and retrieval

## Design Patterns

### 1. Facade Pattern
The `TechInterviewAssistant` class serves as a facade, providing a simplified interface to the complex subsystem of services and components. It coordinates the various services and presents a unified API to the client.

```python
class TechInterviewAssistant:
    def __init__(self, ...):
        # Initialize services
        self.job_tracking_service = JobTrackingService(...)
        self.email_service = EmailService(...)
        self.question_processing_service = QuestionProcessingService(...)
        self.vector_store_service = VectorStoreService(...)
        self.data_service = DataService(...)
        self.workflow_manager = WorkflowManager(...)
```

### 2. Service-Oriented Architecture
The system is organized into services, each responsible for a specific domain of functionality:

```
TechInterviewAssistant
├── EmailService
├── QuestionProcessingService
├── VectorStoreService
├── DataService
└── JobTrackingService
```

### 3. Workflow Pattern (using LangGraph)
The system uses LangGraph to create a workflow that connects the various components. The enhanced workflow now includes question classification, draft generation, retrieval, specialized solving, and evaluation:

```
START → classify_question → draft → retrieve → [coding_solver | conceptual_solver] → evaluate → [END | retry]
```

### 4. Strategy Pattern
The system uses different strategies for different question types:

```python
def route_by_question_type(self, state: State):
    """
    Route based on question type.
    """
    question_type = state.get("question_type", "coding")
    if question_type == "conceptual":
        return "conceptual_solver"
    
    return "coding_solver"
```

### 5. Circuit Breaker Pattern
The system uses a circuit breaker pattern to prevent cascading failures:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=3, reset_timeout=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        
    def can_execute(self):
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Check if enough time has passed to try again
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False
```

### 6. Repository Pattern
The `VectorStoreManager` acts as a repository for storing and retrieving documents:

```python
def add_documents(self, documents):
    # Add documents to vector store
    
def search(self, query, k=3):
    # Search for documents
    
def search_mmr(self, query, k=3, fetch_k=6, lambda_mult=0.7):
    # Search with maximal marginal relevance
```

### 7. State Machine Pattern
The workflow uses a state machine pattern to manage the solution generation process:

```python
def _check_more_questions_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if there are more questions to process.
    """
    current_index = state.get("current_question_index", 0)
    total_questions = state.get("total_questions", 0)
    
    # Check if there are more questions to process
    has_more_questions = current_index < total_questions - 1
    
    # Update state with the flag
    state["has_more_questions"] = has_more_questions
    
    return state
```

## Data Flow

### 1. Email Collection Flow
```
Gmail API → EmailProcessor → Question Extraction → DataFrame of Questions
```

### 2. Solution Generation Flow
```
Question → Classification → Draft → Retrieval → Specialized Solver → Evaluation → Final Solution
```

### 3. Storage Flow
```
Question + Solution → DocumentProcessor → Document → VectorStoreManager → Vector Database
```

### 4. Retrieval Flow
```
Query → HybridRetriever → BM25 Results + Vector Results → Combined Results → Filtered Results
```

### 5. Multi-Question Processing Flow
```
Questions DataFrame → Extract Question → Process Question → Store Solution → Check More Questions → [Loop or End]
```

## Critical Implementation Paths

### 1. Email Processing Path
- `EmailService.collect_questions_from_emails()` → Extract questions from emails
- `EmailService.collect_questions_since_last_run()` → Process new emails since last run

### 2. Solution Generation Path
- `WorkflowManager.create_workflow()` → Create the solution generation workflow
- `WorkflowManager.classify_question()` → Classify the question type
- `WorkflowManager.route_by_question_type()` → Route to the appropriate solver
- `Solver.invoke()` → Generate a solution for coding questions
- `ConceptualSolver.invoke()` → Generate a solution for conceptual questions
- `WorkflowManager.evaluate()` → Evaluate the solution quality

### 3. Multi-Question Processing Path
- `TechInterviewAssistant._extract_questions_node()` → Extract or advance to the next question
- `TechInterviewAssistant._check_more_questions_node()` → Check if there are more questions
- `TechInterviewAssistant._has_more_questions()` → Determine if processing should continue

### 4. Vector Storage Path
- `DocumentProcessor.create_document_from_qa()` → Create document from question and answer
- `VectorStoreService.add_documents()` → Add documents to vector store

### 5. Retrieval Path
- `WorkflowManager._set_up_retrieval()` → Set up the retrieval system
- `retrieve_examples()` → Retrieve similar examples for a question
- `HybridRetriever.get_relevant_documents()` → Get relevant documents

## Key Technical Decisions

### 1. Enhanced Workflow with Question Classification
The decision to classify questions and use specialized solvers improves solution quality by tailoring the approach to the question type.

### 2. Jobs Directory Structure
Organizing job-related functionality in a dedicated directory improves code organization and maintainability.

### 3. Circuit Breaker Pattern
Implementing circuit breakers prevents cascading failures and improves system resilience.

### 4. Multi-Question Processing
Supporting the processing of multiple questions in sequence with state management improves efficiency and user experience.

### 5. Draft-Retrieve-Solve-Evaluate Pattern
The multi-step solution generation process improves solution quality by leveraging similar examples and evaluating results.

### 6. Specialized Solvers
Using different solvers for different question types allows for more tailored and higher-quality solutions.
