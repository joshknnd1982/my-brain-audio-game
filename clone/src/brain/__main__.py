"""Run Brain: python -m brain (from clone/src). This is inspired by Jim Kitchen's Brain."""
from brain.app import main
from brain.data.lifecycle import finish

if __name__ == "__main__":
    finish(main())
