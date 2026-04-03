import sys
import os
import importlib
import tkinter as tk
from tkinter import ttk

# Add the track_creator directory to sys.path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'track_creator'))

def main():
    try:
        app_module = importlib.import_module("ui.app")
        app_class = getattr(app_module, "TrajectoryGeneratorApp")

        root = tk.Tk()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Configure size and center the window on screen.
        window_width = 1200
        window_height = 680
        
        # Center on screen.
        root.withdraw()  # Hide temporarily while calculating geometry.
        root.update_idletasks()
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.deiconify()  # Show centered window.

        app_class(root)
        root.mainloop()
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
