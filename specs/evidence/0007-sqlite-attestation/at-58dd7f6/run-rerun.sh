#!/bin/bash
# research's re-run at 58dd7f6: probe (create/open on both builds), steptable campaign (3.45.1), uv ladder (3.53.1), compare, table
set -u
R=$1; T=$2; W=$3; cd "$R"
Q=$HOME/.cache/veracium-leg/venv-py3.14-0de5a29117f6/bin/python
U=$HOME/.local/share/uv/python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14
SP=$($Q -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')
for m in create open; do
  PYTHONPATH=$T/src:$SP $U -B probe_build_reproduces.py $T/src $(mktemp -d $W/pu.XXXX) $m > probe-u-$m.out 2>&1; echo "PU-$m=$?"
  PYTHONPATH=$T/src $Q -B probe_build_reproduces.py $T/src $(mktemp -d $W/pq.XXXX) $m > probe-q-$m.out 2>&1; echo "PQ-$m=$?"
done
STEPTABLE_WORK=$W PYTHONPATH=$T/src $Q -B steptable.py $T q.json --campaign > q.out 2>&1; echo "Q-EXIT=$?"
STEPTABLE_WORK=$W PYTHONPATH=$T/src:$SP $U -B steptable.py $T u.json > u.out 2>&1; echo "U-EXIT=$?"
$Q -B steptable.py --compare q.json u.json > compare.out 2>&1; echo "C-EXIT=$?"
$Q -B steptable.py --table q.json u.json > table.out 2>&1; echo "T-EXIT=$?"
