
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="IMDO GForm Project Proposal Dashboard", layout="wide")

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
INVALID_TOKENS = {
    "", ".", "n/a", "na", "none", "nil", "ndjd", "jdjd", "jnsnd",
    "ndndn", "trial", "project title"
}

COLUMN_ALIASES = {
    "timestamp": "Timestamp",
    "full_name": "Full Name (optional)",
    "position": "Position / Designation",
    "unit": "College/ Office / Unit",
    "building": "Building or Facility Assigned / Located",
    "email": "Email Address:",
    "project_title": "1. Proposed Project Title:",
    "project_location": "2. Location of the Proposed Project",
    "project_type": "3. Type of Project",
    "description": "Project Description /Rationale",
    "purpose": 'Choose the Main Purpose of your "Project Proposal" by clicking one of the boxes below',
    "justification": "Justification (Why is this project needed? what problem or need will it address?)",
    "benefits": "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)",
    "urgency": "Urgency Level",
    "type_detail": "1. Type of Project",
    "area": "2. Area for Construction / Renovation / Improvement",
    "procurement": "3. Mode of Procurement",
    "docs": "Do u currently have existing documents related to the project?",
}

DISPLAY_NAMES = {
    "Timestamp": "Timestamp",
    "Full Name (optional)": "Proponent",
    "Position / Designation": "Position",
    "College/ Office / Unit": "Unit",
    "Building or Facility Assigned / Located": "Assigned Building",
    "Email Address:": "Email",
    "1. Proposed Project Title:": "Project Title",
    "2. Location of the Proposed Project": "Project Location",
    "3. Type of Project": "Project Category",
    "Project Description /Rationale": "Description / Rationale",
    'Choose the Main Purpose of your "Project Proposal" by clicking one of the boxes below': "Main Purpose",
    "Justification (Why is this project needed? what problem or need will it address?)": "Justification",
    "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)": "Expected Benefits",
    "Urgency Level": "Urgency",
    "1. Type of Project": "Work Type",
    "2. Area for Construction / Renovation / Improvement": "Area / Quantity",
    "3. Mode of Procurement": "Procurement Mode",
    "Do u currently have existing documents related to the project?": "Existing Documents",
}

PRIORITY_ORDER = [
    "High Priority (within 1 year)",
    "Medium Priority (1-3 years)",
    "Low Priority (3+ years)"
]

