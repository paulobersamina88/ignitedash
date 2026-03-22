
from pathlib import Path
from collections import Counter
import re

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="IMDO Google Form Response Dashboard", layout="wide")

# -------------------------------------------------------
# Config / aliases
# -------------------------------------------------------
FIELD_MAP = {
    "timestamp": "Timestamp",
    "unit": "College/ Office / Unit",
    "building": "Building or Facility Assigned / Located",
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

TEXT_FIELDS = [
    FIELD_MAP["description"],
    FIELD_MAP["justification"],
    FIELD_MAP["benefits"],
]

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "will", "have",
    "has", "had", "into", "their", "there", "than", "then", "them", "they", "its", "it's",
    "our", "your", "you", "but", "not", "all", "can", "may", "due", "per", "also", "any",
    "very", "more", "most", "much", "need", "needs", "needed", "project", "proposal", "proposed",
    "space", "area", "building", "facility", "improve", "improved", "improvement", "renovation",
    "repair", "maintenance", "construction", "new", "office", "college", "unit", "address",
    "provide", "provides", "providing", "support", "through", "during", "because", "about",
    "would", "should", "being", "such", "like", "etc", "within", "year", "years", "one",
    "two", "three", "across", "toward", "towards", "based", "related", "currently", "existing",
    "none", "yet", "n", "a", "an", "of", "to", "in", "on", "at", "by", "is", "it", "as",
    "be", "or", "if", "we", "do", "u", "up", "out", "no", "na", "n/a"
}

CATEGORY_COLORS = None  # keep default plotly palette

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def load_data(uploaded, sample_path: Path) -> pd.DataFrame:
    if uploaded is not None:
        return pd.read_csv(uploaded)
    if sample_path.exists():
        return pd.read_csv(sample_path)
    return pd.DataFrame()

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in FIELD_MAP.values():
        if col not in df.columns:
            df[col] = ""
    return df

def clean_text(val) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()

def split_multi_value(series: pd.Series) -> pd.Series:
    vals = []
    for v in series.fillna("").astype(str):
        parts = [p.strip() for p in re.split(r"[;,/]\s*|\n+", v) if p.strip()]
        if not parts and v.strip():
            parts = [v.strip()]
        vals.extend(parts)
    return pd.Series(vals, dtype="object")

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_columns(df)
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].fillna("").astype(str).str.strip()

    df["Timestamp_dt"] = pd.to_datetime(df[FIELD_MAP["timestamp"]], errors="coerce")
    df["Response Date"] = df["Timestamp_dt"].dt.strftime("%Y-%m-%d")

    # anonymized ID for professional presentation
    df = df.sort_values("Timestamp_dt", kind="stable").reset_index(drop=True)
    df["Response ID"] = [f"PRJ-{i+1:03d}" for i in range(len(df))]
    return df

def pie_chart_from_counts(counts_df: pd.DataFrame, names_col: str, values_col: str, title: str):
    if counts_df.empty:
        st.info("No responses available for this item.")
        return
    fig = px.pie(counts_df, names=names_col, values=values_col, title=title, hole=0.0)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

def bar_chart_from_counts(counts_df: pd.DataFrame, x_col: str, y_col: str, title: str, horizontal: bool = False):
    if counts_df.empty:
        st.info("No responses available for this item.")
        return
    if horizontal:
        fig = px.bar(counts_df, x=y_col, y=x_col, orientation="h", title=title, text=y_col)
    else:
        fig = px.bar(counts_df, x=x_col, y=y_col, title=title, text=y_col)
    st.plotly_chart(fig, use_container_width=True)

