from src.rag.vector_store import search_vector
from src.rag.bm25_index import search_bm25


def hybrid_retrieve(query: str, top_k: int = 4) -> list:
    bm25 = search_bm25(query, top_k=top_k)
    vect = search_vector(query, top_k=top_k)

    seen = set()
    merged = []

    for item in bm25 + vect:
        key = item["text"]
        if key not in seen:
            seen.add(key)
            merged.append(item)

    return merged[:top_k]