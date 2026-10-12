"""Derive stdlib_extensions.txt from a traced launcher run: the compiled standard-library modules it loaded.

    strace -f --seccomp-bpf -e trace=openat -e status=successful -o <trace> -- \\
        bash specs/evidence/offline/run_offline.sh --basetemp=<dir>
    python stdlib_extensions_from_trace.py <trace> <lib-dynload dir of VERACIUM_PYTHON> "<where and on what>" \
        > stdlib_extensions.txt

Every successful open of a shared object directly under that interpreter's `lib-dynload` directory, by ANY process
the launcher started (strace -f follows children, so a module an evidence script imports in a subprocess is seen;
`ctypes` is one), names a module: the file name up to its first dot. The output is that set, sorted, one per line,
under a header that records how it was made. Opens from any other interpreter are counted and reported, not listed:
the preflight judges VERACIUM_PYTHON alone.
"""
# Mutation-Matrix: tests/test_offline_preflight.py::test_stdlib_extensions_from_trace_reads_every_process_and_one_interpreter
import pathlib
import re
import sys

trace, dyn = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]).resolve()
opened = re.compile(r'openat\([^,]+, "([^"]+\.so)"')
mods, other = set(), set()
for line in trace.read_text(errors="replace").splitlines():
    m = opened.search(line)
    if not m:
        continue
    p = pathlib.Path(m.group(1))
    if p.parent.name != "lib-dynload":
        continue
    (mods if p.parent.resolve() == dyn else other).add(p.name.split(".")[0] if p.parent.resolve() == dyn else str(p))
print("# The compiled standard-library modules the offline launcher's run loaded, measured: stdlib_preflight.py")
print("# refuses an interpreter that cannot import one of them. Made by stdlib_extensions_from_trace.py from a run of")
print("# run_offline.sh traced with strace -f (every process it started); see that script's docstring for the commands.")
print(f"# {len(mods)} modules from {dyn.name} of the traced interpreter; {len(other)} shared objects from any other")
print("# interpreter's lib-dynload were opened and are not listed.")
if len(sys.argv) > 3:
    print(f"# measured: {sys.argv[3]}")
print("\n".join(sorted(mods)))
