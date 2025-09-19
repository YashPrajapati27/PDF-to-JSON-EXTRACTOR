# 📄 PDF to Structured JSON Extractor

LIVE DEMO :- https://pdf-to-json-extractor-fosk77xxjhptajzgegdczg.streamlit.app/

This project extracts **headings, paragraphs, tables, and images** from PDF files and converts them into a **clean, hierarchical JSON format**.  
It includes an interactive **Streamlit web interface** that allows users to upload PDFs, preview extracted content, and download the structured JSON output.

---

## 🚀 Features
- 📑 **Preserves Page Hierarchy** – Extracted data is organized page by page.
- 🏷 **Heading & Sub-Section Detection** – Automatically detects sections and sub-sections using font size and style heuristics.
- 📜 **Clean Paragraph Extraction** – Removes unwanted whitespace and formatting.
- 📊 **Table Extraction** – Captures tables as structured `table_data` arrays.
- 🖼 **Image & Chart Detection** – Extracts images, flags charts, and optionally performs OCR on them.
- 🌐 **Streamlit Interface** – Simple web UI to upload PDFs, preview results, and download JSON.

---

## 📂 Project Structure
pdf_extractor_project/
├── app.py # Streamlit UI
├── new1.py # Core logic for PDF parsing & JSON creation
├── requirements.txt # Python dependencies


---

## 🛠 Installation

1. **Clone or download** this project.
2. Open a terminal in the project folder and create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # On Windows
   # source venv/bin/activate  # On Mac/Linux
pip install --upgrade pip
pip install -r requirements.txt

▶️ Running the App

Run the Streamlit app:

streamlit run app.py
Then open the local URL shown in the terminal (usually http://localhost:8501).

🖥️ Usage

Upload a PDF from your computer.

(Optional) Enable OCR or Chart Detection from the sidebar.

View the extracted content page by page in expandable sections.

Download the structured JSON by clicking 📥 Download JSON.

📊 Example Output (JSON)
{
  "pages": [
    {
      "page_number": 1,
      "content": [
        {
          "type": "heading",
          "level": "section",
          "section": "Introduction",
          "text": "Introduction"
        },
        {
          "type": "paragraph",
          "section": "Introduction",
          "text": "This is an example paragraph extracted from the PDF."
        },
        {
          "type": "table",
          "section": "Financial Data",
          "table_data": [
            ["Year", "Revenue", "Profit"],
            ["2022", "$10M", "$2M"]
          ]
        }
      ]
    }
  ]
}

🧾 Deliverables

✅ Streamlit App (app.py) – For easy PDF upload, preview, and JSON download.

✅ Core Parser (new1.py) – Modular Python code to parse PDF programmatically.

✅ requirements.txt – Easy installation of dependencies.

✅ README.md – Setup and usage instructions.

🏆 Highlights

Robust handling of text, tables, and images.

Works with both digital and scanned PDFs (with OCR enabled).

Clean and internship-ready project, easy to present and explain.

📜 License

This project is free to use and modify for educational and internship purposes.




