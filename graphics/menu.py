"""
configuration and results screens drawn with pygame (same window of the simulation)

the configuration screen is generated from a schema of sections and fields (see config.py)
"""
import math
import time

import numpy as np
import pygame

from graphics import style
from graphics.style import (BG, PANEL, SIDEBAR, SIDEBAR_HI, SIDEBAR_TXT, ACCENT, ACCENT_DARK, ACCENT_SOFT, ACCENT_TXT,
                            TEXT, MUTED, BORDER, GRID, ERROR, OK, text, fit)

class Theme:
    def __init__(self, size):
        w, h = size
        s = max(0.72, min(1.8, min(h / 820, w / 1300)))
        self.s = s
        self.font = style.font(16 * s)
        self.bold = style.font(16 * s, bold=True)
        self.small = style.font(13 * s)
        self.title = style.font(26 * s, bold=True)
        self.subtitle = style.font(19 * s, bold=True)
        self.mono = style.font(15 * s, mono=True)
        self.row_h = int(40 * s)
        self.pad = int(14 * s)          # inside the cards
        self.gap = int(18 * s)          # around and between the cards
        self.radius = max(4, int(7 * s))

# --- widgets --- #

class Widget:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 0, 0)

    def handle(self, event, screen):
        return False

    def draw(self, surface, theme):
        pass

class Button(Widget):
    def __init__(self, label, callback, primary=False, enabled=True):
        super().__init__()
        self.label = label
        self.callback = callback
        self.primary = primary
        self.enabled = enabled

    def handle(self, event, screen):
        if self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.callback()
            return True
        return False

    def draw(self, surface, theme):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        if self.primary:
            color = (ACCENT_DARK if hover else ACCENT) if self.enabled else BORDER
            style.rounded_rect(surface, self.rect, color, theme.radius)
            text(surface, theme.bold, self.label, self.rect.center, ACCENT_TXT, "center")
        else:
            style.rounded_rect(surface, self.rect, (240, 242, 246) if hover else PANEL, theme.radius, BORDER, 1)
            text(surface, theme.font, self.label, self.rect.center, TEXT if self.enabled else MUTED, "center")

