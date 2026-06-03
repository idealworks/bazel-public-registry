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
from utils import download_direct_link_with_progress

TARRABLE_EXTENSIONS = [".gz", ".xz", ".bz2", ".tar"]


def is_tarrable(path: Path):
    """Returns whether the suffix of path declares it as tar extractable"""
    return any(path.suffix == tar_ext for tar_ext in TARRABLE_EXTENSIONS)


def add_module_to_ws(
    module_name,
    registry_path: Path,
    workspace_path: Path,
    mod_version="",
):
    """Adds the module to a workable workspace and sets it up for editing"""
    workspace_path.mkdir(exist_ok=True)
    if not mod_version:
        mod_version = get_latest_version(f"{registry_path}/modules/{module_name}")
    print(f"Using version {mod_version} from module {module_name}")
    mod_path = Path(f"{registry_path}/modules/{module_name}/{mod_version}")

    with open(mod_path / "source.json", "r", encoding="utf-8") as fp:
        source_cnt = json.load(fp)

    if source_cnt.get("type", "") == "git_repository":
        repo_url = source_cnt["remote"]
        target_dir = workspace_path / repo_url.split("/")[-1].replace(".git", "")
        subprocess.run(
            ["git", "clone", repo_url],
            cwd=workspace_path,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "checkout",
                source_cnt["commit"],
            ],
            cwd=target_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    elif "url" in source_cnt:
        storage_dir = workspace_path / "__storage"
        storage_dir.mkdir(exist_ok=True)
        url = source_cnt["url"]
        target_tarfile = storage_dir / url.split("/")[-1]

        if source_cnt.get("strip_prefix", ""):
            target_dir = workspace_path / source_cnt["strip_prefix"]
        else:
            target_dir = workspace_path / module_name

        if target_dir.exists():
            print(f"{target_dir} already exists, skipping...")
            return target_dir

        print(f"Downloading {url}...")
        download_direct_link_with_progress(url, target_tarfile)

        if is_tarrable(target_tarfile):
            with tarfile.open(target_tarfile, "r") as tar:
                if source_cnt.get("strip_prefix", ""):
                    target_dir = workspace_path / source_cnt["strip_prefix"]
                    tar.extractall(workspace_path)
                else:
                    target_dir = workspace_path / module_name
                    target_dir.mkdir(exist_ok=True)
                    tar.extractall(target_dir)
        elif target_tarfile.suffix == ".zip":
            with zipfile.ZipFile(target_tarfile, "r") as zip_ref:
                if source_cnt.get("strip_prefix", ""):
                    zip_ref.extractall(workspace_path)
                    target_dir = workspace_path / source_cnt["strip_prefix"]
                else:
                    target_dir = workspace_path / module_name
                    target_dir.mkdir(exist_ok=True)
                    zip_ref.extractall(target_dir)

        else:
            raise ValueError(
                f"Unable to extract {target_tarfile}, unknown extension {target_tarfile.suffix}"
            )

        subprocess.run(
            ["git", "init"],
            cwd=target_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=target_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        status = subprocess.run(
            ["git", "commit", "-m", "Initial Commit"],
            cwd=target_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if status.returncode != 0:
            raise ValueError(
                f"Failed to commit to {target_dir}: code: {status.returncode}, stderr: {status.stderr}"
            )
    else:
        raise ValueError("Source url of package is not a github link")

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
        "workspace_path", help="workspace to add the module to", type=str
    )
    parser.add_argument(
        "-v", "--version", help="workspace to add the module to", type=str, default=""
    )
    args = parser.parse_args()
    add_module_to_ws(
        args.module_name,
        Path(args.registry_path),
        Path(args.workspace_path),
        args.version,
    )
