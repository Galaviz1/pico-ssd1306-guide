"""Locate a MicroPython UF2 for the RP2040."""
import glob
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD = "https://micropython.org/download/RPI_PICO/"


def find_uf2(argv_index=1):
    """Path given on the command line, else the newest RPI_PICO-*.uf2 in the repo root."""
    if len(sys.argv) > argv_index and not sys.argv[argv_index].startswith("-"):
        path = sys.argv[argv_index]
        if not os.path.isfile(path):
            raise SystemExit("No such file: %s" % path)
        return path

    hits = sorted(glob.glob(os.path.join(REPO_ROOT, "RPI_PICO-*.uf2")))
    if not hits:
        raise SystemExit(
            "No RPI_PICO-*.uf2 found in %s\n"
            "Firmware is not committed to this repo. Download one from:\n  %s\n"
            "then drop it in the repo root, or pass its path as an argument."
            % (REPO_ROOT, DOWNLOAD)
        )
    return hits[-1]
