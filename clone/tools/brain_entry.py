"""PyInstaller entry point for Brain. This is inspired by Jim Kitchen's Brain.

Same as `python -m brain`; a separate file because PyInstaller wants a script to start from.
"""

from brain.app import main
from brain.data.lifecycle import finish

if __name__ == "__main__":
    finish(main())      # flush the log and end the process at once: nothing may stay behind
