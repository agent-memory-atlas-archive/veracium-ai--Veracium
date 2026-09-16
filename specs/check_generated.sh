#!/bin/bash
# Re-check EVERY generated artifact under specs/, discovered by property.
#
# 2026-09-16, the round-7 seal, in three corrections:
#
#  1. The pre-seal runbook said "all four renders". A status flip left
#     ALLOCATION.md stale, the four passed, only the suite knew.
#  2. The other seat swept and found seven — an enumeration of the render_*
#     family plus allocation.py, which is enumeration wearing a sweep's clothes.
#  3. Discovery by property found seventeen — and FOUR OF THOSE WERE FALSE
#     MEMBERS. `closure_findings.py`, `findings.py`, `generated_block.py` and
#     `reviews.py` are data modules and libraries with no `__main__`: running
#     them with `--check` does nothing at all and exits 0. My sweep printed
#     "ok" for four files that had asserted nothing, inside the tool written to
#     stop exactly that.
#
# So a file with the flags but NO CLI is REPORTED, not silently dropped: a
# check that did not run must never look like a check that passed. If one of
# them grows a `__main__` later it moves into the checked set by itself.
#
# Not "every script with --check": some are checkers of other things entirely
# (`seal_package.py` is another protocol). The pair --write AND --check names a
# regenerable artifact; `__main__` says something actually runs.
set -u
PY=${PY:-.venv/bin/python}
cd "$(dirname "$0")/.." || exit 2
fail=0; ran=0; nocli=0
# RECURSIVE ON PURPOSE. The first version globbed `specs/*.py` and missed three
# generators under `specs/evidence/` — including this round's own frozen-fixture
# checker. That is the identical defect CLAUDE.md records against the P1
# mutation-matrix gate: "check_* under specs/evidence/ was OUTSIDE this domain,
# so two evidence checkers on a line the reviewer was actively mutation-testing
# carried no matrix pointer and nothing demanded one — the gate covered the
# artifacts nobody was attacking and missed the ones under attack." Written
# down, and repeated anyway, in a sweep built because a list had been wrong.
for f in $(find specs -name '*.py' | sort); do
  grep -ql -- '--write' "$f" && grep -ql -- '--check' "$f" || continue
  if ! grep -q '^if __name__ == "__main__"' "$f"; then
    printf "  N/A   %-24s no __main__ — a --check here asserts NOTHING\n" "$(basename "$f")"
    nocli=$((nocli + 1)); continue
  fi
  ran=$((ran + 1))
  out=$($PY "$f" --check 2>&1); rc=$?
  if [ $rc -eq 0 ]; then
    printf "  ok    %-24s %s\n" "$(basename "$f")" "$(echo "$out" | head -1 | cut -c1-58)"
  else
    printf "  STALE %-24s exit %s  %s\n" "$(basename "$f")" "$rc" "$(echo "$out" | head -1 | cut -c1-58)"
    fail=$((fail + 1))
  fi
done
echo "$ran generated artifact(s) CHECKED, $nocli with no CLI (nothing asserted), $fail stale"
[ $fail -eq 0 ] || exit 1
