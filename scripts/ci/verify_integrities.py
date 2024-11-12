#!/bin/python3

import json
import os
import subprocess

mismatch_found = False
for module in os.listdir("modules"):
    module_path = os.path.join("modules", module)
    for version in os.listdir(module_path):
        module_v_path = os.path.join(module_path, version)
        if not "overlay" in os.listdir(module_v_path):
            continue
        with open(os.path.join(module_v_path, "source.json"), "r") as fp:
            cnt = json.load(fp)
        for category in ["overlay", "patches"]:
            if category not in cnt:
                continue
            for fname, sha_integ_val in cnt[category].items():
                f_fullpath = os.path.join(module_v_path, category, fname)
                calc_integ = (
                    subprocess.check_output(["./scripts/calc-integrity.sh", f_fullpath])
                    .decode()
                    .strip()
                )
                if sha_integ_val != calc_integ:
                    print(
                        f"Mismatch between calc integrity for module: {module}, version: {version}, category: {category} fname: {fname}\n  calculated integ: {calc_integ}\n  expected integ: {sha_integ_val}"
                    )
                    mismatch_found = True

if mismatch_found:
    exit(1)
