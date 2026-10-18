"""CI: the installed packages satisfy the requirements in manifest.json (the lock file must not drift from it)."""

import json
import sys
from importlib.metadata import PackageNotFoundError, version

from packaging.requirements import Requirement

manifest = json.load(open("custom_components/friedafetch/manifest.json", encoding="utf-8"))
problems = []
for line in manifest["requirements"]:
    req = Requirement(line)
    try:
        installed = version(req.name)
    except PackageNotFoundError:
        problems.append(f"{req.name} is not installed (requirements/manifest.txt is out of date)")
        continue
    if not req.specifier.contains(installed, prereleases=True):
        problems.append(f"{req.name} {installed} does not satisfy {req.specifier}")
print("\n".join(problems) or f"{len(manifest['requirements'])} manifest requirements satisfied")
sys.exit(1 if problems else 0)
