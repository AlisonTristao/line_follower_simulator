"""
geometry of the track: poses, sampling by arc length, closure, kinks and markings
(lengths in meters, headings in radians, segment angles in degrees)
"""
import math

import numpy as np

from .model import Curve, Straight, LEFT, RIGHT

TWO_PI = 2 * math.pi

def wrap(angle):
    # angle in [-pi, pi]
    return math.atan2(math.sin(angle), math.cos(angle))

def side_sign(side):
    return 1.0 if side == LEFT else -1.0

def segment_length(segment):
    if isinstance(segment, Straight):
        return abs(segment.length)
    return abs(math.radians(segment.angle) * segment.radius)

def total_length(track):
    return sum(segment_length(s) for s in track.segments)

def start_heading(segment, heading):
    # heading at the beginning of the segment (an absolute straight can break the tangent)
    if isinstance(segment, Straight) and segment.heading is not None:
        return math.radians(segment.heading)
    return heading

def point_on(segment, pose, s):
    """
    pose (x, y, heading) at the arc length s from the start of the segment
    """
    x0, y0, h0 = pose
    h0 = start_heading(segment, h0)
    if isinstance(segment, Straight):
        return x0 + s * math.cos(h0), y0 + s * math.sin(h0), h0
    k = side_sign(segment.side)
    r = segment.radius
    cx, cy = x0 - k * r * math.sin(h0), y0 + k * r * math.cos(h0)
    h = h0 + k * s / r
    return cx + k * r * math.sin(h), cy - k * r * math.cos(h), h

def end_pose(segment, pose):
    return point_on(segment, pose, segment_length(segment))

def poses(track):
    """
    pose at the start of each segment and at the end of the track: len(segments) + 1 poses
    """
    out = [(0.0, 0.0, 0.0)]
    for segment in track.segments:
        out.append(end_pose(segment, out[-1]))
    return out

def segment_polylines(track, curve_step_deg=3.0):
    """
    points of each segment for drawing: list of (M, 2) arrays
    """
    lines = []
    pose = (0.0, 0.0, 0.0)
    for segment in track.segments:
        length = segment_length(segment)
        n = 2 if isinstance(segment, Straight) else max(8, int(math.ceil(abs(segment.angle) / curve_step_deg)) + 1)
        pts = [point_on(segment, pose, s)[:2] for s in np.linspace(0.0, length, n)]
        lines.append(np.array(pts))
        pose = end_pose(segment, pose)
    return lines

def sample(track, spacing=None, count=None, closed=None):
    """
    points equally spaced along the track (arc length): (N, 2) array
    closed: drops the last point when the track is closed (it is the first one); default: automatic
    """
    length = total_length(track)
    if length <= 0:
        return np.zeros((1, 2))
    if count is None:
        count = max(2, int(math.ceil(length / spacing)) + 1)
    targets = np.linspace(0.0, length, count)
    out = np.empty((count, 2))
    pose = (0.0, 0.0, 0.0)
    start = 0.0
    i = 0
    segments = track.segments
    for k, segment in enumerate(segments):
        seg_len = segment_length(segment)
        last = k == len(segments) - 1
        while i < count and (targets[i] <= start + seg_len or last):
            out[i] = point_on(segment, pose, min(max(targets[i] - start, 0.0), seg_len))[:2]
            i += 1
        pose = end_pose(segment, pose)
        start += seg_len
    if closed is None:
        closed = is_closed(track)
    return out[:-1] if closed and len(out) > 2 else out

def closure_error(track):
    """
    (distance [m], heading error [rad]) between the end of the track and its start
    """
    x, y, h = poses(track)[-1]
    first = start_heading(track.segments[0], 0.0) if track.segments else 0.0
    return math.hypot(x, y), wrap(h - first)

def is_closed(track, distance_tol=1e-3, angle_tol=math.radians(0.1)):
    if not track.segments:
        return False
    d, a = closure_error(track)
    return d < distance_tol and abs(a) < angle_tol

def kinks(track, tol=math.radians(0.05)):
    """
    joints where the heading jumps (absolute straights): list of (segment index, angle [deg])
    the joint between the end and the start is included when the track is closed in position
    """
    out = []
    pose = (0.0, 0.0, 0.0)
    for i, segment in enumerate(track.segments):
        if i > 0:
            jump = wrap(start_heading(segment, pose[2]) - pose[2])
            if abs(jump) > tol:
                out.append((i, math.degrees(jump)))
        pose = end_pose(segment, pose)
    if track.segments:
        d, a = closure_error(track)
        if d < 1e-3 and abs(a) > tol:
            out.append((0, math.degrees(-a)))
    return out

