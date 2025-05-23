import streamlit as st
import pandas as pd
import pdfplumber
import re
import base64

st.set_page_config(page_title="Quick Remediation Note Generator")
st.title("🔍 Generate Your Quick Remediation Note")
st.markdown("Upload your ASSET Student Performance Table PDF to get started.")

uploaded_file = st.file_uploader("📄 Upload PDF Report", type=["pdf"])

if uploaded_file:
    st.success("PDF uploaded successfully!")
    generate = st.button("⚡ Generate my Quick Remediation Note")

    if generate:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

        # Updated: Flexible pattern to match correct answers
        correct_line = re.findall(r"Correct\s*Answers.*?([A-D](?:\s+[A-D]){39})", full_text, re.IGNORECASE)
        if not correct_line:
            st.error("Correct answers row not found in PDF.")
            st.stop()

        correct_answers = correct_line[0].strip().split()
        if len(correct_answers) != 40:
            st.error("Could not find 40 correct answers.")
            st.stop()

        # Extract student response lines
        student_rows = re.findall(r"\d{1,2}\s+([A-Za-z\s.]+?)\s+([A-D✓\*\s]{40,})", full_text)
        if not student_rows:
            st.error("Could not extract student responses from the table.")
            st.stop()

        data = []
        for name, response_line in student_rows:
            raw = response_line.strip().split()
            row = []
            i = 0
            while len(row) < 40 and i < len(raw):
                val = raw[i]
                if val == "✓":
                    row.append(correct_answers[len(row)])
                elif val in ["A", "B", "C", "D"]:
                    row.append(val)
                else:
                    row.append("")
                i += 1
            data.append([name.strip()] + row)

        df = pd.DataFrame(data, columns=["Name"] + [f"Q{i+1}" for i in range(40)])

        stats = []
        for i in range(1, 41):
            col = f"Q{i}"
            correct = correct_answers[i-1]
            responses = df[col]
            attempted = responses[responses != ""]
            total = len(attempted)
            correct_count = (attempted == correct).sum()
            acc = round(100 * correct_count / total, 1) if total else 0

            wrong_counts = attempted[attempted != correct].value_counts(normalize=True) * 100
            dominant_wrong = ""
            for opt, pct in wrong_counts.items():
                if pct >= 30:
                    dominant_wrong = f"{opt}: {round(pct,1)}%"
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
