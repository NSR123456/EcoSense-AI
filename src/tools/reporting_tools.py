from src.report.pdf_generator import generate_pdf_report


def build_pdf(result: dict) -> str:
    return generate_pdf_report(result)