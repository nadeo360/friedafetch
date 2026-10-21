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
 3. what CI runs, run here first (not with --skip-tests), on the commit to be released next to the other
    repository's origin/main – exactly what CI will see: ruff, the tests (with the IMAP tests where Dovecot is
    installed), bandit, the type check and the browser tests, in environments with the pinned versions of the
    requirement locks (built once in ~/.cache/friedafetch-release, again when a lock changes);
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
import os
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
CACHE = Path.home() / ".cache" / "friedafetch-release"
# the other repository (its origin/main is what this one's CI checks out) and how its tests are told where it is
OTHER = {"friedafetch": ("friedafetch-mail", "POSTFACH_DIR"), "friedafetch_mail": ("ha-icloud-mcp", "FRIEDA_DIR")}
DOVECOT = ["/opt/homebrew/opt/dovecot/sbin/dovecot", "/usr/local/opt/dovecot/sbin/dovecot", "/usr/sbin/dovecot"]


class ReleaseError(Exception):
    pass


def run(*args: str | Path, capture: bool = True, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    """A command whose failure stops the release (with its output); never part of a pipe."""
    args = tuple(str(a) for a in args)
    print("  $", " ".join(args), flush=True)
    done = subprocess.run(  # noqa: S603
        args, cwd=cwd, capture_output=capture, text=True, check=False, env={**os.environ, **env} if env else None
    )
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip() if capture else ""
        raise ReleaseError(f"{' '.join(args[:3])} … failed ({done.returncode})" + (f":\n{detail}" if detail else ""))
    return (done.stdout or "").strip() if capture else ""


def _pins(locks: list[Path]) -> list[str]:
    """The pinned requirements of hash-locked files, without the hashes (they are for Linux wheels; CI checks them)."""
    pins: set[str] = set()
    for lock in locks:
        for line in lock.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].rstrip(" \\")
            if "==" in line and not line.startswith((" ", "-")):
                pins.add(line.strip())
    return sorted(pins)


def ci_env(name: str, locks: list[Path], *, browsers: bool = False) -> Path:
    """A Python environment with the pinned versions CI installs; rebuilt only when the locks change."""
    pins = _pins([lock for lock in locks if lock.exists()])
    key = hashlib.sha256("\n".join(pins).encode()).hexdigest()
    venv = CACHE / name
    python = venv / "bin" / "python"
    stored = (venv / ".key").read_text(encoding="utf-8") if (venv / ".key").exists() else ""
    if not python.exists() or stored != key:
        print(f"  building the {name} environment (pinned versions of {', '.join(lock.name for lock in locks)})")
        shutil.rmtree(venv, ignore_errors=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        reqs = CACHE / f"{name}.txt"
        reqs.write_text("\n".join(pins) + "\n", encoding="utf-8")
        uv = shutil.which("uv") or os.environ.get("UV")
        if uv:
            run(uv, "venv", "-q", "--python", f"{sys.version_info.major}.{sys.version_info.minor}", venv)
            run(uv, "pip", "install", "-q", "--python", python, "-r", reqs)
        else:
            run(sys.executable, "-m", "venv", venv)
            run(python, "-m", "pip", "install", "-q", "-r", reqs)
        (venv / ".key").write_text(key, encoding="utf-8")
    if browsers:
        run(python, "-m", "playwright", "install", "chromium", "webkit")
    return python


def ci_checks(root: Path, domain: str) -> None:
    """What CI runs, on HEAD next to the other repository's origin/main, in throwaway worktrees."""
    other_name, other_env = OTHER[domain]
    other = Path(os.environ.get(other_env) or root.parent / other_name)
    run("git", "-C", other, "fetch", "-q", "origin")
    tmp = Path(tempfile.mkdtemp(prefix="release-"))
    here, there = tmp / "self", tmp / "other"
    run("git", "worktree", "add", "-q", "--detach", here, "HEAD", cwd=root)
    run("git", "-C", other, "worktree", "add", "-q", "--detach", there, "origin/main")
    try:
        _checks(here, there, domain, other_env)
    except ReleaseError as err:
        raise ReleaseError(
            f"{err}\n\nChecked next to {other_name} at origin/main, as CI will. If this change needs something of "
            f"{other_name} that is only on its dev branch, release {other_name} first."
        ) from err
    finally:
        run("git", "worktree", "remove", "--force", here, cwd=root)
        run("git", "-C", other, "worktree", "remove", "--force", there)
        shutil.rmtree(tmp, ignore_errors=True)


def _checks(here: Path, there: Path, domain: str, other_env: str) -> None:
    """ruff, the tests, bandit, the type check and the browser tests in the worktree of the commit to release."""
    if domain == "friedafetch_mail":  # CI links Frieda in the same way
        (here / "custom_components" / "friedafetch").symlink_to(there / "custom_components" / "friedafetch")
    reqs = here / "requirements"
    python = ci_env(f"{domain}-ci", [reqs / "test.txt", reqs / "types.txt", reqs / "lint.txt", reqs / "bandit.txt"])
    run(python, "-m", "ruff", "check", ".", cwd=here)
    run(python, "-m", "ruff", "format", "--check", ".", cwd=here)
    dovecot = shutil.which("dovecot") or next((d for d in DOVECOT if Path(d).exists()), None)
    if (here / "tests_imap").exists() and not dovecot:
        print("  ! no Dovecot here: the IMAP tests are skipped locally (CI runs them)", flush=True)
    env = {"IMAP_TESTS_REQUIRED": "1"} if dovecot and (here / "tests_imap").exists() else None
    run(python, "-m", "pytest", "-q", "-p", "no:cacheprovider", capture=False, cwd=here, env=env)
    if (reqs / "bandit.txt").exists():
        run(python, "-m", "bandit", "-q", "-r", "custom_components", "-c", "pyproject.toml", cwd=here)
    if (reqs / "types.txt").exists():
        run(python.parent / "basedpyright", "--pythonpath", python, capture=False, cwd=here)
    preview = here / "tools" / "preview"
    if (preview / "tests").exists():
        ui_lock = reqs / "ui.txt" if (reqs / "ui.txt").exists() else there / "requirements" / "ui.txt"
        ui = ci_env("ui", [ui_lock], browsers=True)
        browsers = ["--browser", "chromium", "--browser", "webkit"]
        run(ui, "-m", "pytest", "-q", "-n", "auto", *browsers, capture=False, cwd=preview, env={other_env: str(there)})


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

    print("3. what CI runs, here first", flush=True)
    if skip_tests:
        print("  (skipped)", flush=True)
    else:
        ci_checks(root, domain)

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
    parser.add_argument("--skip-tests", action="store_true", help="leave out the local CI checks (CI still runs)")
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
