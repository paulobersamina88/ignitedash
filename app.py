from pathlib import Path
import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="IMDO Prioritization Dashboard", layout="wide")

INVALID_TOKENS = {
    "", ".", "n/a", "na", "none", "project title", "ndjd", "jdjd", "ndndn", "jnsnd"
}

COLS = {
    "unit": "College/ Office / Unit",
    "building": "Building or Facility Assigned / Located",
    "email": "Email Address:",
    "title": "1. Proposed Project Title:",
    "location": "2. Location of the Proposed Project",
    "ptype": "3. Type of Project",
    "desc": "Project Description /Rationale",
    "purpose": 'Choose the Main Purpose of your "Project Proposal" by clicking one of the boxes below',
    "just": "Justification (Why is this project needed? what problem or need will it address?)",
    "benefits": "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)",
    "urgency": "Urgency Level",
    "worktype": "1. Type of Project",
    "area": "2. Area for Construction / Renovation / Improvement",
    "procurement": "3. Mode of Procurement",
    "docs": "Do u currently have existing documents related to the project?",
}

DATA_FILES = {
    "Latest sample_data.csv": "sample_data.csv",
    "Latest raw_uploaded_result.csv": "raw_uploaded_result.csv",
}


def load_csv_with_fallback(file_obj_or_path):
    """Read CSV robustly even when the file is saved in ANSI/Windows encoding."""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    last_error = None

    for enc in encodings:
        try:
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_csv(file_obj_or_path, encoding=enc)
        except Exception as e:
            last_error = e

    raise last_error


def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def looks_invalid(text: str) -> bool:
    t = clean_text(text).lower()
    return t in INVALID_TOKENS


def doc_count(text: str) -> int:
    t = clean_text(text)
    if not t or t.lower() in {"none yet", "none", "n/a", "na"}:
        return 0
    return len([p for p in re.split(r"[;,]\s*", t) if p.strip()])


def theme_tags(row) -> str:
    text = " ".join([
        clean_text(row.get(COLS["desc"], "")),
        clean_text(row.get(COLS["just"], "")),
        clean_text(row.get(COLS["benefits"], "")),
    ]).lower()

    tags = []
    if any(k in text for k in ["safety", "hazard", "leak", "falling", "deteriorat", "risk", "roof", "flood"]):
        tags.append("Safety")
    if any(k in text for k in ["aacup", "ched", "copc", "rqat", "arta", "suc levelling", "compliance"]):
        tags.append("Compliance")
    if any(k in text for k in ["laboratory", "lab", "research", "instruction", "students", "learning", "classroom"]):
        tags.append("Academic")
    if any(k in text for k in ["solar", "wind", "generator", "electrical", "power", "energy", "lighting"]):
        tags.append("Utilities")
    if any(k in text for k in ["waiting", "receiving", "releasing", "service"]):
        tags.append("Service")

    return ", ".join(tags) if tags else "General"


def priority_score(row) -> int:
    score = 0
    urgency = clean_text(row[COLS["urgency"]])
    procurement = clean_text(row[COLS["procurement"]])
    docs = doc_count(row[COLS["docs"]])

    if "High Priority" in urgency:
        score += 40
    elif "Medium Priority" in urgency:
        score += 20
    else:
        score += 10

    text = " ".join([
        clean_text(row[COLS["title"]]),
        clean_text(row[COLS["desc"]]),
        clean_text(row[COLS["just"]]),
        clean_text(row[COLS["benefits"]]),
    ]).lower()

    if any(k in text for k in ["falling", "deteriorat", "unsafe", "safety hazard", "leaking", "roof", "risk", "flood"]):
        score += 20
    if any(k in text for k in ["aacup", "ched", "copc", "arta", "rqat", "suc levelling", "compliance"]):
        score += 12
    if any(k in text for k in ["laboratory", "lab", "research", "students", "learning", "engineering", "classroom"]):
        score += 10
    if any(k in text for k in ["solar", "wind", "generator", "energy", "electrical", "power", "lighting"]):
        score += 8

    if "BAC Process" in procurement:
        score += 5
    else:
        score += 2

    score += min(docs, 3) * 3
    return score


def recommendation(score: int) -> str:
    if score >= 72:
        return "Top Priority"
    if score >= 55:
        return "High Priority"
    if score >= 38:
        return "Medium Priority"
    return "For Validation"


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for c in COLS.values():
        if c not in df.columns:
            df[c] = ""

    def is_bad(row):
        core = [
            clean_text(row[COLS["title"]]),
            clean_text(row[COLS["desc"]]),
            clean_text(row[COLS["just"]]),
            clean_text(row[COLS["benefits"]]),
            clean_text(row[COLS["building"]]),
        ]
        invalid_core = sum(looks_invalid(x) for x in core)
        return invalid_core >= 2

    df["Invalid Entry"] = df.apply(is_bad, axis=1)
    df = df[~df["Invalid Entry"]].copy()

    df = df.reset_index(drop=True)
    df["Response ID"] = [f"PRJ-{i+1:03d}" for i in range(len(df))]
    df["Document Count"] = df[COLS["docs"]].apply(doc_count)
    df["Theme Tags"] = df.apply(theme_tags, axis=1)
    df["Priority Score"] = df.apply(priority_score, axis=1)
    df["IMDO Recommendation"] = df["Priority Score"].apply(recommendation)
    df = df.sort_values(["Priority Score", COLS["urgency"]], ascending=[False, True]).reset_index(drop=True)

    return df


