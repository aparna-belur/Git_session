import time
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).with_name("readings.csv")
REQUIRED = {"device_id", "reading_time", "temperature", "status"}

st.set_page_config(page_title="Sensor dashboard", layout="wide")


@st.cache_data(show_spinner="Loading data...")
def load_data(path: str) -> pd.DataFrame:
    time.sleep(2)  # pretend this is a slow query
    return pd.read_csv(path, parse_dates=["reading_time"])


st.title("Sensor dashboard")

# ---- Sidebar: data source ----
st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload a CSV (optional)", type="csv")
if st.sidebar.button("Clear cache"):
    st.cache_data.clear()

started = time.perf_counter()
if uploaded is not None:
    df = pd.read_csv(uploaded, parse_dates=["reading_time"])
else:
    df = load_data(str(DATA_FILE))
st.sidebar.caption(f"Data ready in {time.perf_counter() - started:.2f}s")

missing = REQUIRED - set(df.columns)
if missing:
    st.error(f"Missing columns: {sorted(missing)}")
    st.stop()

# ---- Sidebar: filters ----
st.sidebar.header("Filters")
all_devices = sorted(df["device_id"].unique())
devices = st.sidebar.multiselect("Devices", all_devices, default=all_devices)

min_date = df["reading_time"].dt.date.min()
max_date = df["reading_time"].dt.date.max()
date_range = st.sidebar.date_input(
    "Date range", (min_date, max_date), min_value=min_date, max_value=max_date
)
if len(date_range) != 2:
    st.info("Pick an end date.")
    st.stop()
start, end = date_range

top = float(df["temperature"].max())
max_temp = st.sidebar.slider(
    "Show readings up to (°C)", float(df["temperature"].min()), top, top, step=0.5
)

# ---- Session state: count reruns ----
if "runs" not in st.session_state:
    st.session_state.runs = 0
st.session_state.runs += 1
st.sidebar.divider()
st.sidebar.caption(f"Script reruns this session: {st.session_state.runs}")

# ---- Filter the data ----
mask = (
    df["device_id"].isin(devices)
    & (df["reading_time"].dt.date >= start)
    & (df["reading_time"].dt.date <= end)
    & (df["temperature"] <= max_temp)
)
view = df[mask]

if view.empty:
    st.warning("No data for these filters.")
    st.stop()

# ---- Metrics ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Readings", len(view))
c2.metric("Avg temp", f"{view['temperature'].mean():.1f} °C")
c3.metric("Max temp", f"{view['temperature'].max():.1f} °C")
c4.metric("Alerts", int((view["status"] == "ALERT").sum()))

# ---- Tabs ----
tab_chart, tab_table, tab_stats = st.tabs(["Chart", "Table", "Stats"])

with tab_chart:
    chart_type = st.radio("Chart type", ["Line (hourly)", "Bar (daily avg)"], horizontal=True)
    pivot = view.pivot_table(index="reading_time", columns="device_id", values="temperature")
    if chart_type.startswith("Line"):
        st.line_chart(pivot)
    else:
        st.bar_chart(pivot.resample("D").mean())

with tab_table:
    st.dataframe(view, hide_index=True)
    st.download_button(
        "Download filtered CSV",
        view.to_csv(index=False).encode("utf-8"),
        file_name="filtered.csv",
        mime="text/csv",
    )

with tab_stats:
    stats = view.groupby("device_id")["temperature"].agg(["count", "mean", "min", "max"]).round(2)
    st.dataframe(stats)
    st.bar_chart(view["status"].value_counts())