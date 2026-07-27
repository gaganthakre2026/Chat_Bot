from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.core.config import Settings, get_settings
from app.rag.prompts import NOT_FOUND_ANSWER, build_grounded_answer_prompt
from app.rag.state import RAGState
from app.services.llm_provider import LLMProvider, get_llm_provider
from app.services.supabase_vector_store import SupabaseVectorStore, get_vector_store


class RAGPipeline:
    def __init__(
        self,
        vector_store: SupabaseVectorStore,
        llm_provider: LLMProvider,
        settings: Settings,
    ):
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.settings = settings
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(RAGState)
        graph.add_node("retrieve_node", self.retrieve_node)
        graph.add_node("grade_relevance_node", self.grade_relevance_node)
        graph.add_node("generate_node", self.generate_node)
        graph.add_node("groundedness_check_node", self.groundedness_check_node)
        graph.add_node("format_response_node", self.format_response_node)

        graph.set_entry_point("retrieve_node")
        graph.add_edge("retrieve_node", "grade_relevance_node")
        graph.add_edge("grade_relevance_node", "generate_node")
        graph.add_edge("generate_node", "groundedness_check_node")
        graph.add_edge("groundedness_check_node", "format_response_node")
        graph.add_edge("format_response_node", END)
        return graph.compile()

    def run(self, question: str, document_id: str, user_id: str) -> RAGState:
        initial_state: RAGState = {
            "question": question,
            "document_id": document_id,
            "user_id": user_id,
            "retrieved_chunks": [],
            "answer": "",
            "confidence": 0.0,
            "grounded": False,
        }
        return self.graph.invoke(initial_state)

    def retrieve_node(self, state: RAGState) -> RAGState:
        query_embedding = self.llm_provider.embed_query(state["question"])
        chunks = self.vector_store.query(
            document_id=state["document_id"],
            user_id=state["user_id"],
            embedding=query_embedding,
            top_k=self.settings.rag_top_k,
        )
        return {"retrieved_chunks": chunks}

    def grade_relevance_node(self, state: RAGState) -> RAGState:
        threshold = self.settings.rag_similarity_threshold
        relevant_chunks = [
            chunk for chunk in state.get("retrieved_chunks", []) if chunk["score"] >= threshold
        ]
        if not relevant_chunks:
            return {
                "retrieved_chunks": [],
                "answer": NOT_FOUND_ANSWER,
                "confidence": 0.0,
                "grounded": True,
            }
        return {"retrieved_chunks": relevant_chunks}

    def generate_node(self, state: RAGState) -> RAGState:
        if state.get("answer") == NOT_FOUND_ANSWER:
            return {}

        prompt = build_grounded_answer_prompt(
            question=state["question"],
            chunks=state.get("retrieved_chunks", []),
        )
        answer = self.llm_provider.generate_answer(prompt).strip()
        if not answer:
            answer = NOT_FOUND_ANSWER
        return {"answer": answer}

    def groundedness_check_node(self, state: RAGState) -> RAGState:
        chunks = state.get("retrieved_chunks", [])
        answer = state.get("answer", "")
        if answer == NOT_FOUND_ANSWER or not chunks:
            return {"confidence": 0.0, "grounded": True}

        grounded = self.llm_provider.check_groundedness(answer, chunks)
        avg_similarity = sum(chunk["score"] for chunk in chunks) / len(chunks)
        confidence = (avg_similarity * 0.7) + (0.3 if grounded else 0.0)

        if not grounded:
            return {
                "answer": NOT_FOUND_ANSWER,
                "confidence": min(avg_similarity * 0.35, 0.35),
                "grounded": False,
            }

        return {"confidence": confidence, "grounded": True}

    def format_response_node(self, state: RAGState) -> RAGState:
        confidence = max(0.0, min(float(state.get("confidence", 0.0)), 1.0))
        return {
            "answer": state.get("answer", NOT_FOUND_ANSWER),
            "retrieved_chunks": state.get("retrieved_chunks", []),
            "confidence": round(confidence, 2),
            "grounded": bool(state.get("grounded", False)),
        }


@lru_cache
def get_rag_pipeline() -> RAGPipeline:
    return RAGPipeline(
        vector_store=get_vector_store(),
        llm_provider=get_llm_provider(),
        settings=get_settings(),
    )
