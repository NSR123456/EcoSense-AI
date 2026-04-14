from typing import TypedDict, List, Dict, Any, Optional


class EcoSenseState(TypedDict, total=False):
    query: str
    building_id: str
    compare_building_id: Optional[str]
    requested_goal: Optional[str]
    operator_note: Optional[str]
    multimodal_inputs: List[Dict[str, Any]]
    multimodal_evidence: List[Dict[str, Any]]
    multimodal_meta: Dict[str, Any]

    route: str
    plan: Dict[str, Any]

    metrics: Dict[str, Any]
    insights: Dict[str, Any]

    issues: List[Dict[str, Any]]
    causes: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    compliance: Dict[str, Any]
    comparison: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    retrieval_meta: Dict[str, Any]
    critiques: List[Dict[str, Any]]

    confidence: Dict[str, Any]
    messages: List[Dict[str, Any]]

    technical: str
    simple: str
    final_response: Dict[str, Any]