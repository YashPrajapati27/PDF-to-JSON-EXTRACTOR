import streamlit as st
import json
import tempfile
import os
import shutil
from new1 import build_structured_json

st.set_page_config(page_title="PDF to Structured JSON", layout="wide")

st.title("📄 PDF → Structured JSON Extractor")
st.write("Upload a PDF, and this tool will extract headings, paragraphs, tables, and images into a structured JSON format.")

st.sidebar.header("Settings")
enable_ocr = st.sidebar.checkbox("Enable OCR on Images", value=False)
detect_charts = st.sidebar.checkbox("Detect Charts", value=True)
save_images = st.sidebar.checkbox("Save Images", value=True)

uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

if uploaded_file:
    st.success(f"✅ File uploaded: {uploaded_file.name}")
    tmpdir = tempfile.mkdtemp()
    try:
        pdf_path = os.path.join(tmpdir, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.read())
        st.info("⏳ Processing PDF... This may take a moment.")
        structured_data = build_structured_json(
            pdf_path=pdf_path,
            output_dir=tmpdir,
            do_ocr=enable_ocr,
            detect_charts_flag=detect_charts,
            save_images=save_images
        )
        st.success("✅ Extraction complete!")
        st.subheader("📑 Extracted Content")
        for page in structured_data["pages"]:
            with st.expander(f"📄 Page {page['page_number']}", expanded=False):
                for item in page["content"]:
                    if item["type"] in ["heading", "paragraph"]:
                        st.markdown(f"**{item['type'].capitalize()}**: {item['text']}")
                    elif item["type"] == "table":
                        st.markdown("**Table:**")
                        st.table(item["table_data"])
                    elif item["type"] in ["image", "chart"]:
                        if item["image_path"] and save_images:
                            img_path = os.path.join(tmpdir, item["image_path"])
                            st.image(img_path, caption=f"{item['type'].capitalize()}")
                        if item["description"]:
                            st.caption(f"OCR: {item['description']}")
        json_output = json.dumps(structured_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Download JSON",
            data=json_output,
            file_name="structured_output.json",
            mime="application/json"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
