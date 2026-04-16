import argparse
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.ingestion.data_loader import load_dataset
from src.graph.workflow import run_workflow
from src.tools.reporting_tools import build_pdf


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _run_for_building(building_id: str, query: str) -> dict:
    result = run_workflow(query=query, building_id=building_id)
    resp = result.get("final_response", {})
    report_path = build_pdf(result)

    return {
        "building_id": building_id,
        "risk": resp.get("risk_card", {}).get("value", "N/A"),
        "top_issue": resp.get("issue_card", {}).get("value", "N/A"),
        "top_action": resp.get("action_card", {}).get("value", "N/A"),
        "confidence": resp.get("confidence_card", {}).get("score", "N/A"),
        "report_path": report_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Run scheduled EcoSense analysis and generate reports.")
    parser.add_argument(
        "--query",
        default="Provide weekly operational priorities and compliance-ready summary.",
        help="Query used for each building analysis.",
    )
    parser.add_argument(
        "--building",
        action="append",
        default=[],
        help="Specific building_id to run (repeatable). If omitted, runs all buildings.",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(ROOT, "outputs", "automation"),
        help="Output directory for automation summaries.",
    )
    args = parser.parse_args()

    _ensure_dir(args.out)
    df = load_dataset()
    if df.empty:
        raise SystemExit("No dataset found. Cannot run automation.")

    building_ids = args.building or sorted(df["building_id"].unique().tolist())
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    summaries = []
    for bid in building_ids:
        try:
            summaries.append(_run_for_building(building_id=bid, query=args.query))
        except Exception as exc:
            summaries.append({"building_id": bid, "error": str(exc)})

    summary_data = {
        "generated_at": datetime.now().isoformat(),
        "query": args.query,
        "building_count": len(building_ids),
        "results": summaries,
    }

    summary_path = os.path.join(args.out, f"weekly_summary_{run_ts}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    latest_path = os.path.join(args.out, "latest_summary.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Automation run complete. Summary saved: {summary_path}")
    for item in summaries:
        if "error" in item:
            print(f"- {item['building_id']}: ERROR {item['error']}")
        else:
            print(
                f"- {item['building_id']}: risk={item['risk']} "
                f"issue={item['top_issue']} action={item['top_action']} report={item['report_path']}"
            )


if __name__ == "__main__":
    main()
