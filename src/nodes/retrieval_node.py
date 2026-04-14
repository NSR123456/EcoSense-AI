from src.graph.state import EcoSenseState
from src.tools.retrieval_tools import get_evidence_for_query


def retrieval_node(state: EcoSenseState) -> EcoSenseState:
    query = state.get("query", "")
    building_id = state.get("building_id", "unknown")
    route = state.get("route", "unknown")

    retrieval_query = (
        f"{query} building {building_id} "
        f"energy anomalies variability base load route {route}"
    ).strip()

    rag_evidence = get_evidence_for_query(retrieval_query, top_k=4)
    multimodal_evidence = state.get("multimodal_evidence", []) or []

    evidence = []
    seen = set()
    for item in multimodal_evidence + rag_evidence:
        text = item.get("text", "")
        key = text if text else str(item)
        if key in seen:
            continue
        seen.add(key)
        evidence.append(item)

    by_source = {}
    for item in evidence:
        src = str(item.get("source", "unknown")).lower()
        by_source[src] = by_source.get(src, 0) + 1

    retrieval_meta = {
        "enabled": True,
        "query": retrieval_query,
        "total_evidence": len(evidence),
        "bm25_count": by_source.get("bm25", 0),
        "vector_count": by_source.get("vector", 0),
        "multimodal_count": by_source.get("multimodal", 0),
        "route": route,
    }

    msgs = state.get("messages", [])
    msgs.append(
        {
            "agent": "Retrieval",
            "type": "evidence",
            "content": (
                f"RAG fetched {len(evidence)} item(s) "
                f"(bm25={retrieval_meta['bm25_count']}, vector={retrieval_meta['vector_count']}, "
                f"multimodal={retrieval_meta['multimodal_count']})"
            ),
        }
    )

    return {
        **state,
        "evidence": evidence,
        "retrieval_meta": retrieval_meta,
        "messages": msgs,
    }
