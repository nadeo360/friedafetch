#!/usr/bin/env python3
"""Release from dev: version, checks, main, CI, GitHub release, and a check of the built zip.

    scripts/release.py --draft                        # notes skeleton from the commits since the last tag
    scripts/release.py 2.0.17 --notes notes.md --dry-run
    scripts/release.py 2.0.17 --notes notes.md        # the release itself

The same file serves Frieda and Frieda Postfach (the integration is the one real folder in custom_components). Run
it with the Python that has the test requirements (ruff, pytest), from a clean `dev`. It stops at the first problem
and never releases what CI has not passed:

 1. dev is clean and contains everything of origin/main (merged Dependabot pull requests), the tag is new;
 2. the manifest gets the version (one commit "Version X" on dev, if needed);
 3. ruff and the tests run (not with --skip-tests);
 4. main takes dev by fast-forward and is pushed; the remote is checked to have exactly that commit;
 5. every CI run of that commit has to succeed;
 6. the release is created with the notes (German, then English after a line "---");
 7. the zip the release workflow attaches is downloaded: its checksum, its version and every file are compared with
    the tagged source;
 8. back to dev.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

CI_TIMEOUT = 45 * 60  # seconds
ASSET_TIMEOUT = 20 * 60
POLL = 20
OK = {"success", "skipped", "neutral"}


class ReleaseError(Exception):
    pass


def run(*args: str, capture: bool = True, cwd: Path | None = None) -> str:
    """A command whose failure stops the release (with its output); never part of a pipe."""
    print("  $", " ".join(args), flush=True)
    done = subprocess.run(args, cwd=cwd, capture_output=capture, text=True, check=False)  # noqa: S603
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip() if capture else ""
        raise ReleaseError(f"{' '.join(args[:3])} … failed ({done.returncode})" + (f":\n{detail}" if detail else ""))
    return (done.stdout or "").strip() if capture else ""


def gh() -> str:
    path = shutil.which("gh") or "/opt/homebrew/bin/gh"
    if not Path(path).exists():
        raise ReleaseError("GitHub CLI (gh) not found")
    return path


def integration(root: Path) -> tuple[str, dict]:
    """The integration of this repository: the one real (not linked) folder in custom_components."""
    folders = [p for p in (root / "custom_components").iterdir() if p.is_dir() and not p.is_symlink()]
    if len(folders) != 1:
        raise ReleaseError(f"expected one integration in custom_components, found {[p.name for p in folders]}")
    manifest = json.loads((folders[0] / "manifest.json").read_text(encoding="utf-8"))
    return folders[0].name, manifest


def title(manifest: dict, version: str) -> str:
    """The release title: Frieda (iCloud) becomes "Frieda 2.0.17", Frieda Postfach "Frieda Postfach 1.0.24"."""
    return f"{re.sub(r'\s*\(.*\)$', '', manifest['name'])} {version}"


def last_tag() -> str | None:
    tags = run("git", "tag", "--list", "v*", "--sort=-v:refname").splitlines()
    return tags[0] if tags else None


def draft() -> None:
    """A skeleton for the notes: the commits since the last tag, to be rewritten for people."""
    run("git", "fetch", "-q", "origin", "--tags")
    since = last_tag()
    log = run("git", "log", "--no-merges", "--format=- **%s**%n%n%b", f"{since}..dev" if since else "dev")
    print("## Neu / New\n")
    print(re.sub(r"\n{3,}", "\n\n", log).strip())
    print("\n---\n\n- (English summary)")


def check_notes(path: Path) -> None:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ReleaseError(f"{path} is empty")
    if "\n---\n" not in text:
        print("  ! the notes have no line '---' between the German and the English part", flush=True)


def wait_for_ci(sha: str) -> None:
    """Every workflow run of the pushed commit must finish successfully.

    Workflows show up one after the other after a push: all done counts only when the number of runs stayed the same
    over one more look.
    """
    deadline = time.monotonic() + CI_TIMEOUT
    settled = -1
    while True:
        runs = json.loads(
            run(gh(), "run", "list", "--commit", sha, "--json", "databaseId,workflowName,status,conclusion", "-L", "50")
        )
        pending = [r for r in runs if r["status"] != "completed"]
        failed = [r for r in runs if r["status"] == "completed" and r["conclusion"] not in OK]
        if failed:
            names = ", ".join(f"{r['workflowName']} ({r['conclusion']})" for r in failed)
            raise ReleaseError(f"CI failed for {sha[:7]}: {names} – nothing was released")
        if runs and not pending:
            if len(runs) == settled:
                print(f"  CI: {len(runs)} runs passed", flush=True)
                return
            settled = len(runs)
        else:
            settled = -1
        if time.monotonic() > deadline:
            raise ReleaseError(f"CI did not finish within {CI_TIMEOUT // 60} minutes – nothing was released")
        print(f"  CI: {len(runs) - len(pending)} of {len(runs)} runs done, waiting …", flush=True)
        time.sleep(POLL)


def verify_assets(tag: str, domain: str, version: str) -> None:
    """The zip of the release: checksum, version, and every file equal to the tagged source."""
    deadline = time.monotonic() + ASSET_TIMEOUT
    wanted = {f"{domain}.zip", f"{domain}.zip.sha256"}
    while True:
        assets = {a["name"] for a in json.loads(run(gh(), "release", "view", tag, "--json", "assets"))["assets"]}
        if wanted <= assets:
            break
        if time.monotonic() > deadline:
            raise ReleaseError(f"the release workflow attached no {domain}.zip within {ASSET_TIMEOUT // 60} minutes")
        print("  waiting for the release assets …", flush=True)
        time.sleep(POLL)
    with tempfile.TemporaryDirectory() as tmp:
        run(gh(), "release", "download", tag, "-p", f"{domain}.zip", "-p", f"{domain}.zip.sha256", "-D", tmp)
        data = (Path(tmp) / f"{domain}.zip").read_bytes()
        expected = (Path(tmp) / f"{domain}.zip.sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(data).hexdigest() != expected:
        raise ReleaseError(f"{domain}.zip does not match its .sha256")
    tracked = set(run("git", "ls-tree", "-r", "--name-only", tag, f"custom_components/{domain}/").splitlines())
    prefix = f"custom_components/{domain}/"
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = {n.removeprefix("./") for n in zf.namelist() if not n.endswith("/")}
        if json.loads(zf.read("manifest.json"))["version"] != version:
            raise ReleaseError(f"the zip's manifest.json is not version {version}")
        source = {p.removeprefix(prefix) for p in tracked}
        if names != source:
            raise ReleaseError(f"zip and tag differ in files: {sorted(names ^ source)[:10]}")
        for name in sorted(names):
            blob = subprocess.run(  # noqa: S603 - git with fixed arguments
                ["git", "show", f"{tag}:{prefix}{name}"],  # noqa: S607
                capture_output=True,
                check=True,
            ).stdout
            if zf.read(name) != blob:
                raise ReleaseError(f"{name} in the zip differs from the tagged source")
    print(f"  {domain}.zip: checksum, version {version} and all {len(names)} files match the tag", flush=True)


def release(version: str, notes: Path, *, dry_run: bool, skip_tests: bool) -> None:
    root = Path(run("git", "rev-parse", "--show-toplevel"))
    domain, manifest = integration(root)
    tag = f"v{version}"
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ReleaseError(f"'{version}' is not a version like 1.2.3")
    check_notes(notes)

    print("1. dev and origin/main", flush=True)
    if run("git", "branch", "--show-current") != "dev":
        raise ReleaseError("release from the branch dev")
    if run("git", "status", "--porcelain"):
        raise ReleaseError("dev has uncommitted changes")
    run("git", "fetch", "origin", "--tags")
    missing = int(run("git", "rev-list", "--count", "dev..origin/main"))
    if missing:
        raise ReleaseError(
            f"origin/main has {missing} commit(s) dev lacks (a merged pull request?): "
            "git rebase origin/main on dev first, then run this again"
        )
    if run("git", "tag", "--list", tag):
        raise ReleaseError(f"the tag {tag} exists already")

    print(f"2. version {version}", flush=True)
    path = root / "custom_components" / domain / "manifest.json"
    if manifest["version"] != version:
        text = path.read_text(encoding="utf-8")
        new = re.sub(r'("version":\s*")[^"]*(")', rf"\g<1>{version}\g<2>", text, count=1)
        if dry_run:
            print(f"  (dry run: manifest {manifest['version']} -> {version}, not written)", flush=True)
        else:
            path.write_text(new, encoding="utf-8")
            run("git", "add", str(path))
            run("git", "commit", "-q", "-m", f"Version {version}")

    print("3. lint and tests", flush=True)
    if skip_tests:
        print("  (skipped)", flush=True)
    else:
        run(sys.executable, "-m", "ruff", "check", ".", cwd=root)
        run(sys.executable, "-m", "ruff", "format", "--check", ".", cwd=root)
        run(sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", capture=False, cwd=root)

    if dry_run:
        print(f"Dry run done: {title(manifest, version)} would be released from {run('git', 'rev-parse', 'HEAD')[:7]}.")
        return

    print("4. main and push", flush=True)
    run("git", "switch", "-q", "main")
    try:
        run("git", "merge", "-q", "--ff-only", "origin/main")
        run("git", "merge", "-q", "--ff-only", "dev")
        sha = run("git", "rev-parse", "HEAD")
        run("git", "push", "origin", "main")
        remote = run("git", "ls-remote", "origin", "refs/heads/main").split()[0]
        if remote != sha:
            raise ReleaseError(f"origin/main is {remote[:7]}, not the pushed {sha[:7]}")

        print("5. CI", flush=True)
        wait_for_ci(sha)

        print(f"6. release {tag}", flush=True)
        run(
            gh(),
            "release",
            "create",
            tag,
            "--target",
            sha,
            "--title",
            title(manifest, version),
            "--notes-file",
            str(notes),
        )

        print("7. release assets", flush=True)
        run("git", "fetch", "origin", "--tags")
        verify_assets(tag, domain, version)
    finally:
        print("8. back to dev", flush=True)
        run("git", "switch", "-q", "dev")
    print(f"Released {title(manifest, version)}: {run(gh(), 'release', 'view', tag, '--json', 'url', '-q', '.url')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("version", nargs="?", help="the new version, e.g. 2.0.17")
    parser.add_argument("--notes", type=Path, help="release notes (Markdown: German, '---', English)")
    parser.add_argument("--draft", action="store_true", help="print a notes skeleton from the commits and stop")
    parser.add_argument("--dry-run", action="store_true", help="check and test only: no commit, push or release")
    parser.add_argument("--skip-tests", action="store_true", help="leave out ruff and the tests (CI still runs)")
    args = parser.parse_args()
    try:
        if args.draft:
            draft()
            return 0
        if not args.version or not args.notes:
            parser.error("version and --notes are needed (or --draft)")
        release(args.version, args.notes, dry_run=args.dry_run, skip_tests=args.skip_tests)
    except ReleaseError as err:
        print(f"\nStopped: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
