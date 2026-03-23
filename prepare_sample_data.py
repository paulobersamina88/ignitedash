from pathlib import Path
import pandas as pd

# Input/output files
RAW_FILE = "raw_uploaded_result.csv"
OUTPUT_FILE = "sample_data.csv"

# Expected columns of your dashboard
TARGET_COLUMNS = [
    "Timestamp",
    "Column 1",
    "Full Name (optional)",
    "Position / Designation",
    "College/ Office / Unit",
    "Building or Facility Assigned / Located",
    "Email Address:",
    "1. Proposed Project Title:",
    "2. Location of the Proposed Project",
    "3. Type of Project",
    "Project Description /Rationale",
    'Choose the Main Purpose of your "Project Proposal" by clicking one of the boxes below',
    "Justification (Why is this project needed? what problem or need will it address?)",
    "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)",
    "Urgency Level",
    "1. Type of Project",
    "2. Area for Construction / Renovation / Improvement",
    "3. Mode of Procurement",
    "Do u currently have existing documents related to the project?",
]

# Common alternate header names from Google Form / Google Sheet exports
COLUMN_ALIASES = {
    "Timestamp": [
        "Timestamp",
    ],
    "Column 1": [
        "Column 1",
    ],
    "Full Name (optional)": [
        "Full Name (optional)",
        "Full Name",
        "Name",
    ],
    "Position / Designation": [
        "Position / Designation",
        "Position/Designation",
    ],
    "College/ Office / Unit": [
        "College/ Office / Unit",
        "College / Office / Unit",
        "College/Office/Unit",
    ],
    "Building or Facility Assigned / Located": [
        "Building or Facility Assigned / Located",
        "Building or Facility Assigned/Located",
    ],
    "Email Address:": [
        "Email Address:",
        "Email Address",
    ],
    "1. Proposed Project Title:": [
        "1. Proposed Project Title:",
        "1. Proposed Project Title",
    ],
    "2. Location of the Proposed Project": [
        "2. Location of the Proposed Project",
    ],
    "3. Type of Project": [
        "3. Type of Project",
    ],
    "Project Description /Rationale": [
        "Project Description /Rationale",
        "Project Description / Rationale",
    ],
    'Choose the Main Purpose of your "Project Proposal" by clicking one of the boxes below': [
        'Choose the Main Purpose of your "Project Proposal" by clicking one of the boxes below',
        'Choose the Main Purpose of your Project Proposal by clicking one of the boxes below',
    ],
    "Justification (Why is this project needed? what problem or need will it address?)": [
        "Justification (Why is this project needed? what problem or need will it address?)",
    ],
    "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)": [
        "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)",
    ],
    "Urgency Level": [
        "Urgency Level",
    ],
    "1. Type of Project": [
        "1. Type of Project",
    ],
    "2. Area for Construction / Renovation / Improvement": [
        "2. Area for Construction / Renovation / Improvement",
    ],
    "3. Mode of Procurement": [
        "3. Mode of Procurement",
    ],
    "Do u currently have existing documents related to the project?": [
        "Do u currently have existing documents related to the project?",
        "Do you currently have existing documents related to the project?",
    ],
}

def load_csv_with_fallback(path: str) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_error = e
    raise last_error

def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def find_matching_column(df_columns, aliases):
    normalized = {str(c).strip().lower(): c for c in df_columns}
    for alias in aliases:
        key = alias.strip().lower()
        if key in normalized:
            return normalized[key]
    return None

def transform_to_sample_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    df_raw = clean_headers(df_raw)
    output = pd.DataFrame()

    for target_col in TARGET_COLUMNS:
        match = find_matching_column(df_raw.columns, COLUMN_ALIASES.get(target_col, [target_col]))
        if match:
            output[target_col] = df_raw[match]
        else:
            output[target_col] = ""

    # Remove fully blank rows
    important_cols = [
        "1. Proposed Project Title:",
        "Project Description /Rationale",
        "Justification (Why is this project needed? what problem or need will it address?)",
        "Expected Benefits (Example: improved learning space, safety, increased capacity, etc.)",
        "College/ Office / Unit",
    ]

    output = output.dropna(how="all")
    mask = output[important_cols].fillna("").astype(str).apply(
        lambda row: any(x.strip() for x in row), axis=1
    )
    output = output[mask].copy()

    output.reset_index(drop=True, inplace=True)
    return output

def main():
    if not Path(RAW_FILE).exists():
        raise FileNotFoundError(f"Cannot find {RAW_FILE}")

    df_raw = load_csv_with_fallback(RAW_FILE)
    df_sample = transform_to_sample_data(df_raw)
    df_sample.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Created {OUTPUT_FILE}")
    print(f"Raw rows: {len(df_raw)}")
    print(f"Output rows: {len(df_sample)}")
    print("Columns:")
    for c in df_sample.columns:
        print(f" - {c}")

if __name__ == "__main__":
    main()
