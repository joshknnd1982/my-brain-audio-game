"""PyInstaller entry point for Brain. This is inspired by Jim Kitchen's Brain.

Same as `python -m brain`; a separate file because PyInstaller wants a script to start from.
"""
import sys

from brain.app import main

if __name__ == "__main__":
    sys.exit(main())
