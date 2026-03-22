# IMDO GForm Project Proposal Dashboard

A Streamlit dashboard for reviewing Google Form responses on project proposals.

## Files
- `app.py` - main Streamlit app
- `sample_data.csv` - sample dataset based on the shared responses
- `requirements.txt` - Python dependencies

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features
- KPI cards for total proposals, high-priority items, readiness, and existing documents
- Filters by unit, project location, category, urgency, procurement, and quality
- Charts for proposal distribution and readiness
- Prioritization table using a simple score
- Raw data search and CSV export

## Suggested next upgrades
- Add budget estimation fields
- Add project status tracker after seminar validation
- Add printable one-page summary per proposal
- Connect directly to Google Sheets if needed
