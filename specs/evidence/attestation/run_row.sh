#!/bin/sh
# 0007 §4d (I5): one matrix row, after its interpreter is installed. POSIX sh: it runs on GitHub's hosted runners
# (bash, git-bash on Windows) and inside the distro containers (busybox sh on Alpine), as a NON-root user.
#   run_row.sh <python> <route> <runner_image> <expect_prefix> <run_id> <job_id> <out>
set -eu
PY=$1; ROUTE=$2; IMAGE=$3; PREFIX=$4; RUN_ID=$5; JOB_ID=$6; OUT=$7
if [ "$(id -u 2>/dev/null || echo 1)" = "0" ]; then
    echo "run_row.sh: refusing to run as root (the geteuid entries are job:runs: the job runs non-root)" >&2
    exit 1
fi
"$PY" -m venv .venv-attest
if [ -x .venv-attest/bin/python ]; then VPY=.venv-attest/bin/python; else VPY=.venv-attest/Scripts/python.exe; fi
"$VPY" -m pip install --disable-pip-version-check -q -c specs/evidence/attestation/constraints.txt -e ".[dev,mcp]"
exec "$VPY" specs/attestation_job.py --route "$ROUTE" --runner-image "$IMAGE" --expect-prefix "$PREFIX" \
    --run-id "$RUN_ID" --job-id "$JOB_ID" --out "$OUT"
