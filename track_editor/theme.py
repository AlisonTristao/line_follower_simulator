"""
colors and ttk styles of the editor (same palette of the simulator menus)
"""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG          = "#f3f4f7"
PANEL       = "#ffffff"
CANVAS      = "#fafafb"
TEXT        = "#1e2026"
MUTED       = "#737882"
BORDER      = "#d6d9e0"
GRID        = "#e3e6eb"
GRID_MINOR  = "#f0f1f4"
ACCENT      = "#006ee6"
ACCENT_DARK = "#0058be"
ACCENT_SOFT = "#e1edfc"
TRACK       = "#22252c"
OK          = "#148c46"
ERROR       = "#cd2d2d"
LEFT        = "#006ee6"
RIGHT       = "#eb7814"
PICK        = "#b4329a"

FAMILY = "Segoe UI"
BASE = 10
SCALE = 1.0         # pixels of the screen per pixel at 96 dpi

def enable_dpi_awareness():
    # windows: crisp window on screens with scale > 100% (otherwise the window is stretched and blurry)
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

def px(value):
    return int(round(value * SCALE))

def font(delta=0, weight="normal"):
    return (FAMILY, BASE + delta, weight)

def setup(root):
    global FAMILY, SCALE
    SCALE = max(1.0, root.winfo_fpixels("1i") / 96.0)
    families = set(tkfont.families(root))
    FAMILY = next((f for f in ("Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans") if f in families), "TkDefaultFont")
    root.configure(bg=BG)
    # default fonts (the option database would override the fonts of the ttk styles)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name).configure(family=FAMILY, size=BASE)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", background=BG, foreground=TEXT, font=font(), bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER, troughcolor=BG, focuscolor=ACCENT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=PANEL)
    style.configure("Title.TLabel", background=PANEL, font=font(1, "bold"))
    style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=font(-1))
    style.configure("Ok.TLabel", background=PANEL, foreground=OK, font=font(0, "bold"))
    style.configure("Error.TLabel", background=PANEL, foreground=ERROR, font=font(0, "bold"))
    style.configure("Status.TLabel", background=PANEL, foreground=MUTED, font=font(-1))
    style.configure("TButton", background=PANEL, padding=(px(10), px(5)), relief="solid", borderwidth=1, bordercolor=BORDER)
    style.map("TButton", background=[("pressed", "#e4e7ec"), ("active", "#eef0f4"), ("disabled", BG)],
              foreground=[("disabled", MUTED)])
    style.configure("Small.TButton", padding=(px(4), px(5)))
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff", bordercolor=ACCENT, relief="solid",
                    lightcolor=ACCENT, darkcolor=ACCENT, font=font(0, "bold"))
    style.map("Accent.TButton", background=[("pressed", ACCENT_DARK), ("active", ACCENT_DARK), ("disabled", BORDER)],
              foreground=[("disabled", "#ffffff")])
    style.configure("TEntry", fieldbackground=PANEL, padding=(px(6), px(4)))
    style.map("TEntry", bordercolor=[("focus", ACCENT)], fieldbackground=[("disabled", BG)], foreground=[("disabled", MUTED)])
    style.configure("TCombobox", fieldbackground=PANEL, padding=(px(6), px(4)), arrowsize=px(14))
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)], bordercolor=[("focus", ACCENT)])
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=PANEL, indicatorbackground=PANEL, indicatorforeground=ACCENT)
        style.map(name, background=[("active", PANEL)], indicatorbackground=[("selected", PANEL)])
    style.configure("Bg.TCheckbutton", background=BG)
    style.map("Bg.TCheckbutton", background=[("active", BG)])
    style.configure("TNotebook", background=PANEL, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=BG, padding=(px(16), px(6)), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
    style.configure("Treeview", background=PANEL, fieldbackground=PANEL, rowheight=px(26), borderwidth=0)
    style.configure("Treeview.Heading", background=BG, font=font(-1, "bold"), relief="flat")
    style.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", TEXT)])
    style.configure("Vertical.TScrollbar", background=BG, troughcolor=PANEL, arrowsize=px(12), borderwidth=0)
    return style

class ScrollFrame(ttk.Frame):
    """
    vertical scrolling for the side panels (the content never gets cut on small windows)
    """
    def __init__(self, parent, width):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, width=px(width))
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(0, 0, anchor="nw", window=self.inner)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._update)
        self.canvas.bind("<Configure>", self._update)
        self.bind_all("<MouseWheel>", self._wheel, add="+")

    def _update(self, event=None):
        self.canvas.itemconfigure(self._window, width=self.canvas.winfo_width())
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # the scroll bar only appears when needed
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            if not self.bar.winfo_ismapped():
                self.bar.pack(side="right", fill="y")
        elif self.bar.winfo_ismapped():
            self.bar.pack_forget()
            self.canvas.yview_moveto(0)

    def _wheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None and widget is not self:
            widget = widget.master
        if widget is self and self.bar.winfo_ismapped():
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

def card(parent, title, subtitle=None):
    """
    white panel with a title; returns the frame for the content
    """
    outer = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    outer.pack(fill="x", pady=(0, px(12)))
    head = ttk.Frame(outer, style="Card.TFrame", padding=(px(12), px(10), px(12), 0))
    head.pack(fill="x")
    ttk.Label(head, text=title, style="Title.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(head, text=subtitle, style="Muted.TLabel", wraplength=px(260), justify="left").pack(anchor="w", pady=(2, 0))
    body = ttk.Frame(outer, style="Card.TFrame", padding=(px(12), px(8), px(12), px(12)))
    body.pack(fill="x")
    body.columnconfigure(1, weight=1)
    return body

def row(parent, r, label, widget, unit=None):
    # label | widget | unit on a grid row
    ttk.Label(parent, text=label, style="Card.TLabel").grid(row=r, column=0, sticky="w", pady=px(3), padx=(0, px(10)))
    widget.grid(row=r, column=1, sticky="ew", pady=px(3))
    if unit is not None:
        kw = {"textvariable": unit} if isinstance(unit, tk.Variable) else {"text": unit}
        ttk.Label(parent, style="Muted.TLabel", width=4, **kw).grid(row=r, column=2, sticky="w", padx=(6, 0))
