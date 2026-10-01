"""
track editor: straights and curves, side markings, closing of the track and .tfg files
"""
import math
import os
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox, ttk

from . import geometry as G
from . import tfg
from . import theme as T
from .canvas import TrackCanvas
from .model import Curve, History, Marking, Straight, Track, LEFT, RIGHT

TRACKS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tracks")

class TrackEditor:
    def __init__(self, root, path=None):
        self.root = root
        self.track = Track()
        self.history = History()
        self.path = None
        self.modified = False
        self.selected = None
        self.unit = "cm"
        self.unit_factor = tfg.UNITS[self.unit]

        T.setup(root)
        root.minsize(T.px(1060), T.px(620))
        self._variables()
        self._menu()
        self._layout()
        self._shortcuts()
        root.protocol("WM_DELETE_WINDOW", self.quit)

        self.refresh(fit=True)
        if path:
            root.after(50, lambda: self.open(path))

    # --- units --- #

    def fmt(self, meters):
        return f"{meters / self.unit_factor:.6g}"

    def _length(self, var, name, positive=True):
        try:
            value = float(var.get().replace(",", ".")) * self.unit_factor
        except ValueError:
            raise ValueError(f"{name}: invalid number")
        if positive and value <= 0:
            raise ValueError(f"{name} must be greater than zero")
        return value

    def _number(self, var, name, low=None, high=None):
        try:
            value = float(var.get().replace(",", "."))
        except ValueError:
            raise ValueError(f"{name}: invalid number")
        if (low is not None and value < low) or (high is not None and value > high):
            raise ValueError(f"{name} must be between {low:g} and {high:g}")
        return value

    def _set_unit(self, event=None):
        new = self.var_unit.get()
        if new == self.unit:
            return
        old_factor, new_factor = self.unit_factor, tfg.UNITS[new]
        for var in (self.var_length, self.var_radius, self.var_mark_distance, self.var_close_radius):
            try:
                var.set(f"{float(var.get()) * old_factor / new_factor:.6g}")
            except ValueError:
                pass
        self.unit, self.unit_factor = new, new_factor
        self.var_unit_label.set(new)
        self.refresh()

    # --- interface --- #

    def _variables(self):
        self.var_unit = tk.StringVar(value=self.unit)
        self.var_unit_label = tk.StringVar(value=self.unit)
        self.var_length = tk.StringVar(value="20")
        self.var_follow = tk.BooleanVar(value=True)
        self.var_heading = tk.StringVar(value="0")
        self.var_radius = tk.StringVar(value="10")
        self.var_angle = tk.StringVar(value="90")
        self.var_side = tk.StringVar(value=LEFT)
        self.var_mark_side = tk.StringVar(value=LEFT)
        self.var_mark_distance = tk.StringVar(value="5")
        self.var_close_radius = tk.StringVar(value="10")
        self.var_ppm = tk.StringVar()
        self.var_area_h = tk.StringVar()
        self.var_area_w = tk.StringVar()
        self.var_origin_x = tk.StringVar()
        self.var_origin_y = tk.StringVar()
        self.var_grid = tk.BooleanVar(value=True)
        self.var_markings = tk.BooleanVar(value=True)
        self.var_status = tk.StringVar(value="")
        self.var_mouse = tk.StringVar(value="")

    def _menu(self):
        bar = tk.Menu(self.root)
        file = tk.Menu(bar, tearoff=0)
        file.add_command(label="New", accelerator="Ctrl+N", command=self.new)
        file.add_command(label="Open...", accelerator="Ctrl+O", command=self.open)
        file.add_separator()
        file.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file.add_command(label="Save as...", accelerator="Ctrl+Shift+S", command=self.save_as)
        file.add_separator()
        file.add_command(label="Quit", command=self.quit)
        bar.add_cascade(label="File", menu=file)

        edit = tk.Menu(bar, tearoff=0)
        edit.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        edit.add_separator()
        edit.add_command(label="Remove segment", accelerator="Del", command=self.remove)
        edit.add_command(label="Clear track", command=self.clear)
        bar.add_cascade(label="Edit", menu=edit)

        track = tk.Menu(bar, tearoff=0)
        track.add_command(label="Close track", command=self.close_track)
        track.add_command(label="Origin at the center of the track", command=self.center_origin)
        track.add_command(label="Pick the origin on the map", command=self.pick_origin)
        bar.add_cascade(label="Track", menu=track)

        view = tk.Menu(bar, tearoff=0)
        view.add_command(label="Fit to window", accelerator="F", command=lambda: self.view.fit())
        view.add_checkbutton(label="Grid", variable=self.var_grid, command=self._toggle_view)
        view.add_checkbutton(label="Markings", variable=self.var_markings, command=self._toggle_view)
        bar.add_cascade(label="View", menu=view)

        help_ = tk.Menu(bar, tearoff=0)
        help_.add_command(label="Shortcuts", command=self._help)
        bar.add_cascade(label="Help", menu=help_)
        self.root.config(menu=bar)

    def _layout(self):
        main = ttk.Frame(self.root, padding=T.px(12))
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = T.ScrollFrame(main, width=300)
        left.grid(row=0, column=0, sticky="ns", padx=(0, T.px(12)))
        center = tk.Frame(main, bg=T.PANEL, highlightbackground=T.BORDER, highlightthickness=1)
        center.grid(row=0, column=1, sticky="nsew")
        right = T.ScrollFrame(main, width=300)
        right.grid(row=0, column=2, sticky="ns", padx=(T.px(12), 0))

        self._segment_panel(left.inner)
        self._marking_panel(left.inner)
        self._closing_panel(left.inner)
        self._view_panel(center)
        self._list_panel(right.inner)
        self._summary_panel(right.inner)
        self._export_panel(right.inner)

        status = ttk.Frame(self.root, style="Card.TFrame", padding=(T.px(12), T.px(4)))
        status.pack(fill="x", side="bottom")
        ttk.Label(status, textvariable=self.var_status, style="Status.TLabel").pack(side="left")
        ttk.Label(status, textvariable=self.var_mouse, style="Status.TLabel").pack(side="right")

    def _entry(self, parent, var, width=12):
        entry = ttk.Entry(parent, textvariable=var, width=width)
        return entry

    def _segment_panel(self, parent):
        body = T.card(parent, "Segment", "New segment or the values of the selected one")
        self.tabs = ttk.Notebook(body)
        self.tabs.grid(row=0, column=0, columnspan=3, sticky="ew")

        tab = ttk.Frame(self.tabs, style="Card.TFrame", padding=(0, 10, 0, 4))
        tab.columnconfigure(1, weight=1)
        T.row(tab, 0, "Length", self._entry(tab, self.var_length), self.var_unit_label)
        ttk.Checkbutton(tab, text="Follow the tangent", variable=self.var_follow,
                        command=self._update_heading_state).grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        self.entry_heading = self._entry(tab, self.var_heading)
        T.row(tab, 2, "Absolute heading", self.entry_heading, "deg")
        self.tabs.add(tab, text="Straight")

        tab = ttk.Frame(self.tabs, style="Card.TFrame", padding=(0, 10, 0, 4))
        tab.columnconfigure(1, weight=1)
        T.row(tab, 0, "Radius", self._entry(tab, self.var_radius), self.var_unit_label)
        T.row(tab, 1, "Angle", self._entry(tab, self.var_angle), "deg")
        sides = ttk.Frame(tab, style="Card.TFrame")
        ttk.Radiobutton(sides, text="Left", value=LEFT, variable=self.var_side).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(sides, text="Right", value=RIGHT, variable=self.var_side).pack(side="left")
        T.row(tab, 2, "Turn to", sides)
        self.tabs.add(tab, text="Curve")

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        for i in range(3):
            buttons.columnconfigure(i, weight=1, uniform="b")
        ttk.Button(buttons, text="Add", style="Accent.TButton", command=self.add).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Insert", command=self.insert_after).grid(row=0, column=1, sticky="ew", padx=4)
        self.btn_apply = ttk.Button(buttons, text="Apply", command=self.apply_selected)
        self.btn_apply.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        self._update_heading_state()

    def _marking_panel(self, parent):
        body = T.card(parent, "Marking", "Side mark at the end of the selected segment")
        sides = ttk.Frame(body, style="Card.TFrame")
        ttk.Radiobutton(sides, text="Left", value=LEFT, variable=self.var_mark_side).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(sides, text="Right", value=RIGHT, variable=self.var_mark_side).pack(side="left")
        T.row(body, 0, "Side", sides)
        T.row(body, 1, "Distance", self._entry(body, self.var_mark_distance), self.var_unit_label)
        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1, uniform="b")
        buttons.columnconfigure(1, weight=1, uniform="b")
        self.btn_mark = ttk.Button(buttons, text="Apply", command=self.apply_marking)
        self.btn_mark.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Apply to all", command=self.apply_marking_all).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _closing_panel(self, parent):
        body = T.card(parent, "Close the track", "Adds curve + straight + curve from the end to the start, with continuous tangent")
        self.lbl_closure = ttk.Label(body, style="Card.TLabel")
        self.lbl_closure.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        T.row(body, 1, "Curves radius", self._entry(body, self.var_close_radius), self.var_unit_label)
        self.btn_close = ttk.Button(body, text="Close track", command=self.close_track)
        self.btn_close.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    def _view_panel(self, parent):
        bar = ttk.Frame(parent, style="Card.TFrame", padding=(T.px(10), T.px(8)))
        bar.pack(fill="x")
        ttk.Button(bar, text="Fit (F)", command=lambda: self.view.fit()).pack(side="left")
        ttk.Checkbutton(bar, text="Grid", variable=self.var_grid, command=self._toggle_view).pack(side="left", padx=(14, 0))
        ttk.Checkbutton(bar, text="Markings", variable=self.var_markings, command=self._toggle_view).pack(side="left", padx=(10, 0))
        unit = ttk.Combobox(bar, textvariable=self.var_unit, values=list(tfg.UNITS), state="readonly", width=5)
        unit.pack(side="right")
        unit.bind("<<ComboboxSelected>>", self._set_unit)
        ttk.Label(bar, text="Unit", style="Card.TLabel").pack(side="right", padx=(0, T.px(6)))
        tk.Frame(parent, bg=T.BORDER, height=1).pack(fill="x")
        self.view = TrackCanvas(parent, self)
        self.view.canvas.pack(fill="both", expand=True)

    def _list_panel(self, parent):
        body = T.card(parent, "Segments", "Order of the track; click to select")
        tree = ttk.Treeview(body, columns=("n", "type", "value"), show="headings", height=11, selectmode="browse")
        tree.heading("n", text="#")
        tree.heading("type", text="Type")
        tree.heading("value", text="Values")
        tree.column("n", width=T.px(30), minwidth=T.px(30), anchor="center", stretch=False)
        tree.column("type", width=T.px(64), minwidth=T.px(64), stretch=False)
        tree.column("value", width=T.px(150), minwidth=T.px(80), stretch=True)
        tree.tag_configure("kink", foreground=T.ERROR)
        tree.grid(row=0, column=0, columnspan=3, sticky="ew")
        tree.bind("<<TreeviewSelect>>", self._tree_select)
        self.tree = tree
        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        for i in range(4):
            buttons.columnconfigure(i, weight=1, uniform="b")
        for i, (label, command) in enumerate((("Up", lambda: self.move(-1)), ("Down", lambda: self.move(1)),
                                              ("Delete", self.remove), ("Clear", self.clear))):
            ttk.Button(buttons, text=label, command=command, style="Small.TButton").grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 0 if i == 3 else 3))
        undo = ttk.Frame(body, style="Card.TFrame")
        undo.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        undo.columnconfigure(0, weight=1, uniform="u")
        undo.columnconfigure(1, weight=1, uniform="u")
        ttk.Button(undo, text="Undo", command=self.undo).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(undo, text="Redo", command=self.redo).grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def _summary_panel(self, parent):
        body = T.card(parent, "Track")
        self.summary = {}
        for i, key in enumerate(("Length", "Segments", "Smallest radius", "Kinks", "Exported points")):
            ttk.Label(body, text=key, style="Card.TLabel").grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(body, style="Card.TLabel", font=T.font(0, "bold"))
            lbl.grid(row=i, column=1, columnspan=2, sticky="e", pady=2)
            self.summary[key] = lbl

    def _export_panel(self, parent):
        body = T.card(parent, "Export", "Resolution of the points, area and origin of the simulator")
        fields = [
            ("Points per meter", self.var_ppm, None),
            ("Area height", self.var_area_h, self.var_unit_label),
            ("Area width", self.var_area_w, self.var_unit_label),
            ("Origin x", self.var_origin_x, self.var_unit_label),
            ("Origin y", self.var_origin_y, self.var_unit_label),
        ]
        for i, (label, var, unit) in enumerate(fields):
            entry = self._entry(body, var)
            entry.bind("<Return>", lambda e: self.apply_settings())
            entry.bind("<FocusOut>", lambda e: self.apply_settings(quiet=True))
            T.row(body, i, label, entry, unit)
        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=len(fields), column=0, columnspan=3, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1, uniform="b")
        buttons.columnconfigure(1, weight=1, uniform="b")
        ttk.Button(buttons, text="Center origin", command=self.center_origin).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Pick on map", command=self.pick_origin).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _shortcuts(self):
        def guard(action):
            # the text shortcuts of the entries are kept (Ctrl+Z inside an entry, Delete, ...)
            def handler(event):
                if isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
                    return None
                action()
                return "break"
            return handler

        def always(action):
            def handler(event):
                action()
                return "break"
            return handler

        r = self.root
        for key, action in (("<Control-z>", self.undo), ("<Control-y>", self.redo), ("<Control-Z>", self.redo),
                            ("<Delete>", self.remove), ("<f>", lambda: self.view.fit()), ("<F>", lambda: self.view.fit())):
            r.bind_all(key, guard(action))
        for key, action in (("<Control-n>", self.new), ("<Control-o>", self.open), ("<Control-s>", self.save),
                            ("<Control-S>", self.save_as), ("<Escape>", self.escape)):
            r.bind_all(key, always(action))

    def _help(self):
        messagebox.showinfo("Shortcuts", "\n".join((
            "Ctrl+N   new track", "Ctrl+O   open", "Ctrl+S   save", "Ctrl+Shift+S   save as",
            "Ctrl+Z / Ctrl+Y   undo / redo", "Del   remove the selected segment", "F   fit the track to the window",
            "Esc   clear the selection / cancel the origin pick", "",
            "Mouse: click selects a segment, drag moves the map, wheel zooms")))

    # --- state --- #

    def _change(self):
        # call before changing the track (undo)
        self.history.push(self.track, self.selected)
        self.modified = True

    def _title(self):
        name = os.path.basename(self.path) if self.path else "untitled"
        self.root.title(f"Track editor - {name}{' *' if self.modified else ''}")

    def refresh(self, fit=False):
        if self.selected is not None and self.selected >= len(self.track.segments):
            self.selected = len(self.track.segments) - 1 if self.track.segments else None
        self._fill_tree()
        self._fill_summary()
        self._fill_settings()
        state = "normal" if self.selected is not None else "disabled"
        self.btn_apply.configure(state=state)
        self.btn_mark.configure(state=state)
        self._title()
        if fit:
            self.root.after(30, self.view.fit)
        else:
            self.view.redraw()

    def _describe(self, segment):
        if isinstance(segment, Straight):
            direction = "tangent" if segment.heading is None else f"heading {segment.heading:g} deg"
            return "Straight", f"{self.fmt(segment.length)} {self.unit}, {direction}"
        return "Curve", f"R {self.fmt(segment.radius)} {self.unit}, {segment.angle:.4g} deg {segment.side}"

    def _fill_tree(self):
        kinks = dict(G.kinks(self.track))
        self.tree.delete(*self.tree.get_children())
        for i, segment in enumerate(self.track.segments):
            kind, text = self._describe(segment)
            if i in kinks:
                text = f"kink {kinks[i]:+.1f} deg | {text}"
            self.tree.insert("", "end", iid=str(i), values=(i + 1, kind, text), tags=("kink",) if i in kinks else ())
        if self.selected is not None:
            self.tree.selection_set(str(self.selected))
            self.tree.see(str(self.selected))

    def _fill_summary(self):
        track = self.track
        radii = [s.radius for s in track.segments if isinstance(s, Curve)]
        kinks = G.kinks(track)
        length = G.total_length(track)
        s = self.summary
        s["Length"].configure(text=f"{self.fmt(length)} {self.unit}")
        s["Segments"].configure(text=str(len(track.segments)))
        s["Smallest radius"].configure(text=f"{self.fmt(min(radii))} {self.unit}" if radii else "-")
        s["Kinks"].configure(text=str(len(kinks)), foreground=T.ERROR if kinks else T.TEXT)
        s["Exported points"].configure(text=str(max(2, int(round(length * track.points_per_meter)) + 1)) if length else "-")

        if not track.segments:
            self.lbl_closure.configure(text="Empty track", style="Muted.TLabel")
            self.btn_close.configure(state="disabled")
        elif G.is_closed(track):
            self.lbl_closure.configure(text="Closed", style="Ok.TLabel")
            self.btn_close.configure(state="disabled")
        else:
            d, a = G.closure_error(track)
            self.lbl_closure.configure(text=f"Open: gap {d / self.unit_factor:.3g} {self.unit}, heading {math.degrees(a):+.1f} deg",
                                       style="Error.TLabel")
            self.btn_close.configure(state="normal")

    def _fill_settings(self):
        t = self.track
        for var, value in ((self.var_ppm, f"{t.points_per_meter:.6g}"), (self.var_area_h, self.fmt(t.area.height)),
                           (self.var_area_w, self.fmt(t.area.width)), (self.var_origin_x, self.fmt(t.origin[0])),
                           (self.var_origin_y, self.fmt(t.origin[1]))):
            var.set(value)

    def apply_settings(self, quiet=False):
        try:
            ppm = self._number(self.var_ppm, "Points per meter", 1, 100000)
            height = self._length(self.var_area_h, "Area height")
            width = self._length(self.var_area_w, "Area width")
            ox = self._length(self.var_origin_x, "Origin x", positive=False)
            oy = self._length(self.var_origin_y, "Origin y", positive=False)
        except ValueError as error:
            if not quiet:
                messagebox.showerror("Invalid value", str(error))
            self._fill_settings()
            return
        t = self.track
        new = (ppm, height, width, (ox, oy))
        if all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) for a, b in
               zip((t.points_per_meter, t.area.height, t.area.width, *t.origin), (ppm, height, width, ox, oy))):
            return
        self._change()
        t.points_per_meter, t.area.height, t.area.width, t.origin = new
        self.refresh()

    def set_status(self, text):
        self.var_status.set(text)

    def set_mouse(self, point):
        if point is None:
            self.var_mouse.set("")
        else:
            self.var_mouse.set(f"x {self.fmt(point[0])}  y {self.fmt(point[1])} {self.unit}")

    def _update_heading_state(self):
        self.entry_heading.configure(state="disabled" if self.var_follow.get() else "normal")

    def _toggle_view(self):
        self.view.show_grid = self.var_grid.get()
        self.view.show_markings = self.var_markings.get()
        self.view.redraw()

    # --- selection --- #

    def select(self, index):
        self.selected = index
        if index is not None:
            segment = self.track.segments[index]
            if isinstance(segment, Straight):
                self.tabs.select(0)
                self.var_length.set(self.fmt(segment.length))
                self.var_follow.set(segment.heading is None)
                if segment.heading is not None:
                    self.var_heading.set(f"{segment.heading:g}")
                self._update_heading_state()
            else:
                self.tabs.select(1)
                self.var_radius.set(self.fmt(segment.radius))
                self.var_angle.set(f"{segment.angle:.6g}")
                self.var_side.set(segment.side)
            marking = self.track.markings[index]
            self.var_mark_side.set(marking.side)
            self.var_mark_distance.set(self.fmt(marking.distance))
            self.set_status(f"segment {index + 1} selected")
        else:
            self.set_status("")
        self.refresh()

    def _tree_select(self, event=None):
        items = self.tree.selection()
        index = int(items[0]) if items else None
        if index != self.selected:
            self.select(index)

    def escape(self):
        if self.view.picking_origin:
            self.view.set_picking_origin(False)
            self.set_status("origin pick canceled")
        else:
            self.select(None)

    # --- segments --- #

    def _segment(self):
        try:
            if self.tabs.index(self.tabs.select()) == 0:
                length = self._length(self.var_length, "Length")
                heading = None if self.var_follow.get() else self._number(self.var_heading, "Heading", -360, 360)
                return Straight(length, heading)
            radius = self._length(self.var_radius, "Radius")
            angle = self._number(self.var_angle, "Angle", 0, 360)
            if angle <= 0:
                raise ValueError("Angle must be greater than zero")
            return Curve(radius, angle, self.var_side.get())
        except ValueError as error:
            messagebox.showerror("Invalid value", str(error))
            return None

    def _marking(self):
        try:
            return Marking(self.var_mark_side.get(), self._length(self.var_mark_distance, "Marking distance", positive=False))
        except ValueError as error:
            messagebox.showerror("Invalid value", str(error))
            return None

    def add(self):
        segment, marking = self._segment(), self._marking()
        if segment is None or marking is None:
            return
        self._change()
        self.selected = self.track.append(segment, marking)
        self.set_status(f"segment {self.selected + 1} added")
        self.refresh()

    def insert_after(self):
        if self.selected is None:
            self.add()
            return
        segment, marking = self._segment(), self._marking()
        if segment is None or marking is None:
            return
        self._change()
        self.selected = self.track.insert(self.selected + 1, segment, marking)
        self.set_status(f"segment {self.selected + 1} inserted")
        self.refresh()

    def apply_selected(self):
        if self.selected is None:
            return
        segment = self._segment()
        if segment is None:
            return
        self._change()
        self.track.replace(self.selected, segment)
        self.set_status(f"segment {self.selected + 1} changed")
        self.refresh()

    def apply_marking(self):
        marking = self._marking()
        if self.selected is None or marking is None:
            return
        self._change()
        self.track.markings[self.selected] = marking
        self.refresh()

    def apply_marking_all(self):
        marking = self._marking()
        if marking is None or not self.track.segments:
            return
        self._change()
        self.track.markings = [Marking(marking.side, marking.distance) for _ in self.track.segments]
        self.set_status("marking applied to all the segments")
        self.refresh()

    def move(self, step):
        if self.selected is None:
            return
        new = self.selected + step
        if not 0 <= new < len(self.track.segments):
            return
        self._change()
        self.selected = self.track.move(self.selected, step)
        self.refresh()

    def remove(self):
        if self.selected is None:
            return
        self._change()
        self.track.remove(self.selected)
        self.set_status(f"segment {self.selected + 1} removed")
        if self.selected >= len(self.track.segments):
            self.selected = len(self.track.segments) - 1 if self.track.segments else None
        self.refresh()

    def clear(self):
        if not self.track.segments:
            return
        if not messagebox.askyesno("Clear track", "Remove all the segments? (Ctrl+Z undoes it)"):
            return
        self._change()
        self.track.clear()
        self.selected = None
        self.refresh()

    def close_track(self):
        if not self.track.segments:
            return
        try:
            radius = self._length(self.var_close_radius, "Curves radius")
        except ValueError as error:
            messagebox.showerror("Invalid value", str(error))
            return
        pieces = G.closing_segments(self.track, radius)
        if pieces is None:
            messagebox.showwarning("Close track", "It is not possible to close the track with this radius: try a smaller one.")
            return
        if not pieces:
            self.set_status("the track is already closed")
            return
        self._change()
        marking = self.track.markings[-1] if self.track.markings else Marking()
        for piece in pieces:
            self.selected = self.track.append(piece, Marking(marking.side, marking.distance))
        self.set_status(f"track closed with {len(pieces)} segments")
        self.refresh()

    def undo(self):
        state = self.history.undo(self.track, self.selected)
        if state is None:
            self.set_status("nothing to undo")
            return
        self.track, self.selected = state
        self.modified = True
        self.refresh()

    def redo(self):
        state = self.history.redo(self.track, self.selected)
        if state is None:
            self.set_status("nothing to redo")
            return
        self.track, self.selected = state
        self.modified = True
        self.refresh()

    # --- origin --- #

    def center_origin(self):
        if not self.track.segments:
            return
        x0, y0, x1, y1 = G.bounds(self.track)
        self._change()
        self.track.origin = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.refresh()

    def pick_origin(self):
        self.view.set_picking_origin(True)
        self.set_status("click on the map to place the origin")

    def set_origin(self, point):
        self.view.set_picking_origin(False)
        self._change()
        self.track.origin = point
        self.set_status("origin changed")
        self.refresh()

    # --- files --- #

    def _confirm_discard(self):
        if not self.modified:
            return True
        answer = messagebox.askyesnocancel("Unsaved changes", "Save the changes of the track?")
        if answer is None:
            return False
        return self.save() if answer else True

    def new(self):
        if not self._confirm_discard():
            return
        self.track, self.path, self.selected, self.modified = Track(), None, None, False
        self.history.clear()
        self.refresh(fit=True)

    def open(self, path=None):
        if not self._confirm_discard():
            return
        if path is None:
            path = filedialog.askopenfilename(title="Open track", initialdir=TRACKS_FOLDER,
                                              filetypes=[("Track", "*.tfg"), ("All files", "*.*")])
            if not path:
                return
        try:
            track, info = tfg.load(path)
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            messagebox.showerror("Open track", f"Could not open {path}:\n{error}")
            return
        self.track, self.path, self.selected, self.modified = track, path, None, False
        self.history.clear()
        self.var_unit.set(info["display_unit"])
        self._set_unit()
        message = f"opened {os.path.basename(path)}"
        if info["version"] == 1:
            message += " (old format: converted, it is saved in the new format)"
        self.set_status(message)
        if info["warnings"]:
            messagebox.showwarning("Old track", "\n".join(info["warnings"]))
        self.refresh(fit=True)

    def save(self):
        if self.path is None or not self.path.lower().endswith(".tfg"):
            return self.save_as()
        return self._write(self.path)

    def save_as(self):
        os.makedirs(TRACKS_FOLDER, exist_ok=True)
        path = filedialog.asksaveasfilename(title="Save track", initialdir=TRACKS_FOLDER, defaultextension=".tfg",
                                            initialfile=os.path.basename(self.path) if self.path else "track.tfg",
                                            filetypes=[("Track", "*.tfg")])
        return self._write(path) if path else False

    def _write(self, path):
        if not self.track.segments:
            messagebox.showwarning("Save track", "The track has no segments.")
            return False
        if not G.is_closed(self.track) and not messagebox.askyesno(
                "Open track", "The track is not closed: the simulator expects a closed track. Save anyway?"):
            return False
        try:
            tfg.save(self.track, path, self.unit)
        except OSError as error:
            messagebox.showerror("Save track", str(error))
            return False
        self.path, self.modified = path, False
        self.set_status(f"saved {os.path.basename(path)}")
        self._title()
        return True

    def quit(self):
        if self._confirm_discard():
            self.root.destroy()

def main(path=None):
    T.enable_dpi_awareness()
    root = tk.Tk()
    scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
    w = min(int(1440 * scale), int(root.winfo_screenwidth() * 0.92))
    h = min(int(860 * scale), int(root.winfo_screenheight() * 0.86))
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{max(0, (root.winfo_screenheight() - h) // 3)}")
    TrackEditor(root, path)
    root.mainloop()
