import argparse
import os
import json
import io
import statistics
from typing import List, Dict, Any, Optional, Tuple

try:
    import fitz
except Exception as e:
    raise ImportError("PyMuPDF (fitz) is required. pip install pymupdf") from e

try:
    import pdfplumber
except Exception as e:
    raise ImportError("pdfplumber is required. pip install pdfplumber") from e

from PIL import Image, ImageFilter

try:
    import pytesseract
    HAS_TESSERACT = True
except Exception:
    HAS_TESSERACT = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def pil_from_pixmap(pix):
    if pix.n >= 5:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return img

def is_chart_image(img: Image.Image, edge_thresh: float = 0.03) -> bool:
    w, h = img.size
    if w * h == 0:
        return False
    try:
        if HAS_CV2:
            arr = np.array(img.convert("L"))
            edges = cv2.Canny(arr, 50, 150)
            edge_density = float(np.count_nonzero(edges)) / (w * h)
            return edge_density > edge_thresh
        else:
            edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
            arr = np.array(edges)
            strong_edges = (arr > 50).sum()
            edge_density = float(strong_edges) / (w * h)
            return edge_density > edge_thresh
    except Exception:
        return False

def clean_text(t: Optional[str]) -> Optional[str]:
    if t is None:
        return None
    s = t.strip()
    return s if s != "" else None

def extract_with_fitz(pdf_path: str) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    pages_blocks = []
    for p_idx in range(len(doc)):
        page = doc[p_idx]
        page_dict = page.get_text("dict")
        raw_blocks = page_dict.get("blocks", [])
        span_sizes = []
        for b in raw_blocks:
            if b.get("type", 1) == 0:
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        span_sizes.append(span.get("size", 0.0))
        if len(span_sizes) == 0:
            avg_size = 0.0
            std_size = 0.0
        else:
            avg_size = statistics.mean(span_sizes)
            std_size = statistics.pstdev(span_sizes) if len(span_sizes) > 1 else 0.0

        blocks_for_page = []
        for block in raw_blocks:
            btype = block.get("type", 1)
            bbox = block.get("bbox", [0, 0, 0, 0])
            top = float(bbox[1])
            if btype == 0:
                text_pieces = []
                max_span_size = 0.0
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        st = span.get("text", "")
                        sz = span.get("size", 0.0)
                        line_text += st
                        max_span_size = max(max_span_size, sz)
                    text_pieces.append(line_text)
                block_text = "\n".join(text_pieces).strip()
                blocks_for_page.append({
                    "kind": "text",
                    "bbox": bbox,
                    "top": top,
                    "text": block_text,
                    "max_span_size": max_span_size,
                    "avg_page_span_size": avg_size,
                    "std_page_span_size": std_size
                })
            elif btype == 1:
                img_info = block.get("image", {})
                if isinstance(img_info, dict):
                    xref = img_info.get("xref")
                else:
                    xref = None
                blocks_for_page.append({
                    "kind": "image",
                    "bbox": bbox,
                    "top": top,
                    "image_xref": xref,
                    "image_meta": img_info if isinstance(img_info, dict) else None
                })
        pages_blocks.append(blocks_for_page)
    doc.close()
    return pages_blocks

def extract_tables_pdfplumber(pdf_path: str) -> Dict[int, List[Dict[str, Any]]]:
    results = {}
    with pdfplumber.open(pdf_path) as pdf:
        for p_idx, page in enumerate(pdf.pages):
            page_tables = []
            try:
                tables = page.find_tables()
            except Exception:
                tables = []
            for t in tables:
                try:
                    table_data = t.extract()
                except Exception:
                    try:
                        table_data = page.extract_table(t.bbox) or []
                    except Exception:
                        table_data = []
                bbox = t.bbox if hasattr(t, "bbox") else None
                page_tables.append({
                    "bbox": bbox,
                    "top": bbox[1] if bbox else None,
                    "table": table_data
                })
            results[p_idx] = page_tables
    return results

def save_image_from_xref(doc, xref, out_path):
    pix = fitz.Pixmap(doc, xref)
    img = pil_from_pixmap(pix)
    img.save(out_path, format="PNG")
    return out_path

