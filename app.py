import streamlit as st
import pandas as pd
import pdfplumber
import re
import base64
from io import BytesIO

st.set_page_config(page_title="Quick Remediation Note Generator")
st.title("🔍 Generate Your Quick Remediation Note")
st.markdown("Upload your ASSET Student Performance Table PDF to get started.")

uploaded_file = st.file_uploader("📄 Upload PDF Report", type=["pdf"])

if uploaded_file:
    st.success("PDF uploaded successfully!")
    generate = st.button("⚡ Generate my Quick Remediation Note")

    if generate:
        with pdfplumber.open(uploaded_file) as pdf:
            pages = pdf.pages
            text = " ".join(page.extract_text() for page in pages if page.extract_text())

        # Extract Correct Answers and Student Responses
        correct_answers = re.findall(r"Correct Answers.*?(\\b[A-D]\\b.*?)\\n", text)
        table_text = re.findall(r"Student Performance Table.*?\\n(.*?)\\n\\s*% answered correct", text, re.S)

        if not correct_answers or not table_text:
            st.error("Could not extract student performance table or correct answers.")
        else:
            corrects = correct_answers[0].split()
            lines = table_text[0].split("\\n")
            data = []
            for line in lines:
                cols = line.strip().split()
                if len(cols) > 10:
                    data.append(cols[:41])

            df = pd.DataFrame(data, columns=["Name"] + [f"Q{i+1}" for i in range(40)])

            # Compute accuracy and option distribution
            stats = []
            for i in range(1, 41):
                col = f"Q{i}"
                counts = df[col].value_counts(normalize=True)
                total = df[col].notna().sum()
                correct = (df[col] == corrects[i-1]).sum()
                acc = round(100 * correct / total, 1) if total else 0

                dominant_wrong = ""
                for opt in ['A', 'B', 'C', 'D']:
                    pct = round(100 * counts.get(opt, 0), 1)
                    if opt != corrects[i-1] and pct >= 30:
                        dominant_wrong = f"{opt}: {pct}%"
                        break

                buckets = []
                if acc < 30:
                    buckets.append("Difficult")
                    if not dominant_wrong:
                        buckets.append("Critical Learning Gap")
                if dominant_wrong:
                    buckets.append("Misconception")
                if acc > 70:
                    buckets.append("Easy")

                stats.append({
                    "Q": i,
                    "Accuracy%": acc,
                    "DominantWrongOption%": dominant_wrong,
                    "Buckets": " | ".join(buckets)
                })

            summary_df = pd.DataFrame(stats)
            st.subheader("Dashboard Summary")
            st.dataframe(summary_df, use_container_width=True)

            # Generate downloadable markdown report
            def generate_report_md(df):
                lines = ["# Quick Remediation Note\n\n", "## Detailed Table\n"]
                lines.append("| Q | Accuracy% | DominantWrongOption% | Buckets |\n")
                lines.append("|----|------------|----------------------|---------|\n")
                for _, row in df.iterrows():
                    lines.append(f"| {row['Q']} | {row['Accuracy%']} | {row['DominantWrongOption%']} | {row['Buckets']} |\n")
                return "".join(lines)

            report_md = generate_report_md(summary_df)
            b64 = base64.b64encode(report_md.encode()).decode()
            href = f'<a href="data:text/markdown;base64,{b64}" download="Quick_Remediation_Note.md">📥 Download Markdown Report</a>'
            st.markdown(href, unsafe_allow_html=True)
