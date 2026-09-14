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


if __name__ == "__main__":
    counts, n_sessions = chunk_sentence_counts()
    hist = collections.Counter(counts)
    chunks = len(counts)
    multi = sum(1 for c in counts if c > 1)
    sentences = sum(counts)
    sent_in_multi = sum(c for c in counts if c > 1)
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
