from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="MDM Client Report Dashboard",
    page_icon="📱",
    layout="wide",
)


REPORTS_DIR = Path("reports")

REQUIRED_COLUMNS = {
    "Device Name",
    "Serial Number",
    "Model",
    "OS Version",
    "Group Path",
    "Application Name",
    "Application Version",
}

MAIN_GROUPS = [
    "Ticketmaster and LiveNation",
    "Ticketmaster Clubs",
    "Ticketmaster Sport",
]

TMLN_GOVERNING_BODIES = [
    "Academy Music Group (AMG)",
    "ASM Global (Sheffield/Derby)",
    "Independent",
    "LiveNation Entertainment (LNE)",
    "North Yorkshire Council (NYC)",
]

CLUBS_SUBGROUPS = [
    "Dual Universe & Ticketweb Checkin Venues",
    "TicketWeb Check-In Venues",
    "Universe Venues",
]


def normalise_text(value: object) -> str:
    return str(value or "").strip()


def classify_main_group(group_path: object, source_file: object = "") -> str:
    text = f"{normalise_text(group_path)} {normalise_text(source_file)}".lower()

    if "sport" in text:
        return "Ticketmaster Sport"

    if (
        "club" in text
        or "universe" in text
        or "ticketweb" in text
        or "ticket web" in text
        or "check-in" in text
        or "checkin" in text
    ):
        return "Ticketmaster Clubs"

    return "Ticketmaster and LiveNation"


def classify_tmln_governing_body(group_path: object, source_file: object = "") -> str:
    text = f"{normalise_text(group_path)} {normalise_text(source_file)}".lower()

    mappings = {
        "Academy Music Group (AMG)": ["academy music", "amg"],
        "ASM Global (Sheffield/Derby)": ["asm global", "sheffield", "derby"],
        "Independent": ["independent"],
        "LiveNation Entertainment (LNE)": ["livenation", "live nation", "lne"],
        "North Yorkshire Council (NYC)": ["north yorkshire", "nyc"],
    }

    for label, keywords in mappings.items():
        if any(keyword in text for keyword in keywords):
            return label

    return "Unmapped"


def classify_clubs_subgroup(group_path: object, source_file: object = "") -> str:
    text = f"{normalise_text(group_path)} {normalise_text(source_file)}".lower()

    has_universe = "universe" in text or "boxoffice" in text or "box office" in text
    has_ticketweb = "ticketweb" in text or "ticket web" in text or "check-in" in text or "checkin" in text

    if has_universe and has_ticketweb:
        return "Dual Universe & Ticketweb Checkin Venues"
    if has_ticketweb:
        return "TicketWeb Check-In Venues"
    if has_universe:
        return "Universe Venues"

    return "Unmapped"


def normalise_app_name(app_name: object) -> str:
    value = normalise_text(app_name)
    if value.lower() == "boxoffice":
        return "Universe"
    return value


@st.cache_data(show_spinner=False)
def load_report_file(path: str) -> pd.DataFrame:
    file_path = Path(path)
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    if "Device Name" in df.columns:
        df = df[~df["Device Name"].astype(str).str.startswith("---", na=False)]

    df = df.replace({"nan": "", "None": "", "NaN": ""})
    df["Source File"] = file_path.name

    if "Group Path" not in df.columns:
        df["Group Path"] = ""

    if "Application Name" in df.columns:
        df["Application Display Name"] = df["Application Name"].map(normalise_app_name)
    else:
        df["Application Display Name"] = ""

    df["Main Group"] = df.apply(
        lambda row: classify_main_group(row.get("Group Path", ""), row.get("Source File", "")),
        axis=1,
    )

    df["Client Subgroup"] = ""
    df.loc[df["Main Group"] == "Ticketmaster and LiveNation", "Client Subgroup"] = df[
        df["Main Group"] == "Ticketmaster and LiveNation"
    ].apply(
        lambda row: classify_tmln_governing_body(row.get("Group Path", ""), row.get("Source File", "")),
        axis=1,
    )

    df.loc[df["Main Group"] == "Ticketmaster Clubs", "Client Subgroup"] = df[
        df["Main Group"] == "Ticketmaster Clubs"
    ].apply(
        lambda row: classify_clubs_subgroup(row.get("Group Path", ""), row.get("Source File", "")),
        axis=1,
    )

    df.loc[df["Main Group"] == "Ticketmaster Sport", "Client Subgroup"] = "Ticketmaster Sport"

    return df


