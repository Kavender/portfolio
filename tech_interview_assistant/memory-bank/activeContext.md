# Active Context: Tech Interview Assistant

## Current Work Focus
The Tech Interview Assistant project is currently focused on the following areas:

1. **Enhanced Agentic Workflow**: The system has been refactored to use a more sophisticated agentic workflow with state management, question classification, and specialized solvers for different question types.

2. **Jobs Directory Structure**: A new `src/jobs/` directory has been created to better organize the main workflow components and job-related functionality.

3. **Multi-Question Processing**: The system now supports processing multiple questions in sequence, maintaining state between questions and tracking progress.

4. **Question Type Classification**: The workflow now includes automatic classification of questions as either "coding" or "conceptual" with specialized handling for each type.

5. **Circuit Breaker Pattern**: Enhanced error handling with circuit breaker patterns to prevent cascading failures and improve system resilience.

## Recent Changes

### Jobs Directory Implementation
- Created a new `src/jobs/` directory to organize job-related functionality
- Moved and enhanced the incremental update script to `src/jobs/run_incremental_update.py`
- Implemented the main agentic workflow in `src/jobs/main_agentic_flow.py`

### Workflow Enhancement
- Enhanced the `WorkflowManager` class with more sophisticated question handling
- Implemented question type classification and specialized solvers
- Added a draft-retrieve-solve-evaluate workflow pattern
- Improved error handling with retry mechanisms and circuit breakers

### Question Processing Improvements
- Added support for conceptual questions with specialized handling
- Enhanced the solution generation with a multi-step approach
- Improved example retrieval for better solution quality
- Added evaluation steps to verify solution quality

### Multi-Question Processing
- Implemented state management for processing multiple questions
- Added tracking of question index and progress
- Enhanced the workflow to loop through all questions in a batch
- Improved error recovery to continue processing after failures

### Error Handling Improvements
- Implemented circuit breaker pattern to prevent repeated failures
- Added more detailed error logging and categorization
- Enhanced timeout handling for API requests
- Improved recovery mechanisms for transient failures

## Active Decisions and Considerations

### 1. Question Classification Approach
- Currently using a simple heuristic for question classification
- Considering more sophisticated classification using embeddings or ML
- Exploring ways to handle hybrid questions that have both coding and conceptual aspects

### 2. Workflow State Management
- Using LangGraph for state management in the workflow
- Considering enhancements to make state persistence more robust
- Exploring ways to visualize workflow state for debugging

### 3. Error Recovery Strategies
- Implementing circuit breakers for critical components
- Considering more sophisticated backoff strategies
- Exploring ways to handle partial failures and continue processing

### 4. Solution Quality Metrics
- Developing metrics to evaluate solution quality
- Considering automated testing of generated solutions
- Exploring ways to compare solutions to reference implementations

### 5. Performance Optimization
- Optimizing the workflow for better throughput
- Considering parallel processing for batch operations
- Exploring ways to reduce API costs while maintaining quality

## Important Patterns and Preferences

### Code Organization
- Jobs are organized in the `src/jobs/` directory
- Workflow components are in the `src/graph/` directory
- Services remain in the `src/services/` directory
- Each component has a clear responsibility and API

### Workflow Design
- The workflow is designed as a directed graph with clear state transitions
- Question classification determines the processing path
- Retrieval of similar examples enhances solution quality
- Evaluation ensures solution meets quality standards

### Solution Format
- Coding solutions include reasoning, pseudocode, code, and tests
- Conceptual solutions include explanation, key points, examples, and visualization code
- All solutions include a report with domain-specific insights
- JSON format ensures consistent structure for storage and retrieval

### Error Handling
- Circuit breakers prevent cascading failures
- Detailed error logging for debugging
- Graceful degradation when components fail
- Retry mechanisms for transient failures

### Configuration Management
- Command-line arguments for runtime configuration
- Environment variables for API keys and credentials
- Configuration files for system settings
- Sensible defaults with override capabilities

## Learnings and Project Insights

### 1. Agentic Workflow Design
- State management is critical for complex workflows
- Clear separation of concerns improves maintainability
- Conditional routing based on content type improves quality
- Evaluation steps ensure quality control

### 2. Question Classification
- Different question types require different handling
- Simple heuristics can be effective for basic classification
- Hybrid approaches may be needed for complex questions
- Classification affects the entire solution generation process

### 3. Error Handling Strategies
- Circuit breakers are effective for preventing cascading failures
- Detailed error categorization helps with debugging
- Timeout management is critical for external API calls
- Recovery mechanisms improve overall system reliability

### 4. Multi-Question Processing
- State management becomes more complex with multiple questions
- Progress tracking is important for user feedback
- Error handling must allow continuing after failures
- Batch size affects performance and reliability

### 5. Solution Quality
- Multi-step generation improves solution quality
- Retrieval of similar examples provides valuable context
- Evaluation ensures solutions meet quality standards
- Different question types require different quality metrics
