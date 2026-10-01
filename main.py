"""
Line Follower Simulator

configuration screen -> Play -> simulation -> results (save the run) -> configuration ...
all the settings are on the configuration screen (the last ones are kept in last_config.json)
"""
import os
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

def open_editor(cfg):
    """
    opens the track editor (another window) with the selected track file
    """
    path = C.track_path(cfg["track"]["file"])
    args = [sys.executable, "-m", "track_editor"] + ([path] if path and os.path.exists(path) else [])
    subprocess.Popen(args, cwd=C.ROOT)
    if pygame.display.get_surface() is not None and pygame.display.get_surface().get_flags() & pygame.FULLSCREEN:
        # in full screen the editor would stay behind the simulator
        pygame.display.iconify()
    return "track editor opened: save the track in tracks/ and come back"

def default_name(cfg):
    ctrl = "gpc" if cfg["controller"]["type"] == "gpc" else f"qlpv_{cfg['qlpv']['scheduling']}"
    return f"{ctrl}_{time.strftime('%Y%m%d_%H%M%S')}"

def main():
    cfg = C.load()
    open_window(cfg["simulation"]["screen_size"], WINDOW_SIZES)
    message = None

    while True:
        screen = ConfigScreen(cfg, C.SCHEMA, C.coerce, C.defaults, subtitle=C.describe, message=message, check=C.check,
                              actions={"open_editor": open_editor})
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
