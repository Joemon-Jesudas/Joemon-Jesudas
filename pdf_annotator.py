# services/pdf_annotator.py
import fitz  # PyMuPDF
from typing import Dict, Any, List
import io

def _norm_polygon_to_rect(polygon: List[float]) -> fitz.Rect:
    # polygon may be [x1,y1,x2,y2,...] or list of points; take min/max
    xs = polygon[0::2]
    ys = polygon[1::2]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return fitz.Rect(x0, y0, x1, y1)

def annotate_pdf_with_chunks(input_pdf_bytes: bytes, highlights: Dict[int, List[Dict[str, Any]]]) -> bytes:
    """
    highlights: {page_idx: [ {bbox: [x1,y1,...], label: str}, ... ] }
    """
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    for page_idx, items in highlights.items():
        if page_idx < 0 or page_idx >= doc.page_count:
            continue
        page = doc.load_page(page_idx)
        for item in items:
            bbox = item.get("bbox")
            label = item.get("label", "")
            if not bbox:
                continue
            rect = _norm_polygon_to_rect(bbox)
            # Add highlight annotation
            try:
                annot = page.add_highlight_annot(rect)
                annot.set_info(contents=label)
                annot.update()
            except Exception:
                # fallback to drawing rectangle
                r = page.new_shape()
                r.draw_rect(rect)
                r.finish(width=0.8)
                r.commit()
    out = doc.write()
    doc.close()
    return out

def build_highlights_from_analyze_result(analyze_result: Dict[str, Any], keywords: List[str] = None) -> Dict[int, List[Dict[str, Any]]]:
    """
    Given the analyze_result (dict or object converted to dict), return
    a mapping page->list of {bbox, label} for lines that match keywords.
    """
    highlights = {}
    pages = analyze_result.get("pages", [])
    if not pages:
        return highlights
    for p_idx, page in enumerate(pages):
        items = []
        for line in page.get("lines", []):
            text = line.get("content", "")
            bbox = line.get("boundingBox") or line.get("polygon") or line.get("bounding_box") or line.get("bbox")
            # Check keywords
            if keywords:
                for kw in keywords:
                    if kw.lower() in (text or "").lower():
                        items.append({"bbox": bbox if bbox else [], "label": text})
                        break
        if items:
            highlights[p_idx] = items
    return highlights
