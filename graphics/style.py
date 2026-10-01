"""
visual style shared by the simulator and the menus: colors, fonts and anti-aliased drawing
"""
import math

import pygame
import pygame.gfxdraw

# --- colors --- #

BG          = (243, 244, 247)
CANVAS      = (250, 250, 251)
PANEL       = (255, 255, 255)
SIDEBAR     = (36, 40, 48)
SIDEBAR_HI  = (52, 58, 70)
SIDEBAR_TXT = (205, 210, 220)
ACCENT      = (0, 110, 230)
ACCENT_DARK = (0, 88, 190)
ACCENT_SOFT = (225, 237, 252)
ACCENT_TXT  = (255, 255, 255)
TEXT        = (30, 32, 38)
MUTED       = (115, 120, 130)
BORDER      = (214, 217, 224)
GRID        = (236, 238, 242)
ERROR       = (205, 45, 45)
OK          = (20, 140, 70)
TRACK       = (34, 37, 44)
TRACK_DONE  = (160, 165, 175)
TRACK_SOFT  = (190, 194, 202)
REFERENCE   = (235, 75, 50)
PREDICTION  = (0, 110, 230)
CAR         = (0, 110, 230)

# colors of the lines of the graphs (one per line of a graph)
PALETTE = [(0, 110, 230), (235, 120, 20), (20, 150, 90), (150, 75, 200), (210, 50, 80), (0, 160, 175)]

# --- fonts --- #

FACE = "segoeui,helveticaneue,helvetica,arial"
MONO = "consolas,menlo,dejavusansmono,couriernew"
_fonts = {}

def font(size, bold=False, mono=False):
    key = (int(size), bold, mono)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(MONO if mono else FACE, max(8, int(size)), bold=bold)
    return _fonts[key]

def text(surface, fnt, value, pos, color=TEXT, anchor="topleft"):
    img = fnt.render(str(value), True, color)
    rect = img.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})
    surface.blit(img, rect)
    return rect

def fit(fnt, value, width):
    # cuts the text to fit in the width
    value = str(value)
    if fnt.size(value)[0] <= width:
        return value
    while value and fnt.size(value + "...")[0] > width:
        value = value[:-1]
    return value + "..."

# --- anti-aliased primitives --- #

def circle(surface, color, center, radius):
    x, y, r = int(round(center[0])), int(round(center[1])), int(round(radius))
    if r < 1:
        surface.set_at((x, y), color)
        return
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)
    pygame.gfxdraw.aacircle(surface, x, y, r, color)

def ring(surface, color, center, radius, width=1):
    # circle outline with anti-aliased edges
    x, y, r = int(round(center[0])), int(round(center[1])), int(round(radius))
    for i in range(max(1, int(width))):
        pygame.gfxdraw.aacircle(surface, x, y, r - i, color)

def polygon(surface, color, points):
    # filled with integer vertices, the edge is drawn with sub-pixel anti-aliasing
    points = [(float(x), float(y)) for x, y in points]
    pygame.gfxdraw.filled_polygon(surface, [(round(x), round(y)) for x, y in points], color)
    pygame.draw.aalines(surface, color, True, points)

def line(surface, color, p1, p2, width=1):
    if width <= 1:
        pygame.draw.aaline(surface, color, p1, p2)
        return
    (x1, y1), (x2, y2) = p1, p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    nx, ny = -(y2 - y1) / length * width / 2, (x2 - x1) / length * width / 2
    polygon(surface, color, [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)])

def ribbon(surface, color, points, half_width):
    """
    thick anti-aliased line through the points (ribbon polygon with round caps)
    """
    import numpy as np
    pts = np.asarray(points, dtype=float)
    if len(pts) == 1:
        circle(surface, color, pts[0], half_width)
        return
    d = np.gradient(pts, axis=0)
    d /= np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
    normal = np.column_stack((-d[:, 1], d[:, 0]))
    # fill a bit inside (the integer vertices do not show) and cover the edge with sub-pixel anti-aliased lines
    inset = min(1.2, half_width * 0.5)
    left, right = pts + normal * (half_width - inset), pts - normal * (half_width - inset)
    pygame.gfxdraw.filled_polygon(surface, np.rint(np.vstack((left, right[::-1]))).astype(int).tolist(), color)
    for offset in (0.4, 0.9, 1.3):
        if offset < half_width:
            pygame.draw.aalines(surface, color, False, (pts + normal * (half_width - offset)).tolist())
            pygame.draw.aalines(surface, color, False, (pts - normal * (half_width - offset)).tolist())
    circle(surface, color, pts[0], half_width)
    circle(surface, color, pts[-1], half_width)

def rounded_rect(surface, rect, color, radius, border=None, border_width=1):
    """
    filled rectangle with anti-aliased round corners (and an optional border)
    """
    rect = pygame.Rect(rect)
    if border is not None:
        _rounded(surface, rect, border, radius)
        rect = rect.inflate(-2 * border_width, -2 * border_width)
        radius = max(0, radius - border_width)
    _rounded(surface, rect, color, radius)

def _rounded(surface, rect, color, radius):
    radius = int(min(radius, rect.width // 2, rect.height // 2))
    if radius < 2:
        pygame.draw.rect(surface, color, rect)
        return
    pygame.draw.rect(surface, color, rect.inflate(-2 * radius, 0))
    pygame.draw.rect(surface, color, rect.inflate(0, -2 * radius))
    r = radius - 1
    for cx, cy in ((rect.left + radius, rect.top + radius), (rect.right - radius - 1, rect.top + radius),
                   (rect.left + radius, rect.bottom - radius - 1), (rect.right - radius - 1, rect.bottom - radius - 1)):
        pygame.gfxdraw.filled_circle(surface, cx, cy, r, color)
        pygame.gfxdraw.aacircle(surface, cx, cy, r, color)

def card(surface, rect, radius=10, color=PANEL, border=BORDER, alpha=None):
    """
    panel with border; alpha < 255 draws it translucent (cached surface)
    """
    rect = pygame.Rect(rect)
    if alpha is None or alpha >= 255:
        rounded_rect(surface, rect, color, radius, border, 1)
        return
    key = (rect.size, radius, color, border, alpha)
    img = _cards.get(key)
    if img is None:
        img = pygame.Surface(rect.size, pygame.SRCALPHA)
        rounded_rect(img, img.get_rect(), (*color, alpha), radius, (*border, alpha) if border else None, 1)
        _cards[key] = img
    surface.blit(img, rect)

_cards = {}

def smooth(draw, size, scale=2):
    """
    renders draw(surface, scale) on a surface `scale` times bigger and smooths it down (supersampling),
    for static images with thick lines (plots of the results)
    """
    big = pygame.Surface((size[0] * scale, size[1] * scale), pygame.SRCALPHA)
    draw(big, scale)
    return pygame.transform.smoothscale(big, size)

def enable_dpi_awareness():
    # windows: avoid the blurry upscaling of the window when the screen scale is not 100%
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
