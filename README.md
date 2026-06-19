# MDM Device Intelligence Dashboard

A Streamlit dashboard for analysing MDM CSV exports.

## Features

- CSV upload from the browser
- KPI summary cards
- Device inventory by model and group
- OS version lifecycle tracking
- Application version drift analysis
- Duplicate serial number and device name checks
- Searchable full inventory
- Excel export of filtered results

## Files

Upload these files to GitHub:

- `app.py`
- `requirements.txt`
- `README.md`

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload the files in this project.
3. Go to Streamlit Community Cloud.
4. Create a new app from the GitHub repository.
5. Set the main file path to:

```text
app.py
```

6. Deploy the app.
7. Upload your MDM CSV report from the dashboard.
