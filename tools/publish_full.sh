#!/usr/bin/env bash
# Build, test and push the full image for a release tag, e.g. tools/publish_full.sh v0.2.0
# The slim image is published by .github/workflows/publish.yml. Run `docker login` first.

set -euo pipefail

tag="${1:?usage: tools/publish_full.sh vX.Y.Z}"
repo="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

# Build from a clean checkout of the tag, so local edits and untracked files stay out of the image.
checkout="$(mktemp -d)"
trap 'git -C "$repo" worktree remove --force "$checkout"' EXIT
git -C "$repo" worktree add --detach "$checkout" "$tag"

version="$(python3 "$checkout/tools/validate_release_version.py" "$tag")"
image="biogemt/bioannohub:$version-full"

docker build --build-arg IMAGE=full -t "$image" "$checkout"
docker run --rm --entrypoint python -w /repository "$image" -m pytest -m 'not integration'
docker push "$image"
