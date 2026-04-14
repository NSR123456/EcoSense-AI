def compute_confidence(issues=None, evidence=None, critiques=None) -> dict:
    issues = issues or []
    evidence = evidence or []
    critiques = critiques or []

    score = 50
    if issues:
        score += 15
    if evidence:
        score += min(len(evidence) * 8, 24)
    if critiques:
        score -= min(len(critiques) * 10, 20)

    score = max(0, min(100, score))
    label = "high" if score >= 75 else ("medium" if score >= 50 else "low")

    return {"score": score, "label": label}