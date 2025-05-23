import streamlit as st
import pandas as pd
import pdfplumber
import re
import base64

st.set_page_config(page_title="Quick Remediation Note Generator")
st.title("🧠 Generate Your Quick Remediation Note")

st.markdown("Upload your ASSET Student Performance Table PDF to get started.")

uploaded_file = st.file_uploader("📄 Upload PDF Report", type=["pdf"])

if uploaded_file:
    st.success("PDF uploaded successfully!")
    generate = st.button("⚡ Generate my Quick Remediation Note")

    if generate:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

        st.markdown("🔍 **Extracted PDF Text**")
        st.text_area("", full_text, height=150)

        correct_line = re.findall(r"Correct\s+Answers\s+.*?([A-D\s]+)\n", full_text)
        if not correct_line:
            st.error("❌ Correct answers row not found in PDF.")
            st.stop()

        correct_answers = correct_line[0].strip().split()
        if len(correct_answers) != 40:
            st.error(f"❌ Expected 40 correct answers, found {len(correct_answers)}.")
            st.stop()
        st.success(f"✅ Extracted {len(correct_answers)} correct answers.")

        lines = full_text.splitlines()
        student_lines = []

        for line in lines:
            if re.match(r"^\d+\s+[A-Za-z]", line):
                student_lines.append(line.strip())

        if not student_lines:
            st.warning("⚠️ Could not extract student answers from PDF.")
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

        csv = df_summary.to_csv(index=False).encode('utf-8')
        b64 = base64.b64encode(csv).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="Quick_Remediation_Note.csv">📥 Download CSV Report</a>'
        st.markdown(href, unsafe_allow_html=True)
