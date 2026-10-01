"""
python -m track_editor [file.tfg]
"""
import sys

from .app import main

main(sys.argv[1] if len(sys.argv) > 1 else None)
