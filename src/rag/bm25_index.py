from rank_bm25 import BM25Okapi

_DOCS = [
    "Buildings with high usage variability should review HVAC and lighting schedules.",
    "Peak demand management can reduce electricity costs by 15 to 25 percent.",
    "Always-on base loads often indicate standby waste or uncontrolled equipment operation.",
    "Energy audits should prioritize anomaly-heavy buildings for operational inspection.",
    "Replacing inefficient cooling equipment can significantly reduce long-term energy use.",
]

_tokens = [d.lower().split() for d in _DOCS]
_bm25 = BM25Okapi(_tokens)


def search_bm25(query: str, top_k: int = 3) -> list:
    q = query.lower().split()
    scores = _bm25.get_scores(q)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"text": _DOCS[i], "score": float(s), "source": "bm25"} for i, s in ranked]