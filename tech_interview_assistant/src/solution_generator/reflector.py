from typing import Optional
import re
import ast
import json
from pydantic import BaseModel, Field
from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.parser_utils import CustomPydanticOutputParser
from utils.logger import default_logger as logger


class Feedback(BaseModel):
    """
    Feedback model for solution evaluation.
    """
    solution_type: str = Field(description="Type of solution: 'coding' or 'conceptual'")
    codebase: Optional[dict] = Field(default=None, description="Codebase details for coding solutions")
    conceptual: Optional[dict] = Field(default=None, description="Conceptual details for conceptual solutions")
    report: Optional[dict] = Field(default_factory=dict, description="Report with additional insights")
    
    class Config:
        arbitrary_types_allowed = True


class ErrorResponse(BaseModel):
    """
    Error response model for solution evaluation.
    """
    error_category: str = Field(
        description="Type of error based on the solution provided, including `no error`, "
                    "`factual error`, `logical inconsistency`, `missing key details` or "
                    "`other type of errors`."
    )
    solution: str = Field(
        description="The updated solution. If cannot solve the problem with high confidence, "
                   "just say `Failed to Solve`."
    )
    
    class Config:
        arbitrary_types_allowed = True


class SolutionReflector:
    """
    Class for reflecting on and improving solutions.
    """
    
    def __init__(self, llm):
        """
        Initialize the SolutionReflector.
        
        Args:
            llm: Language model to use for reflection
        """
        self.llm = llm
        self.rubric_chain = self._create_rubric_based_reflection_chain()
        self.error_chain = self._create_error_detection_chain()
        self.classification_chain = self._create_question_classification_chain()
    
    def _create_question_classification_chain(self):
        """
        Create a chain for classifying questions.
        
        Returns:
            Classification chain
        """ 
        classification_prompt = ChatPromptTemplate.from_template(
            "You are an AI that classifies data science technical interview questions. "
            "Given the question: '{question}', classify it as one of the following types: "
            "1) Concept Review 2) Data Structure and Database 3) Coding Best Practices"
        )
        return classification_prompt | self.llm | StrOutputParser()
    
    def _create_rubric_based_reflection_chain(self):
        """
        Create a chain for rubric-based reflection.
        
        Returns:
            Rubric-based reflection chain
        """
        parser = CustomPydanticOutputParser(pydantic_object=Feedback)
        
        system_message = """
        You are an expert code reviewer. Evaluate the provided solution according to these criteria:
        1. Clarity: Is the solution clear and easy to understand?
        2. Technical Accuracy: Is the solution technically accurate and correct?
        3. Completeness: Does the solution cover all relevant aspects of the question?

        Your response must be a valid JSON object with the following structure:
        - solution_type: "coding" or "conceptual"
        - codebase: (for coding solutions) containing reasoning, pseudocode, code, and tests
        - conceptual: (for conceptual solutions) containing explanation, key_points, examples
        - report: containing insights about the solution

        Use double quotes for all property names and string values.
        """

        human_message = """
        Question: {question}
        Solution: {solution}

        Provide your evaluation in JSON format.
        """
        chat_prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": system_message},
            {"role": "user", "content": human_message}
        ])
        return chat_prompt | self.llm | parser
    
    def _create_error_detection_chain(self):
        """
        Create a chain for error detection.
        
        Returns:
            Error detection chain
        """
        parser = CustomPydanticOutputParser(pydantic_object=ErrorResponse)

        system_message = """
        You are an expert code reviewer. Examine the solution and identify any errors or issues.

        Your response must be a valid JSON object with the following structure:
        - error_category: Type of error found, or "no error" if none
        - solution: The updated solution with corrections, or the original if no errors

        Use double quotes for all property names and string values.
        """

        human_message = """
        Question: {question}
        Solution: {solution}

        Provide your error analysis in JSON format.
        """

        chat_prompt = ChatPromptTemplate.from_messages([
            {"role": "system", "content": system_message},
            {"role": "user", "content": human_message}
        ])

        return chat_prompt | self.llm | parser
    
    def classify_question(self, question: str) -> str:
        """
        Classify a question.
        
        Args:
            question: Question to classify
            
        Returns:
            Question classification
        """
        return self.classification_chain.invoke({"question": question}).strip()
    
    def reflect_and_improve(
        self,
        question: str,
        solution: str,
        max_reflection_passes: int = 3
    ) -> str:
        """
        Reflect on and improve a solution.
        
        Args:
            question: Question the solution is for
            solution: Solution to improve
            max_reflection_passes: Maximum number of reflection passes
            
        Returns:
            Improved solution
        """
        try:
            if isinstance(solution, str):
                try:
                    if solution.strip().startswith('{') and solution.strip().endswith('}'):
                        json_compatible = re.sub(r"'([^']*)'", r'"\1"', solution)
                        current_solution = json.loads(json_compatible)
                    else:
                        current_solution = ast.literal_eval(solution)
                except:
                    parser = CustomPydanticOutputParser(pydantic_object=Feedback)
                    text = parser._normalize_to_json(solution)
                    current_solution = parser._robust_json_parse(text)

                    if current_solution is None:
                        raise ValueError("Could not parse solution")
            else:
                current_solution = solution
        except:
            current_solution = {
                "solution_type": "coding",
                "codebase": {
                    "code": solution,
                    "reasoning": "",
                    "pseudocode": "",
                    "tests": ""
                },
                "report": {}
            }
        
        try:
            if isinstance(current_solution, dict):
                solution_str = json.dumps(current_solution)
            else:
                solution_str = str(current_solution)

            from langchain_core.messages import HumanMessage, SystemMessage
            
            system_prompt = """
            You are an expert code reviewer. Evaluate the provided solution according to these criteria:
            1. Clarity: Is the solution clear and easy to understand?
            2. Technical Accuracy: Is the solution technically accurate and correct?
            3. Completeness: Does the solution cover all relevant aspects of the question?

            Your response must be a valid JSON object with the following structure:
            {
              "solution_type": "coding or conceptual",
              "codebase": {
                "reasoning": "explanation of approach",
                "pseudocode": "high-level algorithm",
                "code": "actual code implementation",
                "tests": "test cases"
              },
              "report": {
                "model_or_algorithm": "description of algorithm used"
              }
            }
            """
            
            human_prompt = f"""
            Question: {question}
            Solution: {solution_str}

            Provide your evaluation in JSON format.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            raw_result = self.llm.invoke(messages)
            content = raw_result.content
            json_pattern = re.compile(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})', re.DOTALL)
            match = json_pattern.search(content)
            
            if match:
                json_str = match.group(1)
                
                try:
                    parsed_json = json.loads(json_str)
                    current_solution = parsed_json
                except json.JSONDecodeError:
                    parser = CustomPydanticOutputParser(pydantic_object=Feedback)
                    normalized_json = parser._normalize_to_json(json_str)
                    parsed_json = parser._robust_json_parse(normalized_json)
                    
                    if parsed_json:
                        current_solution = parsed_json
            
        except Exception as e:
            logger.error(f"Error during reflection: {str(e)}")
            pass
        
        return current_solution
    
    def detect_and_fix_errors(self, question: str, solution: str) -> str:
        """
        Detect and fix errors in a solution.
        
        Args:
            question: Question the solution is for
            solution: Solution to check for errors
            
        Returns:
            Corrected solution
        """
        try:
            if isinstance(solution, dict):
                solution_str = json.dumps(solution)
            else:
                solution_str = str(solution)
            
            from langchain_core.messages import HumanMessage, SystemMessage
            
            system_prompt = """
            You are an expert code reviewer. Examine the solution and identify any errors or issues.

            Your response must be a valid JSON object with the following structure:
            {
              "error_category": "Type of error found, or 'no error' if none",
              "solution": "The updated solution with corrections, or the original if no errors"
            }

            Use double quotes for all property names and string values.
            """
            
            human_prompt = f"""
            Question: {question}
            Solution: {solution_str}

            Provide your error analysis in JSON format.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            raw_result = self.llm.invoke(messages)
            content = raw_result.content
            json_pattern = re.compile(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})', re.DOTALL)
            match = json_pattern.search(content)
            
            if match:
                json_str = match.group(1)
                try:
                    parsed_json = json.loads(json_str)   
                    if parsed_json.get("error_category", "").lower() == "no error":
                        return solution
                    return parsed_json.get("solution", solution)
                    
                except json.JSONDecodeError:
                    parser = CustomPydanticOutputParser(pydantic_object=ErrorResponse)
                    normalized_json = parser._normalize_to_json(json_str)
                    parsed_json = parser._robust_json_parse(normalized_json)
                    
                    if parsed_json:
                        if parsed_json.get("error_category", "").lower() == "no error":
                            return solution
                        
                        return parsed_json.get("solution", solution)
    
            return solution
            
        except Exception as e:
            logger.error(f"Error during error detection: {str(e)}")
            return solution
