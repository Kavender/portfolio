from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableSequence
from src.graph.schemas import State, FullSolution, PythonGenerator


class Solver:
    def __init__(self, llm: BaseChatModel, prompt: ChatPromptTemplate):
        self.parser = PydanticOutputParser(pydantic_object=FullSolution)
        self.chain = prompt | llm | self.parser

    def __call__(self, state: State) -> dict:
        """
        Calls the chain with the user 'messages'. Optionally includes 'examples' if present.
        Returns a dict with either 'candidate' or 'messages' as the key, depending on presence of examples.
        """
        inputs = {"messages": state["messages"]}
        has_examples = bool(state.get("examples"))
        output_key = "candidate"
        if has_examples:
            output_key = "messages"
            inputs["examples"] = state["examples"]
        
        response = self.chain.invoke(inputs)
        if not response or not isinstance(response, PythonGenerator):
            return {output_key: AIMessage(content="No valid response from the chain.")}

        return {output_key: response.dict()}
