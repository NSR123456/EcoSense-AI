from src.rag.retriever import hybrid_retrieve


def get_evidence_for_query(query: str, top_k: int = 4) -> list:
    return hybrid_retrieve(query, top_k=top_k)