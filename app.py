import streamlit as st
import pandas as pd
import pdfplumber
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
            st.info("Extracting tables from the PDF...")
            tables = []
            for page in pdf.pages:
                tables += page.extract_tables()

        if not tables:
            st.error("No tables found in the PDF.")
            st.stop()

        # Try to find the Student Performance Table (with 40+ Q columns)
        target_table = None
        for table in tables:
            if any("Correct Answers" in str(cell) for cell in table[0]) and len(table[0]) >= 41:
                target_table = table
                break

        if not target_table:
            st.error("Could not locate the student performance table in this PDF.")
            st.stop()

        # Parse table
        header = target_table[0]
        correct_answers = header[1:41]
        data = target_table[1:]

        df = pd.DataFrame(data, columns=["Name"] + [f"Q{i+1}" for i in range(40)] + ["Score", "Scaled Score", "Percentile", "Performance"])
        df = df.fillna("")

        # Compute question-wise stats
        stats = []
        for i in range(1, 41):
            col = f"Q{i}"
            correct = correct_answers[i-1]
            responses = df[col]
            attempts = responses[responses != ""]
            total = len(attempts)
            correct_count = (attempts == correct).sum()
            acc = round(100 * correct_count / total, 1) if total > 0 else 0

            wrong_counts = attempts[attempts != correct].value_counts(normalize=True) * 100
            dominant_wrong = ""
            for opt, pct in wrong_counts.items():
                if pct >= 30:
                    dominant_wrong = f"{opt}: {round(pct, 1)}%"
                    break

            spread = all(pct <= 30 for pct in wrong_counts.values())
            buckets = []
            if acc < 30:
                buckets.append("Difficult")
                if spread and dominant_wrong == "":
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

        # Markdown report download
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