def normalize_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def is_invalid(val: str) -> bool:
    v = normalize_text(val).lower()
    return v in INVALID_TOKENS

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # trim column names
    df.columns = [str(c).strip() for c in df.columns]

    # keep only known columns where possible
    for _, col in COLUMN_ALIASES.items():
        if col not in df.columns:
            df[col] = ""

    # normalize text columns
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).fillna("").str.strip()

    # timestamp
    if "Timestamp" in df.columns:
        df["Timestamp_dt"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df["Date Submitted"] = df["Timestamp_dt"].dt.date.astype("string")
    else:
        df["Timestamp_dt"] = pd.NaT
        df["Date Submitted"] = ""

    # consolidated project title
    df["Project Title Clean"] = df["1. Proposed Project Title:"].where(
        ~df["1. Proposed Project Title:"].apply(is_invalid),
        "Untitled Proposal"
    )

    # data quality scoring
    required_fields = [
        "1. Proposed Project Title:",
        "College/ Office / Unit",
        "2. Location of the Proposed Project",
        "3. Type of Project",
        "Project Description /Rationale",
        "Urgency Level",
    ]

    def missing_count(row):
        count = 0
        for c in required_fields:
            if is_invalid(row.get(c, "")):
                count += 1
        return count

    def quality_flag(row):
        mc = missing_count(row)
        title = normalize_text(row.get("1. Proposed Project Title:", "")).lower()
        desc = normalize_text(row.get("Project Description /Rationale", "")).lower()
        if mc >= 3 or title in INVALID_TOKENS or desc in INVALID_TOKENS:
            return "Needs Review"
        if mc >= 1:
            return "Partially Complete"
        return "Ready"

    df["Missing Required Fields"] = df.apply(missing_count, axis=1)
    df["Submission Quality"] = df.apply(quality_flag, axis=1)

    # document count
    def count_docs(x):
        x = normalize_text(x)
        if not x or is_invalid(x) or x.lower() == "none yet":
            return 0
        return len([p for p in x.split(",") if p.strip()])

    df["Existing Document Count"] = df["Do u currently have existing documents related to the project?"].apply(count_docs)

    # simple score for initial prioritization
    urgency_score_map = {
        "High Priority (within 1 year)": 3,
        "Medium Priority (1-3 years)": 2,
        "Low Priority (3+ years)": 1,
    }
    doc_bonus = df["Existing Document Count"].clip(upper=3)
    quality_bonus = df["Submission Quality"].map({"Ready": 2, "Partially Complete": 1, "Needs Review": 0}).fillna(0)
    df["Priority Score"] = (
        df["Urgency Level"].map(urgency_score_map).fillna(0) * 4
        + quality_bonus
        + doc_bonus
    )

    # label rows that look like tests/placeholders
    def suspicious(row):
        suspicious_words = {"trial", "ndjd", "jdjd", "ndndn", ".", "none"}
        fields = [
            normalize_text(row.get("1. Proposed Project Title:", "")).lower(),
            normalize_text(row.get("Project Description /Rationale", "")).lower(),
            normalize_text(row.get("College/ Office / Unit", "")).lower(),
        ]
        return any(f in suspicious_words for f in fields)

    df["Possible Test Entry"] = df.apply(suspicious, axis=1)

    # nicer names for view
    df_view = df.rename(columns=DISPLAY_NAMES)
    return df_view

def metric_card(label, value):
    st.metric(label, value)

def safe_multiselect(label, series):
    opts = sorted([x for x in series.dropna().astype(str).unique().tolist() if x.strip()])
    return st.multiselect(label, opts)

# -------------------------------------------------------
# UI
# -------------------------------------------------------
st.title("IMDO Project Proposal Dashboard")
st.caption("For Google Form responses on proposed infrastructure, renovation, repair, and facility projects.")

with st.expander("How to use this dashboard", expanded=False):
    st.markdown(
        """
        1. Upload the CSV export from your Google Form responses, or use the built-in sample file.  
        2. Filter by unit, location, project type, urgency, procurement mode, and submission quality.  
        3. Review the priority table, document readiness, and entries that may need validation.  
        """
    )

sample_path = Path(__file__).parent / "sample_data.csv"

left, right = st.columns([1, 1])
with left:
    use_sample = st.checkbox("Use built-in sample data", value=True)
with right:
    uploaded = st.file_uploader("Upload Google Form CSV", type=["csv"])

df_raw = None
if uploaded is not None:
    df_raw = pd.read_csv(uploaded)
elif use_sample and sample_path.exists():
    df_raw = pd.read_csv(sample_path)

if df_raw is None:
    st.warning("Please upload a CSV file or enable the sample data.")
    st.stop()

df = clean_dataframe(df_raw)

# -------------------------------------------------------
# Filters
# -------------------------------------------------------
st.sidebar.header("Filters")

units = safe_multiselect("Unit / College / Office", df["Unit"] if "Unit" in df.columns else pd.Series(dtype=str))
locations = safe_multiselect("Project Location", df["Project Location"] if "Project Location" in df.columns else pd.Series(dtype=str))
categories = safe_multiselect("Project Category", df["Project Category"] if "Project Category" in df.columns else pd.Series(dtype=str))
urgency = st.sidebar.multiselect("Urgency", PRIORITY_ORDER, default=PRIORITY_ORDER)
procurement = safe_multiselect("Procurement Mode", df["Procurement Mode"] if "Procurement Mode" in df.columns else pd.Series(dtype=str))
quality = st.sidebar.multiselect(
    "Submission Quality",
    ["Ready", "Partially Complete", "Needs Review"],
    default=["Ready", "Partially Complete", "Needs Review"]
)
hide_tests = st.sidebar.checkbox("Hide possible test / placeholder entries", value=True)

filtered = df.copy()
if units:
    filtered = filtered[filtered["Unit"].isin(units)]
if locations:
    filtered = filtered[filtered["Project Location"].isin(locations)]
if categories:
    filtered = filtered[filtered["Project Category"].isin(categories)]
if urgency:
    filtered = filtered[filtered["Urgency"].isin(urgency)]
if procurement:
    filtered = filtered[filtered["Procurement Mode"].isin(procurement)]
if quality:
    filtered = filtered[filtered["Submission Quality"].isin(quality)]
if hide_tests and "Possible Test Entry" in filtered.columns:
    filtered = filtered[~filtered["Possible Test Entry"]]

# -------------------------------------------------------
# KPIs
# -------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    metric_card("Total Proposals", int(len(filtered)))
with c2:
    metric_card("High Priority", int((filtered["Urgency"] == "High Priority (within 1 year)").sum()))
with c3:
    metric_card("Ready Submissions", int((filtered["Submission Quality"] == "Ready").sum()))
with c4:
    metric_card("Needs Review", int((filtered["Submission Quality"] == "Needs Review").sum()))
with c5:
    metric_card("With Existing Docs", int((filtered["Existing Document Count"] > 0).sum()))

# -------------------------------------------------------
# Charts
# -------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Prioritization", "Document Readiness", "Raw Data"])

with tab1:
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        by_unit = filtered["Unit"].value_counts().reset_index()
        by_unit.columns = ["Unit", "Count"]
        if not by_unit.empty:
            fig = px.bar(by_unit, x="Unit", y="Count", title="Projects by Unit / College / Office")
            st.plotly_chart(fig, use_container_width=True)

    with row1_col2:
        by_urg = filtered["Urgency"].value_counts().reindex(PRIORITY_ORDER, fill_value=0).reset_index()
        by_urg.columns = ["Urgency", "Count"]
        if not by_urg.empty:
            fig = px.pie(by_urg, names="Urgency", values="Count", title="Urgency Distribution")
            st.plotly_chart(fig, use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        by_cat = filtered["Project Category"].value_counts().reset_index()
        by_cat.columns = ["Project Category", "Count"]
        if not by_cat.empty:
            fig = px.bar(by_cat, x="Project Category", y="Count", title="Projects by Category")
            st.plotly_chart(fig, use_container_width=True)

    with row2_col2:
        by_proc = filtered["Procurement Mode"].value_counts().reset_index()
        by_proc.columns = ["Procurement Mode", "Count"]
        if not by_proc.empty:
            fig = px.bar(by_proc, x="Procurement Mode", y="Count", title="Procurement Mode Distribution")
            fig.update_layout(xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Quick Proposal Summary")
    summary_cols = [
        "Timestamp", "Proponent", "Position", "Unit", "Project Title", "Project Location",
        "Project Category", "Urgency", "Submission Quality", "Existing Document Count"
    ]
    existing = [c for c in summary_cols if c in filtered.columns]
    st.dataframe(filtered[existing].sort_values(by="Timestamp", ascending=False), use_container_width=True)

with tab2:
    st.subheader("Initial Prioritization Matrix")
    st.caption("Simple score based on urgency, submission quality, and presence of existing documents.")

    pr_cols = ["Project Title", "Unit", "Project Location", "Urgency", "Submission Quality", "Existing Documents", "Priority Score"]
    if "Existing Documents" not in filtered.columns and "Do u currently have existing documents related to the project?" in filtered.columns:
        filtered["Existing Documents"] = filtered["Do u currently have existing documents related to the project?"]

    pr_existing = [c for c in pr_cols if c in filtered.columns]
    pr_table = filtered[pr_existing].sort_values(by="Priority Score", ascending=False)
    st.dataframe(pr_table, use_container_width=True)

    scatter_df = filtered.copy()
    urgency_num = scatter_df["Urgency"].map({
        "High Priority (within 1 year)": 3,
        "Medium Priority (1-3 years)": 2,
        "Low Priority (3+ years)": 1,
    }).fillna(0)
    quality_num = scatter_df["Submission Quality"].map({"Ready": 3, "Partially Complete": 2, "Needs Review": 1}).fillna(0)

    scatter_df["Urgency Score"] = urgency_num
    scatter_df["Readiness Score"] = quality_num

    if not scatter_df.empty:
        fig = px.scatter(
            scatter_df,
            x="Readiness Score",
            y="Urgency Score",
            size="Priority Score",
            color="Unit",
            hover_name="Project Title",
            hover_data=["Project Location", "Procurement Mode"],
            title="Urgency vs Submission Readiness"
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Existing Document Readiness")

    docs = filtered.groupby("Unit", dropna=False).agg(
        proposals=("Project Title", "count"),
        avg_docs=("Existing Document Count", "mean"),
        ready=("Submission Quality", lambda s: (s == "Ready").sum()),
        needs_review=("Submission Quality", lambda s: (s == "Needs Review").sum()),
    ).reset_index()

    if not docs.empty:
        fig = px.bar(
            docs,
            x="Unit",
            y=["ready", "needs_review"],
            barmode="group",
            title="Ready vs Needs Review by Unit"
        )
        st.plotly_chart(fig, use_container_width=True)

    review_cols = [
        "Project Title", "Unit", "Proponent", "Urgency", "Submission Quality",
        "Missing Required Fields", "Existing Documents", "Justification", "Expected Benefits"
    ]
    if "Existing Documents" not in filtered.columns and "Do u currently have existing documents related to the project?" in filtered.columns:
        filtered["Existing Documents"] = filtered["Do u currently have existing documents related to the project?"]

    review_existing = [c for c in review_cols if c in filtered.columns]
    st.dataframe(
        filtered[review_existing].sort_values(
            by=["Submission Quality", "Missing Required Fields", "Urgency"],
            ascending=[True, False, True]
        ),
        use_container_width=True
    )

with tab4:
    st.subheader("Raw / Detailed Data")

    keyword = st.text_input("Search keyword in title / description / justification")
    raw = filtered.copy()

    if keyword:
        k = keyword.lower()
        mask = (
            raw["Project Title"].astype(str).str.lower().str.contains(k, na=False) |
            raw["Description / Rationale"].astype(str).str.lower().str.contains(k, na=False) |
            raw["Justification"].astype(str).str.lower().str.contains(k, na=False)
        )
        raw = raw[mask]

    st.dataframe(raw, use_container_width=True)

    csv_bytes = raw.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered data as CSV",
        data=csv_bytes,
        file_name="imdo_filtered_projects.csv",
        mime="text/csv"
    )
