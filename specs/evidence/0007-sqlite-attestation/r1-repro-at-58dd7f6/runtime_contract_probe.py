"""Measure the accepted 0013 model's independent runtime contract.

This does not implement the proposed runtime_status function.
Usage: PYTHONPATH=<tree>/src python runtime_contract_probe.py <tree> <out.json>
"""
import copy
import hashlib
import importlib.util
import json
import pathlib
import platform
import sqlite3
import sys

tree = pathlib.Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("migrations_0013_review", tree / "specs/migrations_0013.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
from veracium.store import schema_version as sv
artifact = json.loads((tree / "specs/generated/migration_0013_evidence.json").read_text())
product_runtime_supported = sv.runtime_supported()
with m._draft() as artifact:
    probes = m.authorizer_probes()
    result = {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
              "schema_runtime_supported": sv.runtime_supported(),
              "migration_artifact_problems": m.migration_runtime_artifact_problems(artifact),
              "authorizer_probes": probes,
              "migration_runtime_supported": m.migration_runtime_supported(artifact),
              "matching_migration_records": sum(sv.build_identity(r) == sv.build_identity(sv.runtime_identity())
                                                for r in artifact["migration_runtimes"])}
    original = m._authorizer
    m._authorizer = lambda *_: sqlite3.SQLITE_OK
    try:
        result["permissive_authorizer"] = {"schema_runtime_supported": sv.runtime_supported(),
                                          "authorizer_probes": m.authorizer_probes(),
                                          "migration_runtime_supported": m.migration_runtime_supported(artifact)}
    finally:
        m._authorizer = original

# Literal key in amendment 4d / INV-SA12; these are constructed records, NOT
# measurements from two real machines. Architecture is only beside the key.
identity = sv.runtime_identity()
with sqlite3.connect(":memory:") as c:
    options = sorted(r[0] for r in c.execute("PRAGMA compile_options"))
identity["compile_options_sha256"] = hashlib.sha256("\n".join(options).encode()).hexdigest()
def proposed_key(record):
    return (record["sqlite_version"], record["source_id"],
            tuple(sorted(record["features"].items())), record["compile_options_sha256"])
x86, arm = copy.deepcopy(identity), copy.deepcopy(identity)
x86["machine"], arm["machine"] = "x86_64", "aarch64"
result["architecture_key_model"] = {"kind": "constructed contract counterexample; not a cross-architecture measurement",
                                    "x86_record": x86, "arm_record": arm,
                                    "same_proposed_key": proposed_key(x86) == proposed_key(arm)}
result["product_runtime_supported_outside_model"] = product_runtime_supported
path = pathlib.Path(sys.argv[2]); path.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"python": result["python"], "sqlite": result["sqlite"],
                  "schema_runtime_supported": result["schema_runtime_supported"],
                  "authorizer_true": sum(v is True for v in probes.values()),
                  "authorizer_total": len(probes),
                  "migration_runtime_supported": result["migration_runtime_supported"],
                  "architecture_key_collision_model": result["architecture_key_model"]["same_proposed_key"]}))
