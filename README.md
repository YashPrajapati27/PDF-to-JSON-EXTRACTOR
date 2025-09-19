PDF → Structured JSON extractor
--------------------------------

What it does:
  - Extracts text blocks and infers headings (section / sub-section)
  - Extracts tables (using pdfplumber)
  - Extracts images and heuristically flags charts
  - Optionally runs OCR on images (pytesseract)
  - Outputs structured JSON with page-level hierarchy

Prerequisites:
  - Python 3.8+
  - pip
  - (Optional, for OCR) Tesseract installed on system and pytesseract package

Install:
  pip install -r requirements.txt

  # If using OCR, install Tesseract:
  # Ubuntu/Debian: sudo apt install tesseract-ocr
  # macOS (brew): brew install tesseract
  # Windows: download from tesseract project, add to PATH

Run:
  python pdf_to_structured_json.py sample.pdf output.json --output-dir extraction_out --ocr

Flags:
  --ocr            : Enable OCR on images (requires tesseract & pytesseract)
  --no-charts      : Disable chart detection heuristics
  --no-save-images : Do not save extracted images to disk

Output:
  - JSON file (output.json) with structure:
    {
      "pages": [
        {
          "page_number": 1,
          "content": [
             { "type": "heading", "level": "section", "text": "...", "section": "..."},
             { "type": "paragraph", "text": "...", "section": "...", "sub_section": "..." },
             { "type": "table", "table_data": [...] },
             { "type": "chart", "image_path": "assets/page1_img1.png", "description": "..."}
          ]
        }
      ]
    }

Notes:
  - Table detection depends on how tables are rendered in the PDF. For some PDFs, you may get better results with Camelot (requires extra system deps).
  - Heading detection is heuristic-based (font size and short all-caps fallback). Tune thresholds in script if needed.
