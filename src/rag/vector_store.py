import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_RAG = True
except ImportError:
    HAS_RAG = False

_model = None
_index = None
_docs = []


DEFAULT_DOCS = [
    "Buildings with high usage variability should review HVAC and lighting schedules.",
    "Peak demand management can reduce electricity costs by 15 to 25 percent.",
    "Always-on base loads often indicate standby waste or uncontrolled equipment operation.",
    "Energy audits should prioritize anomaly-heavy buildings for operational inspection.",
    "Replacing inefficient cooling equipment can significantly reduce long-term energy use.",
]


def _ensure_index():
    global _model, _index, _docs
    if _index is not None:
        return
    if not HAS_RAG:
        return

    _docs = list(DEFAULT_DOCS)
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    embs = _model.encode(_docs, convert_to_numpy=True).astype(np.float32)
    _index = faiss.IndexFlatL2(embs.shape[1])
    _index.add(embs)


def search_vector(query: str, top_k: int = 3) -> list:
    _ensure_index()
    if _index is None or _model is None:
        return []

    q = _model.encode([query], convert_to_numpy=True).astype(np.float32)
    _, idxs = _index.search(q, top_k)
    return [{"text": _docs[i], "source": "vector"} for i in idxs[0] if 0 <= i < len(_docs)]