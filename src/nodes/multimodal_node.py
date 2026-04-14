from src.graph.state import EcoSenseState


def multimodal_node(state: EcoSenseState) -> EcoSenseState:
    inputs = state.get("multimodal_inputs", []) or []
    operator_note = (state.get("operator_note", "") or "").strip()

    evidence = []
    image_count = 0
    pdf_count = 0
    other_count = 0

    for item in inputs:
        name = str(item.get("name", "uploaded_file"))
        mime = str(item.get("type", "unknown"))
        size = int(item.get("size", 0) or 0)
        size_kb = round(size / 1024, 1) if size else 0

        if "image" in mime:
            image_count += 1
            desc = f"Operator uploaded image '{name}' ({size_kb} KB) as visual evidence."
        elif "pdf" in mime:
            pdf_count += 1
            desc = f"Operator uploaded PDF '{name}' ({size_kb} KB) as document evidence."
        else:
            other_count += 1
            desc = f"Operator uploaded file '{name}' ({size_kb} KB) as additional evidence."

        evidence.append({"text": desc, "source": "multimodal", "file_name": name, "mime_type": mime})
        extracted = str(item.get("extracted_text", "")).strip()
        extractor = str(item.get("extractor", "")).strip()
        if extracted:
            snippet = extracted[:450] + ("..." if len(extracted) > 450 else "")
            method = f" via {extractor}" if extractor else ""
            evidence.append(
                {
                    "text": f"Extracted content from '{name}'{method}: {snippet}",
                    "source": "multimodal",
                    "file_name": name,
                    "mime_type": mime,
                }
            )

    if operator_note:
        evidence.append(
            {
                "text": f"Operator note: {operator_note}",
                "source": "multimodal",
                "file_name": "operator_note",
                "mime_type": "text/plain",
            }
        )

    multimodal_meta = {
        "enabled": True,
        "inputs_count": len(inputs),
        "image_count": image_count,
        "pdf_count": pdf_count,
        "other_count": other_count,
        "has_operator_note": bool(operator_note),
    }

    msgs = state.get("messages", [])
    msgs.append(
        {
            "agent": "Multimodal",
            "type": "evidence",
            "content": (
                f"Received multimodal inputs={len(inputs)} "
                f"(images={image_count}, pdfs={pdf_count}, other={other_count}), "
                f"operator_note={'yes' if operator_note else 'no'}, "
                f"text_extracted={sum(1 for i in inputs if str(i.get('extracted_text','')).strip())}"
            ),
        }
    )

    return {
        **state,
        "multimodal_evidence": evidence,
        "multimodal_meta": multimodal_meta,
        "messages": msgs,
    }