@st.cache_data(show_spinner=False)
def load_reports_from_folder() -> pd.DataFrame:
    files = sorted(REPORTS_DIR.glob("*.csv"))

    if not files:
        return pd.DataFrame()

    frames = [load_report_file(str(file)) for file in files]
    return pd.concat(frames, ignore_index=True)


def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    with st.sidebar:
        st.header("Filters")

        source_files = st.multiselect("Report file", sorted(df["Source File"].dropna().unique()))
        main_groups = st.multiselect("Main group", MAIN_GROUPS)
        subgroups = st.multiselect("Client subgroup", sorted(df["Client Subgroup"].dropna().unique()))

        def add_filter(label: str, column: str):
            if column not in df.columns:
                return []
            values = sorted([v for v in df[column].dropna().unique() if str(v).strip()])
            return st.multiselect(label, values)

        models = add_filter("Model", "Model")
        os_versions = add_filter("OS Version", "OS Version")
        apps = add_filter("Application", "Application Display Name")
        app_versions = add_filter("Application Version", "Application Version")

    filter_map = {
        "Source File": source_files,
        "Main Group": main_groups,
        "Client Subgroup": subgroups,
        "Model": models,
        "OS Version": os_versions,
        "Application Display Name": apps,
        "Application Version": app_versions,
    }

    for column, selected in filter_map.items():
        if selected and column in filtered.columns:
            filtered = filtered[filtered[column].isin(selected)]

    return filtered


def unique_devices(df: pd.DataFrame) -> pd.DataFrame:
    subset_cols = [
        c
        for c in [
            "Main Group",
            "Client Subgroup",
            "Device Name",
            "Serial Number",
            "Model",
            "OS Version",
            "Group Path",
            "SSID",
            "Source File",
        ]
        if c in df.columns
    ]
    if not subset_cols:
        return df.drop_duplicates()
    return df[subset_cols].drop_duplicates()


def to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, table in tables.items():
            table.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()


def version_sort_value(value: str):
    parts = []
    for part in str(value).replace("-", ".").split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)
    return parts


st.title("📱 MDM Client Report Dashboard")
st.caption("Reads all CSV reports committed to the GitHub `reports/` folder.")

df = load_reports_from_folder()

if df.empty:
    st.warning("No CSV reports found. Add one or more MDM CSV exports to a `reports/` folder in the GitHub repository.")
    st.code(
        """your-repo/
├── app.py
├── requirements.txt
├── README.md
└── reports/
    ├── UKClientDevices_UnitedKingdom_20260618161808.csv
    └── another_client_report.csv""",
        language="text",
    )
    st.stop()

missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
if missing_columns:
    st.warning(f"Missing expected columns: {', '.join(missing_columns)}. Available views will still load where possible.")

filtered = filter_df(df)
devices = unique_devices(filtered)

device_col = "Device Name" if "Device Name" in filtered.columns else None
serial_col = "Serial Number" if "Serial Number" in filtered.columns else None

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Reports", df["Source File"].nunique())
kpi2.metric("Rows", f"{len(filtered):,}")
kpi3.metric("Unique Devices", f"{devices.shape[0]:,}")
kpi4.metric("Main Groups", filtered["Main Group"].nunique())
kpi5.metric("Subgroups", filtered["Client Subgroup"].nunique())
kpi6.metric("Applications", filtered["Application Display Name"].nunique())

tabs = st.tabs([
    "Client Summary",
    "TM1 Entry",
    "Clubs Apps",
    "OS Lifecycle",
    "Duplicates",
    "Device Detail",
    "Export",
])

