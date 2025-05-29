
from typing import List
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from src.graph.schemas import FullSolution, State
from src.utils.logger import default_logger as logger


class HybridRetriever(BaseRetriever):
    """
    A hybrid retriever that combines BM25 (syntactic) with 
    vector-based semantic retrieval (using maximal marginal relevance).
    """
    bm25_retriever: BM25Retriever
    vectorstore: Chroma
    embeddings: OpenAIEmbeddings
    alpha: float = 0.5  # Weight for the semantic score
    k: int = 3          # How many final results to return

    class Config:
        arbitrary_types_allowed = True

    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        1. Retrieve top BM25 docs
        2. Retrieve top MMR docs from Chroma
        3. Merge by a weighted scoring strategy
        """
        # ---- BM25 retrieval ----
        bm25_docs = self.bm25_retriever.invoke(query)
        
        # ---- Vector store MMR retrieval ----
        total = len(self.vectorstore.get()["documents"])
        mmr_k    = min(self.k * 2, total)
        fetch_k  = min(self.k * 4, total)
        vector_docs = self.vectorstore.max_marginal_relevance_search(
            query,
            k=mmr_k,
            fetch_k=fetch_k,
        )
        
        # ---- Merge search results from two retrievers ----
        # Use a list of (doc, score) tuples instead of a dictionary
        combined_doc_scores = []
        
        # Add BM25 docs with scores
        for rank, doc in enumerate(bm25_docs):
            score = 1.0 / (rank + 1) * (1 - self.alpha)
            # Use page_content and metadata as a unique identifier
            combined_doc_scores.append((doc, score))
        
        # Add vector docs with scores
        for rank, doc in enumerate(vector_docs):
            score = 1.0 / (rank + 1) * self.alpha
            # Check if this doc is already in the list
            found = False
            for i, (existing_doc, existing_score) in enumerate(combined_doc_scores):
                if (existing_doc.page_content == doc.page_content and 
                    existing_doc.metadata == doc.metadata):
                    # Update the score
                    combined_doc_scores[i] = (existing_doc, existing_score + score)
                    found = True
                    break
            
            if not found:
                combined_doc_scores.append((doc, score))
        
        # Sort by score
        combined_sorted = sorted(combined_doc_scores, key=lambda x: x[1], reverse=True)
        
        # Get top k docs
        limit = min(self.k, len(combined_sorted))
        top_docs = [doc for doc, _ in combined_sorted[:limit]]
        
        return top_docs

    async def aget_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        """Implement async retrieval if needed."""
        raise NotImplementedError("Async retrieval not implemented.")


def format_example(question: str, solution, use_report_details=True) -> str:
    """
    Convert one (question + FullSolution JSON) pair into a text snippet for similarity retrieval.
    """

    try:
        full_sol = FullSolution.model_validate_json(solution)
    except:
        # If failed on parsing, fallback to raw text
        logger.warning(f"Failed parsing solution-'{solution}' as FullSolution")
        return f"<problem>\n{question}\n</problem>\n<solution>\n{solution}\n</solution>"
    
    reasoning = full_sol.codebase.reasoning
    pseudocode = full_sol.codebase.pseudocode
    code = full_sol.codebase.code
    tests = full_sol.codebase.tests or ""
    report_str = ""

    if use_report_details:
        details_list = []
        report = full_sol.report

        if report.data_preprocessing:
            details_list.append(f"Data Preprocessing: {report.data_preprocessing}")
        if report.model_or_algorithm:
            details_list.append(f"Algorithm/Model: {report.model_or_algorithm}")
        if report.hyperparameters:
            details_list.append(f"Hyperparameters: {report.hyperparameters}")
        if report.evaluation_metrics:
            details_list.append(f"Evaluation Metrics: {report.evaluation_metrics}")
        if report.assumptions_or_caveats:
            details_list.append(f"Assumptions or Caveats: {report.assumptions_or_caveats}")

        report_str = "\n".join(details_list) if details_list else "No additional domain-specific details."
        
    return (
        f"<problem>\n{question}\n</problem>\n"
        f"<solution>\n"
        f"Reasoning: {reasoning}\n"
        f"Pseudocode: {pseudocode}\n"
        f"Code:\n{code}\n"
        f"Tests:\n{tests}\n"
        f"{report_str}"
        f"</solution>"
    )


def retrieve_examples(state: State, retriever: HybridRetriever, config: RunnableConfig):
    top_k = config["configurable"].get("k") or 2

    candidate = state.get("candidate")
    if not candidate:
        # Nothing to query with ⇒ return empty examples and continue gracefully
        return {"examples": ""}
    
    # Extract code from the message
    code = ""
    # 2a. AIMessage with tool calls
    if isinstance(candidate, AIMessage) and candidate.tool_calls:
        code = candidate.tool_calls[0]["args"].get("code", "")
    # 2b. dict produced by solvers
    elif isinstance(candidate, dict):
        code = candidate.get("codebase", {}).get("code", "")
    # 2c. Anything else – fall back to the raw string
    else:
        code = str(candidate)

    if not code:
        # Still nothing usable → no examples.
        return {"examples": ""}
    
    # TODO: USE HYBRID RETRIVAL TO GET RELEVANT DOC AND FORMAT USING format_example
    docs = retriever.invoke(code)
    docs_str = "\n".join([doc.page_content for doc in docs[:top_k]])

    examples_str = f"""
    You previously solved the following problems in this competition:
    <Examples>
    {docs_str}
    <Examples>
    Approach this new question with similar sophistication."""

    return {"examples": examples_str}
