"""
track made of straight and curve segments (all lengths in meters, angles in degrees)

the track starts at (0, 0) with heading 0 (x axis); x to the right and y upwards
"""
import copy
from dataclasses import dataclass, field

LEFT = "left"
RIGHT = "right"

@dataclass
class Straight:
    length: float                   # [m]
    heading: float = None           # absolute heading [deg]; None follows the tangent of the previous segment

    kind = "straight"

@dataclass
class Curve:
    radius: float                   # [m]
    angle: float                    # turn [deg] > 0
    side: str = LEFT                # turns to the left or to the right

    kind = "curve"

@dataclass
class Marking:
    """side marking at the end of a segment (perpendicular to the track)"""
    side: str = LEFT
    distance: float = 0.05          # distance to the line [m]

@dataclass
class Area:
    """rectangle of the track (simulator limits), centered on the origin"""
    height: float = 1.0             # [m]
    width: float = 2.0              # [m]

@dataclass
class Track:
    segments: list = field(default_factory=list)
    markings: list = field(default_factory=list)     # one marking per segment
    area: Area = field(default_factory=Area)
    origin: tuple = (0.0, 0.0)                       # center of the area / origin of the exported points [m]
    points_per_meter: float = 100.0                  # resolution of the exported points

    def copy(self):
        return copy.deepcopy(self)

    # --- editing (keeps one marking per segment) --- #

    def insert(self, index, segment, marking=None):
        index = max(0, min(index, len(self.segments)))
        self.segments.insert(index, segment)
        self.markings.insert(index, marking or Marking())
        return index

    def append(self, segment, marking=None):
        return self.insert(len(self.segments), segment, marking)

    def replace(self, index, segment):
        self.segments[index] = segment

    def remove(self, index):
        del self.segments[index]
        del self.markings[index]

    def move(self, index, step):
        # moves the segment (and its marking) up or down in the order; returns the new index
        new = index + step
        if not (0 <= index < len(self.segments)) or not (0 <= new < len(self.segments)):
            return index
        for items in (self.segments, self.markings):
            items[index], items[new] = items[new], items[index]
        return new

    def clear(self):
        self.segments.clear()
        self.markings.clear()

class History:
    """undo / redo with snapshots of the whole track (the tracks are small)"""
    def __init__(self, limit=300):
        self.limit = limit
        self.undo_stack = []
        self.redo_stack = []

    def push(self, track, selection=None):
        # call before changing the track
        self.undo_stack.append((track.copy(), selection))
        if len(self.undo_stack) > self.limit:
            del self.undo_stack[0]
        self.redo_stack.clear()

    def undo(self, track, selection=None):
        if not self.undo_stack:
            return None
        self.redo_stack.append((track.copy(), selection))
        return self.undo_stack.pop()

    def redo(self, track, selection=None):
        if not self.redo_stack:
            return None
        self.undo_stack.append((track.copy(), selection))
        return self.redo_stack.pop()

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
