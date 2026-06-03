#!/usr/bin/env python3
"""CI: show what changed in a package between its previous registry version and the
new version added in a pull request.

For every module version newly added in the PR (a new ``modules/<module>/<version>/``
directory, detected by an added ``source.json``), this materializes both the previous
registry version and the new version exactly as Bazel resolves a module — download or
clone the source, strip the prefix, copy overlay files and apply patches — and emits a
unified diff of the resulting package contents.

The report is written to the GitHub step summary and to ``package_diff_report.md`` (the
workflow uses that file to post a sticky PR comment). This job is informational and
always exits 0 so it never blocks a merge.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Repo checkout root: `bazel run` sets BUILD_WORKSPACE_DIRECTORY to the workspace (where `.git`
# and `modules/` live); fall back to the source location for direct (non-Bazel) runs.
REPO_ROOT = Path(
    os.environ.get("BUILD_WORKSPACE_DIRECTORY") or Path(__file__).resolve().parents[2]
)
MODULES_DIR = REPO_ROOT / "modules"

try:
    # Provided as Bazel deps: //scripts:add_module_to_ws pulls in utils -> requests and version.
    from add_module_to_ws import add_module_to_ws
    from version import Version
except ImportError:
    # Fallback for direct invocation from a checkout (requires deps installed locally).
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from add_module_to_ws import add_module_to_ws
    from version import Version

# Keep the diff readable in a PR comment / step summary (GitHub comments cap at 65536
# chars). The full diff is always reproducible locally via add_module_to_ws.py.
MAX_DIFF_LINES = 2000
REPORT_PATH = REPO_ROOT / "package_diff_report.md"


def added_versions(base_sha):
    """Return {module: [new_version, ...]} for version dirs whose source.json was added."""
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=A", base_sha, "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    )
    added = {}
    for line in out.splitlines():
        parts = Path(line).parts
        # modules/<module>/<version>/source.json
        if len(parts) == 4 and parts[0] == "modules" and parts[3] == "source.json":
            added.setdefault(parts[1], []).append(parts[2])
    return added


def previous_version(module, new_version):
    """Greatest existing version of `module` strictly less than `new_version`, or None."""
    new_v = Version.parse(new_version)
    candidates = []
    for entry in (MODULES_DIR / module).iterdir():
        if not entry.is_dir() or entry.name == new_version:
            continue
        try:
            parsed = Version.parse(entry.name)
        except ValueError:
            continue
        if parsed < new_v:
            candidates.append((parsed, entry.name))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def diff_dirs(prev_dir, new_dir):
    """Return (changed-files summary, full unified diff) between two package roots."""
    common = ["--exclude=.git", str(prev_dir), str(new_dir)]
    summary = subprocess.run(
        ["diff", "-rqN", *common], capture_output=True, text=True
    ).stdout.strip()
    full = subprocess.run(
        ["diff", "-ruN", *common], capture_output=True, text=True
    ).stdout
    return summary, full


def truncate(text, max_lines):
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text, False
    return "\n".join(lines[:max_lines]), True


def diff_one(module, new_version, report):
    report.append(f"\n## `{module}` → `{new_version}`\n")
    prev_version = previous_version(module, new_version)
    if prev_version is None:
        report.append("First version of this module in the registry — nothing to compare against.\n")
        return
    report.append(f"Comparing **{prev_version}** → **{new_version}**\n")
    with tempfile.TemporaryDirectory() as td:
        prev_dir = add_module_to_ws(module, REPO_ROOT, Path(td) / "prev", prev_version)
        new_dir = add_module_to_ws(module, REPO_ROOT, Path(td) / "new", new_version)
        summary, full = diff_dirs(prev_dir, new_dir)
        if not summary and not full.strip():
            report.append("_No differences in package contents._\n")
            return
        if summary:
            report.append("**Changed files:**\n\n```\n" + summary + "\n```\n")
        body, truncated = truncate(full, MAX_DIFF_LINES)
        note = f"\n... (diff truncated at {MAX_DIFF_LINES} lines) ..." if truncated else ""
        report.append(
            "<details><summary>Full diff</summary>\n\n```diff\n" + body + note + "\n```\n</details>\n"
        )


def write_outputs(text):
    REPORT_PATH.write_text(text)
    print(text)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fp:
            fp.write(text + "\n")


def main():
    base_sha = os.environ.get("BASE_SHA") or "origin/master"
    added = added_versions(base_sha)

    report = ["# 📦 Package version diff\n"]
    if not added:
        report.append("_No new module versions added in this PR._")
        write_outputs("\n".join(report))
        return

    for module in sorted(added):
        for new_version in sorted(added[module]):
            try:
                diff_one(module, new_version, report)
            except Exception as exc:  # noqa: BLE001
                report.append(f"⚠️ Failed to diff `{module}` `{new_version}`: `{exc}`\n")

    write_outputs("\n".join(report))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        # Informational job: never block the PR on a diffing failure.
        print(f"package diff job error: {exc}", file=sys.stderr)
    sys.exit(0)
