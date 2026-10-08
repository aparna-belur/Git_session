import json
import random

import numpy as np
import pandas as pd

random.seed(7)
rng = np.random.default_rng(7)

devices = pd.DataFrame(
    {
        "device_id": ["A1", "A2", "B1", "B2", "C1"],
        "site": ["Pune", "Pune", "Mumbai", "Mumbai", "Delhi"],
        "model": ["M1", "M2", "M1", "M2", "M1"],
        "installed": ["2025-03-01", "2025-06-15", "2025-01-10", "2026-02-20", "2025-09-05"],
    }
)
devices.to_csv("devices.csv", index=False)

times = pd.date_range("2026-10-01", periods=48 * 4, freq="30min", tz="UTC")
levels = {"A1": 22, "A2": 30, "B1": 20, "B2": 26, "Z9": 25}

records = []
for device, level in levels.items():
    n = len(times) if device != "Z9" else 6
    for i in range(n):
        temp = round(float(level + 3 * np.sin(i * 2 * np.pi / 48) + rng.normal(0, 1.2)), 1)
        status = "ALERT" if temp >= 34 else "WARN" if temp >= 30 else "OK"
        records.append(
            {
                "device_id": device,
                "ts": int(times[i].timestamp()),
                "temperature": temp,
                "humidity": int(rng.integers(30, 70)),
                "status": random.choice([status, status.lower(), status.title(), f" {status} "]),
            }
        )

# make the data messy, like real device output
for rec in random.sample(records, 40):
    rec["device_id"] = rec["device_id"].lower()
for rec in random.sample(records, 40):
    rec["temperature"] = str(rec["temperature"])
for rec in random.sample(records, 25):
    rec["temperature"] = None
for rec in random.sample(records, 3):
    rec["temperature"] = 999.9
for rec in random.sample(records, 30):
    del rec["humidity"]
records += random.sample(records, 15)  # duplicate deliveries
random.shuffle(records)

with open("raw_readings.jsonl", "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec) + "\n")

print(len(records), "records written to raw_readings.jsonl")
print(len(devices), "devices written to devices.csv")