with tabs[0]:
    st.subheader("Client Group Summary")

    if device_col:
        main_summary = (
            devices.groupby("Main Group")[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values("Devices", ascending=False)
        )
        st.write("Devices by main group")
        st.bar_chart(main_summary.set_index("Main Group")["Devices"])
        st.dataframe(main_summary, use_container_width=True, hide_index=True)

        subgroup_summary = (
            devices.groupby(["Main Group", "Client Subgroup"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values(["Main Group", "Devices"], ascending=[True, False])
        )
        st.write("Devices by subgroup")
        st.dataframe(subgroup_summary, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Ticketmaster and LiveNation — TM1 Entry Versions")

    tmln = filtered[
        (filtered["Main Group"] == "Ticketmaster and LiveNation")
        & (filtered["Application Display Name"].str.lower() == "tm1 entry")
    ]

    if tmln.empty:
        st.info("No TM1 Entry rows found for Ticketmaster and LiveNation.")
    else:
        tm1_summary = (
            tmln.groupby(["Client Subgroup", "Application Version"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values(["Client Subgroup", "Devices"], ascending=[True, False])
        )
        st.dataframe(tm1_summary, use_container_width=True, hide_index=True)

        selected_subgroup = st.selectbox(
            "Inspect governing body",
            sorted(tmln["Client Subgroup"].dropna().unique()),
        )
        chart_data = tm1_summary[tm1_summary["Client Subgroup"] == selected_subgroup]
        st.bar_chart(chart_data.set_index("Application Version")["Devices"])

with tabs[2]:
    st.subheader("Ticketmaster Clubs — Universe and TicketWeb Check-In")

    clubs = filtered[filtered["Main Group"] == "Ticketmaster Clubs"]

    if clubs.empty:
        st.info("No Ticketmaster Clubs rows found.")
    else:
        club_summary = (
            clubs.groupby(["Client Subgroup", "Application Display Name", "Application Version"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values(["Client Subgroup", "Application Display Name", "Devices"], ascending=[True, True, False])
        )

        st.caption("Note: BoxOffice is displayed as Universe.")
        st.dataframe(club_summary, use_container_width=True, hide_index=True)

        selected_club_subgroup = st.selectbox(
            "Inspect club subgroup",
            sorted(clubs["Client Subgroup"].dropna().unique()),
        )
        subgroup_apps = club_summary[club_summary["Client Subgroup"] == selected_club_subgroup]
        st.bar_chart(subgroup_apps.set_index("Application Display Name")["Devices"])

with tabs[3]:
    st.subheader("OS Version Tracking")

    if "OS Version" in devices.columns and device_col:
        os_counts = (
            devices.groupby(["Main Group", "OS Version"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values("OS Version", key=lambda s: s.map(version_sort_value), ascending=False)
        )
        st.dataframe(os_counts, use_container_width=True, hide_index=True)

        overall_os = (
            devices.groupby("OS Version")[device_col]
            .nunique()
            .sort_values(ascending=False)
        )
        st.bar_chart(overall_os)
    else:
        st.info("OS Version and Device Name columns are required for this view.")

with tabs[4]:
    st.subheader("Duplicate Device Checks")

    if serial_col:
        serial_dupes = (
            devices.groupby(serial_col)
            .size()
            .reset_index(name="Device Records")
            .query("`Device Records` > 1")
            .sort_values("Device Records", ascending=False)
        )
        st.write("Duplicate serial numbers")
        st.dataframe(serial_dupes, use_container_width=True, hide_index=True)

    if device_col:
        name_dupes = (
            devices.groupby(device_col)
            .size()
            .reset_index(name="Device Records")
            .query("`Device Records` > 1")
            .sort_values("Device Records", ascending=False)
        )
        st.write("Duplicate device names")
        st.dataframe(name_dupes, use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Searchable Device Detail")

    search = st.text_input("Search any field", placeholder="Device name, serial, client, app, OS, source file...")
    detail = filtered.copy()

    if search:
        mask = detail.astype(str).apply(
            lambda row: row.str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        detail = detail[mask]

    st.dataframe(detail, use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Export Filtered Results")

    export_tables = {
        "Filtered Rows": filtered,
        "Unique Devices": devices,
    }

    if device_col:
        export_tables["Client Summary"] = (
            devices.groupby(["Main Group", "Client Subgroup"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values("Devices", ascending=False)
        )

    if {"Application Display Name", "Application Version"}.issubset(filtered.columns) and device_col:
        export_tables["App Versions"] = (
            filtered.groupby(["Main Group", "Client Subgroup", "Application Display Name", "Application Version"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values("Devices", ascending=False)
        )

    excel_bytes = to_excel_bytes(export_tables)
    filename = f"mdm_client_report_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    st.download_button(
        "Download Excel Export",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
