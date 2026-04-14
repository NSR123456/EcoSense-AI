from src.evaluation.quality_scorer import score_quality
from src.evaluation.faithfulness import check_faithfulness


def evaluate_response(technical: str, simple: str) -> dict:
    return {
        "quality": score_quality(technical),
        "faithfulness": check_faithfulness(technical, simple),
    }