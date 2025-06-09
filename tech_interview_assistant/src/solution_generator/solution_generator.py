from typing import Dict, Any, Optional, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from graph.workflow_manager import WorkflowManager
from solution_generator.reflector import SolutionReflector
from solution_generator.validators import SolutionValidator


class SolutionGenerator:
    """
    Class for generating solutions to technical interview questions.
    """
    
    def __init__(
        self, 
        workflow_manager: Optional[WorkflowManager] = None,
        llm = None,
        use_reflection: bool = True,
        max_reflection_passes: int = 3
    ):
        """
        Initialize the SolutionGenerator.
        
        Args:
            workflow_manager: Optional WorkflowManager instance
            llm: Optional language model for reflection (if None, uses the one from workflow_manager)
            use_reflection: Whether to use reflection to improve solutions
            max_reflection_passes: Maximum number of reflection passes
        """
        self.workflow_manager = workflow_manager or WorkflowManager()
        # Get the compiled graph from the workflow manager
        self.graph = self.workflow_manager.return_graph()

        try:
            self.solver = self.graph.nodes["coding_solver"]
        except KeyError:
            self.solver = None
        
        self.llm = llm or self.workflow_manager.llm
        assert self.llm is not None
        # Initialize reflector if reflection is enabled
        self.use_reflection = use_reflection
        self.max_reflection_passes = max_reflection_passes
        if use_reflection:
            self.reflector = SolutionReflector(self.llm)
    
    def classify_question(self, question: str) -> str:
        """
        Classify a question.
        
        Args:
            question: Question to classify
            
        Returns:
            Question classification
        """
        if not self.use_reflection:
            return "Unknown"
            
        return self.reflector.classify_question(question)
    
    def generate_solution(
        self, 
        question: str, 
        examples: Optional[str] = None,
        apply_reflection: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Generate a solution for a question.
        
        Args:
            question: The question text
            examples: Optional examples to guide the solution
            apply_reflection: Whether to apply reflection (overrides instance setting)
        Returns:
            Generated solution
        """
        state = {"messages": [HumanMessage(content=question)]}
        
        if examples:
            state["examples"] = examples
        
        # Use the compiled graph to generate solution
        solution = self.graph.invoke(state)

        should_reflect = self.use_reflection if apply_reflection is None else apply_reflection
        if should_reflect:
            return self._refine_solution(question, solution)
            
        return solution
    
    def _refine_solution(self, question: str, solution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refine a solution using reflection.
        
        Args:
            question: The question text
            solution: The solution to refine
            
        Returns:
            Refined solution
        """
        if "candidate" not in solution:
            return solution
            
        candidate = solution["candidate"]
        if isinstance(candidate, dict):
            solution_type = candidate.get("solution_type", "coding")
            
            if solution_type == "coding" and "codebase" in candidate:
                codebase = candidate["codebase"]
                solution_text = (
                    f"Reasoning: {codebase.get('reasoning', '')}\n\n"
                    f"Pseudocode: {codebase.get('pseudocode', '')}\n\n"
                    f"Code:\n{codebase.get('code', '')}\n\n"
                )
                if "tests" in codebase and codebase["tests"]:
                    solution_text += f"Tests:\n{codebase['tests']}\n\n"
            elif solution_type == "conceptual" and "conceptual" in candidate:
                conceptual = candidate["conceptual"]
                solution_text = (
                    f"Explanation: {conceptual.get('explanation', '')}\n\n"
                    f"Key Points: {conceptual.get('key_points', [])}\n\n"
                )
                if "examples" in conceptual and conceptual["examples"]:
                    solution_text += f"Examples:\n{conceptual['examples']}\n\n"
                if "visualization_code" in conceptual and conceptual["visualization_code"]:
                    solution_text += f"Visualization Code:\n{conceptual['visualization_code']}\n\n"
            else:
                solution_text = str(candidate)
        else:
            solution_text = str(candidate)
        
        improved_text = self.reflector.reflect_and_improve(
            question, 
            solution_text,
            max_reflection_passes=self.max_reflection_passes
        )
        
        corrected_text = self.reflector.detect_and_fix_errors(question, improved_text)
        
        if isinstance(corrected_text, dict):
            solution["candidate"] = corrected_text
        else:
            if "def " in corrected_text or "class " in corrected_text:
                solution["candidate"] = {
                    "solution_type": "coding",
                    "codebase": {
                        "reasoning": "Extracted from reflection process",
                        "pseudocode": "Extracted from reflection process",
                        "code": corrected_text,
                        "tests": "# Tests included in the solution"
                    },
                    "report": {
                        "model_or_algorithm": "Algorithm extracted from reflection"
                    }
                }
            else:
                solution["candidate"] = {
                    "solution_type": "conceptual",
                    "conceptual": {
                        "explanation": corrected_text,
                        "key_points": ["Key point extracted from reflection"]
                    },
                    "report": {
                        "model_or_algorithm": "Concept explained in reflection"
                    }
                }
        
        return solution
    
    def generate_solutions_batch(self, questions: List[str]) -> List[Dict[str, Any]]:
        """
        Generate solutions for a batch of questions.
        
        Args:
            questions: List of question texts
            
        Returns:
            List of generated solutions
        """
        solutions = []
        for question in questions:
            solution = self.generate_solution(question)
            solutions.append(solution)
        return solutions
    
    def validate_solution(self, solution: Union[Dict[str, Any], str]) -> bool:
        """
        Validate a solution.
        
        Args:
            solution: Solution to validate
            
        Returns:
            True if the solution is valid, False otherwise
        """
        if isinstance(solution, dict) and "candidate" in solution:
            candidate = solution["candidate"]
            
            if isinstance(candidate, dict):
                solution_type = candidate.get("solution_type", "coding")
                
                if solution_type == "coding" and "codebase" in candidate:
                    codebase = candidate["codebase"]
                    return "code" in codebase and bool(codebase["code"])
                elif solution_type == "conceptual" and "conceptual" in candidate:
                    conceptual = candidate["conceptual"]
                    return "explanation" in conceptual and bool(conceptual["explanation"])

        return SolutionValidator.has_code(solution)
    
    def run_full_workflow(self, question: str) -> Dict[str, Any]:
        """
        Run the full workflow to generate a solution.
        This is now equivalent to generate_solution for consistency.
        
        Args:
            question: The question text
            
        Returns:
            Result of the workflow
        """
        return self.generate_solution(question)
    
    def extract_code_from_solution(self, solution: Dict[str, Any]) -> Optional[str]:
        """
        Extract code from a solution.
        
        Args:
            solution: Solution to extract code from
            
        Returns:
            Extracted code or None if no code is found
        """
        if "candidate" not in solution:
            return None
            
        candidate = solution["candidate"]
        
        if isinstance(candidate, dict):
            solution_type = candidate.get("solution_type", "coding")
            
            if solution_type == "coding" and "codebase" in candidate:
                codebase = candidate["codebase"]
                if "code" in codebase and codebase["code"]:
                    return codebase["code"]
            elif solution_type == "conceptual" and "conceptual" in candidate:
                conceptual = candidate["conceptual"]
                if "visualization_code" in conceptual and conceptual["visualization_code"]:
                    return conceptual["visualization_code"]
        
        if isinstance(candidate, str):
            code_blocks = SolutionValidator.extract_code_blocks(candidate)
            if code_blocks:
                return "\n\n".join(code_blocks)
        
        return None
