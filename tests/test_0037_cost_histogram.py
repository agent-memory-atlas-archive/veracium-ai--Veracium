"""specs/0037 v24.3 §8 — the cost figures recompute from the EMITTED histogram
alone (the round-7 reviewer: "the emitted sentence-count histogram so the cost
arithmetic can be checked without the dataset"). Research's
`chunk_sentence_census.py` emits `chunk_sentence_histogram.json`; both ship in
`tests/eval/extraction_speech_act/`. The tail bucket "6+" carries BOTH counts
(63 chunks, 631 sentences) because figure B is a sentence-position fraction and
631 cannot be recovered from 63 — so the recompute sums the bucket SENTENCE
counts, never a label times a chunk count. The reconciliation (bucket sums ==
the file's stated totals) is asserted too, so a regeneration that drops a
bucket fails loudly rather than shifting a percentage."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HIST = ROOT / "tests" / "eval" / "extraction_speech_act" / "chunk_sentence_histogram.json"


def _load():
    return json.loads(HIST.read_text(encoding="utf-8"))


def test_the_two_cost_figures_recompute_from_the_histogram_alone():
    h = _load()
    rows = h["histogram"]
    chunks = sum(b["chunks"] for b in rows)
    sentences = sum(b["sentences"] for b in rows)
    one = next(b for b in rows if str(b["sentences_per_chunk"]) == "1")
    assert one["chunks"] == one["sentences"]                       # a one-sentence chunk is one sentence
    a = (chunks - one["chunks"]) / chunks
    b = (sentences - one["sentences"]) / sentences
    assert (chunks, sentences) == (3372, 6608)
    assert (chunks - one["chunks"], sentences - one["sentences"]) == (1809, 5045)
    assert round(100 * a, 1) == 53.6 and round(100 * b, 1) == 76.3      # 0037 §8, labelled: chunks; sentence positions
    # the reconciliation with the file's own stated totals and figures
    assert h["totals"]["chunks"] == chunks and h["totals"]["sentences"] == sentences
    figs = h["figures"]                                            # fractions, keyed A and B
    a_stated = next(v for k, v in figs.items() if k.startswith("A_"))
    b_stated = next(v for k, v in figs.items() if k.startswith("B_"))
    assert round(100 * a_stated, 1) == 53.6 and round(100 * b_stated, 1) == 76.3
    assert abs(a_stated - a) < 1e-3 and abs(b_stated - b) < 1e-3       # the file's figures ARE the recompute
    # the tail bucket carries its own sentence count (never label × chunks)
    tail = next(b for b in rows if str(b["sentences_per_chunk"]).endswith("+"))
    assert tail["chunks"] == 63 and tail["sentences"] == 631 and tail["sentences"] != 6 * tail["chunks"]
    for bkt in rows:
        if str(bkt["sentences_per_chunk"]).isdigit():
            assert bkt["sentences"] == int(bkt["sentences_per_chunk"]) * bkt["chunks"]   # exact for 1–5
    # the claim travels with the file: neither figure is a capture-loss figure
    assert "NOT_a_capture_loss_figure" in h
