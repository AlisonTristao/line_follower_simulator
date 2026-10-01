"""
.tfg files: zip with the segments (json), the points of the line (csv) and the markings (csv)

version 2 (this editor): everything in meters, curves with angle > 0 and side, straights that follow
the tangent (heading null) or have an absolute heading.
the csv files keep the convention of the first version (points from the end to the start, y inverted and
relative to the origin), so the reader of the old simulator still works.

version 1 (old editor) is converted when loaded.
"""
import csv
import io
import json
import math
import os
import zipfile

from . import geometry as G
from .model import Area, Curve, Marking, Straight, Track, LEFT, RIGHT

VERSION = 2
UNITS = {"m": 1.0, "cm": 0.01, "mm": 0.001}

def _side(value):
    value = str(value).lower()
    return RIGHT if value in ("right", "direita") else LEFT

# --- save --- #

def save(track, path, display_unit="cm"):
    base = os.path.splitext(os.path.basename(path))[0]
    length = G.total_length(track)
    count = max(2, int(round(length * track.points_per_meter)) + 1)
    ox, oy = track.origin

    segments = []
    for s in track.segments:
        if isinstance(s, Straight):
            segments.append({"type": "straight", "length": s.length, "heading_deg": s.heading})
        else:
            segments.append({"type": "curve", "radius": s.radius, "angle_deg": s.angle, "side": s.side})
    data = {
        "format": "line-follower-track",
        "version": VERSION,
        "unit": "m",
        "display_unit": display_unit,
        "segments": segments,
        "markings": [{"side": m.side, "distance": m.distance} for m in track.markings],
        "area": {"height": track.area.height, "width": track.area.width},
        "origin": {"x": ox, "y": oy},
        "points_per_meter": track.points_per_meter,
        "total_length": length,
        "closed": G.is_closed(track),
        # read by the simulator of the first version
        "exported_point_count": count,
        "unit_multiplier": 1.0,
        "output_unit": "m",
        "detection_border": {"height": track.area.height, "width": track.area.width},
    }

    points = G.sample(track, count=count, closed=False)[::-1]
    rows = [[i, f"{x - ox:.6f}", f"{-(y - oy):.6f}"] for i, (x, y) in enumerate(points)]
    marks = [[i, m.side, f"{m.distance:.6f}", f"{math.degrees(a):.4f}", f"{x - ox:.6f}", f"{-(y - oy):.6f}"]
             for i, (m, (x, y, a)) in enumerate(zip(track.markings, G.marking_positions(track)))]

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{base}_segments.json", json.dumps(data, indent=2))
        z.writestr(f"{base}.csv", _csv(["idx", "x", "y"], rows))
        z.writestr(f"{base}_markings.csv", _csv(["idx", "side", "distance", "angle_x_axis_degrees", "x", "y"], marks))

