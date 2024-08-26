import os
from langchain import LLMChain
from langchain.prompts import ChatPromptTemplate


def create_question_classification_chain(llm):
    classification_prompt = ChatPromptTemplate.from_template(
        "You are an AI that classifies data science technical interview questions. "
        "Given the question: '{question}', classify it as one of the following types: "
        "1) Concept Review 2) Data Structure and Database 3) Coding Best Practices"
    )
    return LLMChain(llm=llm, prompt=classification_prompt)


def create_qa_chain(llm):
    qa_prompt = ChatPromptTemplate.from_template(
        """
        You are a senior data science interview expert.  
        For `Concept Review` or `Data Structure and Database` type of question, you can rely on your knowledge base or search internet
        for best answer.
        For `Coding Best practices`, you primarily rely on your own coding experience, since the question
        is mostly unique created for the interviewe, but bet on your own decision if you think internet
        search is useful.

        Answer the following {question_type} question using the available tools or your own knowledge: 
        {question}
        """
    )
    return LLMChain(llm=llm, prompt=qa_prompt)


def create_rubric_based_reflection_chain(llm):
    reflection_prompt = ChatPromptTemplate.from_template(
        """
        Evaluate the provided answer according to the following criteria:
        1. **Clarity:** Is the answer clear and easy to understand?
        2. **Technical Accuracy:** Is the answer technically accurate and correct?
        3. **Completeness:** Does the answer cover all relevant aspects of the question?

        Provide feedback on each criterion and suggest specific improvements if necessary.

        Question: {question}
        Answer: {answer}
        """
    )
    return LLMChain(llm=llm, prompt=reflection_prompt)


def create_error_detection_chain(llm):
    error_detection_prompt = ChatPromptTemplate.from_template(
        """
        Carefully examine the following answer and identify any factual errors, logical inconsistencies, or missing key details.
        If any errors are found, suggest a correction.

        Question: {question}
        Answer: {answer}
        """
    )
    return LLMChain(llm=llm, prompt=error_detection_prompt)


def reflect_and_improve_answer(agent, question: str, initial_answer: str, rubric_chain, 
                               error_chain, max_reflection_passes: int = 3) -> str:
    improved_answer = initial_answer
    for _ in range(max_reflection_passes):
        # Step 1: Rubric-Based Reflection
        rubric_feedback = rubric_chain.run({"question": question, "answer": improved_answer})
        print(f"Rubric Feedback:\n{rubric_feedback}\n")

        # Step 2: If improvement suggestions are made, generate a new improved answer
        if "improve" in rubric_feedback.lower():
            improved_answer = agent.invoke({"input": question})

        # Step 3: Error Detection
        error_feedback = error_chain.run({"question": question, "answer": improved_answer})
        print(f"Error Detection Feedback:\n{error_feedback}\n")

        # If no significant issues are found, break the loop early
        if "no errors" in error_feedback.lower() and "improve" not in rubric_feedback.lower():
            break

    return improved_answer


def answer_interview_question(llm, agent, question: str) -> str:
    classification_chain = create_question_classification_chain(llm)
    qa_chain = create_qa_chain(llm)
    rubric_chain = create_rubric_based_reflection_chain(llm)
    error_chain = create_error_detection_chain(llm)

    # Step 1: Classify the question type
    classification_result = classification_chain.run({"question": question})
    question_type = classification_result.strip()

    # Step 2: Use the agent to answer the question with iterative planning and tools
    initial_answer = qa_chain.run({"question_type": question_type, "question": question})
    print(f"Initial Answer: {initial_answer}")

    # Step 3: Reflect and Improve the answer using modular logic
    improved_answer = reflect_and_improve_answer(
        agent=agent,  # Reuse the agent for re-generating answers
        question=question,
        initial_answer=initial_answer,
        rubric_chain=rubric_chain,
        error_chain=error_chain
    )

    return improved_answer


if __name__ == "__main__":
    from langchain.chat_models import ChatOpenAI
    from langchain.agents import initialize_agent, AgentType
    from langchain_community.tools import TavilySearchResults
    from dotenv import load_dotenv, find_dotenv

    _ = load_dotenv(find_dotenv())

    os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_ORGANIZATION"] = os.getenv("OPENAI_ORGANIZATION")
    llm = ChatOpenAI(model=os.getenv("OPENAI_LLM_MODEL"),
                    temperature=os.getenv("TEMPERATURE"),
                    tiktoken_model_name=os.getenv("OPENAI_TOKENIZER"),
                    max_retries=2,
                    )
    
    tavily_search_tool = TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
        # name="...",            # overwrite default tool name
        # description="...",     # overwrite default tool description
    )
    
    tools = [tavily_search_tool, ]

    agent = initialize_agent(
            tools,
            llm,
            agent_type=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # Use an agent that supports iterative planning
            verbose=True
        )

    sampled_question = "Given three random variables independently and identically distributed from a uniform distribution of 0 to 4, what is the probability that the median of them is greater than 3?"
    answer = answer_interview_question(llm=llm, agent=agent, question=sampled_question)
    print(answer)