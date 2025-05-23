import streamlit as st
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
import re

st.set_page_config(page_title="Quick Remediation Note Generator")
st.title("🔍 Generate Your Quick Remediation Note")

mode = st.radio("Choose input type:", ["📄 Upload ASSET PDF", "🖼 Upload Screenshot of Table"])

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return full_text

def extract_text_from_image(uploaded_image):
    img = Image.open(uploaded_image).convert("L")
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text

def extract_correct_answers(text):
    match = re.findall(r"% answered correct \(section\)\s+([\d\s]+)", text)
    if match:
        return [x.strip() for x in match[0].split() if x.strip()]
    return []

def extract_students(text):
    rows = []
    lines = text.splitlines()
    for line in lines:
        match = re.match(r"^\d+\s+([A-Za-z\s.]+)\s+([ABCD✓\*\s]+)$", line)
        if match:
            name = match.group(1).strip()
            answers = match.group(2).strip().split()
            rows.append([name] + answers)
    return rows

if mode == "📄 Upload ASSET PDF":
    uploaded_pdf = st.file_uploader("Upload your ASSET Student Performance PDF", type=["pdf"])
    
    if uploaded_pdf:
        text = extract_text_from_pdf(uploaded_pdf)
        st.text_area("🔍 Extracted PDF Text", text[:3000])
        correct_answers = extract_correct_answers(text)
        if not correct_answers:
            st.warning("⚠️ Could not extract correct answers from PDF.")
        else:
            st.success(f"✅ Extracted {len(correct_answers)} correct answers.")

        students = extract_students(text)
        if students:
            df = pd.DataFrame(students, columns=["Student"] + [f"Q{i+1}" for i in range(len(students[0])-1)])
            st.dataframe(df)
        else:
            st.warning("⚠️ Could not extract student answers from PDF.")

if mode == "🖼 Upload Screenshot of Table":
    uploaded_image = st.file_uploader("Upload screenshot (PNG/JPG)", type=["png", "jpg", "jpeg"])
    
    if uploaded_image:
        text = extract_text_from_image(uploaded_image)
        st.text_area("🔍 OCR Extracted Text", text[:3000])
        
        correct_answers = extract_correct_answers(text)
        if correct_answers:
            st.success(f"✅ Extracted {len(correct_answers)} correct answers from image.")
        else:
            st.warning("⚠️ Could not find correct answer row in screenshot.")

        students = extract_students(text)
        if students:
            df = pd.DataFrame(students, columns=["Student"] + [f"Q{i+1}" for i in range(len(students[0])-1)])
            st.dataframe(df)
        else:
            st.warning("⚠️ Could not extract student rows from screenshot.")