class TextInput(Widget):
    """
    text box: click to edit, Enter / Tab / click outside commits, Esc cancels
    """
    def __init__(self, get, set, allowed=None):
        super().__init__()
        self.get = get
        self.set = set
        self.allowed = allowed or (lambda ch: ch.isprintable())
        self.editing = False
        self.fresh = False
        self.error = False
        self.text = self.format(get())

    def format(self, value):
        return str(value)

    def parse(self, value):
        return value

    def refresh(self):
        if not self.editing:
            self.text = self.format(self.get())

    def begin(self):
        self.editing = True
        self.fresh = True
        self.error = False
        self.text = self.format(self.get())

    def commit(self):
        try:
            self.set(self.parse(self.text.strip()))
            self.error = False
        except (ValueError, TypeError):
            self.error = True
        self.editing = False
        self.text = self.format(self.get())

    def cancel(self):
        self.editing = False
        self.text = self.format(self.get())

    def handle(self, event, screen):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            screen.set_focus(self)
            return True
        if event.type == pygame.KEYDOWN and screen.focus is self:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                screen.set_focus(None)
            elif event.key == pygame.K_TAB:
                screen.focus_next(self, -1 if event.mod & pygame.KMOD_SHIFT else 1)
            elif event.key == pygame.K_ESCAPE:
                self.cancel()
                screen.focus = None
            elif event.key == pygame.K_BACKSPACE:
                self.text = "" if self.fresh else self.text[:-1]
                self.fresh = False
            elif event.unicode and self.allowed(event.unicode):
                self.text = event.unicode if self.fresh else self.text + event.unicode
                self.fresh = False
            return True
        return False

    def draw(self, surface, theme):
        color = ERROR if self.error else (ACCENT if self.editing else BORDER)
        style.rounded_rect(surface, self.rect, PANEL, theme.radius, color, 2 if self.editing or self.error else 1)
        inner = self.rect.inflate(-2 * theme.pad // 2, 0)
        value = fit(theme.mono, self.text, inner.width - 6)
        if self.editing and self.fresh:
            sel = theme.mono.size(value)
            pygame.draw.rect(surface, ACCENT_SOFT, (inner.x, self.rect.centery - sel[1] // 2, sel[0], sel[1]))
        r = text(surface, theme.mono, value, (inner.x, self.rect.centery), TEXT, "midleft")
        if self.editing and int(time.time() * 2) % 2 == 0:
            pygame.draw.line(surface, TEXT, (r.right + 1, r.top + 2), (r.right + 1, r.bottom - 2), 1)

class NumberInput(TextInput):
    def __init__(self, get, set, kind="float"):
        self.kind = kind
        super().__init__(get, set, allowed=lambda ch: ch in "0123456789.-+eE")

    def format(self, value):
        return str(int(value)) if self.kind == "int" else f"{value:g}"

    def parse(self, value):
        return int(round(float(value))) if self.kind == "int" else float(value)

class Choice(Widget):
    """
    selector: click on the left half goes to the previous option, on the right half to the next one
    """
    def __init__(self, options, get, set):
        super().__init__()
        self.options = options
        self.get = get
        self.set = set

    def _move(self, step, screen):
        values = [o[0] for o in self.options]
        i = values.index(self.get()) if self.get() in values else 0
        self.set(values[(i + step) % len(values)])
        screen.changed()

    def handle(self, event, screen):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self._move(-1 if event.pos[0] < self.rect.centerx - self.rect.width // 4 else 1, screen)
            return True
        return False

    def draw(self, surface, theme):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        style.rounded_rect(surface, self.rect, (244, 247, 252) if hover else PANEL, theme.radius, BORDER, 1)
        label = dict(self.options).get(self.get(), str(self.get()))
        arrow_w = theme.font.size("<")[0] + theme.pad
        text(surface, theme.bold, "<", (self.rect.x + theme.pad // 2, self.rect.centery), ACCENT, "midleft")
        text(surface, theme.bold, ">", (self.rect.right - theme.pad // 2, self.rect.centery), ACCENT, "midright")
        text(surface, theme.font, fit(theme.font, label, self.rect.width - 2 * arrow_w), self.rect.center, TEXT, "center")

class Toggle(Widget):
    def __init__(self, get, set):
        super().__init__()
        self.get = get
        self.set = set

    def handle(self, event, screen):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.set(not self.get())
            screen.changed()
            return True
        return False

    def draw(self, surface, theme):
        on = self.get()
        h = int(self.rect.height * 0.7)
        w = int(h * 1.9)
        track = pygame.Rect(self.rect.x, self.rect.centery - h // 2, w, h)
        style.rounded_rect(surface, track, ACCENT if on else BORDER, h // 2)
        knob_x = track.right - h // 2 if on else track.x + h // 2
        style.circle(surface, PANEL, (knob_x, track.centery), h // 2 - max(2, h // 8))
        text(surface, theme.font, "on" if on else "off", (track.right + theme.pad, self.rect.centery), MUTED, "midleft")

# --- screens --- #

class Screen:
    """
    base of the screens: focus of the text inputs and the event loop
    """
    def __init__(self):
        self.focus = None
        self.action = None
        self.widgets = []
        self.theme = None
        self.size = None
        self.dirty = True

    def set_focus(self, widget):
        if self.focus is widget:
            return
        if self.focus is not None:
            self.focus.commit()
            self.changed()
        self.focus = widget
        if widget is not None:
            widget.begin()

    def focus_next(self, widget, step):
        inputs = [w for w in self.widgets if isinstance(w, TextInput)]
        i = inputs.index(widget) if widget in inputs else -1
        self.set_focus(inputs[(i + step) % len(inputs)] if inputs else None)

    def changed(self):
        # a value changed: rebuild the layout (the visibility of the fields can depend on it)
        self.dirty = True

    def build(self, surface):
        raise NotImplementedError

    def draw(self, surface):
        raise NotImplementedError

    def on_event(self, event):
        return False

    def loop(self):
        clock = pygame.time.Clock()
        pygame.key.set_repeat(400, 35)
        pygame.event.clear()
        while self.action is None:
            surface = pygame.display.get_surface()
            if surface.get_size() != self.size:
                self.size = surface.get_size()
                self.theme = Theme(self.size)
                self.dirty = True
            if self.dirty:
                self.dirty = False
                self.build(surface)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.action = "quit"
                    break
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.focus is not None \
                        and not self.focus.rect.collidepoint(event.pos):
                    self.set_focus(None)
                if self.on_event(event):
                    continue
                for widget in list(self.widgets):
                    if widget.handle(event, self):
                        break

            self.draw(surface)
            pygame.display.flip()
            clock.tick(60)
        pygame.key.set_repeat()
        return self.action

class ConfigScreen(Screen):
    """
    one page for each section of the schema (menu on the left), the fields are edited in place
    returns "play" or "quit"; the configuration dict is changed in place
    """
    def __init__(self, cfg, schema, coerce, defaults, title="Line Follower Simulator", subtitle=None, message=None, check=None):
        super().__init__()
        self.check = check or (lambda cfg: [])
        self.cfg = cfg
        self.schema = schema
        self.coerce = coerce
        self.defaults = defaults
        self.title = title
        self.subtitle = subtitle or (lambda cfg: "")
        self.message = message
        self.section = schema[0].key
        self.scroll = 0
        self.rows = []

    def sections(self):
        return [s for s in self.schema if s.visible(self.cfg)]

    def _binding(self, section, field, index=None):
        values = self.cfg[section.key]

        def get():
            return values[field.key][index] if index is not None else values[field.key]

        def set(value):
            if index is not None:
                vector = list(values[field.key])
                vector[index] = value
                value = vector
            values[field.key] = self.coerce(field, value)
        return get, set

    def _reset_section(self):
        self.set_focus(None)
        self.cfg[self.section] = self.defaults()[self.section]
        self.changed()

    def _reset_all(self):
        self.set_focus(None)
        self.cfg.clear()
        self.cfg.update(self.defaults())
        self.changed()

    def _play(self):
        self.set_focus(None)
        errors = self.check(self.cfg)
        if errors:
            self.message = ("cannot play: " + "; ".join(errors), ERROR)
            return
        self.action = "play"

    def _quit(self):
        self.action = "quit"

    def _select(self, key):
        def select():
            self.set_focus(None)
            self.section = key
            self.scroll = 0
            self.changed()
        return select

    def build(self, surface):
        t = self.theme
        w, h = surface.get_size()
        focus_key = getattr(self.focus, "key", None)
        self.focus = None
        self.widgets = []

        sections = self.sections()
        if self.section not in [s.key for s in sections]:
            self.section = sections[0].key

        self.header = pygame.Rect(0, 0, w, int(78 * t.s))
        self.footer = pygame.Rect(0, h - int(74 * t.s), w, int(74 * t.s))
        self.sidebar = pygame.Rect(0, self.header.bottom, max(int(210 * t.s), w // 7), self.footer.top - self.header.bottom)
        self.card_rect = pygame.Rect(self.sidebar.right + t.gap, self.header.bottom + t.gap,
                                     w - self.sidebar.right - 2 * t.gap, self.footer.top - self.header.bottom - 2 * t.gap)
        self.panel = self.card_rect.inflate(-2 * t.pad, -2 * t.pad)

        # menu of the sections
        self.menu = []
        y = self.sidebar.y + t.gap
        for s in sections:
            rect = pygame.Rect(self.sidebar.x, y, self.sidebar.width, int(t.row_h * 1.15))
            button = Button(s.title, self._select(s.key))
            button.rect = rect
            self.menu.append((s, button))
            self.widgets.append(button)
            y += rect.height

        # fields of the current section
        section = next(s for s in sections if s.key == self.section)
        label_w = min(int(self.panel.width * 0.42), int(300 * t.s))
        field_w = min(self.panel.width - label_w - 2 * t.pad, int(440 * t.s))
        row_w = label_w + field_w + t.pad
        self.content_top = self.panel.y + int(t.row_h * 1.9)
        y = self.content_top - self.scroll
        self.rows = []
        for field in section.fields:
            if not field.visible(self.cfg):
                continue
            row = pygame.Rect(self.panel.x, y, row_w, t.row_h)
            box = pygame.Rect(self.panel.x + label_w, y + int(t.row_h * 0.12), field_w, int(t.row_h * 0.76))
            widgets = []
            if field.kind in ("int", "float"):
                widgets.append(NumberInput(*self._binding(section, field), kind=field.kind))
                widgets[-1].rect = box
            elif field.kind == "bool":
                widgets.append(Toggle(*self._binding(section, field)))
                widgets[-1].rect = box
            elif field.kind == "choice":
                widgets.append(Choice(field.options, *self._binding(section, field)))
                widgets[-1].rect = box
            elif field.kind == "vector":
                gap = int(8 * t.s)
                cell = (box.width - gap * (field.size - 1)) // field.size
                for i in range(field.size):
                    widget = NumberInput(*self._binding(section, field, i))
                    widget.rect = pygame.Rect(box.x + i * (cell + gap), box.y, cell, box.height)
                    widgets.append(widget)
            for i, widget in enumerate(widgets):
                widget.key = (field.key, i)
            self.rows.append((field, row, widgets))
            self.widgets.extend(widgets)
            y += t.row_h

        self.clip = pygame.Rect(self.card_rect.x + 1, self.content_top, self.card_rect.width - 2, self.panel.bottom - self.content_top)

        # scroll limits
        content_h = len(self.rows) * t.row_h
        visible_h = self.panel.bottom - self.content_top
        self.max_scroll = max(0, content_h - visible_h)
        if self.scroll > self.max_scroll:
            self.scroll = self.max_scroll
            self.dirty = True

        # footer buttons
        bw, bh = int(150 * t.s), int(44 * t.s)
        y = self.footer.centery - bh // 2
        x = w - t.gap
        self.buttons = []
        for label, callback, primary in (("Play  >", self._play, True), ("Quit", self._quit, False),
                                         ("Reset all", self._reset_all, False), ("Reset page", self._reset_section, False)):
            button = Button(label, callback, primary)
            button.rect = pygame.Rect(x - bw, y, bw, bh)
            x -= bw + int(10 * t.s)
            self.buttons.append(button)
            self.widgets.append(button)

        # keep the focus of the text input that was being edited
        if focus_key is not None:
            for widget in self.widgets:
                if getattr(widget, "key", None) == focus_key and isinstance(widget, TextInput):
                    self.focus = widget
                    widget.begin()

    def on_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if self.panel.collidepoint(pygame.mouse.get_pos()) and self.max_scroll > 0:
                self.scroll = min(self.max_scroll, max(0, self.scroll - event.y * self.theme.row_h))
                self.set_focus(None)
                self.changed()
                return True
        if event.type == pygame.KEYDOWN and self.focus is None:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._play()
                return True
            if event.key == pygame.K_ESCAPE:
                self._quit()
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                keys = [s.key for s in self.sections()]
                step = -1 if event.key in (pygame.K_UP, pygame.K_PAGEUP) else 1
                self._select(keys[(keys.index(self.section) + step) % len(keys)])()
                return True
        # the fields outside of the visible area of the panel do not receive clicks
        if event.type == pygame.MOUSEBUTTONDOWN and not self.clip.collidepoint(event.pos):
            for _, button in self.menu:
                if button.handle(event, self):
                    return True
            for button in self.buttons:
                if button.handle(event, self):
                    return True
            return True
        return False

    def draw(self, surface):
        t = self.theme
        surface.fill(BG)

        # header
        pygame.draw.rect(surface, PANEL, self.header)
        pygame.draw.line(surface, BORDER, self.header.bottomleft, self.header.bottomright)
        text(surface, t.title, self.title, (t.gap, self.header.centery), TEXT, "midleft")
        text(surface, t.font, self.subtitle(self.cfg), (self.header.right - t.gap, self.header.centery), MUTED, "midright")

        # menu
        pygame.draw.rect(surface, SIDEBAR, self.sidebar)
        mouse = pygame.mouse.get_pos()
        for s, button in self.menu:
            active = s.key == self.section
            if active or button.rect.collidepoint(mouse):
                pygame.draw.rect(surface, SIDEBAR_HI, button.rect)
            if active:
                bar = max(3, int(4 * t.s))
                style.rounded_rect(surface, (button.rect.x, button.rect.y + bar, bar, button.rect.height - 2 * bar), ACCENT, bar // 2)
            text(surface, t.bold if active else t.font, s.title, (button.rect.x + t.gap, button.rect.centery),
                 (255, 255, 255) if active else SIDEBAR_TXT, "midleft")

        # panel
        style.card(surface, self.card_rect, t.radius * 2)
        section = next(s for s in self.schema if s.key == self.section)
        text(surface, t.subtitle, section.title, (self.panel.x, self.panel.y), TEXT)
        text(surface, t.small, section.help, (self.panel.x, self.panel.y + int(t.row_h * 0.85)), MUTED)

        hovered = None
        clip = self.clip
        surface.set_clip(clip)
        for i, (field, row, widgets) in enumerate(self.rows):
            if row.collidepoint(mouse) and clip.collidepoint(mouse):
                hovered = field
                style.rounded_rect(surface, row, (244, 247, 252), t.radius)
            elif i % 2:
                style.rounded_rect(surface, row, (250, 251, 253), t.radius)
            text(surface, t.font, fit(t.font, field.label, widgets[0].rect.x - row.x - t.pad), (row.x + int(10 * t.s), row.centery), TEXT, "midleft")
            for widget in widgets:
                widget.draw(surface, t)
        surface.set_clip(None)

        # scroll bar
        if self.max_scroll > 0:
            total = len(self.rows) * t.row_h
            bar_h = max(20, clip.height * clip.height // total)
            bar_y = clip.y + (clip.height - bar_h) * self.scroll // self.max_scroll
            style.rounded_rect(surface, (self.card_rect.right - int(8 * t.s), bar_y, 4, bar_h), BORDER, 2)

        # footer
        pygame.draw.rect(surface, PANEL, self.footer)
        pygame.draw.line(surface, BORDER, self.footer.topleft, self.footer.topright)
        left = self.buttons[-1].rect.x - t.gap
        if hovered is not None and hovered.help:
            info, color = hovered.help, MUTED
        elif self.message:
            info, color = self.message if isinstance(self.message, tuple) else (self.message, TEXT)
        else:
            info, color = "Enter: play  |  Esc: quit  |  Up/Down: pages  |  Tab: next field", MUTED
        text(surface, t.small, fit(t.small, info, left - t.gap), (t.gap, self.footer.centery), color, "midleft")
        for button in self.buttons:
            button.draw(surface, t)

class ResultsScreen(Screen):
    """
    summary of the run, trajectory and lateral error; returns "again", "config" or "quit"
    save(name) must save the run and return the path
    """
    REASONS = {"finished": "track completed", "esc": "stopped (Esc)", "quit": "window closed", "time": "max time reached", None: "stopped"}

    def __init__(self, result, default_name, save):
        super().__init__()
        self.result = result
        self.name = default_name
        self.save_fn = save
        self.message = None
        self.saved_path = None
        rows = result.logger.rows
        self.t = np.array([r["t"] for r in rows])
        self.x = np.array([r["x"] for r in rows])
        self.y = np.array([r["y"] for r in rows])
        self.e = np.array([r["lateral_error"] for r in rows]) * 100

    def _save(self):
        self.set_focus(None)
        try:
            self.saved_path = self.save_fn(self.name)
            self.message = (f"saved: {self.saved_path}", OK)
        except OSError as error:
            self.message = (f"error: {error}", ERROR)

    def _set_name(self, value):
        value = "".join(ch for ch in value if ch.isalnum() or ch in "-_.").strip(".")
        if not value:
            raise ValueError("empty name")
        self.name = value

    def _action(self, action):
        def run():
            self.set_focus(None)
            self.action = action
        return run

    def build(self, surface):
        t = self.theme
        w, h = surface.get_size()
        self.widgets = []
        self.focus = None
        self.header = pygame.Rect(0, 0, w, int(78 * t.s))
        self.footer = pygame.Rect(0, h - int(74 * t.s), w, int(74 * t.s))
        # outer rectangles of the cards, with the same gap around and between them
        g = t.gap
        body = pygame.Rect(g, self.header.bottom + g, w - 2 * g, self.footer.top - self.header.bottom - 2 * g)
        self.metrics_rect = pygame.Rect(body.x, body.y, min(int(420 * t.s), body.width // 3), body.height)
        right = pygame.Rect(self.metrics_rect.right + g, body.y, body.right - self.metrics_rect.right - g, body.height)
        self.path_rect = pygame.Rect(right.x, right.y, right.width, int((right.height - g) * 0.6))
        self.error_rect = pygame.Rect(right.x, self.path_rect.bottom + g, right.width, right.bottom - self.path_rect.bottom - g)

        bh = int(44 * t.s)
        y = self.footer.centery - bh // 2
        name = TextInput(lambda: self.name, self._set_name, allowed=lambda ch: ch.isalnum() or ch in "-_.")
        name.rect = pygame.Rect(t.gap + t.font.size("File name")[0] + t.pad, y, int(320 * t.s), bh)
        save = Button("Save", self._save, primary=True)
        save.rect = pygame.Rect(name.rect.right + int(10 * t.s), y, int(120 * t.s), bh)
        self.name_input = name
        self.widgets = [name, save]

        bw = int(170 * t.s)
        x = w - t.gap
        for label, action, primary in (("Quit", "quit", False), ("Configuration", "config", False), ("Run again", "again", False)):
            button = Button(label, self._action(action), primary)
            button.rect = pygame.Rect(x - bw, y, bw, bh)
            x -= bw + int(10 * t.s)
            self.widgets.append(button)

    def on_event(self, event):
        if event.type == pygame.KEYDOWN and self.focus is None:
            if event.key == pygame.K_ESCAPE:
                self._action("config")()
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._action("again")()
                return True
        return False

    def _card(self, surface, rect, title):
        # draws the card (outer rectangle) and returns the area below the title
        t = self.theme
        style.card(surface, rect, t.radius * 2)
        inner = rect.inflate(-2 * t.pad, -2 * t.pad)
        text(surface, t.bold, title, (inner.x, inner.y), TEXT)
        top = int(t.row_h * 0.95)
        return pygame.Rect(inner.x, inner.y + top, inner.width, inner.height - top)

    def _metrics(self):
        m = self.result.metrics
        if not m:
            return [("Steps", "0")]
        rows = [
            ("Result", self.REASONS.get(m["stop_reason"], m["stop_reason"])),
            ("Time", f"{m['time_s']:.2f} s"),
            ("Coverage", f"{m['coverage_%']:.1f} %"),
            ("Lateral error RMS", f"{m['lat_rms_cm']:.3f} cm"),
            ("Lateral error max", f"{m['lat_max_cm']:.2f} cm"),
            ("Mean speed", f"{m['speed_mean_m_s']:.2f} m/s"),
            ("Solver mean", f"{m['solve_mean_ms']:.2f} ms"),
            ("Solver max", f"{m['solve_max_ms']:.2f} ms"),
        ]
        if m["qp_mean"] > 0:
            rows += [("QPs per step", f"{m['qp_mean']:.2f}"), ("rho mismatch", f"{m['rho_err_mean']:.4f}")]
        rows.append(("Steps", f"{len(self.t)}"))
        return rows

    def _cached(self, key, rect, draw):
        # static images of the plots are rendered once (supersampled) for each size
        cache = self.__dict__.setdefault("_images", {})
        key = (key, tuple(rect))
        if key not in cache:
            cache[key] = style.smooth(draw, rect.size, 3)
        return cache[key]

    def _draw_path(self, surface, rect):
        t = self.theme
        tx, ty = self.result.track
        xs = np.concatenate((tx, self.x)) if len(self.x) else tx
        ys = np.concatenate((ty, self.y)) if len(self.y) else ty
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        scale = min(rect.width / max(x1 - x0, 1e-6), rect.height / max(y1 - y0, 1e-6)) * 0.94
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

        def draw(big, k):
            # the track coordinates have y pointing down (screen), as in the simulator
            to_px = lambda x, y: np.column_stack((k * (rect.width / 2 + (x - cx) * scale), k * (rect.height / 2 + (y - cy) * scale)))
            step = max(1, len(tx) // 4000)
            pygame.draw.lines(big, style.TRACK_SOFT, True, to_px(tx[::step], ty[::step]).tolist(), int(7 * t.s * k))
            if len(self.x) > 1:
                step = max(1, len(self.x) // 4000)
                pts = to_px(self.x[::step], self.y[::step])
                pygame.draw.lines(big, style.PREDICTION, False, pts.tolist(), max(k, int(2.5 * t.s * k)))
                for p, color in ((pts[0], OK), (pts[-1], ERROR)):
                    style.circle(big, PANEL, p, 8 * t.s * k)
                    style.circle(big, color, p, 6 * t.s * k)
        surface.blit(self._cached("path", rect, draw), rect)

    def _draw_error(self, surface, rect):
        t = self.theme
        if len(self.t) < 2:
            return
        plot = pygame.Rect(rect.x + int(54 * t.s), rect.y + int(4 * t.s), rect.width - int(60 * t.s), rect.height - int(30 * t.s))
        lim = max(0.5, float(np.max(np.abs(self.e))) * 1.1)
        for v in (-lim, -lim / 2, 0, lim / 2, lim):
            y = plot.centery - v / lim * plot.height / 2
            pygame.draw.line(surface, BORDER if v == 0 else GRID, (plot.x, y), (plot.right, y), 1)
            text(surface, t.small, f"{v:.2g}", (plot.x - 8, y), MUTED, "midright")
        t_end = max(self.t[-1], 1e-6)
        for i in range(6):
            x = plot.x + plot.width * i / 5
            text(surface, t.small, f"{t_end * i / 5:.3g}", (x, plot.bottom + 6), MUTED, "midtop")
        text(surface, t.small, "lateral error [cm] x time [s]", (plot.right, rect.y - int(t.row_h * 0.9)), MUTED, "topright")

        def draw(big, k):
            step = max(1, len(self.t) // (2 * plot.width))
            xs = k * self.t[::step] / t_end * plot.width
            ys = k * (plot.height / 2 - np.clip(self.e[::step], -lim, lim) / lim * plot.height / 2)
            pygame.draw.lines(big, style.PREDICTION, False, np.column_stack((xs, ys)).tolist(), max(k, int(2 * t.s * k)))
        surface.blit(self._cached("error", plot, draw), plot)

    def draw(self, surface):
        t = self.theme
        surface.fill(BG)
        pygame.draw.rect(surface, PANEL, self.header)
        pygame.draw.line(surface, BORDER, self.header.bottomleft, self.header.bottomright)
        reason = self.REASONS.get(self.result.stop_reason, self.result.stop_reason)
        text(surface, t.title, f"Run finished: {reason}", (t.gap, self.header.centery), TEXT, "midleft")
        text(surface, t.font, self.result.controller, (self.header.right - t.gap, self.header.centery), MUTED, "midright")

        inner = self._card(surface, self.metrics_rect, "Summary")
        y = inner.y
        for label, value in self._metrics():
            text(surface, t.font, label, (inner.x, y), MUTED)
            text(surface, t.bold, value, (inner.right, y), TEXT, "topright")
            y += int(t.row_h * 0.85)

        self._draw_path(surface, self._card(surface, self.path_rect, "Trajectory"))
        legend = self.path_rect.right - t.pad
        for label, color in (("end", ERROR), ("start", OK), ("car", style.PREDICTION), ("track", style.TRACK_SOFT)):
            r = text(surface, t.small, label, (legend, self.path_rect.y + t.pad + 2), MUTED, "topright")
            style.circle(surface, color, (r.x - 9 * t.s, r.centery), 5 * t.s)
            legend = r.x - int(26 * t.s)
        self._draw_error(surface, self._card(surface, self.error_rect, "Lateral error"))

        pygame.draw.rect(surface, PANEL, self.footer)
        pygame.draw.line(surface, BORDER, self.footer.topleft, self.footer.topright)
        text(surface, t.font, "File name", (t.gap, self.footer.centery), TEXT, "midleft")
        for widget in self.widgets:
            widget.draw(surface, t)
        if self.message:
            msg, color = self.message
            right = self.widgets[-1].rect.x - t.pad
            left = self.widgets[1].rect.right + t.pad
            text(surface, t.small, fit(t.small, msg, right - left), (left, self.footer.centery), color, "midleft")

def open_window(screen_size, sizes):
    """
    opens (or resizes) the window; sizes = {screen_size: (w, h) or None for full screen}
    """
    pygame.init()
    size = sizes.get(screen_size)
    if size is None:
        return pygame.display.set_mode(pygame.display.get_desktop_sizes()[0], pygame.FULLSCREEN)
    return pygame.display.set_mode(size)
