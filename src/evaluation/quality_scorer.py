import re


def score_quality(text: str) -> dict:
    if not text:
        return {"score": 0, "reasons": ["Empty output"]}

    score = 40
    reasons = []

    if len(text) > 80:
        score += 15
        reasons.append("Sufficient detail")

    if re.search(r"\d+(\.\d+)?", text):
        score += 15
        reasons.append("Contains quantitative evidence")

    if any(sym in text for sym in ["•", "\n", ":", "-", "|"]):
        score += 10
        reasons.append("Structured response")

    if any(w in text.lower() for w in ["issue", "action", "confidence", "score", "evidence"]):
        score += 10
        reasons.append("Decision-oriented content")

    return {"score": min(score, 100), "reasons": reasons}