#!/bin/env python
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from version import Version


def get_latest_version(module_path):
    all_versions = [
        f for f in os.listdir(module_path) if (Path(module_path) / Path(f)).is_dir()
    ]
    all_versions = [Version.parse(version) for version in all_versions]
    all_versions.sort()
    if not all_versions:
        raise ValueError("No versions found in module")
    return all_versions[-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add a bazel module defined in a registry to a ws to be worked on"
    )
    parser.add_argument("module_name", help="name of the module to be added", type=str)
    parser.add_argument(
        "registry_path", help="Registry to get the module from", type=str
    )
    parser.add_argument(
        "workspace_path", help="workspace to add the module to", type=str
    )
    parser.add_argument(
        "-v", "--version", help="workspace to add the module to", type=str, default=""
    )
    parser.add_argument(
        "--tag-prefix",
        help="Prefix to be set in front of the tag value in the module (used if the repo tagging is different than the module version)",
        type=str,
        default="",
    )
    args = parser.parse_args()

    mod_version = args.version
    if not mod_version:
        mod_version = get_latest_version(
            f"{args.registry_path}/modules/{args.module_name}"
        )
    print(f"Using version {mod_version} from module")
    mod_path = Path(f"{args.registry_path}/modules/{args.module_name}/{mod_version}")

    with open(mod_path / "source.json", "r") as fp:
        source_cnt = json.load(fp)

    match = re.match(r"(https://github\.com/[^/]+/[^/]+)/", source_cnt["url"])

    if not match:
        raise ValueError("Source url of package is not a github link")

    repo_url = match.group(1)
    subprocess.run(
        ["git", "clone", repo_url],
        cwd=args.workspace_path,
        check=True,
        capture_output=True,
        text=True,
    )

    workspace_path = Path(args.workspace_path) / repo_url.split("/")[-1]
    subprocess.run(
        [
            "git",
            "checkout",
            args.tag_prefix + source_cnt["strip_prefix"].split("-")[-1],
        ],
        cwd=workspace_path,
        check=True,
        capture_output=True,
        text=True,
    )

    for overlay_file in source_cnt["overlay"].keys():
        (workspace_path / Path(overlay_file).parent).mkdir(exist_ok=True)
        shutil.copy(
            mod_path / "overlay" / overlay_file,
            workspace_path / Path(overlay_file).parent,
        )

    for patch_file in source_cnt.get("patches", {}).keys():
        status = subprocess.run(
            ["git", "apply", mod_path.absolute() / "patches" / patch_file],
            cwd=workspace_path,
            capture_output=True,
            text=True,
        )
        if status.returncode != 0:
            print(f"Error running patch {patch_file}: {status.stderr}")
