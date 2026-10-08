# %% Step 1: load and inspect
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)

raw = pd.read_json("raw_readings.jsonl", lines=True)
devices = pd.read_csv("devices.csv", parse_dates=["installed"])

print("shape:", raw.shape)
print(raw.head())
raw.info()
print(raw.describe())
print("missing per column:\n", raw.isna().sum())
print(raw["status"].value_counts())
print("devices:", sorted(raw["device_id"].unique()))

# %% Step 2: select and filter
print(raw["temperature"].head(3))                    # one column = Series
print(raw[["device_id", "ts"]].head(3))              # list of columns = DataFrame
print(raw.loc[0:2, ["device_id", "ts"]])             # .loc: by label, end INCLUDED
print(raw.iloc[0:2, 0:2])                            # .iloc: by position, end excluded
print("rows for A1:", (raw["device_id"] == "A1").sum())
print("query result:", len(raw.query("humidity > 60 and device_id == 'A1'")))
print("status contains 'ale':", raw["status"].str.contains("ale", case=False).sum())

# %% Step 3: clean
df = raw.copy()
df["device_id"] = df["device_id"].str.strip().str.upper()
df["status"] = df["status"].str.strip().str.upper()
df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
df["time_utc"] = pd.to_datetime(df["ts"], unit="s", utc=True)
df["time_ist"] = df["time_utc"].dt.tz_convert("Asia/Kolkata")

print("before dedupe:", len(df))
df = df.drop_duplicates(subset=["device_id", "ts"], keep="first")
print("after dedupe :", len(df))

print(df[df["temperature"] > 60][["device_id", "ts", "temperature"]])
df.loc[df["temperature"] > 60, "temperature"] = np.nan

df = df.sort_values(["device_id", "time_utc"]).reset_index(drop=True)
df["temperature"] = df.groupby("device_id")["temperature"].ffill()
df["humidity"] = df["humidity"].fillna(df.groupby("device_id")["humidity"].transform("median"))
df = df.dropna(subset=["temperature"])
print("missing after cleaning:\n", df.isna().sum())
print(df.dtypes)

# %% Step 4: new columns
df["date"] = df["time_ist"].dt.date
df["hour"] = df["time_ist"].dt.hour
df["temp_f"] = (df["temperature"] * 9 / 5 + 32).round(1)
df["status_calc"] = np.select(
    [df["temperature"] >= 34, df["temperature"] >= 30], ["ALERT", "WARN"], default="OK"
)
df["is_alert"] = df["status_calc"] == "ALERT"
df["band"] = pd.cut(
    df["temperature"], bins=[-np.inf, 20, 25, 30, np.inf], labels=["cold", "mild", "warm", "hot"]
)
print("rows where status differs from recomputed:", (df["status"] != df["status_calc"]).sum())
print(df[["device_id", "time_ist", "temperature", "temp_f", "status_calc", "band"]].head())

# %% Step 5: group and aggregate
summary = (
    df.groupby("device_id")
    .agg(
        readings=("ts", "count"),
        avg_temp=("temperature", "mean"),
        max_temp=("temperature", "max"),
        alerts=("is_alert", "sum"),
    )
    .round(2)
    .sort_values("avg_temp", ascending=False)
)
print(summary)
print(pd.crosstab(df["device_id"], df["status_calc"]))
print(df.groupby(["device_id", "date"])["temperature"].mean().round(1).head(8))

# %% Step 6: join with the devices table
inner = df.merge(devices, on="device_id", how="inner")
left = df.merge(devices, on="device_id", how="left", validate="many_to_one")
print("rows -> df:", len(df), " inner:", len(inner), " left:", len(left))
print("orphan devices (no metadata):", left.loc[left["site"].isna(), "device_id"].unique())

outer = df.merge(devices, on="device_id", how="outer", indicator=True)
print(outer["_merge"].value_counts())
print("devices with no readings:", outer.loc[outer["_merge"] == "right_only", "device_id"].tolist())

