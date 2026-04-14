import re


def check_faithfulness(technical: str, simple: str) -> dict:
    if not technical or not simple:
        return {"faithful": False, "ratio": 0.0, "reason": "Missing content"}

    t_nums = set(re.findall(r"\d+(\.\d+)?", technical))
    s_nums = set(re.findall(r"\d+(\.\d+)?", simple))

    overlap = t_nums & s_nums
    ratio = (len(overlap) / len(t_nums)) if t_nums else 1.0

    return {
        "faithful": ratio >= 0.3,
        "ratio": round(ratio, 2),
        "technical_numbers": len(t_nums),
        "simple_numbers": len(s_nums),
    }