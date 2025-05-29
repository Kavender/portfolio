from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import add_messages
from langchain_core.messages import AIMessage, AnyMessage


class Ignore(BaseModel):
    """Call this to ignore the email. Only call this if user has said to do so."""

    ignore: bool


class EmailData(TypedDict):
    id: str
    thread_id: str
    from_email: str
    subject: str
    page_content: str
    send_time: str
    to_email: str


class State(TypedDict):
    email: EmailData
    messages: Annotated[List[AnyMessage], add_messages]
    candidate: AIMessage
    examples: str
    status: str
    question_type: Optional[str]


class PythonGenerator(BaseModel):
    """Python-based solution for data science technical questions."""

    reasoning: Optional[str] = Field(description="High-level conceptual solution.")
    pseudocode: Optional[str] = Field(description="Step-by-step outline of the approach in plain English.")
    code: str = Field(description="Valid Python 3 solution to the problem.", pattern=r"(def |class |import |from )")
    tests: Optional[str] = Field(
        default="",  # Add a default empty string
        description="Established test cases or demonstration code to verify correctness of coding solution."
    )


class ConceptualSolution(BaseModel):
    """Solution model for conceptual questions."""
    
    explanation: str = Field(description="Comprehensive explanation of the concept.")
    key_points: List[str] = Field(description="Key points or takeaways about the concept.")
    examples: Optional[str] = Field(None, description="Real-world examples illustrating the concept.")
    visualization_code: Optional[str] = Field(
        None, 
        description="Optional Python code to visualize or demonstrate the concept."
    )


class SolutionReport(BaseModel):
    """
    Domain-specific insights or advanced context for data science solutions.
    """
    data_preprocessing: Optional[str] = Field(
        None, 
        description="How data is loaded, cleaned, or featurized."
    )
    model_or_algorithm: Optional[str] = Field(
        None,
        description="Which model or algorithm was chosen and why."
    )
    hyperparameters: Optional[str] = Field(
        None,
        description="Key hyperparameters or tuning approach."
    )
    evaluation_metrics: Optional[str] = Field(
        None,
        description="Which metrics or methods used for model evaluation."
    )
    assumptions_or_caveats: Optional[str] = Field(
        None,
        description="Any domain-specific assumptions or known limitations."
    )


class FullSolution(BaseModel):
    """
    A combined model capturing both coding and conceptual solutions.
    """
    solution_type: str = Field(
        description="Type of solution: 'coding' or 'conceptual'"
    )
    codebase: Optional[PythonGenerator] = None
    conceptual: Optional[ConceptualSolution] = None
    report: Optional[SolutionReport] = Field(
        default_factory=lambda: SolutionReport(
            data_preprocessing=None,
            model_or_algorithm=None,
            hyperparameters=None,
            evaluation_metrics=None,
            assumptions_or_caveats=None
        ),
        description="Optional report with additional insights about the solution"
    )
