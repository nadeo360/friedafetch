#!/bin/sh
# Regenerates the hash-pinned requirement files that CI and the release workflow install with
# "pip install --require-hashes". Needs uv (https://docs.astral.sh/uv/). Run from the repository root after
# changing requirements_dev.txt, a requirements/*.in file or the requirements in manifest.json.
set -e
python3 - <<'PY'
import json
reqs = json.load(open("custom_components/friedafetch/manifest.json"))["requirements"]
head = "# The runtime requirements of manifest.json"
open("requirements/manifest.in", "w").write(f"{head} (CI checks that they install cleanly and match)\n" + "\n".join(reqs) + "\npackaging\n")
open("requirements/sbom.in", "w").write(f"{head} plus the SBOM generator (release workflow)\n" + "\n".join(reqs) + "\ncyclonedx-bom\n")
PY
OPTS="--generate-hashes --python-version 3.14.2 --python-platform x86_64-unknown-linux-gnu --quiet"
for name in lint bandit icons; do
  uv pip compile "requirements/$name.in" $OPTS --custom-compile-command "scripts/lock_requirements.sh" -o "requirements/$name.txt"
done
# the .in files keep the ranges of manifest.json; the exact versions come from requirements_dev.txt, so the manifest
# check, the SBOM and the tests all use the same versions
for name in manifest sbom; do
  uv pip compile "requirements/$name.in" $OPTS --constraint requirements_dev.txt \
    --custom-compile-command "scripts/lock_requirements.sh" -o "requirements/$name.txt"
done
uv pip compile requirements_dev.txt $OPTS --custom-compile-command "scripts/lock_requirements.sh" -o requirements/test.txt
