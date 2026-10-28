#!/bin/bash
# 0007 I6 (§4g.8 Gate, v0.6): the two CONSTRUCTED routes beside the real builds — sqlite.org's own 3.45.1 amalgamation,
# built twice: as is (a build no attestation record matches, so `verified` if it reproduces the evidence), and with
# SQLITE_OMIT_GENERATED_COLUMNS (a build that cannot pass §4b step 1, so `refused`, with its failing step). Research's
# stage-1 read of the round-3 fix shape (2026-10-27) proposed the second: a default pre-3.25 build cannot even be
# loaded by CPython 3.14's _sqlite3 (it imports 3.25's sqlite3_create_window_function), so it would show an ImportError,
# never a refused route. These are constructed routes, labelled as such; neither is a CI matrix row.
#   build_route_libs.sh <work-dir>      # then: LD_LIBRARY_PATH=<work-dir>/lib-<variant> <python> route_probe.py
set -euo pipefail
W=${1:?work dir}; ZIP=sqlite-amalgamation-3450100.zip
ZIP_SHA256=5592243caf28b2cdef41e6ab58d25d653dfc53deded8450eb66072c929f030c4   # https://www.sqlite.org/2024/$ZIP
mkdir -p "$W" && cd "$W"
[ -f "$ZIP" ] || curl -sSfLO "https://www.sqlite.org/2024/$ZIP"
echo "$ZIP_SHA256  $ZIP" | sha256sum -c -
rm -rf sqlite-amalgamation-3450100 && unzip -q "$ZIP"
for v in default omit-generated-columns; do
  FLAGS="-DSQLITE_ENABLE_COLUMN_METADATA"
  [ "$v" = omit-generated-columns ] && FLAGS="$FLAGS -DSQLITE_OMIT_GENERATED_COLUMNS"
  mkdir -p "lib-$v"
  # the soname libsqlite3.so.0 is what CPython's _sqlite3 links against, so LD_LIBRARY_PATH substitutes this build
  gcc -O2 -fPIC -shared $FLAGS -Wl,-soname,libsqlite3.so.0 -o "lib-$v/libsqlite3.so.0" sqlite-amalgamation-3450100/sqlite3.c -lpthread -ldl -lm
  echo "built lib-$v ($FLAGS): $(sha256sum lib-$v/libsqlite3.so.0 | cut -c1-16)"
done
