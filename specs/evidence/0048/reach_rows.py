"""0048 §2c-ii rows 5 and 7 as commands (round 1's archive note: "attach the executable script/output behind §2c-ii's
prose-described reproduction"). Run from an export of the pin:

    PYTHONPATH=<export>/src python reach_rows.py <export> 5|7

Row 5: with SLOW mapped to DECAY, `expire()` under factor 2.0 / nan / 0.5 on one SLOW edge at 0.9 observed 400 days
    ago, then the user's full edge listing. Prints one line per factor: what expire() returned and what the read did.
Row 7: every pydantic field in `veracium.schema` whose metadata carries a numeric bound, with its model's `frozen` and
    `validate_assignment`.
It asserts that `veracium` is imported from <export>, so a run cannot silently measure another tree.
"""
import datetime as dt
import pathlib
import sys

root, row = pathlib.Path(sys.argv[1]).resolve(), sys.argv[2]
import veracium  # noqa: E402

assert pathlib.Path(veracium.__file__).resolve().is_relative_to(root), f"veracium imported from {veracium.__file__}"

if row == "5":
    from veracium import Edge, EvidenceAuthor, Provenance
    from veracium import schema as S
    from veracium.config import MemoryConfig
    from veracium.lifecycle import expire
    from veracium.store.sqlite import SqliteStore

    now = dt.datetime(2026, 10, 10, tzinfo=dt.timezone.utc)
    saved = S.DEFAULT_EXPIRY[S.Volatility.SLOW]
    S.DEFAULT_EXPIRY[S.Volatility.SLOW] = S.ExpiryBehavior.DECAY
    try:
        for f in (2.0, float("nan"), 0.5):
            st = SqliteStore(":memory:")
            st.add_edge(Edge(id="e-1", user_id="u", subject="user", relation="works_on", object="Atlas",
                             volatility=S.Volatility.SLOW,
                             provenance=Provenance(author_of_evidence=EvidenceAuthor.USER, evidence_ref="ev",
                                                   confidence=0.9, observed_at=now - dt.timedelta(days=400))))
            try:
                r = expire(st, "u", MemoryConfig(decay_factor=f), now=now)
            except Exception as ex:  # noqa: BLE001 — the outcome is the measurement
                r = f"{type(ex).__name__}"
            try:
                es = st.edges("u", active_only=False, include_quarantined=True)
                read = f"read ok, confidence {es[0].provenance.confidence}"
            except Exception as ex:  # noqa: BLE001
                e0 = ex.errors()[0] if hasattr(ex, "errors") else {"loc": (), "msg": str(ex)}
                read = f"read raises {type(ex).__name__}: {'.'.join(map(str, e0['loc']))}: {e0['msg']}"
            print(f"factor {f}: expire -> {r}; {read}")
    finally:
        S.DEFAULT_EXPIRY[S.Volatility.SLOW] = saved
elif row == "7":
    import annotated_types as at
    import pydantic
    from veracium import schema

    out = []
    for name, obj in sorted(vars(schema).items()):
        if isinstance(obj, type) and issubclass(obj, pydantic.BaseModel) and obj.__module__ == schema.__name__:
            for fname, fi in obj.model_fields.items():
                b = [repr(m) for m in fi.metadata if isinstance(m, (at.Ge, at.Le, at.Gt, at.Lt, at.Interval))]
                if b:
                    out.append((name, fname, b, obj.model_config.get("frozen", False),
                                obj.model_config.get("validate_assignment", False)))
    for o in out:
        print(f"{o[0]}.{o[1]} {o[2]} frozen={o[3]} validate_assignment={o[4]}")
    print(f"{len(out)} bounded field(s)")
else:
    sys.exit(f"no such row {row!r}: rows 5 and 7 only (row 8 is census_0048.py)")