def show_question_header(title: str, count: int):
    st.markdown(
        f"""
        <div style="background:#673ab7;color:white;padding:12px 16px;border-radius:12px 12px 0 0;
                    font-size:1.35rem;font-weight:700;margin-top:8px;">
            {title}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"**{count} responses**")

def response_list_block(title: str, series: pd.Series, max_items: int = 12):
    cleaned = [clean_text(x) for x in series if clean_text(x)]
    st.subheader(title)
    if not cleaned:
        st.info("No responses available.")
        return
    for item in cleaned[:max_items]:
        st.markdown(
            f"""
            <div style="background:#f5f5f5;border-radius:8px;padding:12px 14px;margin-bottom:10px;
                        border-left:4px solid #673ab7;">
                {item}
            </div>
            """,
            unsafe_allow_html=True,
        )
    if len(cleaned) > max_items:
        st.caption(f"Showing {max_items} of {len(cleaned)} responses.")

def extract_keywords(series: pd.Series, top_n: int = 12):
    all_text = " ".join([clean_text(x).lower() for x in series if clean_text(x)])
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", all_text)
    tokens = [t for t in tokens if t not in STOPWORDS and not t.isdigit()]
    counts = Counter(tokens)
    data = pd.DataFrame(counts.most_common(top_n), columns=["Keyword", "Count"])
    return data

def theme_summary(series: pd.Series):
    theme_rules = {
        "Safety / Hazard": ["safety", "hazard", "danger", "unsafe", "fire", "leak", "flood", "risk", "security"],
        "Accreditation / Compliance": ["aacup", "copc", "ched", "arta", "rqAT".lower(), "compliance", "levelling", "audit"],
        "Learning / Laboratory Upgrade": ["laboratory", "lab", "classroom", "learning", "instruction", "equipment", "training"],
        "Utilities / Power / Water": ["power", "electrical", "water", "generator", "solar", "lighting", "drainage"],
        "Space / Capacity Need": ["space", "capacity", "extension", "room", "office", "center", "venue"],
        "Rehabilitation / Deterioration": ["rehabilitation", "repair", "renovation", "deterioration", "damaged", "ceiling", "roof"],
    }

    counts = Counter()
    clean_responses = [clean_text(x).lower() for x in series if clean_text(x)]
    for text in clean_responses:
        matched = False
        for theme, keys in theme_rules.items():
            if any(k in text for k in keys):
                counts[theme] += 1
                matched = True
        if not matched:
            counts["Other / Specific Unit Need"] += 1

    df = pd.DataFrame(counts.items(), columns=["Theme", "Count"]).sort_values("Count", ascending=False)
    return df

def categorical_counts(series: pd.Series, split_values: bool = False):
    if split_values:
        s = split_multi_value(series)
    else:
        s = series.fillna("").astype(str).str.strip()
        s = s[s != ""]
    if s.empty:
        return pd.DataFrame(columns=["Response", "Count"])
    out = s.value_counts().reset_index()
    out.columns = ["Response", "Count"]
    return out

def anonymized_table(df: pd.DataFrame):
    wanted = [
        "Response ID",
        FIELD_MAP["project_title"],
        FIELD_MAP["unit"],
        FIELD_MAP["project_location"],
        FIELD_MAP["project_type"],
        FIELD_MAP["urgency"],
        FIELD_MAP["purpose"],
        FIELD_MAP["procurement"],
        FIELD_MAP["docs"],
    ]
    cols = [c for c in wanted if c in df.columns]
    renamed = {
        "Response ID": "Response ID",
        FIELD_MAP["project_title"]: "Project Title",
        FIELD_MAP["unit"]: "Unit / Office",
        FIELD_MAP["project_location"]: "Project Location",
        FIELD_MAP["project_type"]: "Type of Project",
        FIELD_MAP["urgency"]: "Urgency",
        FIELD_MAP["purpose"]: "Purpose / Justification Category",
        FIELD_MAP["procurement"]: "Procurement Mode",
        FIELD_MAP["docs"]: "Existing Documents",
    }
    view = df[cols].rename(columns=renamed)
    st.dataframe(view, use_container_width=True)

# -------------------------------------------------------
# Main UI
# -------------------------------------------------------
st.title("IMDO Google Form Response Dashboard")
st.caption("Google Form-style presentation of project proposal responses with anonymized, professional summaries.")

sample_path = Path(__file__).parent / "sample_data.csv"
with st.sidebar:
    st.header("Data Source")
    use_sample = st.checkbox("Use built-in sample data", value=True)
    uploaded = st.file_uploader("Upload Google Form CSV", type=["csv"])
    st.divider()
    st.header("Filters")
    hide_blank = st.checkbox("Hide blank / empty responses in charts", value=True)

df_raw = None
if uploaded is not None:
    df_raw = pd.read_csv(uploaded)
elif use_sample:
    df_raw = load_data(None, sample_path)

if df_raw is None or df_raw.empty:
    st.warning("Please upload your Google Form CSV or keep the sample data enabled.")
    st.stop()

df = normalize_df(df_raw)

# sidebar filters excluding names
units = sorted([x for x in df[FIELD_MAP["unit"]].dropna().astype(str).unique().tolist() if x.strip()])
types = sorted([x for x in df[FIELD_MAP["project_type"]].dropna().astype(str).unique().tolist() if x.strip()])
urgencies = sorted([x for x in df[FIELD_MAP["urgency"]].dropna().astype(str).unique().tolist() if x.strip()])

with st.sidebar:
    selected_units = st.multiselect("Unit / Office", units, default=units)
    selected_types = st.multiselect("Type of Project", types, default=types)
    selected_urgencies = st.multiselect("Urgency Level", urgencies, default=urgencies)

filtered = df.copy()
if selected_units:
    filtered = filtered[filtered[FIELD_MAP["unit"]].isin(selected_units)]
if selected_types:
    filtered = filtered[filtered[FIELD_MAP["project_type"]].isin(selected_types)]
if selected_urgencies:
    filtered = filtered[filtered[FIELD_MAP["urgency"]].isin(selected_urgencies)]

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Responses", len(filtered))
c2.metric("Unique Units", filtered[FIELD_MAP["unit"]].nunique())
c3.metric("Project Types", filtered[FIELD_MAP["project_type"]].nunique())
c4.metric("Urgency Levels Used", filtered[FIELD_MAP["urgency"]].nunique())

tab1, tab2, tab3, tab4 = st.tabs([
    "Google Form Summary",
    "Text Response Summary",
    "Anonymized Response List",
    "Download"
])

with tab1:
    show_question_header("A. Project Type Summary", len(filtered))

    col1, col2 = st.columns(2)
    with col1:
        counts = categorical_counts(filtered[FIELD_MAP["project_type"]])
        pie_chart_from_counts(counts, "Response", "Count", "3. Type of Project")

    with col2:
        counts = categorical_counts(filtered[FIELD_MAP["urgency"]])
        pie_chart_from_counts(counts, "Response", "Count", "Urgency Level")

    st.divider()
    show_question_header("B. Purpose / Justification Category", len(filtered))
    purpose_counts = categorical_counts(filtered[FIELD_MAP["purpose"]])
    bar_chart_from_counts(purpose_counts, "Response", "Count", 'Choose the Main Purpose of your "Project Proposal"', horizontal=True)

    st.divider()
    show_question_header("C. Procurement Mode", len(filtered))
    procurement_counts = categorical_counts(filtered[FIELD_MAP["procurement"]])
    pie_chart_from_counts(procurement_counts, "Response", "Count", "3. Mode of Procurement")

    st.divider()
    show_question_header("D. Existing Documents", len(filtered))
    docs_counts = categorical_counts(filtered[FIELD_MAP["docs"]], split_values=True)
    bar_chart_from_counts(docs_counts, "Response", "Count", "Existing Documents Mentioned", horizontal=True)

    st.divider()
    show_question_header("E. Unit / Office Distribution", len(filtered))
    unit_counts = categorical_counts(filtered[FIELD_MAP["unit"]])
    bar_chart_from_counts(unit_counts, "Response", "Count", "Responses by Unit / Office", horizontal=True)

with tab2:
    show_question_header("C. Brief Description of the Proposed Project", len(filtered))
    response_list_block("Project Description / Rationale", filtered[FIELD_MAP["description"]], max_items=10)

    st.divider()
    show_question_header("D. Summary of Justification Responses", len(filtered))

    col1, col2 = st.columns(2)
    with col1:
        theme_df = theme_summary(filtered[FIELD_MAP["justification"]])
        bar_chart_from_counts(theme_df, "Theme", "Count", "General Themes from Justification Responses", horizontal=True)

    with col2:
        keywords_df = extract_keywords(filtered[FIELD_MAP["justification"]], top_n=12)
        bar_chart_from_counts(keywords_df, "Keyword", "Count", "Most Frequent Justification Keywords", horizontal=True)

    st.markdown("### Anonymized Justification Responses")
    just_df = filtered[["Response ID", FIELD_MAP["project_title"], FIELD_MAP["justification"]]].copy()
    just_df = just_df.rename(columns={
        FIELD_MAP["project_title"]: "Project Title",
        FIELD_MAP["justification"]: "Justification Response"
    })
    st.dataframe(just_df, use_container_width=True)

    st.divider()
    show_question_header("E. Summary of Expected Benefits Responses", len(filtered))

    col1, col2 = st.columns(2)
    with col1:
        benefit_keywords = extract_keywords(filtered[FIELD_MAP["benefits"]], top_n=12)
        bar_chart_from_counts(benefit_keywords, "Keyword", "Count", "Most Frequent Expected Benefit Keywords", horizontal=True)
    with col2:
        benefit_themes = theme_summary(filtered[FIELD_MAP["benefits"]])
        bar_chart_from_counts(benefit_themes, "Theme", "Count", "General Themes from Expected Benefits", horizontal=True)

    st.markdown("### Anonymized Expected Benefits Responses")
    ben_df = filtered[["Response ID", FIELD_MAP["project_title"], FIELD_MAP["benefits"]]].copy()
    ben_df = ben_df.rename(columns={
        FIELD_MAP["project_title"]: "Project Title",
        FIELD_MAP["benefits"]: "Expected Benefits Response"
    })
    st.dataframe(ben_df, use_container_width=True)

with tab3:
    st.subheader("Anonymized Google Form Response Table")
    st.caption("Names, email addresses, and designations are intentionally excluded for a more professional presentation.")
    anonymized_table(filtered)

    st.subheader("Project Titles and Locations")
    title_view = filtered[["Response ID", FIELD_MAP["project_title"], FIELD_MAP["project_location"], FIELD_MAP["building"]]].rename(columns={
        FIELD_MAP["project_title"]: "Project Title",
        FIELD_MAP["project_location"]: "Project Location",
        FIELD_MAP["building"]: "Building / Facility"
    })
    st.dataframe(title_view, use_container_width=True)

with tab4:
    st.subheader("Export Filtered, Anonymized Data")
    export_cols = [
        "Response ID",
        "Response Date",
        FIELD_MAP["unit"],
        FIELD_MAP["building"],
        FIELD_MAP["project_title"],
        FIELD_MAP["project_location"],
        FIELD_MAP["project_type"],
        FIELD_MAP["description"],
        FIELD_MAP["purpose"],
        FIELD_MAP["justification"],
        FIELD_MAP["benefits"],
        FIELD_MAP["urgency"],
        FIELD_MAP["type_detail"],
        FIELD_MAP["area"],
        FIELD_MAP["procurement"],
        FIELD_MAP["docs"],
    ]
    export_cols = [c for c in export_cols if c in filtered.columns]
    export_df = filtered[export_cols].copy()
    st.dataframe(export_df, use_container_width=True)

    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download anonymized filtered CSV",
        data=csv_bytes,
        file_name="imdo_gform_anonymized_summary.csv",
        mime="text/csv"
    )
