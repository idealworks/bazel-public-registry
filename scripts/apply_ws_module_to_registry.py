#!/bin/python
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests


def generate_integrity(fpath: Path):
    hasher = hashlib.sha256()
    with fpath.open("rb") as f:
        while chunk := f.read(16384):
            hasher.update(chunk)
    digest = base64.b64encode(hasher.digest()).decode()
    return f"sha256-{digest}"


@dataclass
class ModuleHeader:
    name: str
    version: str
    compatibility_level: Optional[int] = None  # Optional since it's not in all entries


@dataclass
class BazelDep:
    name: str
    version: str


@dataclass
class LocalPathOverride:
    module_name: str
    path: str


@dataclass
class ModuleDeclaration:
    header: ModuleHeader
    bazel_deps: List[BazelDep]
    local_path_overrides: Dict[str, LocalPathOverride]

    def has_local_path_overrides(self):
        """Checks if the module declaration has any local_path_override entries"""
        return len(self.local_path_overrides) != 0

    def all_deps_processed(self, ws_modules, processed_deps):
        """checks whether all the dependencies of the module are already processed
        based on the list of processed modules"""
        for bazel_dep in self.bazel_deps:
            if bazel_dep.name in ws_modules and bazel_dep.name not in processed_deps:
                return False
        return True


def safe_download_archive_url(download_dir: Path, remote_url):
    resp = requests.get(remote_url, stream=True)
    if resp.status_code != 200:
        raise ValueError(f"Cannot download '{remote_url}' to '{download_dir}': {resp}")

    total_size = int(resp.headers.get("content-length", 1))

    out_filename = remote_url.split("/")[-1]

    cur_size = 0
    last_print_time = time.time()
    if not (download_dir / out_filename).exists():
        with open(download_dir / out_filename, "wb") as fp:
            for chunk in resp.iter_content(chunk_size=8192):
                if (time.time() - last_print_time) > 5:
                    print(
                        "Download progress: {:.2f}%: {}/{}".format(
                            cur_size / total_size * 100, cur_size, total_size
                        )
                    )
                    last_print_time = time.time()
                cur_size += len(chunk)
                fp.write(chunk)
    return out_filename


@dataclass
class SourceData:
    archive_url: str
    strip_prefix: str


def git_remote_to_source_data(git_remote, commit_hash):
    """Transform a git remote value to a downloadable url for an archive and a strip_prefix based on how each remote compresses sources"""
    # input ("https://gitlab.freedesktop.org/xorg/lib/libxtrans/", "0dc46e7ed5bdd876467f9dbb314ba6b8094e541b")
    # url: "https://gitlab.freedesktop.org/xorg/lib/libxtrans/-/archive/0dc46e7ed5bdd876467f9dbb314ba6b8094e541b/libxtrans-0dc46e7ed5bdd876467f9dbb314ba6b8094e541b.tar.gz"
    # prefix: "libxtrans-0dc46e7ed5bdd876467f9dbb314ba6b8094e541b"
    if "gitlab" in git_remote:
        match = re.search(
            r"(?P<domain>[\w\.-]+)/(?P<repo>[\w\-/]+)(?=\.git$)", git_remote
        )
        repo_name = match.group("repo").split("/")[-1]
        archive_url = git_remote.replace(
            ".git", f"/-/archive/{commit_hash}/{repo_name}-{commit_hash}.tar.gz"
        )
        strip_prefix = f"{repo_name}-{commit_hash}"
        return SourceData(archive_url, strip_prefix)
    if "github" in git_remote:
        git_remote = git_remote.replace(".git", "")
        if "git@github.com:" in git_remote:
            git_remote = git_remote.replace("git@github.com:", "https://github.com/")
        archive_url = f"{git_remote}/archive/{commit_hash}.tar.gz"
        repo_name = git_remote.replace(".git", "").split("/")[-1]
        strip_prefix = f"{repo_name}-{commit_hash}"
        return SourceData(archive_url, strip_prefix)
    # input ("https://git.kernel.org/pub/scm/libs/libcap/libcap.git", "9eb56596eef5e55a596aa97ecaf8466ea559d05c")
    # url: "https://web.git.kernel.org/pub/scm/libs/libcap/libcap.git/snapshot/libcap-9eb56596eef5e55a596aa97ecaf8466ea559d05c.tar.gz"
    # prefix: "libcap-9eb56596eef5e55a596aa97ecaf8466ea559d05c"
    if "git.kernel.org" in git_remote:
        repo_name = git_remote.replace(".git", "").split("/")[-1]
        mod_git_remote = git_remote.replace(
            "https://git.kernel.org", "https://web.git.kernel.org"
        )
        archive_url = f"{mod_git_remote}/snapshot/{repo_name}-{commit_hash}.tar.gz"
        strip_prefix = f"{repo_name}-{commit_hash}"
        return SourceData(archive_url, strip_prefix)

    raise ValueError(f"{git_remote} not convertible to archive url")


