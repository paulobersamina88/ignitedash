# IMDO Prioritization Dashboard

This package contains:
- `app.py` - Streamlit dashboard with automatic cleaning, anonymization, and prioritization
- `sample_data.csv` - cleaned dataset based on the latest uploaded Google Form results
- `raw_uploaded_result.csv` - direct encoded version of the uploaded result for reference
- `requirements.txt`

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## What changed
- removes garbage/test entries automatically
- hides names/emails in the dashboard
- adds IMDO priority scoring and recommendation tags
- keeps Google Form style summary charts
