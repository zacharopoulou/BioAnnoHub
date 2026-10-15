"""Same as ``bioannohub download-benchmarks`` (kept for convenience): see benchmarks/BENCHMARKS.md."""

import sys

from bio_annotation.cli import main

if __name__ == "__main__":
    sys.exit(main(["download-benchmarks", *sys.argv[1:]]))
