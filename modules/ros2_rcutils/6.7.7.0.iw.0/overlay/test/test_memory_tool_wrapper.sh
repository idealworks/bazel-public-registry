#!/bin/bash

set -e

RUNFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

export LD_PRELOAD="${RUNFILES_DIR}/../${PRELOAD_LIB}"
echo "RUNFILES_DIR: ${RUNFILES_DIR}"
echo "LD_PRELOAD: ${LD_PRELOAD}"
echo "pwd: `pwd`"
echo "TEST_BINARY_LOC: `pwd`/${TEST_BINARY_LOC}"

# Verify library exists
if [ ! -f "${LD_PRELOAD}" ]; then
    echo "ERROR: LD_PRELOAD library not found: ${LD_PRELOAD}"
    exit 1
fi

exec ${TEST_BINARY_LOC}