def marking_positions(track):
    """
    position (x, y) and direction (rad, perpendicular to the track) of the marking of each segment
    """
    out = []
    pose = (0.0, 0.0, 0.0)
    for segment, marking in zip(track.segments, track.markings):
        pose = end_pose(segment, pose)
        x, y, h = pose
        normal = h + side_sign(marking.side) * math.pi / 2
        out.append((x + marking.distance * math.cos(normal), y + marking.distance * math.sin(normal), normal))
    return out

def bounds(track, margin=0.0):
    # (xmin, ymin, xmax, ymax) of the line
    lines = segment_polylines(track)
    pts = np.vstack(lines) if lines else np.zeros((1, 2))
    lo, hi = pts.min(axis=0) - margin, pts.max(axis=0) + margin
    return lo[0], lo[1], hi[0], hi[1]

def closing_segments(track, radius):
    """
    segments (curve, straight, curve) that close the track with continuous tangent, from the end pose
    to the start pose, with curves of the given radius (shortest path of the Dubins CSC family).
    returns [] when it is already closed and None when it is not possible
    """
    if not track.segments or radius <= 0:
        return None
    if is_closed(track):
        return []
    x0, y0, h0 = poses(track)[-1]
    x1, y1 = 0.0, 0.0
    h1 = start_heading(track.segments[0], 0.0)
    r = radius

    def center(x, y, h, side):
        k = side_sign(side)
        return x - k * r * math.sin(h), y + k * r * math.cos(h)

    best = None
    for s1 in (LEFT, RIGHT):
        for s2 in (LEFT, RIGHT):
            c1, c2 = center(x0, y0, h0, s1), center(x1, y1, h1, s2)
            vx, vy = c2[0] - c1[0], c2[1] - c1[1]
            dist = math.hypot(vx, vy)
            base = math.atan2(vy, vx)
            if s1 == s2:
                options = [(base, dist)]
            else:
                if dist < 2 * r:
                    continue
                length = math.sqrt(dist ** 2 - 4 * r ** 2)
                offset = math.atan2(2 * r, length)
                options = [(base + offset, length), (base - offset, length)]
            for phi, length in options:
                k1, k2 = side_sign(s1), side_sign(s2)
                turn1 = (k1 * (phi - h0)) % TWO_PI
                turn2 = (k2 * (h1 - phi)) % TWO_PI
                pieces = []
                if turn1 * r > 1e-9:
                    pieces.append(Curve(radius=r, angle=math.degrees(turn1), side=s1))
                if length > 1e-9:
                    pieces.append(Straight(length=length))
                if turn2 * r > 1e-9:
                    pieces.append(Curve(radius=r, angle=math.degrees(turn2), side=s2))
                # keeps only the candidates that really arrive at the start (checks the geometry)
                pose = (x0, y0, h0)
                for piece in pieces:
                    pose = end_pose(piece, pose)
                if math.hypot(pose[0] - x1, pose[1] - y1) > 1e-6 or abs(wrap(pose[2] - h1)) > 1e-6:
                    continue
                total = turn1 * r + length + turn2 * r
                if best is None or total < best[0]:
                    best = (total, pieces)
    return None if best is None else best[1]

def nearest_segment(track, x, y, max_distance):
    # index of the segment nearest to (x, y) (world), or None
    best, best_d = None, max_distance
    for i, pts in enumerate(segment_polylines(track)):
        a, b = pts[:-1], pts[1:]
        ab = b - a
        t = np.clip(((x - a[:, 0]) * ab[:, 0] + (y - a[:, 1]) * ab[:, 1]) / np.maximum((ab ** 2).sum(axis=1), 1e-18), 0, 1)
        d = np.hypot(a[:, 0] + t * ab[:, 0] - x, a[:, 1] + t * ab[:, 1] - y).min()
        if d < best_d:
            best, best_d = i, d
    return best

def to_simulator(points):
    """
    editor coordinates (x right, y up, start heading +x) -> simulator track coordinates
    (y down on the screen, start heading upwards like the generated tracks), centered on the origin
    """
    pts = np.asarray(points, dtype=float)
    sim = np.column_stack((-pts[:, 1], -pts[:, 0]))
    lo, hi = sim.min(axis=0), sim.max(axis=0)
    return sim - (lo + hi) / 2
