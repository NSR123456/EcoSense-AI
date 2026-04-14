import os
import datetime
import textwrap
from fpdf import FPDF

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _safe_text(value) -> str:
    """Convert any object to safe printable text."""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("—", "-")
    text = text.replace("•", "-")
    text = text.replace("\t", " ")
    text = text.replace("\r", " ")
    return text.strip()


def _wrap_long_line(text: str, width: int = 90) -> str:
    """
    Wrap long lines manually so fpdf does not choke on long fragments.
    """
    lines = []
    for raw_line in text.splitlines() if text else [""]:
        raw_line = raw_line.strip()
        if not raw_line:
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            raw_line,
            width=width,
            break_long_words=True,
            break_on_hyphens=True
        )
        lines.extend(wrapped if wrapped else [""])
    return "\n".join(lines)


class EcoPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, "EcoSense AI Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.cell(
            0,
            10,
            f"Page {self.page_no()} | {datetime.datetime.now():%Y-%m-%d %H:%M}",
            align="C"
        )

    def safe_multicell(self, text: str, h: int = 6, font_style: str = "", font_size: int = 10):
        self.set_font("Helvetica", font_style, font_size)
        usable_width = self.w - self.l_margin - self.r_margin
        text = _safe_text(text)
        text = _wrap_long_line(text, width=95)
        self.multi_cell(usable_width, h, text, new_x="LMARGIN", new_y="NEXT")


def generate_pdf_report(result: dict, filename: str = None) -> str:
    pdf = EcoPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if not filename:
        filename = f"ecosense_report_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf"

    resp = result.get("final_response", result)

    # Decision Summary
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Decision Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.safe_multicell(resp.get("simple", "No summary."), h=7, font_size=11)

    # Technical Summary
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Technical Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.safe_multicell(resp.get("technical", ""), h=6, font_size=10)

    # Issues
    issues = resp.get("issues", [])
    if issues:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Detected Issues", new_x="LMARGIN", new_y="NEXT")
        for issue in issues:
            line = (
                f"- {issue.get('name', 'Unknown')} | "
                f"severity={issue.get('severity', 'N/A')} | "
                f"confidence={issue.get('confidence', 'N/A')}"
            )
            pdf.safe_multicell(line, h=6, font_size=10)

    # Actions
    actions = resp.get("actions", [])
    if actions:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Recommended Actions", new_x="LMARGIN", new_y="NEXT")
        for action in actions:
            text = (
                f"- {action.get('title', 'Untitled')}\n"
                f"  when={action.get('when', 'N/A')} | "
                f"impact={action.get('impact', 'N/A')} | "
                f"urgency={action.get('urgency', 'N/A')}\n"
                f"  {action.get('what', '')}"
            )
            pdf.safe_multicell(text, h=6, font_size=10)

    # Causes
    causes = resp.get("causes", [])
    if causes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Likely Causes", new_x="LMARGIN", new_y="NEXT")
        for cause in causes:
            if isinstance(cause, dict):
                text = (
                    f"- factor={cause.get('factor', 'N/A')}\n"
                    f"  impact={cause.get('impact', 'N/A')}\n"
                    f"  evidence={cause.get('evidence', 'N/A')}\n"
                    f"  confidence={cause.get('confidence', 'N/A')}"
                )
            else:
                text = f"- {cause}"
            pdf.safe_multicell(text, h=6, font_size=10)

    # Evidence
    evidence = resp.get("evidence", [])
    if evidence:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Evidence", new_x="LMARGIN", new_y="NEXT")
        for item in evidence[:5]:
            text = f"- [{item.get('source', 'unknown')}] {item.get('text', '')}"
            pdf.safe_multicell(text, h=6, font_size=10)

    # Compliance
    compliance = resp.get("compliance", {})
    if compliance:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Compliance", new_x="LMARGIN", new_y="NEXT")
        comp_text = (
            f"Score: {compliance.get('score', 'N/A')}\n"
            f"Status: {compliance.get('status', 'N/A')}"
        )
        pdf.safe_multicell(comp_text, h=6, font_size=10)

    # Critiques
    critiques = resp.get("critiques", [])
    if critiques:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Critiques", new_x="LMARGIN", new_y="NEXT")
        for critique in critiques:
            if isinstance(critique, dict):
                text = f"- {critique.get('type', 'critique')}: {critique.get('message', '')}"
            else:
                text = f"- {critique}"
            pdf.safe_multicell(text, h=6, font_size=10)

    out_path = os.path.join(OUTPUT_DIR, filename)
    pdf.output(out_path)
    return out_path