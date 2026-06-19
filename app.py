import streamlit as st
import pandas as pd

st.set_page_config(page_title="MDM Device Inventory", layout="wide")

st.title("MDM Device Inventory Dashboard")

uploaded_file = st.file_uploader("Upload MDM CSV Report", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    if "Device Name" in df.columns:
        df = df[~df["Device Name"].astype(str).str.startswith("---", na=False)]

    with st.sidebar:
        st.header("Filters")

        def multiselect_if_exists(column):
            if column in df.columns:
                return st.multiselect(column, sorted(df[column].dropna().unique()))
            return []

        models = multiselect_if_exists("Model")
        os_versions = multiselect_if_exists("OS Version")
        apps = multiselect_if_exists("Application Name")
        groups = multiselect_if_exists("Group Path")

    filtered = df.copy()

    if models:
        filtered = filtered[filtered["Model"].isin(models)]
    if os_versions:
        filtered = filtered[filtered["OS Version"].isin(os_versions)]
    if apps:
        filtered = filtered[filtered["Application Name"].isin(apps)]
    if groups:
        filtered = filtered[filtered["Group Path"].isin(groups)]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Rows", len(filtered))
    c2.metric("Unique Devices", filtered["Device Name"].nunique() if "Device Name" in filtered.columns else 0)
    c3.metric("Models", filtered["Model"].nunique() if "Model" in filtered.columns else 0)
    c4.metric("OS Versions", filtered["OS Version"].nunique() if "OS Version" in filtered.columns else 0)

    overview, apps_tab, inventory = st.tabs(["Overview", "Applications", "Inventory"])

    with overview:
        if "Model" in filtered.columns and "Device Name" in filtered.columns:
            st.subheader("Devices by Model")
            st.bar_chart(filtered.groupby("Model")["Device Name"].nunique())

        if "OS Version" in filtered.columns and "Device Name" in filtered.columns:
            st.subheader("Devices by OS Version")
            st.bar_chart(filtered.groupby("OS Version")["Device Name"].nunique())

    with apps_tab:
        if {"Application Name", "Application Version", "Device Name"}.issubset(filtered.columns):
            app_versions = (
                filtered.groupby(["Application Name", "Application Version"])["Device Name"]
                .nunique()
                .reset_index(name="Devices")
                .sort_values("Devices", ascending=False)
            )
            st.dataframe(app_versions, use_container_width=True)

    with inventory:
        search = st.text_input("Search")

        table = filtered.copy()

        if search:
            mask = table.astype(str).apply(
                lambda row: row.str.contains(search, case=False, na=False).any(),
                axis=1
            )
            table = table[mask]

        st.dataframe(table, use_container_width=True)
else:
    st.info("Upload an MDM CSV report to begin.")
