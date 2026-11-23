#!/usr/bin/env python3
"""Check that a release tag matches project.version and print the image version.

Tags are v{version} for releases or v{version}-rcN for test images.
"""

import re
import sys
import tomllib
from pathlib import Path

STABLE_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_release_version.py <release-tag>", file=sys.stderr)
        return 2

    tag = sys.argv[1]
    with PYPROJECT.open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]

    if not STABLE_VERSION.fullmatch(version) or not re.fullmatch(rf"v{re.escape(version)}(-rc[1-9][0-9]*)?", tag):
        print(f"Release tag {tag} does not match project.version {version}", file=sys.stderr)
        return 1

    print(tag.removeprefix("v"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
