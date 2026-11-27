import os
import sys

from akt.cli import main

if __name__ == "__main__":
    try:
        rc = main()
        sys.stdout.flush()
    except BrokenPipeError:
        # The reader closed the pipe early (`akt learn list | head`). Point
        # stdout at devnull so the interpreter's exit flush does not raise again.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        rc = 1
    raise SystemExit(rc)
