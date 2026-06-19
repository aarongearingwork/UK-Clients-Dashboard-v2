import io
from datetime import datetime

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="MDM Device Intelligence",
    page_icon="📱",
    layout="wide",
)


REQUIRED_COLUMNS = {
    "Device Name",
    "Serial Number",
    "Model",
    "OS Version",
    "Group Path",
    "Application Name",
    "Application Version",
}


@st.cache_data(show_spinner=False)
def load_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    if "Device Name" in df.columns:
        df = df[~df["Device Name"].astype(str).str.startswith("---", na=False)]

    df = df.replace({"nan": "", "None": "", "NaN": ""})
    return df


def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    with st.sidebar:
        st.header("Filters")

        def add_filter(label: str, column: str):
            if column not in df.columns:
                return []
            values = sorted([v for v in df[column].dropna().unique() if str(v).strip()])
            return st.multiselect(label, values)

        models = add_filter("Model", "Model")
        os_versions = add_filter("OS Version", "OS Version")
        groups = add_filter("Group Path", "Group Path")
        apps = add_filter("Application Name", "Application Name")
        app_versions = add_filter("Application Version", "Application Version")

    filter_map = {
        "Model": models,
        "OS Version": os_versions,
        "Group Path": groups,
        "Application Name": apps,
        "Application Version": app_versions,
    }

    for column, selected in filter_map.items():
        if selected and column in filtered.columns:
            filtered = filtered[filtered[column].isin(selected)]

    return filtered


def unique_devices(df: pd.DataFrame) -> pd.DataFrame:
    subset_cols = [c for c in ["Device Name", "Serial Number", "Model", "OS Version", "Group Path", "SSID"] if c in df.columns]
    if not subset_cols:
        return df.drop_duplicates()
    return df[subset_cols].drop_duplicates()


def to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, table in tables.items():
            safe_name = sheet_name[:31]
            table.to_excel(writer, index=False, sheet_name=safe_name)
    return output.getvalue()


def version_sort_value(value: str):
    parts = []
    for part in str(value).replace("-", ".").split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)
    return parts


st.title("📱 MDM Device Intelligence Dashboard")
st.caption("Upload an MDM CSV export to analyse inventory, OS spread, app versions, duplicates, and searchable device details.")

uploaded_file = st.file_uploader("Upload MDM CSV report", type=["csv"])

if uploaded_file is None:
    st.info("Upload your MDM CSV report to begin.")
    st.stop()

df = load_csv(uploaded_file)

missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
if missing_columns:
    st.warning(f"The CSV is missing expected columns: {', '.join(missing_columns)}. The dashboard will show the available views only.")

filtered = filter_df(df)
devices = unique_devices(filtered)

device_col = "Device Name" if "Device Name" in filtered.columns else None
serial_col = "Serial Number" if "Serial Number" in filtered.columns else None

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Report Rows", f"{len(filtered):,}")
kpi2.metric("Unique Devices", f"{devices.shape[0]:,}")
kpi3.metric("Models", filtered["Model"].nunique() if "Model" in filtered.columns else 0)
kpi4.metric("OS Versions", filtered["OS Version"].nunique() if "OS Version" in filtered.columns else 0)
kpi5.metric("Applications", filtered["Application Name"].nunique() if "Application Name" in filtered.columns else 0)

tabs = st.tabs([
    "Overview",
    "OS Lifecycle",
    "Applications",
    "Duplicates",
    "Device Detail",
    "Export",
])

with tabs[0]:
    st.subheader("Inventory Overview")

    if "Model" in devices.columns and device_col:
        model_counts = devices.groupby("Model")[device_col].nunique().sort_values(ascending=False)
        st.write("Devices by model")
        st.bar_chart(model_counts)

    if "Group Path" in devices.columns and device_col:
        group_counts = devices.groupby("Group Path")[device_col].nunique().sort_values(ascending=False)
        st.write("Devices by group")
        st.bar_chart(group_counts)

    st.write("Device inventory")
    st.dataframe(devices, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("OS Version Tracking")

    if "OS Version" in devices.columns and device_col:
        os_counts = devices.groupby("OS Version")[device_col].nunique().reset_index(name="Devices")
        os_counts = os_counts.sort_values("OS Version", key=lambda s: s.map(version_sort_value), ascending=False)

        latest_os = os_counts.iloc[0]["OS Version"] if not os_counts.empty else ""
        devices_on_latest = int(os_counts.loc[os_counts["OS Version"] == latest_os, "Devices"].sum()) if latest_os else 0
        total_devices = int(os_counts["Devices"].sum()) if not os_counts.empty else 0
        latest_pct = round((devices_on_latest / total_devices) * 100, 1) if total_devices else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Highest OS Version in Report", latest_os)
        c2.metric("Devices on Highest Version", f"{devices_on_latest:,}")
        c3.metric("Highest Version Coverage", f"{latest_pct}%")

        st.bar_chart(os_counts.set_index("OS Version")["Devices"])
        st.dataframe(os_counts, use_container_width=True, hide_index=True)
    else:
        st.info("OS Version and Device Name columns are required for this view.")

with tabs[2]:
    st.subheader("Application Version Drift")

    if {"Application Name", "Application Version"}.issubset(filtered.columns) and device_col:
        app_summary = (
            filtered.groupby(["Application Name", "Application Version"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values(["Application Name", "Devices"], ascending=[True, False])
        )

        drift = (
            app_summary.groupby("Application Name")["Application Version"]
            .nunique()
            .reset_index(name="Version Count")
            .sort_values("Version Count", ascending=False)
        )

        st.write("Applications with the most version drift")
        st.dataframe(drift, use_container_width=True, hide_index=True)

        selected_app = st.selectbox(
            "Inspect application",
            sorted(filtered["Application Name"].dropna().unique()),
        )

        selected_app_versions = app_summary[app_summary["Application Name"] == selected_app]
        st.bar_chart(selected_app_versions.set_index("Application Version")["Devices"])
        st.dataframe(selected_app_versions, use_container_width=True, hide_index=True)
    else:
        st.info("Application Name, Application Version, and Device Name columns are required for this view.")

with tabs[3]:
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
    else:
        st.info("Serial Number column is required for duplicate serial checks.")

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

with tabs[4]:
    st.subheader("Searchable Device Detail")

    search = st.text_input("Search any field", placeholder="Device name, serial number, app, OS, group...")
    detail = filtered.copy()

    if search:
        mask = detail.astype(str).apply(
            lambda row: row.str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        detail = detail[mask]

    st.dataframe(detail, use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Export Filtered Results")

    export_tables = {"Filtered Inventory": filtered}

    if device_col:
        export_tables["Unique Devices"] = devices

    if {"Application Name", "Application Version"}.issubset(filtered.columns) and device_col:
        export_tables["App Versions"] = (
            filtered.groupby(["Application Name", "Application Version"])[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values("Devices", ascending=False)
        )

    if "OS Version" in devices.columns and device_col:
        export_tables["OS Summary"] = (
            devices.groupby("OS Version")[device_col]
            .nunique()
            .reset_index(name="Devices")
            .sort_values("Devices", ascending=False)
        )

    excel_bytes = to_excel_bytes(export_tables)
    filename = f"mdm_dashboard_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    st.download_button(
        "Download Excel Export",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
