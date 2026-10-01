"""
saves the data of a run in csv files to plot later

    <name>.csv          one row per simulation step
    <name>_track.csv    points of the track (same coordinates of the car pose columns x, y)
    <name>_meta.json    settings of the run (controller, tuning, ...)

example (pandas):
    df = pd.read_csv("runs/taylor.csv")
    track = pd.read_csv("runs/taylor_track.csv")
    plt.plot(track.x, track.y); plt.plot(df.x, df.y)
"""
import csv
import json
import os
import time

import numpy as np

class RunLogger:
    def __init__(self, path=None, name="run", folder="runs", meta=None):
        if path is None:
            path = os.path.join(folder, f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        self.path = path
        self.meta = dict(meta or {})
        self.rows = []
        self.track = None

    def set_track(self, x, y):
        self.track = (np.asarray(x), np.asarray(y))

    def log(self, **fields):
        # one row per call; the columns are the keys of the first row (new keys are appended)
        self.rows.append(fields)

    def __len__(self):
        return len(self.rows)

    def save(self, path=None):
        if path is not None:
            self.path = path
        if not self.rows:
            print("RunLogger: nothing to save")
            return None

        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        columns = []
        for row in self.rows:
            for key in row:
                if key not in columns:
                    columns.append(key)

        with open(self.path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, restval="")
            writer.writeheader()
            for row in self.rows:
                writer.writerow({k: _to_csv(v) for k, v in row.items()})

        base = os.path.splitext(self.path)[0]
        if self.track is not None:
            with open(base + "_track.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["x", "y"])
                writer.writerows(np.column_stack(self.track).tolist())

        with open(base + "_meta.json", "w") as f:
            json.dump(self.meta, f, indent=2, default=_to_json)

        print(f"Run saved in {self.path} ({len(self.rows)} steps)")
        return self.path

def _to_csv(value):
    if isinstance(value, (np.floating, float)):
        return repr(float(value))
    if isinstance(value, np.integer):
        return int(value)
    return value

def _to_json(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return str(value)
