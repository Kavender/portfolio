import re
import json
from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.outputs import Generation
from langchain_core.exceptions import OutputParserException
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


class Feedback(BaseModel):
    """
    Feedback model for solution evaluation.
    """
    conclusion: bool = Field(description="Decide whether the question is correctly answered by the solution")
    solution: str = Field(description="The updated solution if improvements are needed")
    
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


class CustomPydanticOutputParser(PydanticOutputParser):
    """
    Custom parser for handling various LLM output formats.
    """
    
    def parse_result(self, result):
        """
        Parse the result from the LLM.
        
        Args:
            result: Result from the LLM
            
        Returns:
            Parsed result
        """
        text = result[0].text
        text = text.replace("```", "")
        text = text.replace("json", "")
        text = text.replace("python", "")
        text = text.strip()

        if text.lower().startswith("null"):
            return None
            
        json_pattern = re.compile(r'(\{.*?\})(?=\*\*\*|$)', re.DOTALL)
        match = json_pattern.search(text)
        if not match:
            raise ValueError(f"No JSON object found in the input text: {text}")
            
        text = match.group(1)
        text = re.sub(r'\\([^"\\/bfnrt])', r'\\\\\1', text)

        try:
            return super().parse_result([Generation(text=text)])
        except Exception as exc:
            try:
                data = json.loads(text)
                return self.pydantic_object.parse_obj(data)
            except Exception as e:
                raise OutputParserException(
                    f"Failed to parse output: {str(e)}", llm_output=result
                ) from e


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
        
        reflection_prompt = (
            """
            Evaluate the provided solution according to the following criteria:
            1. **Clarity:** Is the solution clear and easy to understand?
            2. **Technical Accuracy:** Is the solution technically accurate and correct?
            3. **Completeness:** Does the solution cover all relevant aspects of the question?
            """
            + "{format_instructions}"
        )
        
        input_prompt = """
        Compare against each criterion before coming up with an improved version of the solution.
        <<<
        Question: {question}
        Solution: {solution}
        >>>
        """
        
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            reflection_prompt, 
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        human_message_prompt = HumanMessagePromptTemplate.from_template(input_prompt)
        
        chat_prompt = ChatPromptTemplate.from_messages([
            system_message_prompt, 
            human_message_prompt
        ])
        
        return chat_prompt | self.llm | parser
    
    def _create_error_detection_chain(self):
        """
        Create a chain for error detection.
        
        Returns:
            Error detection chain
        """
        parser = CustomPydanticOutputParser(pydantic_object=ErrorResponse)
        
        error_detection_prompt = ChatPromptTemplate.from_template(
            """
            Carefully examine the following solution and identify any factual errors, 
            logical inconsistencies, or missing key details.
            If any errors are found, suggest a correction.

            Question: {question}
            Solution: {solution}

            Return the error analysis in the following format.
            {format_instructions}
            """,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        return error_detection_prompt | self.llm | parser
    
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
        improved_solution = solution
        
        for _ in range(max_reflection_passes):
            try:
                rubric_feedback = self.rubric_chain.invoke({
                    "question": question, 
                    "solution": improved_solution
                })
                
                if rubric_feedback.conclusion:
                    break
                    
                improved_solution = rubric_feedback.solution
                
            except Exception as e:
                print(f"Error during reflection: {str(e)}")
                break
        
        return improved_solution
    
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
            error_feedback = self.error_chain.invoke({
                "question": question, 
                "solution": solution
            })
            
            if error_feedback.error_category.lower() == "no error":
                return solution
                
            return error_feedback.solution
            
        except Exception as e:
            print(f"Error during error detection: {str(e)}")
            return solution
