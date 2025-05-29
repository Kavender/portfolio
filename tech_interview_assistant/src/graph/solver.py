from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from src.graph.schemas import State, FullSolution, ConceptualSolution


class ConceptualSolver:
    """Specialised solver for conceptual / explanatory questions."""

    def __init__(self, llm: BaseChatModel, prompt: ChatPromptTemplate):
        self.parser = PydanticOutputParser(pydantic_object=ConceptualSolution)
        self.chain = prompt | llm | self.parser
        self.raw_chain = prompt | llm  # without enforced parsing

    def __call__(self, state: State):
        inputs = {"messages": state["messages"]}
        if state.get("examples"):
            inputs["examples"] = state["examples"]
            output_key = "messages"
        else:
            output_key = "candidate"
        try:
            parsed: ConceptualSolution = self.chain.invoke(inputs)
            structured = {
                "solution_type": "conceptual",
                "conceptual": parsed.model_dump(),
                "report": {
                    "model_or_algorithm": "Conceptual explanation generated.",
                },
            }
            return {output_key: AIMessage(content=str(structured))}
        except Exception:
            pass
        try:
            raw_output = self.raw_chain.invoke(inputs)
            content = (
                raw_output.content if hasattr(raw_output, "content") else str(raw_output)
            )
        except Exception as e:
            content = f"Error generating solution: {e}"

        structured_fallback = {
            "solution_type": "conceptual",
            "conceptual": {
                "explanation": content,
                "key_points": [],
                "examples": None,
                "visualization_code": None,
            },
            "report": {
                "model_or_algorithm": "Conceptual explanation generated via raw chain.",
            },
        }
        return {output_key: AIMessage(content=str(structured_fallback))}


class Solver:
    """Default solver for coding‑oriented questions (but still builds JSON)."""

    def __init__(self, llm: BaseChatModel, prompt: ChatPromptTemplate):
        self.parser = PydanticOutputParser(pydantic_object=FullSolution)
        self.chain = prompt | llm | self.parser
        self.raw_chain = prompt | llm

    def __call__(self, state: State):
        inputs = {"messages": state["messages"]}
        if state.get("examples"):
            inputs["examples"] = state["examples"]
            output_key = "messages"
        else:
            output_key = "candidate"
        try:
            parsed: FullSolution = self.chain.invoke(inputs)
            result = parsed.model_dump()
            return {output_key: AIMessage(content=str(result))}
        except Exception:
            pass
        try:
            raw_output = self.raw_chain.invoke(inputs)
            content = (
                raw_output.content if hasattr(raw_output, "content") else str(raw_output)
            )
        except Exception as e:
            content = f"Error generating solution: {e}"

        structured_fallback = {
            "solution_type": "coding",
            "codebase": {
                "reasoning": "Generated from raw LLM output; may need review.",
                "pseudocode": "Not available – produced via fallback mode.",
                "code": self._wrap_raw_output_as_code(content),
                "tests": "# No tests – fallback generation",
            },
            "report": {
                "model_or_algorithm": "Auto‑wrapped raw output inside Python stub.",
            },
        }
        return {output_key: AIMessage(content=str(structured_fallback))}
    
    @staticmethod
    def _wrap_raw_output_as_code(raw: str) -> str:
        """Embed *any* raw text inside a tiny Python function so the JSON contract is met."""
        escaped = raw.replace("'", "\\'").replace("\n", "\\n")
        return (
            "# Auto‑generated from raw model output\n"
            "def generated_answer():\n"
            "    '''\n" + escaped + "'''\n"
            "    return '''" + escaped + "'''\n"
        )
