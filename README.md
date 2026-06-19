# MDM Client Report Dashboard

This Streamlit app reads all MDM CSV exports stored in the GitHub repository under:

```text
reports/
```

No browser upload is required. Add new CSV reports to the `reports` folder, commit them, and redeploy or restart the Streamlit app.

## Client grouping logic

The dashboard groups reports into:

- Ticketmaster and LiveNation
- Ticketmaster Clubs
- Ticketmaster Sport

### Ticketmaster and LiveNation

This group is further split into:

- Academy Music Group (AMG)
- ASM Global (Sheffield/Derby)
- Independent
- LiveNation Entertainment (LNE)
- North Yorkshire Council (NYC)

For this group, the dashboard focuses on the `TM1 Entry` app version.

### Ticketmaster Clubs

This group is further split into:

- Dual Universe & Ticketweb Checkin Venues
- TicketWeb Check-In Venues
- Universe Venues

The app `BoxOffice` is displayed as `Universe`.

### Ticketmaster Sport

No further subgrouping is applied.

## Repository structure

```text
your-repo/
├── app.py
├── requirements.txt
├── README.md
└── reports/
    ├── UKClientDevices_UnitedKingdom_20260618161808.csv
    └── another_report.csv
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this project to GitHub.
2. Add your CSV reports to the `reports/` folder.
3. In Streamlit Community Cloud, create a new app from the repository.
4. Set the main file path to:

```text
app.py
```

5. Deploy.
