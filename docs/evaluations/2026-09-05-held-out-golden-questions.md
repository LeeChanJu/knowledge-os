# Held-out Golden Questions Keyword Evaluation

- Date: 2026-09-05
- Suite: `personal-held-out-golden-questions-2026-09-05`
- Suite fingerprint: `14d69cd4216288fb9cdf03db47db5c5ebc617e383ccf5277828f9286f1f02f06`
- Evaluator: `held-out-golden-question-keyword-v1`
- Corpus: 12 current Google Drive documents
- Scored corpus: the source risk register containing the questions is excluded
- Retrieval contract: `retrieval-v2`, keyword, recall at 5

## Why exclusion is required

`12_Known_Risks.md` contains all 15 Golden Questions and their expected-answer criteria. Scoring
that document would measure benchmark memorization rather than retrieval of the underlying design
evidence. Each case therefore declares its stable Document ID in `excluded_document_ids`.

The evaluator fetches up to 100 candidates for exclusion cases, removes excluded documents, and
then applies the case's original limit. The trace preserves the actual candidate request and the
evaluation record preserves both declared exclusions and excluded results. Empty exclusions remain
absent from fingerprint serialization, preserving fingerprints of existing suites.

## Result

| Metric | Result | Gate |
| --- | ---: | ---: |
| Cases | 15 | 15 |
| Mean recall@5 | 0.9333 | 0.9 |
| Mean reciprocal rank | 0.6911 | reported |
| Passed | yes | yes |

Fourteen expected documents appeared in the top five. `GQ-001` did not retrieve the architecture
document. `GQ-005` retrieved its expected ontology document at rank five. Several other correct
documents ranked second or third, so MRR is materially below the phrase-rich baseline even though
the recall gate passes.

## Architectural consequence

Keep Neo4j keyword retrieval as the working baseline: it passes the measured top-five recall gate,
and this result does not justify a new search store or framework. Do not claim ranking quality is
complete. The next semantic or hybrid experiment should be accepted only if it improves this exact
held-out suite—especially `GQ-001`, `GQ-005`, and aggregate MRR—without weakening authorization or
exact-identifier retrieval.

## Reproduction

```bash
PYTHONPATH=src uv run --no-sync python -m knowledge_os.evaluate \
  examples/personal-golden-questions-retrieval-v1.json
```

## Retrieval-v3 evidence

The unchanged suite and fingerprint were rerun after a bounded title-token and document-diversity
experiment. A title-only first attempt improved MRR to 0.750 but reduced recall to 0.8667 because
multiple chunks from one boosted document crowded out other documents; that run failed the gate and
remains in SQLite as negative evidence.

The accepted `lexical-title-diversity-v1` ranker keeps the title signal but admits at most two
chunks per document in the early pass, then appends every deferred chunk in score order so no
candidate is discarded. The final retrieval-v3 result was:

| Metric | Retrieval-v2 | Retrieval-v3 |
| --- | ---: | ---: |
| Mean recall@5 | 0.9333 | 1.0000 |
| Mean reciprocal rank | 0.6911 | 0.8000 |
| Passed | yes | yes |

`GQ-001` moved from absent to rank one. All 15 expected documents appeared in the top five. The
phrase-rich suite retained recall/MRR 1.0, and the authorization suite retained positive
recall/MRR 1.0 with policy pass rate 1.0. The final 15-case run averaged 4.444 ms, with observed p95
8.230 ms and maximum 9.332 ms; the prior retrieval-v2 run averaged 13.793 ms with a cold 114.447 ms
maximum, so this corpus shows no measured latency regression. These are local small-corpus
measurements, not a general performance claim.
