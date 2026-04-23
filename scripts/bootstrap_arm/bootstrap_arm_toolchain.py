"""Bootstraps an arm toolchain dir based on a url direct link and local templates"""

#!/bin/python3

import argparse
import tarfile
import os
import subprocess
import shutil
from pathlib import Path

from utils import download_direct_link_with_progress

DATADIR = Path("scripts/bootstrap_arm/template")


def expand_template(source_path, target_path, substitutions):
    with open(source_path, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
    with open(target_path, "w", encoding="utf-8") as fp:
        for line in lines:
            new_line = line
            for src_sub, target_sub in substitutions.items():
                new_line = new_line.replace(src_sub, target_sub)
            fp.write(new_line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Bootstraps an arm toolchain dir based on a url direct link and local templates"
    )
    parser.add_argument(
        "--override",
        "-o",
        help="Whether to overrite the target file if it exists",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "target_ws", help="Workspace dir in which to bootstrap the dir", type=str
    )
    parser.add_argument("url", help="Source url to pull from", type=str)
    parser.add_argument(
        "version", help="Version to be written in module and build", type=str
    )
    args = parser.parse_args()

    target_ws = Path(args.target_ws)
    target_tar_fpath = target_ws / args.url.split("/")[-1]

    if not target_tar_fpath.exists() or args.override:
        download_direct_link_with_progress(args.url, target_tar_fpath)
        with tarfile.open(target_tar_fpath, "r") as tar:
            tar.extractall(target_ws)
            target_dir = target_ws / os.path.commonprefix(
                [member.name for member in tar.getmembers()]
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
        subprocess.run(
            ["git", "commit", "-m", "Initial Commit"],
            cwd=target_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        with tarfile.open(target_tar_fpath, "r") as tar:
            target_dir = target_ws / os.path.commonprefix(
                [member.name for member in tar.getmembers()]
            )

    target_bzl_dir = target_dir / "bzl"
    target_bzl_dir.mkdir(exist_ok=True)
    expand_template(DATADIR / "config.bzl.tpl", target_bzl_dir / "config.bzl", {})
    with open(target_bzl_dir / "BUILD.bazel", "w", encoding="utf-8") as fp:
        fp.write("")
    expand_template(DATADIR / "config.bzl.tpl", target_bzl_dir / "config.bzl", {})
    expand_template(
        DATADIR / "main_BUILD.bazel.tpl",
        target_dir / "BUILD.bazel",
        {"@@VERSION@@": ".".join(args.version.split(".")[:-2])},
    )
    expand_template(
        DATADIR / "MODULE.bazel.tpl",
        target_dir / "MODULE.bazel",
        {"@@VERSION@@": args.version},
    )
    print("patches applied")
