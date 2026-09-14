"""The counting script behind 0037 §8's cost estimate — round 6, finding 3.

The reviewer: *"Section 8 reports 1,809 multi-sentence chunks out of 3,372
chunks, then describes that fraction as approximately 54% of sentence positions.
Taking those counts literally, the multi-sentence chunks contain at least 3,618
sentences … at least 69.8% of sentence positions lie in the multi-sentence
chunks. Neither percentage establishes the loss of routine capture."*

**Correct, and the error is research's.** 53.6% is the fraction of CHUNKS that
hold more than one sentence. It was reported as the fraction of SENTENCE
POSITIONS, which is a different quantity and a larger one. This script prints
both, with the per-chunk sentence counts they are derived from, so the label and
the number cannot come apart again.

A `chunk` is a `?`/`!`-delimited run: under the fail-closed contract only the
text's start/end and a `?`/`!` run establish a boundary, so a routine is
capturable only when it IS the whole chunk.

NEITHER figure is a capture-loss figure. Routines are not uniformly distributed
over sentence positions, and the only measured capture result is draw 5's.
"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))   # the repo's src, resolved from this file (no absolute local path)
from veracium.procedural_gate import norm_ws

DATA = os.environ.get("LME_DATA",
                      os.path.expanduser("~/Datasets/longmemeval/longmemeval_s_cleaned.json"))


def chunk_sentence_counts(limit_sessions=500):
    seen, counts = set(), []
    for it in json.load(open(DATA)):
        for sid, sess in zip(it.get("haystack_session_ids", []), it.get("haystack_sessions", [])):
            if sid in seen:
                continue
            seen.add(sid)
            for t in sess:
                if not (isinstance(t, dict) and t.get("role") == "user" and t.get("content")):
                    continue
                for chunk in re.split(r"[?!]+\s*", norm_ws(t["content"])):
                    c = chunk.strip()
                    if c:
                        counts.append(len([x for x in re.split(r"(?<=[.])\s+", c) if x.strip()]))
            if len(seen) >= limit_sessions:
                return counts, len(seen)
    return counts, len(seen)


def summarise(counts, *, tail_from=6):
    """The ONE computation both the printed report and the emitted artifact read.

    Round-7, the reviewer: *"add ... the emitted sentence-count histogram so the
    cost arithmetic can be checked without the dataset."* The histogram is
    bucketed with an exact tail: the `6+` bucket carries BOTH its chunk count and
    its sentence count, so `chunks` and `sentences` reconcile against the buckets
    exactly and each figure is recomputable from the file alone. A tail bucket
    carrying only a chunk count would leave B underivable.
    """
    hist = collections.Counter(counts)
    buckets = []
    for k in sorted(hist):
        if k < tail_from:
            buckets.append({"sentences_per_chunk": str(k), "chunks": hist[k],
                            "sentences": hist[k] * k})
    tail_c = sum(hist[k] for k in hist if k >= tail_from)
    tail_s = sum(hist[k] * k for k in hist if k >= tail_from)
    if tail_c:
        buckets.append({"sentences_per_chunk": f"{tail_from}+", "chunks": tail_c,
                        "sentences": tail_s})
    chunks, sentences = len(counts), sum(counts)
    single = hist[1]
    multi, sent_in_multi = chunks - single, sentences - single
    assert sum(b["chunks"] for b in buckets) == chunks, "buckets must reconcile to the chunk total"
    assert sum(b["sentences"] for b in buckets) == sentences, "buckets must reconcile to the sentence total"
    return {"buckets": buckets, "chunks": chunks, "sentences": sentences,
            "multi_sentence_chunks": multi, "sentences_in_multi_sentence_chunks": sent_in_multi,
            "figure_A_multi_chunk_fraction": round(multi / chunks, 4),
            "figure_B_sentence_position_fraction": round(sent_in_multi / sentences, 4)}


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    counts, n_sessions = chunk_sentence_counts()
    s = summarise(counts)
    hist = collections.Counter(counts)
    chunks, sentences = s["chunks"], s["sentences"]
    multi, sent_in_multi = s["multi_sentence_chunks"], s["sentences_in_multi_sentence_chunks"]
    print(f"  sessions {n_sessions}   chunks {chunks:,}   sentences {sentences:,}\n")
    print("  per-chunk sentence counts (the numbers both figures come from):")
    for k in sorted(hist):
        print(f"    {k:>3} sentence(s): {hist[k]:>5} chunks  ({hist[k]*k:>6,} sentences)")
    print()
    print(f"  A. CHUNKS holding more than one sentence     : {multi:,}/{chunks:,} = {multi/chunks:.1%}")
    print(f"  B. SENTENCE POSITIONS in multi-sentence chunks: {sent_in_multi:,}/{sentences:,} = {sent_in_multi/sentences:.1%}")
    print()
    print("  A is the figure 0037 §8 reported. It was LABELLED as B. They are")
    print("  different quantities and B is the larger. Neither is a capture-loss")
    print("  figure: the only measured capture result is draw 5's 0 of 6 rows.")

    if "--emit" in sys.argv:
        out = sys.argv[sys.argv.index("--emit") + 1]
        doc = {
            "artifact": "chunk_sentence_census",
            "purpose": ("the per-chunk sentence-count histogram behind 0037 section 8's cost "
                        "arithmetic, emitted so both figures can be recomputed WITHOUT the dataset"),
            "chunking_rule": ("a chunk is a `?`/`!`-delimited run of one user turn (norm_ws applied); "
                              "sentences within a chunk are split on a period followed by whitespace. "
                              "Under the fail-closed capture contract only the text start/end and a "
                              "`?`/`!` run establish a boundary, so a routine is capturable only when "
                              "it IS the whole chunk"),
            "corpus": {"dataset": os.path.basename(DATA), "dataset_sha256": _sha256(DATA),
                       "sessions": n_sessions, "role_filter": "user"},
            "generated_by": {"script": os.path.basename(__file__),
                             "script_sha256": _sha256(os.path.abspath(__file__))},
            "histogram": s["buckets"],
            "totals": {"chunks": chunks, "sentences": sentences,
                       "multi_sentence_chunks": multi,
                       "sentences_in_multi_sentence_chunks": sent_in_multi},
            "figures": {
                "A_multi_sentence_chunk_fraction": s["figure_A_multi_chunk_fraction"],
                "B_sentence_positions_in_multi_sentence_chunks": s["figure_B_sentence_position_fraction"]},
            "recompute": {
                "chunks": "sum(b.chunks for b in histogram)",
                "sentences": "sum(b.sentences for b in histogram)",
                "A": "(chunks - histogram['1'].chunks) / chunks",
                "B": "(sentences - histogram['1'].sentences) / sentences"},
            "NOT_a_capture_loss_figure": ("neither A nor B measures capture loss: routines are not "
                                          "uniformly distributed over sentence positions, and the only "
                                          "measured capture result is draw 5's")}
        with open(out, "w") as fh:
            json.dump(doc, fh, indent=2, sort_keys=False)
            fh.write("\n")
        print(f"\n  wrote {out}  sha256 {_sha256(out)}")
