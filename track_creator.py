import sys
import os
import tkinter as tk
from tkinter import ttk

# Adicionar o diretório do track_creator ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'track_creator'))

from ui.app import GeradorTrajetoApp


def main():
    try:
        root = tk.Tk()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Configurar tamanho e centralizar janela no monitor
        window_width = 1200
        window_height = 680
        
        # Centralizar na tela
        root.withdraw()  # Esconder janela temporariamente
        root.update_idletasks()
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.deiconify()  # Mostrar janela centralizada

        GeradorTrajetoApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        print(f"ERRO: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