def verify_git_tag_matched_module(actual_git_tag, header, ws_path=""):
    # Match against tags like "2017-02-24-228-g504193e"
    # These can be safely converted to "2017.02.24-228-g504193e"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(\d+-g[0-9a-f]+$)", actual_git_tag)
    if match:
        year, month, day, ext = match.groups()
        return header.version.startswith(f"{year}.{month}.{day}-{ext}")

    # Match against tags like "3.0.0-17-g9f40278"
    # These can be safely converted to "3.0.0.17.g9f40278"
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)-(\d+)-(g[0-9a-f]+$)", actual_git_tag)
    if match:
        major, minor, patch, inc, ext = match.groups()
        return header.version.startswith(f"{major}.{minor}.{patch}.{inc}.{ext}")

    if not header.version.startswith(actual_git_tag):
        ws_loc_str = ""
        if ws_path:
            ws_loc_str = f" at {ws_loc_str}"
        raise ValueError(
            f"Module {header.name}{ws_loc_str} declares version '{header.version}' that does not start with '{actual_git_tag}'"
        )


@dataclass
class ModuleInformation:
    dec: ModuleDeclaration
    ws_path: Path

    def source_data_from_git_repo(self):
        git_remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=self.ws_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        git_commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.ws_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return git_remote_to_source_data(git_remote, git_commit_hash)

    def update_to_registry(
        self, registry_path: Path, force_url="", force_strip_prefix=""
    ):
        mod_path = (
            registry_path / "modules" / self.dec.header.name / self.dec.header.version
        )
        mod_path.mkdir(parents=True, exist_ok=True)
        # Get the exact tag of the repo in the workspace and check that the tag in MODULE.bazel starts with it
        if not force_url:
            try:
                git_rev = subprocess.run(
                    ["git", "describe", "--tags"],
                    cwd=self.ws_path,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            except subprocess.SubprocessError:
                raise subprocess.SubprocessError(
                    f"Unable to run git describe in {self.dec.header.name}"
                )
            if git_rev[0].isdigit():
                verify_git_tag_matched_module(git_rev, self.dec.header, self.ws_path)

        git_status = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.ws_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\n")

        if force_url:
            source_info = SourceData(force_url, force_strip_prefix)
        else:
            source_info = self.source_data_from_git_repo()
        workdir = Path("/tmp") / "apply_ws_module_to_registry"
        workdir.mkdir(parents=True, exist_ok=True)
        filename = safe_download_archive_url(workdir, source_info.archive_url)
        url_integrity = generate_integrity(workdir / filename)

        git_status = [entry for entry in git_status if entry != ""]

        overlay_path = mod_path / "overlay"
        overlay_path.mkdir(parents=True, exist_ok=True)

        # Copy MODULE.bazel to overlay, symlink it and remove it from statuses
        shutil.copy(self.ws_path / "MODULE.bazel", mod_path)
        overlay_json_content = {
            "MODULE.bazel": generate_integrity(mod_path / "MODULE.bazel")
        }
        if not (mod_path / "overlay" / "MODULE.bazel").exists():
            os.symlink("../MODULE.bazel", mod_path / "overlay" / "MODULE.bazel")
        git_status = [entry for entry in git_status if entry != "A  MODULE.bazel"]

        # Loop on all the files in the status and process them accordingly
        source_json_content = {
            "url": source_info.archive_url,
            "integrity": url_integrity,
            "strip_prefix": source_info.strip_prefix,
        }
        modified_files = []
        while git_status:
            entry = git_status.pop()
            fpath = entry[3:]
            if entry.startswith("A "):
                # File is added, add it to overlay
                (mod_path / "overlay" / fpath).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.ws_path / fpath, mod_path / "overlay" / fpath)
                overlay_json_content[entry[3:]] = generate_integrity(
                    mod_path / "overlay" / fpath
                )
            elif entry.startswith("M "):
                # File is modified, add it to patch
                modified_files.append(fpath)
            else:
                raise ValueError(
                    f"File '{entry[3:]}' not added in module {self.ws_path}, either add or reset it"
                )

        # Create patch based on modified files and add it's integrity to source_json_content
        if modified_files:
            patches_path = mod_path / "patches"
            patches_path.mkdir(parents=True, exist_ok=True)
            patch_content = subprocess.run(
                ["git", "diff", "HEAD", "--"] + modified_files,
                cwd=self.ws_path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            patch_path = patches_path / "bazel-modifications.patch"
            with patch_path.open("w") as fp:
                fp.write(patch_content)
            source_json_content["patch_strip"] = 1
            source_json_content["patches"] = {
                "bazel-modifications.patch": generate_integrity(patch_path),
            }

        source_json_content["overlay"] = overlay_json_content
        with (mod_path / "source.json").open("w") as fp:
            json.dump(source_json_content, fp, indent=2)
            fp.write("\n")


def parse_module_file(file_path: Path) -> ModuleDeclaration:
    content = file_path.read_text()

    # Patterns for different types of entries
    module_pattern = re.compile(
        r"module\(\s*"
        r'name\s*=\s*"(?P<name>[^"]+)",\s*'
        r'version\s*=\s*"(?P<version>[^"]+)",?\s*'
        r"(?:compatibility_level\s*=\s*(?P<compatibility_level>\d+),?\s*)?"
        r"\)",
        re.DOTALL,
    )

    bazel_dep_pattern = re.compile(
        r"bazel_dep\(\s*"
        r'name\s*=\s*"(?P<name>[^"]+)",\s*'
        r'version\s*=\s*"(?P<version>[^"]+)"\s*'
        r"\)",
        re.DOTALL,
    )

    # local_path_override_pattern = re.compile(
    #     r"local_path_override\(\s*" r'module_name\s*=\s*"(?P<module_name>[^"]+)",\s*',
    #     re.DOTALL,
    # )

    local_path_override_pattern = re.compile(
        r"local_path_override\(\s*"
        r'module_name\s*=\s*"(?P<module_name>[^"]+)"\s*,\s*'
        r'path\s*=\s*"(?P<path>[^"]+)"\s*,?\s*'
        r"\)"  # Closing parenthesis
    )

    bazel_deps = []
    local_path_overrides = {}

    # Parse module(...) entries
    module = ModuleHeader("", "", 0)
    for match in module_pattern.finditer(content):
        module = ModuleHeader(
            name=match.group("name"),
            version=match.group("version"),
            compatibility_level=(
                int(match.group("compatibility_level"))
                if match.group("compatibility_level")
                else None
            ),
        )

    # Parse bazel_dep(...) entries
    for match in bazel_dep_pattern.finditer(content):
        bazel_deps.append(
            BazelDep(name=match.group("name"), version=match.group("version"))
        )

    # Parse local_path_override(...) entries
    for match in local_path_override_pattern.finditer(content):
        local_path_overrides[match.group("module_name")] = LocalPathOverride(
            module_name=match.group("module_name"), path=match.group("path")
        )

    return ModuleDeclaration(module, bazel_deps, local_path_overrides)


def module_declarations_get_with_name(module_infos, modname):
    for module_inf in module_infos:
        if module_inf.dec.header.name == modname:
            return module_inf.dec
    return None


def find_files(filename, search_dir):
    matches = []
    for root, _, files in os.walk(search_dir):
        if filename in files:
            matches.append(Path(root) / filename)
    return matches


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Creates a registry entry for all the modules in a workspace"
    )
    parser.add_argument("workspace_path", help="Path to the module workspace", type=str)
    parser.add_argument(
        "registry_path", help="Registry to add the modules to", type=str
    )
    parser.add_argument(
        "-u",
        "--url",
        help="Force url to be used instead of parsing remote in git repo and converting to archive url",
        type=str,
        default="",
    )
    parser.add_argument(
        "-s",
        "--strip-prefix",
        help="Force change prefix to be stripped from the archive url",
        type=str,
        default="",
    )
    args = parser.parse_args()

    if (args.url and not args.strip_prefix) or (not args.url and args.strip_prefix):
        raise ValueError("url and strip prefix should be provided together")

    module_bazel_paths = find_files("MODULE.bazel", args.workspace_path)
    all_module_infos = []
    for module_path in module_bazel_paths:
        module_dec: ModuleDeclaration = parse_module_file(module_path)
        module_info = ModuleInformation(module_dec, module_path.parent)
        # Sanity check that the modules do not reference local_path_overrides
        if module_dec.has_local_path_overrides():
            raise ValueError(
                f"Module {module_dec.header.name} has local_path_override inside, make sure to remove it"
            )
        all_module_infos.append(module_info)

    # Remove the child modules from the list (example modules)
    parent_module_infos = []
    for module_info in all_module_infos:
        module_has_parent = False
        for maybe_parent in all_module_infos:
            if maybe_parent.ws_path == module_info.ws_path:
                continue
            if maybe_parent.ws_path in module_info.ws_path.parents:
                print(
                    f"Warn: module {module_info.dec.header.name} will be skipped as child as it's a child of {maybe_parent.dec.header.name}"
                )
                module_has_parent = True
                continue
        if not module_has_parent:
            parent_module_infos.append(module_info)
    all_module_infos = parent_module_infos

    # Check that the modules in the ws reference eachother
    for module_info in all_module_infos:
        for dep in module_info.dec.bazel_deps:
            dep_module_dec = module_declarations_get_with_name(
                all_module_infos, dep.name
            )
            if (
                dep_module_dec is not None
                and dep_module_dec.header.version != dep.version
            ):
                raise ValueError(
                    f"Module {module_info.dec.header.name} references dependency {dep.name} with version {dep.version} but the version in the workspace is {dep_module_dec.header.version}"
                )

    all_ws_module_names = [
        module_info.dec.header.name for module_info in all_module_infos
    ]

    to_be_processed = all_module_infos.copy()
    already_processed = []
    while len(to_be_processed) != 0:
        processed_module_infos_copy = to_be_processed.copy()
        while len(processed_module_infos_copy) != 0:
            maybe_processed_module = processed_module_infos_copy.pop()
            if maybe_processed_module.dec.all_deps_processed(
                all_ws_module_names, already_processed
            ):
                maybe_processed_module.update_to_registry(
                    Path(args.registry_path), args.url, args.strip_prefix
                )
                already_processed.append(maybe_processed_module.dec.header.name)
                to_be_processed = [
                    module_info
                    for module_info in to_be_processed
                    if module_info.dec.header.name
                    != maybe_processed_module.dec.header.name
                ]