def _csv(header, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()

# --- load --- #

def load(path):
    """
    returns (track, info); info = {"display_unit", "version", "warnings"}
    """
    with zipfile.ZipFile(path, "r") as z:
        names = z.namelist()
        json_name = next((n for n in names if n.endswith("_segments.json")), None) or next((n for n in names if n.endswith(".json")), None)
        if json_name is None:
            raise ValueError("invalid .tfg file: no json with the segments")
        data = json.loads(z.read(json_name).decode("utf-8"))
        marks_name = next((n for n in names if n.endswith("_markings.csv")), None)
        marks_rows = list(csv.DictReader(io.StringIO(z.read(marks_name).decode("utf-8")))) if marks_name else []

    if data.get("version") == VERSION:
        return _load_v2(data)
    return _load_v1(data, marks_rows)

def _load_v2(data):
    track = Track()
    for item in data["segments"]:
        if item["type"] == "straight":
            heading = item.get("heading_deg")
            track.segments.append(Straight(float(item["length"]), None if heading is None else float(heading)))
        elif item["type"] == "curve":
            track.segments.append(Curve(float(item["radius"]), float(item["angle_deg"]), _side(item.get("side"))))
        else:
            raise ValueError(f"unknown segment type {item['type']!r}")
    marks = data.get("markings", [])
    track.markings = [Marking(_side(m.get("side")), float(m.get("distance", 0.05))) for m in marks[:len(track.segments)]]
    track.markings += [Marking() for _ in range(len(track.segments) - len(track.markings))]
    area = data.get("area", {})
    track.area = Area(float(area.get("height", 1.0)), float(area.get("width", 2.0)))
    origin = data.get("origin", {})
    track.origin = (float(origin.get("x", 0.0)), float(origin.get("y", 0.0)))
    track.points_per_meter = float(data.get("points_per_meter", 100.0))
    return track, {"display_unit": data.get("display_unit", "m"), "version": VERSION, "warnings": []}

def _load_v1(data, marks_rows):
    """
    old editor: the json has the values in meters when dimensions_converted_to_output_unit is true
    (otherwise they are multiplied by unit_multiplier); the straights have absolute angles and a curve
    turns to its side when its angle is negative
    """
    warnings = []
    factor = float(data.get("unit_multiplier") or 1.0)
    scale = 1.0 if data.get("dimensions_converted_to_output_unit") else factor

    track = Track()
    heading = 0.0
    for item in data.get("segments", []):
        kind = item.get("type")
        if kind == "straight":
            angle = float(item.get("angle_degrees", 0.0))
            # the absolute angle becomes "follow the tangent" when it is the same direction
            same = abs(G.wrap(math.radians(angle) - heading)) < 1e-6
            segment = Straight(float(item.get("length", 0.0)) * scale, None if same else angle)
        elif kind == "curve":
            angle = float(item.get("central_angle_degrees", 0.0))
            if angle > 0:
                warnings.append(f"segment {item.get('order', len(track.segments) + 1)}: curve with a positive angle "
                                f"(went backwards in the old editor), converted to a normal curve")
            segment = Curve(float(item.get("radius", 0.0)) * scale, abs(angle), _side(item.get("side")))
        else:
            raise ValueError(f"unknown segment type {kind!r}")
        track.segments.append(segment)
        heading = G.end_pose(segment, (0.0, 0.0, heading))[2]

    if marks_rows:
        rows = sorted(marks_rows, key=lambda r: int(float(r.get("idx", 0))))
        track.markings = [Marking(_side(r.get("side")), float(r.get("distance", 0.0)) * scale) for r in rows]
    else:
        track.markings = [Marking(_side(m.get("side")), float(m.get("distance", 0.0)) * scale) for m in data.get("markings", [])]
    track.markings = track.markings[:len(track.segments)]
    track.markings += [Marking() for _ in range(len(track.segments) - len(track.markings))]

    border = data.get("detection_border") or {}
    height = float(border.get("height", 0.5)) * (1.0 if data.get("dimensions_converted_to_output_unit") else factor)
    track.area = Area(height, 2 * height)
    origin = data.get("visual_export_origin") if data.get("dimensions_converted_to_output_unit") else data.get("visual_export_origin_m")
    origin = origin or {}
    track.origin = (float(origin.get("x", 0.0)) * (1.0 if data.get("dimensions_converted_to_output_unit") else factor),
                    float(origin.get("y", 0.0)) * (1.0 if data.get("dimensions_converted_to_output_unit") else factor))
    length = G.total_length(track)
    count = data.get("exported_point_count")
    if count and length > 0:
        track.points_per_meter = float(count) / length

    unit = data.get("output_unit")
    return track, {"display_unit": unit if unit in UNITS else "m", "version": 1, "warnings": warnings}

# --- simulator --- #

def load_points(path, spacing=0.01):
    """
    points of the line for the simulator: x, y arrays [m] in the simulator coordinates
    (centered, start heading upwards on the screen), equally spaced
    """
    track, _ = load(path)
    if not track.segments:
        raise ValueError(f"{path}: the track has no segments")
    pts = G.to_simulator(G.sample(track, spacing=spacing))
    return pts[:, 0], pts[:, 1]