full = inner.copy()
full["days_since_install"] = (full["time_utc"] - full["installed"].dt.tz_localize("UTC")).dt.days
print(full[["device_id", "site", "installed", "days_since_install"]].drop_duplicates("device_id"))

# %% Step 7: time series
wide = full.pivot_table(index="time_utc", columns="device_id", values="temperature")
print(wide.resample("D").mean().round(1))
print(wide.resample("6h").max().head(4))

full = full.sort_values(["device_id", "time_utc"]).reset_index(drop=True)
full["roll6"] = (
    full.groupby("device_id")["temperature"]
    .transform(lambda s: s.rolling(6, min_periods=1).mean())
    .round(2)
)
full["delta"] = full.groupby("device_id")["temperature"].diff()
print(full[["device_id", "time_utc", "temperature", "roll6", "delta"]].head(6))

latest = full.sort_values("time_utc").groupby("device_id").tail(1)
print(latest[["device_id", "time_utc", "temperature"]])

top3 = full.sort_values("temperature", ascending=False).groupby("device_id").head(3)
print(top3[["device_id", "time_utc", "temperature"]].sort_values(["device_id", "temperature"], ascending=[True, False]))

full["rank_in_device"] = full.groupby("device_id")["temperature"].rank(ascending=False, method="first")
print(full.loc[full["rank_in_device"] == 1, ["device_id", "time_utc", "temperature"]])

# %% Step 8: reshape
heat = full.pivot_table(index="hour", columns="device_id", values="temperature", aggfunc="mean").round(1)
print(heat.head(6))
long = wide.reset_index().melt(id_vars="time_utc", var_name="device_id", value_name="temperature")
print(long.shape, long.head(3).to_dict("records"))

# %% Step 9: speed - vectorise, do not loop
big = pd.DataFrame({"x": np.arange(300_000, dtype="float64")})

t0 = time.perf_counter()
big["y"] = big["x"] * 2 + 1
t_vec = time.perf_counter() - t0

t0 = time.perf_counter()
big["z"] = big["x"].apply(lambda v: v * 2 + 1)
t_apply = time.perf_counter() - t0

small = big.head(30_000)
t0 = time.perf_counter()
small.apply(lambda r: r["x"] * 2 + 1, axis=1)
t_rows = (time.perf_counter() - t0) * 10   # scale 30k rows up to 300k

print(f"vectorised: {t_vec * 1000:.1f} ms | apply per value: {t_apply * 1000:.0f} ms | apply per row (est.): {t_rows * 1000:.0f} ms")

# %% Step 10: dtypes and memory
before = full.memory_usage(deep=True).sum()
for col in ["device_id", "status", "site", "model"]:
    full[col] = full[col].astype("category")
after = full.memory_usage(deep=True).sum()
print(f"memory: {before / 1000:.0f} KB -> {after / 1000:.0f} KB")
print(full.dtypes[["device_id", "status", "temperature", "time_utc"]])

# %% Step 11: the classic mistake (copy vs view)
a1 = df[df["device_id"] == "A1"]
a1["temperature"] = 0
print("A1 mean in df after changing the copy:", round(df.loc[df["device_id"] == "A1", "temperature"].mean(), 2))

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    df[df["device_id"] == "A1"]["temperature"] = 0      # chained assignment: does nothing
print("chained assignment warning:", [type(w.message).__name__ for w in caught])
print("A1 mean still:", round(df.loc[df["device_id"] == "A1", "temperature"].mean(), 2))

# %% Step 12: save results (CSV, Parquet, partitioned Parquet)
out = Path("out")
out.mkdir(exist_ok=True)
full.to_csv(out / "clean.csv", index=False)
full.to_parquet(out / "clean.parquet", index=False)
full.to_parquet(out / "by_date", partition_cols=["date"], index=False)

print("csv     :", (out / "clean.csv").stat().st_size, "bytes")
print("parquet :", (out / "clean.parquet").stat().st_size, "bytes")
print("folders :", sorted(p.name for p in (out / "by_date").iterdir()))
back = pd.read_parquet(out / "clean.parquet")
print(back.dtypes[["temperature", "time_utc", "device_id"]])
print("rows read back:", len(back))