"""
view of the track: zoom on the mouse, pan by dragging, click selects a segment
the view is redrawn only when something changes (the mouse position goes to the status bar)
"""
import math
import tkinter as tk

from . import geometry as G
from . import theme as T

def nice_step(raw):
    # 1, 2 or 5 x 10^n just above raw
    if raw <= 0:
        return 1.0
    exp = math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * 10 ** exp >= raw:
            return m * 10 ** exp
    return 10 ** (exp + 1)

class TrackCanvas:
    RULER = 26      # scaled by the dpi in __init__

    def __init__(self, parent, app):
        self.app = app
        self.RULER = T.px(26)
        # small requested size: the map is what shrinks when the window is small
        self.canvas = tk.Canvas(parent, bg=T.CANVAS, highlightthickness=0, cursor="arrow", width=200, height=200)
        self.zoom = 200.0              # px per meter
        self.center = (0.0, 0.0)        # world point at the center of the view
        self.show_grid = True
        self.show_markings = True
        self.picking_origin = False
        self._drag = None

        c = self.canvas
        c.bind("<Configure>", lambda e: self.redraw())
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._move)
        c.bind("<ButtonRelease-1>", self._release)
        for button in (2, 3):
            c.bind(f"<ButtonPress-{button}>", self._press_pan)
            c.bind(f"<B{button}-Motion>", self._move)
            c.bind(f"<ButtonRelease-{button}>", self._release)
        c.bind("<MouseWheel>", lambda e: self._zoom_at(e.x, e.y, 1.15 if e.delta > 0 else 1 / 1.15))
        c.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, 1.15))
        c.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 1 / 1.15))
        c.bind("<Motion>", self._motion)
        c.bind("<Leave>", lambda e: self.app.set_mouse(None))

    # --- coordinates --- #

    def size(self):
        return max(self.canvas.winfo_width(), 10), max(self.canvas.winfo_height(), 10)

    def to_screen(self, x, y):
        w, h = self.size()
        return w / 2 + (x - self.center[0]) * self.zoom, h / 2 - (y - self.center[1]) * self.zoom

    def to_world(self, sx, sy):
        w, h = self.size()
        return self.center[0] + (sx - w / 2) / self.zoom, self.center[1] - (sy - h / 2) / self.zoom

    def fit(self):
        # the track and its area
        track = self.app.track
        ox, oy = track.origin
        x0, y0 = ox - track.area.width / 2, oy - track.area.height / 2
        x1, y1 = ox + track.area.width / 2, oy + track.area.height / 2
        if track.segments:
            bx0, by0, bx1, by1 = G.bounds(track)
            x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
        w, h = self.size()
        span_x, span_y = max(x1 - x0, 1e-3), max(y1 - y0, 1e-3)
        self.zoom = max(1.0, min((w - 2 * self.RULER - 60) / span_x, (h - 2 * self.RULER - 60) / span_y))
        self.center = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.redraw()

    # --- mouse --- #

    def _press(self, event):
        if self.picking_origin:
            self.app.set_origin(self.to_world(event.x, event.y))
            return
        index = G.nearest_segment(self.app.track, *self.to_world(event.x, event.y), 8 / self.zoom)
        if index is not None:
            self.app.select(index)
            self._drag = None
        else:
            self._press_pan(event)

    def _press_pan(self, event):
        self._drag = (event.x, event.y, self.center, False)
        self.canvas.config(cursor="fleur")

    def _move(self, event):
        if self._drag is None:
            return
        x0, y0, center, moved = self._drag
        dx, dy = event.x - x0, event.y - y0
        if not moved and math.hypot(dx, dy) < 4:
            return
        self._drag = (x0, y0, center, True)
        self.center = (center[0] - dx / self.zoom, center[1] + dy / self.zoom)
        self.redraw()

    def _release(self, event):
        if self._drag is not None and not self._drag[3] and event.num == 1:
            # click on an empty place: clears the selection
            self.app.select(None)
        self._drag = None
        self.canvas.config(cursor="crosshair" if self.picking_origin else "arrow")

    def _zoom_at(self, sx, sy, factor):
        x, y = self.to_world(sx, sy)
        self.zoom = max(1.0, min(self.zoom * factor, 50000.0))
        nx, ny = self.to_world(sx, sy)
        self.center = (self.center[0] + x - nx, self.center[1] + y - ny)
        self.redraw()

    def _motion(self, event):
        self.app.set_mouse(self.to_world(event.x, event.y))

    def set_picking_origin(self, value):
        self.picking_origin = value
        self.canvas.config(cursor="crosshair" if value else "arrow")
        self.redraw()

    # --- drawing --- #

    def redraw(self):
        c = self.canvas
        c.delete("all")
        w, h = self.size()
        track = self.app.track
        unit, factor = self.app.unit, self.app.unit_factor

        step = nice_step(70 / self.zoom / factor) * factor      # grid step in meters, round in the work unit
        if self.show_grid:
            self._grid(step / 5, T.GRID_MINOR)
            self._grid(step, T.GRID)

        # area of the track (simulator limits) and origin
        ox, oy = track.origin
        ax0, ay0 = self.to_screen(ox - track.area.width / 2, oy + track.area.height / 2)
        ax1, ay1 = self.to_screen(ox + track.area.width / 2, oy - track.area.height / 2)
        c.create_rectangle(ax0, ay0, ax1, ay1, outline=T.MUTED, dash=(6, 4), width=1)
        c.create_text(ax0 + 6, ay0 + 6, anchor="nw", fill=T.MUTED, font=T.font(-1),
                      text=f"area {self.app.fmt(track.area.width)} x {self.app.fmt(track.area.height)} {unit}")
        sx, sy = self.to_screen(ox, oy)
        color = T.PICK if self.picking_origin else T.MUTED
        c.create_line(sx - 8, sy, sx + 8, sy, fill=color, width=2 if self.picking_origin else 1)
        c.create_line(sx, sy - 8, sx, sy + 8, fill=color, width=2 if self.picking_origin else 1)

        # line
        lines = G.segment_polylines(track)
        selected = self.app.selected
        for i, pts in enumerate(lines):
            coords = [v for x, y in pts for v in self.to_screen(x, y)]
            sel = i == selected
            c.create_line(*coords, fill=T.ACCENT if sel else T.TRACK, width=T.px(6 if sel else 3),
                          capstyle="round", joinstyle="round")

        poses = G.poses(track)
        r = T.px(2.5)
        for x, y, _ in poses[1:-1]:
            px, py = self.to_screen(x, y)
            c.create_oval(px - r, py - r, px + r, py + r, fill=T.PANEL, outline=T.TRACK)

        # markings: bar from the line to the marking
        if self.show_markings and track.segments:
            for (mx, my, a), (x, y, _), marking in zip(G.marking_positions(track), poses[1:], track.markings):
                bx, by = math.cos(a), math.sin(a)
                p0 = self.to_screen(mx - bx * 0.012, my - by * 0.012)
                p1 = self.to_screen(mx + bx * 0.012, my + by * 0.012)
                col = T.LEFT if marking.side == "left" else T.RIGHT
                c.create_line(*p0, *p1, fill=col, width=max(T.px(3), min(T.px(8), 0.02 * self.zoom)))

        # kinks (heading jumps)
        for index, angle in G.kinks(track):
            x, y, _ = poses[index]
            px, py = self.to_screen(x, y)
            r = T.px(9)
            c.create_oval(px - r, py - r, px + r, py + r, outline=T.ERROR, width=T.px(2))

        # start (arrow with the direction) and end
        if track.segments:
            h0 = G.start_heading(track.segments[0], 0.0)
            px, py = self.to_screen(0.0, 0.0)
            a, r = T.px(26), T.px(5)
            c.create_line(px, py, px + a * math.cos(h0), py - a * math.sin(h0), fill=T.OK, width=T.px(3), arrow="last",
                          arrowshape=(T.px(10), T.px(12), T.px(5)))
            c.create_oval(px - r, py - r, px + r, py + r, fill=T.OK, outline=T.PANEL, width=T.px(2))
            if not G.is_closed(track):
                ex, ey = self.to_screen(*poses[-1][:2])
                c.create_line(ex, ey, px, py, fill=T.ERROR, dash=(4, 4))
                c.create_oval(ex - r, ey - r, ex + r, ey + r, fill=T.ERROR, outline=T.PANEL, width=T.px(2))
        else:
            px, py = self.to_screen(0.0, 0.0)
            c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=T.OK, outline=T.PANEL, width=2)
            c.create_text(w / 2, h / 2, text="Add a straight or a curve to start the track", fill=T.MUTED, font=T.font(2))

        if self.picking_origin:
            c.create_text(w / 2, self.RULER + 16, text="Click on the map to place the origin (Esc cancels)",
                          fill=T.PICK, font=T.font(1, "bold"))

        self._rulers(step)

    def _grid(self, step, color):
        c = self.canvas
        w, h = self.size()
        x0, y1 = self.to_world(0, 0)
        x1, y0 = self.to_world(w, h)
        if step * self.zoom < 6:
            return
        k = math.floor(x0 / step)
        while k * step <= x1:
            sx, _ = self.to_screen(k * step, 0)
            c.create_line(sx, 0, sx, h, fill=color)
            k += 1
        k = math.floor(y0 / step)
        while k * step <= y1:
            _, sy = self.to_screen(0, k * step)
            c.create_line(0, sy, w, sy, fill=color)
            k += 1

    def _rulers(self, step):
        # rulers with the values in the work unit
        c = self.canvas
        w, h = self.size()
        r = self.RULER
        factor = self.app.unit_factor
        c.create_rectangle(0, 0, w, r, fill=T.PANEL, outline="")
        c.create_rectangle(0, 0, r, h, fill=T.PANEL, outline="")
        c.create_line(0, r, w, r, fill=T.BORDER)
        c.create_line(r, 0, r, h, fill=T.BORDER)
        x0, y1 = self.to_world(r, r)
        x1, y0 = self.to_world(w, h)
        k = math.floor(x0 / step)
        while k * step <= x1:
            sx, _ = self.to_screen(k * step, 0)
            if sx > r:
                c.create_line(sx, r - 7, sx, r, fill=T.MUTED)
                c.create_text(sx + 3, 4, anchor="nw", text=f"{k * step / factor:g}", fill=T.MUTED, font=T.font(-2))
            k += 1
        k = math.floor(y0 / step)
        while k * step <= y1:
            _, sy = self.to_screen(0, k * step)
            if sy > r:
                c.create_line(r - 7, sy, r, sy, fill=T.MUTED)
                c.create_text(r - 4, sy - 3, anchor="se", text=f"{k * step / factor:g}", fill=T.MUTED, font=T.font(-2), angle=90)
            k += 1
        c.create_text(4, 4, anchor="nw", text=self.app.unit, fill=T.TEXT, font=T.font(-2, "bold"))
