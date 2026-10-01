"""
Line Follower Simulator

configuration screen -> Play -> simulation -> results (save the run) -> configuration ...
all the settings are on the configuration screen (the last ones are kept in last_config.json)
"""
import glob
import os
import shutil
import subprocess
import sys
import time

import pygame

import runner
import config as C
from graphics.graphics_elements import FULL, MEDIUM, SMALL
from graphics.menu import ConfigScreen, ResultsScreen, open_window

WINDOW_SIZES = {FULL: None, MEDIUM: (1400, 750), SMALL: (800, 600)}
RUNS_FOLDER = "runs"

def save_run(result, name):
    # runs/<name>.csv (+ _track.csv and _meta.json), without overwriting an old run
    path = os.path.join(RUNS_FOLDER, f"{name}.csv")
    i = 2
    while os.path.exists(path):
        path = os.path.join(RUNS_FOLDER, f"{name}_{i}.csv")
        i += 1
    return result.logger.save(path)

# time when the track editor was opened (the track saved after it is selected when the user comes back)
editor_opened = None

def _fullscreen():
    surface = pygame.display.get_surface()
    return surface is not None and surface.get_flags() & pygame.FULLSCREEN

def _use_track(cfg, name):
    cfg["track"]["file"] = name
    cfg["track"]["track_type"] = C.TRACK_FILE

def open_editor(cfg):
    """
    opens the track editor (another window) with the selected track file
    """
    global editor_opened
    path = C.track_path(cfg["track"]["file"])
    args = [sys.executable, "-m", "track_editor"] + ([path] if path and os.path.exists(path) else [])
    subprocess.Popen(args, cwd=C.ROOT)
    editor_opened = time.time()
    if _fullscreen():
        # in full screen the editor would stay behind the simulator
        pygame.display.iconify()
    return "track editor opened: save the track in tracks/ and come back (it is selected here)"

def on_focus(cfg):
    """
    back to the simulator: selects the track saved in the editor after it was opened
    """
    global editor_opened
    if editor_opened is None:
        return None
    saved = [(os.path.getmtime(p), p) for p in glob.glob(os.path.join(C.TRACKS_FOLDER, "*.tfg"))]
    saved = [item for item in saved if item[0] > editor_opened]
    if not saved:
        return None
    mtime, path = max(saved)
    editor_opened = mtime
    _use_track(cfg, os.path.basename(path))
    return f"using the track {os.path.basename(path)} (saved in the editor)"

def browse_track(cfg):
    """
    native dialog to choose a .tfg (it runs in another process: tkinter and pygame do not share the window loop)
    """
    code = ("import sys, tkinter as tk; from tkinter import filedialog; r = tk.Tk(); r.withdraw(); "
            "r.attributes('-topmost', True); "
            "print(filedialog.askopenfilename(parent=r, title='Choose a track', initialdir=sys.argv[1], "
            "filetypes=[('Track', '*.tfg'), ('All files', '*.*')]) or '')")
    surface = pygame.display.get_surface()
    size, full = surface.get_size(), _fullscreen()
    if full:
        pygame.display.iconify()
    out = subprocess.run([sys.executable, "-c", code, C.TRACKS_FOLDER], capture_output=True, text=True)
    if full:
        pygame.display.set_mode(size, pygame.FULLSCREEN)
    path = out.stdout.strip()
    if not path:
        return None

    # the tracks used by the simulator live in the tracks/ folder
    os.makedirs(C.TRACKS_FOLDER, exist_ok=True)
    name = os.path.basename(path)
    dest = os.path.join(C.TRACKS_FOLDER, name)
    copied = False
    if not (os.path.exists(dest) and os.path.samefile(path, dest)):
        base, ext = os.path.splitext(name)
        i = 2
        while os.path.exists(dest):
            name = f"{base}_{i}{ext}"
            dest = os.path.join(C.TRACKS_FOLDER, name)
            i += 1
        shutil.copyfile(path, dest)
        copied = True
    error = C.track_error(name)
    if error:
        return (f"could not use {name}: {error}", (205, 45, 45))
    _use_track(cfg, name)
    return f"using the track {name}" + (" (copied to tracks/)" if copied else "")

def default_name(cfg):
    ctrl = "gpc" if cfg["controller"]["type"] == "gpc" else f"qlpv_{cfg['qlpv']['scheduling']}"
    return f"{ctrl}_{time.strftime('%Y%m%d_%H%M%S')}"

def main():
    cfg = C.load()
    open_window(cfg["simulation"]["screen_size"], WINDOW_SIZES)
    message = None

    while True:
        screen = ConfigScreen(cfg, C.SCHEMA, C.coerce, C.defaults, subtitle=C.describe, message=message, check=C.check,
                              actions={"open_editor": open_editor, "browse_track": browse_track, "on_focus": on_focus})
        if screen.loop() == "quit":
            break
        C.save(cfg)

        action = "again"
        while action == "again":
            result = runner.run(cfg)
            action = ResultsScreen(result, default_name(cfg), lambda name, r=result: save_run(r, name)).loop()

        if action == "quit":
            break
        message = f"last run: {result.controller} | lateral error RMS {result.metrics.get('lat_rms_cm', float('nan')):.3f} cm"

    C.save(cfg)
    pygame.quit()

if __name__ == "__main__":
    main()
