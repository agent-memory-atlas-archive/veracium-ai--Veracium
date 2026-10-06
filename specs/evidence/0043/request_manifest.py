"""0043 round 6 (R5-01) — THE REQUESTED PROPOSITION, from the request manifest (spec A3-quinquies).

Round 5 scored a question's ROW REFERENCE as its requested fact: q006 asks WHEN the user moved to Porto, and an answer
naming Porto while declining the date counted as answering. The requested propositions now come from the request
manifest — adjudicated blind by both seats, frozen, bound by the sha256 of its BYTES — never from the row reference.

The run (and every re-score) REFUSES, writing no rate, when:
  - the manifest file's bytes are not the frozen digest, or the ledger records a different digest;
  - the manifest's blind input does not re-derive from this run's ledger and the examiner's view (its shipped bytes are
    bound by the digest the manifest records, and its content must equal a fresh derivation, the `source` label aside);
  - a kept question has no manifest entry;
  - an entry's requested set is empty (a whole-fact absent question: there is no fact string to read, and §8's limit
    stands for it).

`class_determining` applies A3-quinquies's four steps: (1) ambiguous → UNRESOLVED, cause ambiguous-question; (2)
event-time and unanswerable → class `absent`, the requested proposition is the event TIME, the rows are context; (3)
otherwise the requested fact of the STRICTEST class decides (quarantined > untrusted > grounded); (4) facts sharing
that class form the tie set the interpreter reads (any asserted → ANSWERED; else any withheld → the bucket; else OTHER).
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "request-manifest" / "MANIFEST.json"
BLIND_PATH = HERE / "request-manifest" / "blind_input.json"
FROZEN_SHA256 = "2862495c8bceb48dae6164deb856e145a5a7d1ae40a4940f1f3d487eeb329fb8"     # the frozen manifest's bytes (spec A3-quinquies states the same digest)
ORDER = {"quarantined": 0, "untrusted": 1, "grounded": 2}
FIXTURE_CLASS = {"quarantined": "present-but-quarantined", "untrusted": "present-but-untrusted", "grounded": "present-and-trusted"}


class Refused(Exception):
    pass


def _strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def load(path: pathlib.Path = MANIFEST_PATH, *, frozen: bool = True) -> tuple[dict, str]:
    """The manifest and the sha256 of its bytes. `frozen=False` admits another manifest — a GENERATED one for a fake
    run's questions (it says so in its own `generated` field, and `bind` refuses it on a real run)."""
    raw = pathlib.Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if frozen and digest != FROZEN_SHA256:
        raise Refused(f"the request manifest's bytes are not the frozen manifest: sha256 {digest} != {FROZEN_SHA256}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs), digest


def _examiner_since(src_dir: pathlib.Path) -> dict:
    spec = importlib.util.spec_from_file_location("rm_examiner_view", HERE / "examiner_view.py")
    ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
    view = ev.view(ev.fixture_store(os.path.join(tempfile.mkdtemp(), "f.db")), "u")
    return {(v["subject"], v["relation"], v["object"]): v["since"] for v in view}


def derive_blind(res: dict) -> dict:
    """The blind labelling input as research's extractor derives it (make_blind_input.py, research a79767ea): each
    question's id and text, and the fixture rows' subject / relation / object / since — no row reference, answer,
    arm, outcome, class or interpreter output."""
    record = res["detail"][0]["record"]
    since = _examiner_since(HERE)
    return {"fixture_rows": {k: {**{f: v[f] for f in ("subject", "relation", "object")},
                                 "since": since.get((v["subject"], v["relation"], v["object"]))}
                             for k, v in sorted(record.items())},
            "questions": [{"id": q["id"], "text": q["text"]} for q in res["questions"]]}


def blind_text(res: dict, source: str) -> str:
    """The blind input's bytes, in the extractor's own serialisation (indent 1, UTF-8 unescaped, a final newline)."""
    return json.dumps({"source": source, **derive_blind(res)}, indent=1, ensure_ascii=False) + "\n"


def is_real(res: dict) -> bool:
    """A ledger from a real model run (any configured model other than the pipeline's fake)."""
    models = res.get("config", {}).get("models")
    return not (isinstance(models, dict) and (set(models.values()) <= {"fake"} or models == {"note": "fake model"}))


def generate(res: dict, out: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A GENERATED manifest for a FAKE run's questions — each kept question's requested facts are its row reference,
    facet none: it exercises the mechanics only, is NOT adjudicated, says so, and `bind` refuses it on a real run
    (research's stage-1 condition: otherwise the generated path would bypass the blind protocol)."""
    out = pathlib.Path(out)
    spec = importlib.util.spec_from_file_location("rm_examiner_view2", HERE / "examiner_view.py")
    ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
    view = ev.view(ev.fixture_store(os.path.join(tempfile.mkdtemp(), "g.db")), "u")
    record = res["detail"][0]["record"]
    eid = {(v["subject"], v["relation"], v["object"]): k for k, v in record.items()}
    blind = blind_text(res, "GENERATED for a fake run (not adjudicated)")
    (out / "generated_blind_input.json").write_text(blind, encoding="utf-8")
    qs = {q["id"]: {"requested": sorted(eid[(view[i - 1]["subject"], view[i - 1]["relation"], view[i - 1]["object"])] for i in q["rows"]),
                    "facet": "none", "ambiguous": False, "answerable_from_fixture": True}
          for q in res["questions"] if q["id"] in res["kept"]}
    man = {"manifest": "GENERATED test manifest — NOT adjudicated, not blind", "generated": True,
           "blind_input_sha256": hashlib.sha256(blind.encode("utf-8")).hexdigest(), "questions": qs}
    (out / "generated_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out / "generated_manifest.json", out / "generated_blind_input.json"


def blind_problems(res: dict, man: dict, blind_path: pathlib.Path = BLIND_PATH) -> list[str]:
    """Does the manifest's blind input re-derive from THIS run's ledger and the examiner's view?"""
    raw = pathlib.Path(blind_path).read_bytes()
    out = []
    if hashlib.sha256(raw).hexdigest() != man["blind_input_sha256"]:
        out.append(f"the shipped blind input's bytes are not the digest the manifest records ({man['blind_input_sha256']})")
    shipped = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs)
    record = res["detail"][0]["record"]
    if any(x["record"] != record for x in res["detail"]):
        out.append("the fixture differs across the ledger's detail rows")
    derived = derive_blind(res)
    for key in ("fixture_rows", "questions"):
        if shipped.get(key) != derived[key]:
            out.append(f"the blind input's {key} do not re-derive from this run's ledger and the examiner's view")
    return out


def bind(res: dict, man: dict, digest: str, blind_path: pathlib.Path = BLIND_PATH) -> None:
    """Every refusal A3-quinquies names, before any answer is scored."""
    if man.get("generated") and is_real(res):
        raise Refused("a GENERATED request manifest (not adjudicated, not blind) cannot score a real run — the blind "
                      "protocol has no bypass")
    if res.get("manifest_sha256") not in (None, digest):
        raise Refused(f"the ledger records manifest sha256 {res['manifest_sha256']}, the file's bytes are {digest}")
    bad = blind_problems(res, man, blind_path)
    if bad:
        raise Refused("the request manifest's blind input does not re-derive: " + "; ".join(bad))
    for qid in res["kept"]:
        e = man["questions"].get(qid)
        if e is None:
            raise Refused(f"kept question {qid} has no request-manifest entry — no rate")
        if not e["requested"]:
            raise Refused(f"{qid}: the manifest's requested set is empty (a whole-fact absent question has no fact string "
                          f"to read; §8's limit stands) — no rate")


def class_determining(entry: dict, record: dict, classes: dict) -> dict:
    """A3-quinquies's four steps over one manifest entry. `record` is the run's fixture (row id → s/r/o) and `classes`
    each row's trust class. Returns the interpreter's view of the requested proposition and the expected class."""
    rows = sorted(entry["requested"])
    out = {"requested": rows, "facet": entry["facet"], "ambiguous": entry["ambiguous"] or False,
           "answerable": entry["answerable_from_fixture"]}
    # step 1, ambiguity, is the interpreter's FIRST check (the flag travels in `ambiguous`): the class below is the one
    # the question's UNRESOLVED outcome is counted in
    if entry["facet"] == "temporal:event-time" and not entry["answerable_from_fixture"]:
        return {**out, "class_fact": f"{rows[0]}@event-time", "class_set": [f"{r}@event-time" for r in rows],
                "event_time": True, "fixture_class": "absent"}
    strictest = min(ORDER[classes[r]] for r in rows)
    tie = [r for r in rows if ORDER[classes[r]] == strictest]
    return {**out, "class_fact": tie[0], "class_set": tie, "event_time": False,
            "fixture_class": FIXTURE_CLASS[classes[tie[0]]]}
