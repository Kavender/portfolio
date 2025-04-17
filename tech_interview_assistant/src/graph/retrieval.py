
from typing import List
from collections import defaultdict
import chromadb
from langchain_core.documents import Document
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from src.graph.schemas import FullSolution, State


# TODO: THINK WHAT TO STORE IN THE VECTOR DB, 1.JUST QUESTION, 2. QUESTION+ANSWER, 3. Q+A+EXAMPLE?
class HybridRetriever(BaseRetriever):
    """
    A hybrid retriever that combines BM25 (syntactic) with 
    Redis-based semantic retrieval (using maximal marginal relevance).
    """
    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vectorstore: Chroma,
        embeddings: OpenAIEmbeddings,
        alpha: float = 0.5,  # Weight for the semantic score
        k: int = 3          # How many final results to return
    ):
        self.bm25_retriever = bm25_retriever
        self.vectorstore = vectorstore
        self.embeddings = embeddings
        self.alpha = alpha
        self.k = k

    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        1. Retrieve top BM25 docs
        2. Retrieve top MMR docs from Chroma
        3. Merge by a weighted scoring strategy
        """
        combined_doc_scores = defaultdict(float)
        # ---- BM25 retrieval ----
        bm25_docs = self.bm25_retriever.get_relevant_documents(query)
        for rank, doc in enumerate(bm25_docs):
            score = 1.0 / (rank + 1)
            combined_doc_scores[doc] += (1 - self.alpha) * score
        
        # ---- Vector store MMR retrieval ----
        # `maximal_marginal_relevance_search` returns a list of (Document, score)
        vector_docs = self.vectorstore.max_marginal_relevance_search(
            query,
            k=self.k * 2,
            fetch_k=self.k * 4,
        )
        for rank, doc in enumerate(vector_docs):
            score = 1.0 / (rank + 1)
            combined_doc_scores[doc] += self.alpha * score

        # ---- Merge search results from two retrievers ----
        combined_sorted = sorted(combined_doc_scores.items(), key=lambda x: x[1], reverse=True)
        limit = min([self.k, len(combined_sorted)+ 1])
        top_docs = [doc for doc, _ in combined_sorted[: limit]]
        return top_docs

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """Implement async retrieval if needed."""
        raise NotImplementedError("Async retrieval not implemented.")


# TODO: ASSUME ['solution'] is json string, will finalize once decided on the sql part
def format_example(question: str, solution, use_report_details=True) -> str:
    """
    Convert one (question + FullSolution JSON) pair into a text snippet for similarity retrieval.
    """

    try:
        full_sol = FullSolution.parse_raw(solution)
    except:
        # If failed on parsing, fallback to raw text
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

        # Build a nice multiline summary for 'details'
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
    ai_message: AIMessage = state["candidate"]
    if not ai_message.tool_calls:
        raise ValueError("Draft agent did not produce a valid code block")
    code = ai_message.tool_calls[0]["args"]["code"]
    
    # TODO: USE HYBRID RETRIVAL TO GET RELEVANT DOC AND FORMAT USING format_example
    examples_str = "\n".join(
        [doc.page_content for doc in retriever.get_relevant_documents(code)[:top_k]]
    )
    examples_str = f"""
    You previously solved the following problems in this competition:
    <Examples>
    {examples_str}
    <Examples>
    Approach this new question with similar sophistication."""
    return {"examples": examples_str}