def build_structured_json(pdf_path: str,
                          output_dir: str,
                          do_ocr: bool = False,
                          detect_charts_flag: bool = True,
                          save_images: bool = True) -> Dict[str, Any]:
    ensure_dir(output_dir)
    assets_dir = os.path.join(output_dir, "assets")
    if save_images:
        ensure_dir(assets_dir)

    fitz_pages_blocks = extract_with_fitz(pdf_path)
    tables_by_page = extract_tables_pdfplumber(pdf_path)
    doc = fitz.open(pdf_path)
    document = {"pages": []}

    for p_idx, blocks in enumerate(fitz_pages_blocks):
        page_content: List[Dict[str, Any]] = []
        current_section = None
        current_subsection = None

        table_items = []
        for t in tables_by_page.get(p_idx, []):
            top = t.get("top") if t.get("top") is not None else 0
            table_items.append({
                "kind": "table",
                "bbox": t.get("bbox"),
                "top": top,
                "table": t.get("table")
            })

        image_items = []
        img_counter = 0
        for b in blocks:
            if b["kind"] == "image":
                top = b.get("top", 0)
                xref = b.get("image_xref")
                if not xref:
                    continue
                img_counter += 1
                img_name = f"page{p_idx+1}_img{img_counter}.png"
                img_path = os.path.join(assets_dir, img_name) if save_images else None
                try:
                    if save_images:
                        save_image_from_xref(doc, xref, img_path)
                        pil_img = Image.open(img_path)
                    else:
                        pix = fitz.Pixmap(doc, xref)
                        pil_img = pil_from_pixmap(pix)
                        img_path = None
                except Exception:
                    pil_img = None
                image_items.append({
                    "kind": "image",
                    "bbox": b.get("bbox"),
                    "top": top,
                    "image_path": img_path,
                    "pil_image": pil_img
                })

        text_items = []
        for b in blocks:
            if b["kind"] == "text":
                top = b.get("top", 0)
                text_items.append({
                    "kind": "text",
                    "bbox": b.get("bbox"),
                    "top": top,
                    "text": b.get("text"),
                    "max_span_size": b.get("max_span_size", 0.0),
                    "avg_page_span_size": b.get("avg_page_span_size", 0.0),
                    "std_page_span_size": b.get("std_page_span_size", 0.0)
                })

        merged = []
        merged.extend(text_items)
        merged.extend(table_items)
        merged.extend(image_items)
        merged.sort(key=lambda x: (x.get("top", 0)))

        for item in merged:
            kind = item["kind"]
            if kind == "text":
                text = clean_text(item.get("text", ""))
                if not text:
                    continue
                max_sz = item.get("max_span_size", 0.0)
                avg = item.get("avg_page_span_size", 0.0)
                std = item.get("std_page_span_size", 0.0)
                if std > 0:
                    if max_sz >= (avg + 1.4 * std) and len(text) < 200:
                        current_section = text.replace("\n", " ").strip()
                        current_subsection = None
                        page_content.append({
                            "type": "heading",
                            "level": "section",
                            "section": current_section,
                            "sub_section": None,
                            "text": current_section
                        })
                        continue
                    elif max_sz >= (avg + 0.8 * std) and len(text) < 200:
                        current_subsection = text.replace("\n", " ").strip()
                        page_content.append({
                            "type": "heading",
                            "level": "sub_section",
                            "section": current_section,
                            "sub_section": current_subsection,
                            "text": current_subsection
                        })
                        continue
                one_line = text.replace("\n", " ").strip()
                if len(one_line.split()) <= 6 and one_line.isupper():
                    current_subsection = None
                    current_section = one_line
                    page_content.append({
                        "type": "heading",
                        "level": "section",
                        "section": current_section,
                        "sub_section": None,
                        "text": current_section
                    })
                    continue
                page_content.append({
                    "type": "paragraph",
                    "section": current_section,
                    "sub_section": current_subsection,
                    "text": one_line
                })
            elif kind == "table":
                rows = item.get("table", []) or []
                clean_rows = [[("" if cell is None else str(cell).strip()) for cell in row] for row in rows]
                page_content.append({
                    "type": "table",
                    "section": current_section,
                    "sub_section": current_subsection,
                    "description": None,
                    "table_data": clean_rows
                })
            elif kind == "image":
                pil_img = item.get("pil_image")
                image_path = item.get("image_path")
                is_chart = False
                ocr_text = None
                if pil_img is not None:
                    if detect_charts_flag:
                        try:
                            is_chart = is_chart_image(pil_img)
                        except Exception:
                            is_chart = False
                    if do_ocr and HAS_TESSERACT:
                        try:
                            ocr_text = pytesseract.image_to_string(pil_img).strip()
                            if ocr_text == "":
                                ocr_text = None
                        except Exception:
                            ocr_text = None
                entry_type = "chart" if is_chart else "image"
                entry = {
                    "type": entry_type,
                    "section": current_section,
                    "sub_section": current_subsection,
                    "image_path": os.path.relpath(image_path, output_dir) if image_path else None,
                    "description": ocr_text
                }
                page_content.append(entry)

        document["pages"].append({
            "page_number": p_idx + 1,
            "content": page_content
        })
    doc.close()
    return document

def main():
    parser = argparse.ArgumentParser(description="Parse a PDF into a structured JSON.")
    parser.add_argument("input_pdf", help="Path to input PDF")
    parser.add_argument("output_json", help="Path to output JSON file")
    parser.add_argument("--output-dir", default="output_extraction", help="Directory to store assets (images) and JSON")
    parser.add_argument("--ocr", action="store_true", help="Attempt OCR on images (requires pytesseract & tesseract)")
    parser.add_argument("--no-charts", dest="detect_charts", action="store_false", help="Disable chart detection heuristics")
    parser.add_argument("--no-save-images", dest="save_images", action="store_false", help="Do not save extracted images to disk")
    args = parser.parse_args()

    ensure_dir(args.output_dir)
    structured = build_structured_json(
        pdf_path=args.input_pdf,
        output_dir=args.output_dir,
        do_ocr=args.ocr,
        detect_charts_flag=args.detect_charts,
        save_images=args.save_images
    )
    out_path = args.output_json
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2, ensure_ascii=False)
    print(f"Saved structured JSON to: {out_path}")
    if args.save_images:
        print(f"Saved media assets to: {os.path.join(args.output_dir, 'assets')}")

if __name__ == "__main__":
    main()

