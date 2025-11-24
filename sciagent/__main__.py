"""Allow running sciagent as a module: python -m sciagent"""

from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())

