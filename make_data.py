import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
times = pd.date_range("2026-10-01", periods=72, freq="h")
levels = {"A1": 22, "A2": 30, "B1": 20, "B2": 26}

frames = []
for device, level in levels.items():
    n = len(times)
    temp = level + 3 * np.sin(np.arange(n) * 2 * np.pi / 24) + rng.normal(0, 1.5, n)
    frames.append(
        pd.DataFrame(
            {"device_id": device, "reading_time": times, "temperature": temp.round(1)}
        )
    )

df = pd.concat(frames, ignore_index=True)
df.loc[df.sample(frac=0.02, random_state=1).index, "temperature"] = np.nan
df["status"] = np.select(
    [df["temperature"] >= 34, df["temperature"] >= 30], ["ALERT", "WARN"], default="OK"
)
df.to_csv("readings.csv", index=False)

print(df.shape)
print(df["status"].value_counts())
print(df.head())