#!/bin/env python

"""Adds a module to a workspace for local modifications"""

import tarfile
import zipfile
import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess

from version import get_latest_version


def apply_overlay_and_patches(
    module_name,
    registry_path: Path,
    target_dir: Path,
    mod_version="",
):
    """Adds the module to a workable workspace and sets it up for editing"""
    if not mod_version:
        mod_version = get_latest_version(f"{registry_path}/modules/{module_name}")
    print(f"Using version {mod_version} from module {module_name}")
    mod_path = Path(f"{registry_path}/modules/{module_name}/{mod_version}")

    with open(mod_path / "source.json", "r", encoding="utf-8") as fp:
        source_cnt = json.load(fp)

    for overlay_file in source_cnt.get("overlay", {}).keys():
        (target_dir / Path(overlay_file).parent).mkdir(exist_ok=True)
        shutil.copy(
            mod_path / "overlay" / overlay_file,
            target_dir / Path(overlay_file).parent,
        )

    for patch_file in source_cnt.get("patches", {}).keys():
        status = subprocess.run(
            ["git", "apply", mod_path.absolute() / "patches" / patch_file],
            cwd=target_dir,
            capture_output=True,
            check=False,
            text=True,
        )
        if status.returncode != 0:
            print(f"Error running patch {patch_file}: {status.stderr}")

    return target_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add a bazel module defined in a registry to a ws to be worked on"
    )
    parser.add_argument("module_name", help="name of the module to be added", type=str)
    parser.add_argument(
        "registry_path", help="Registry to get the module from", type=str
    )
    parser.add_argument(
        "target_path", help="Local path of the repo to apply the overlay and patches to", type=str
    )
    parser.add_argument(
        "-v", "--version", help="workspace to add the module to", type=str, default=""
    )
    args = parser.parse_args()
    # `bazel run` changes cwd to the runfiles dir; resolve relative args from where the user ran it
    base = Path(os.environ.get("BUILD_WORKING_DIRECTORY", "."))

    if not Path(args.target_path).exists():
        raise ValueError(f"Target path {args.target_path} does not exist")
    apply_overlay_and_patches(
        args.module_name,
        base / args.registry_path,
        base / args.target_path,
        args.version,
    )
