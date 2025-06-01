from typing import List, Dict, Any, Optional, Union
import time
import pandas as pd
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph, START
from utils.logger import get_logger
from data_manager.job_tracker import JobTracker
from graph.workflow_manager import WorkflowManager
from solution_generator.solution_generator import SolutionGenerator


class QuestionProcessingService:
    """
    Service for processing questions and generating solutions.
    
    This service encapsulates functionality related to processing questions,
    generating solutions, and reflecting on and improving those solutions.
    """
    
    def __init__(
        self,
        job_tracker: Optional[JobTracker] = None,
        llm_model: str = "claude-3-7-sonnet-20250219",
        temperature: float = 0,
        max_reflection_passes: int = 3
    ):
        """
        Initialize the QuestionProcessingService.
        
        Args:
            job_tracker: JobTracker instance for tracking jobs
            llm_model: LLM model to use for solution generation
            temperature: Temperature parameter for the LLM
            max_reflection_passes: Maximum number of reflection passes
        """
        self.logger = get_logger("question_processing_service")
        self.logger.info("Initializing QuestionProcessingService")
        
        # Initialize LLM
        self.llm = ChatAnthropic(model=llm_model, temperature=temperature)
        
        # Initialize components
        self.workflow_manager = WorkflowManager()
        self.solution_generator = SolutionGenerator(
            workflow_manager=self.workflow_manager,
            llm=self.llm,
            use_reflection=True,
            max_reflection_passes=max_reflection_passes
        )
        
        # Initialize job tracker if provided, otherwise create a new one
        if job_tracker:
            self.job_tracker = job_tracker
        else:
            self.job_tracker = JobTracker()
        
        # Create the workflow graph
        self.graph = self._create_workflow_graph()
        
        self.logger.info("QuestionProcessingService initialized successfully")
    
    def _create_workflow_graph(self) -> StateGraph:
        """
        Create the workflow graph.
        
        Returns:
            Configured StateGraph
        """
        # Create a new StateGraph
        workflow = StateGraph(state_schema=dict)
        
        # Add nodes
        workflow.add_node("generate_solution", self._generate_solution_node)
        workflow.add_node("reflect_and_improve", self._reflect_and_improve_node)
        
        # Add edges
        workflow.add_edge(START, "generate_solution")
        workflow.add_edge("generate_solution", "reflect_and_improve")
        workflow.add_edge("reflect_and_improve", END)
        
        # Compile the graph
        return workflow.compile()
    
    def _generate_solution_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a solution for the current question.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated solution
        """
        # Get the current question
        question = state["current_question"]
        
        # Check if we have similar examples to use
        examples = state.get("similar_examples")
        
        # Generate solution
        solution = self.solution_generator.generate_solution(
            question=question,
            examples=examples
        )
        
        # Update state with the solution
        state["candidate"] = solution["candidate"]
        
        return state
    
    def _reflect_and_improve_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reflect on and improve the generated solution.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with improved solution
        """
        # Get the current question and solution
        question = state["current_question"]
        solution = state["candidate"]
        
        # Create a reflector if not already in the solution generator
        reflector = self.solution_generator.reflector
        
        # Extract solution text
        if isinstance(solution, dict):
            if "codebase" in solution and solution["codebase"] is not None:
                codebase = solution["codebase"]
                solution_text = (
                    f"Reasoning: {codebase.get('reasoning', '')}\n\n"
                    f"Pseudocode: {codebase.get('pseudocode', '')}\n\n"
                    f"Code:\n{codebase.get('code', '')}\n\n"
                )
                if "tests" in codebase and codebase["tests"]:
                    solution_text += f"Tests:\n{codebase['tests']}\n\n"
            else:
                solution_text = str(solution)
        else:
            solution_text = str(solution)
        
        # Reflect and improve
        improved_text = reflector.reflect_and_improve(
            question=question,
            solution=solution_text,
            max_reflection_passes=3
        )
        
        # Detect and fix errors
        final_solution = reflector.detect_and_fix_errors(
            question=question,
            solution=improved_text
        )
        
        # Update state with improved solution
        state["final_solution"] = final_solution
        
        return state
    
    def process_question(self, question: str, examples: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process a single question.
        
        Args:
            question: Question text
            examples: Optional list of similar examples
            
        Returns:
            Dictionary with processing results
        """
        # Create initial state
        state = {
            "current_question": question,
            "messages": [HumanMessage(content=question)],
            "similar_examples": examples
        }

        result = self.graph.invoke(state)
        
        return result
    
    def process_questions_batch(
        self, 
        questions: Union[List[str], pd.DataFrame], 
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of questions.
        
        Args:
            questions: List of questions or DataFrame containing questions
            batch_size: Number of questions to process in each batch
            
        Returns:
            List of results for each question
        """
        # Start job tracking
        job_run_id = self.job_tracker.start_job("question_processing", {
            "num_questions": len(questions) if isinstance(questions, list) else len(questions.index),
            "batch_size": batch_size
        })
        
        try:
            start_time = time.time()
            
            results = []
            
            # Convert list to DataFrame if needed
            if isinstance(questions, list):
                questions_df = pd.DataFrame({"question_content": questions})
            else:
                questions_df = questions
            
            # Process in batches
            for i in range(0, len(questions_df), batch_size):
                batch = questions_df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    # Get question content
                    question_content = row["question_content"]
                    
                    # Create state with the question
                    result = self.process_question(question_content)
                    
                    # Add link if available
                    if "link" in row:
                        result["current_link"] = row["link"]
                    
                    results.append(result)
            
            end_time = time.time()
            
            # Record metrics
            metrics = {
                "duration_seconds": end_time - start_time,
                "questions_processed": len(results),
                "batch_size": batch_size
            }
            
            self.job_tracker.record_metrics(job_run_id, metrics)
            self.job_tracker.end_job(job_run_id, "completed")
            
            self.logger.info(f"Processed {len(results)} questions")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing questions: {str(e)}", exc_info=True)
            self.job_tracker.record_metrics(job_run_id, {"error": str(e)})
            self.job_tracker.end_job(job_run_id, "failed")
            
            # Return empty list
            return []
