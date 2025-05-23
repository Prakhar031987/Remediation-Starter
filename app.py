import streamlit as st
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image
import io
import re
import base64

st.set_page_config(page_title="Quick Remediation Note Generator")
st.title("🧠 Generate Your Quick Remediation Note")

st.markdown("Upload your ASSET Student Performance Table PDF or screenshot to get started.")

# --- Input selector ---
input_type = st.radio("Select Input Type", ["📄 Upload ASSET PDF", "🌅 Upload Screenshot of Table"])

uploaded_file = None
if input_type == "📄 Upload ASSET PDF":
    uploaded_file = st.file_uploader("📄 Upload your ASSET Student Performance PDF", type=["pdf"])
else:
    uploaded_file = st.file_uploader("🖼 Upload Screenshot (JPG, PNG)", type=["png", "jpg", "jpeg"])

def extract_text_from_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img, config="--psm 6")

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

# --- PROCESS BUTTON ---
if uploaded_file:
    st.success("File uploaded successfully!")
    if st.button("⚡ Generate my Quick Remediation Note"):
        raw_text = ""
        try:
            if input_type == "📄 Upload ASSET PDF":
                raw_text = extract_text_from_pdf(uploaded_file)
            else:
                raw_text = extract_text_from_image(uploaded_file.read())
        except Exception as e:
            st.error(f"⚠️ Error reading file: {e}")
            st.stop()

        st.markdown("🔍 **Extracted Text**")
        st.text_area("", raw_text, height=200)

        # --- Extract correct answers ---
        correct_line = re.findall(r"Correct\s+Answers\s+.*?([A-D\s]+)\n", raw_text)
        if not correct_line:
            st.error("❌ Correct answers row not found in text.")
            st.stop()

        correct_answers = correct_line[0].strip().split()
        if len(correct_answers) != 40:
            st.error(f"❌ Expected 40 correct answers, found {len(correct_answers)}.")
            st.stop()
        st.success(f"✅ Extracted {len(correct_answers)} correct answers.")

        # --- Extract student rows ---
        lines = raw_text.splitlines()
        student_lines = [line.strip() for line in lines if re.match(r"^\d+\s+[A-Za-z]", line)]

        if not student_lines:
            st.warning("⚠️ Could not extract student answers.")
            st.stop()

        student_data = []
        for line in student_lines:
            parts = re.split(r"\s{2,}|	", line.strip())
            if len(parts) < 45:
                continue
            name = parts[1]
            responses = parts[2:42]
            student_data.append([name] + responses)

        df = pd.DataFrame(student_data, columns=["Student"] + list(range(1, 41)))

        # --- Dashboard Summary ---
        summary = []
        for i in range(40):
            q = i + 1
            correct = correct_answers[i]
            col = str(q)
            options = df[col].value_counts(normalize=True) * 100
            acc = options.get(correct, 0.0)
            wrong_options = options.drop(labels=[correct], errors='ignore')
            dominant_wrong = ''
            if not wrong_options.empty:
                top_wrong = wrong_options.idxmax()
                if wrong_options[top_wrong] >= 30:
                    dominant_wrong = f"{top_wrong}: {wrong_options[top_wrong]:.0f}%"
            buckets = []
            if acc < 30:
                buckets.append("Difficult")
                if all(p <= 30 for p in wrong_options.values):
                    buckets.append("Critical Learning Gap")
            if dominant_wrong:
                buckets.append("Misconception")
            if acc > 70:
                buckets.append("Easy")
            summary.append({
                "Q": q,
                "Accuracy%": f"{acc:.0f}",
                "DominantWrongOption%": dominant_wrong,
                "Buckets": " | ".join(buckets)
            })

        df_summary = pd.DataFrame(summary)
        st.subheader("📊 Dashboard Summary")
        st.dataframe(df_summary, use_container_width=True)

        # --- Download ---
        csv = df_summary.to_csv(index=False).encode('utf-8')
        b64 = base64.b64encode(csv).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="Quick_Remediation_Note.csv">📥 Download CSV Report</a>'
        st.markdown(href, unsafe_allow_html=True)