def split_counter(series):
    counter = Counter()
    for val in series.fillna("").astype(str):
        for p in re.split(r"[;,]\s*", val):
            p = p.strip()
            if p:
                counter[p] += 1

    if not counter:
        return pd.DataFrame(columns=["Response", "Count"])

    return pd.DataFrame(counter.items(), columns=["Response", "Count"]).sort_values("Count", ascending=False)


def load_default_csv(selected_label: str) -> pd.DataFrame:
    base_path = Path(__file__).parent
    file_path = base_path / DATA_FILES[selected_label]
    if not file_path.exists():
        st.error(f"Default file not found: {file_path.name}")
        st.stop()
    return load_csv_with_fallback(file_path)


st.title("IMDO Prioritization Dashboard")
st.caption("Cleaned and anonymized Google Form results with automatic prioritization.")

st.sidebar.header("Data Source")
default_source = st.sidebar.selectbox(
    "Choose attached CSV",
    list(DATA_FILES.keys()),
    index=0,
)
uploaded = st.sidebar.file_uploader("Or upload updated CSV", type=["csv"])

if uploaded is not None:
    df_raw = load_csv_with_fallback(uploaded)
    source_name = f"Uploaded file: {uploaded.name}"
else:
    df_raw = load_default_csv(default_source)
    source_name = f"Attached file: {DATA_FILES[default_source]}"

df = clean_df(df_raw)

st.sidebar.success(source_name)
st.sidebar.caption(f"Raw rows loaded: {len(df_raw)}")
st.sidebar.caption(f"Valid rows after cleaning: {len(df)}")
st.sidebar.header("Filters")

rec_opts = ["Top Priority", "High Priority", "Medium Priority", "For Validation"]
selected_rec = st.sidebar.multiselect(
    "IMDO Recommendation",
    rec_opts,
    default=rec_opts,
)

unit_options = sorted(df[COLS["unit"]].dropna().astype(str).unique().tolist())
selected_units = st.sidebar.multiselect(
    "Unit / Office",
    unit_options,
    default=unit_options,
)

filtered = df[
    df["IMDO Recommendation"].isin(selected_rec)
    & df[COLS["unit"]].isin(selected_units)
].copy()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Valid Proposals", len(filtered))
c2.metric("Top Priority", int((filtered["IMDO Recommendation"] == "Top Priority").sum()))
c3.metric("High Priority", int((filtered["IMDO Recommendation"] == "High Priority").sum()))
c4.metric("Medium Priority", int((filtered["IMDO Recommendation"] == "Medium Priority").sum()))
c5.metric("Removed Invalid Entries", int(df_raw.shape[0] - df.shape[0]))

tab1, tab2, tab3, tab4 = st.tabs([
    "Prioritization",
    "Google Form Summary",
    "Anonymized Responses",
    "Download",
])

with tab1:
    st.subheader("Ranked Project List")
    show_cols = [
        "Response ID",
        COLS["title"],
        COLS["unit"],
        COLS["location"],
        COLS["ptype"],
        COLS["urgency"],
        COLS["procurement"],
        "Document Count",
        "Theme Tags",
        "Priority Score",
        "IMDO Recommendation",
    ]

    view = filtered[show_cols].rename(columns={
        COLS["title"]: "Project Title",
        COLS["unit"]: "Unit / Office",
        COLS["location"]: "Location",
        COLS["ptype"]: "Project Type",
        COLS["urgency"]: "Urgency",
        COLS["procurement"]: "Procurement Mode",
    })
    st.dataframe(view, use_container_width=True)

    rec_counts = filtered["IMDO Recommendation"].value_counts().reset_index()
    rec_counts.columns = ["Recommendation", "Count"]

    if not rec_counts.empty:
        fig = px.bar(
            rec_counts,
            x="Recommendation",
            y="Count",
            text="Count",
            title="IMDO Recommendation Summary",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)

    with col1:
        counts = filtered[COLS["ptype"]].value_counts().reset_index()
        counts.columns = ["Response", "Count"]
        if not counts.empty:
            fig = px.pie(counts, names="Response", values="Count", title="3. Type of Project")
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        counts = filtered[COLS["urgency"]].value_counts().reset_index()
        counts.columns = ["Response", "Count"]
        if not counts.empty:
            fig = px.pie(counts, names="Response", values="Count", title="Urgency Level")
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    purpose_counts = split_counter(filtered[COLS["purpose"]])
    if not purpose_counts.empty:
        fig = px.bar(
            purpose_counts,
            x="Count",
            y="Response",
            orientation="h",
            title='Purpose / Justification Categories',
            text="Count",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Anonymized Proposal Details")
    detail_cols = [
        "Response ID",
        COLS["title"],
        COLS["desc"],
        COLS["just"],
        COLS["benefits"],
        "Theme Tags",
        "IMDO Recommendation",
    ]

    detail = filtered[detail_cols].rename(columns={
        COLS["title"]: "Project Title",
        COLS["desc"]: "Description / Rationale",
        COLS["just"]: "Justification",
        COLS["benefits"]: "Expected Benefits",
    })
    st.dataframe(detail, use_container_width=True)

with tab4:
    st.subheader("Export Cleaned Results")
    export_df = filtered.drop(columns=[COLS["email"], "Invalid Entry"], errors="ignore")
    st.dataframe(export_df, use_container_width=True)

    st.download_button(
        "Download cleaned prioritized CSV",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="imdo_cleaned_prioritized_results.csv",
        mime="text/csv",
    )
