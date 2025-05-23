import streamlit as st
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image
import re
import base64

st.set_page_config(page_title="Quick Remediation Note Generator")
st.title("🧠 Generate Your Quick Remediation Note")

st.markdown("Upload your ASSET Student Performance Table PDF or screenshot to get started.")

mode = st.radio("Select Input Type", ["📄 Upload ASSET PDF", "🖼️ Upload Screenshot of Table"])

# OCR fallback
def extract_text_from_image(image_file):
    img = Image.open(image_file)
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text

# Common logic for extracting correct answers and student responses
def process_text(full_text):
    st.markdown("🔍 **Extracted Text (for debugging)**")
    st.text_area("", full_text, height=200)

    correct_line = re.findall(r"Correct\s+Answers\s*:?[\sA-D]*([A-D\s]{40,})", full_text, re.IGNORECASE)
    if not correct_line:
        st.error("❌ Correct answers row not found in PDF.")
        return

    correct_answers = correct_line[0].strip().split()
    if len(correct_answers) != 40:
        st.error(f"❌ Expected 40 correct answers, found {len(correct_answers)}.")
        return

    st.success(f"✅ Extracted {len(correct_answers)} correct answers.")

    lines = full_text.splitlines()
    student_lines = [line.strip() for line in lines if re.match(r"^\d+\s+[A-Za-z].*?[A-D✓-]{20,}", line)]

    if not student_lines:
        st.warning("⚠️ Could not extract student answers from input.")
        return

    student_data = []
    for line in student_lines:
        parts = re.split(r"\s{2,}|\t", line.strip())
        if len(parts) < 45:
            continue
        name = parts[1]
        responses = parts[2:42]
        student_data.append([name] + responses)

    if not student_data:
        st.erro
