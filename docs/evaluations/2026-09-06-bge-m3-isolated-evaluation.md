# BGE-M3 isolated retrieval evaluation — 2026-09-06

## Decision

Do not replace the working 1,536-dimensional vector-index configuration or embed the personal
corpus with BGE-M3 yet. The fixed local model is executable and multilingual, but this first
measured dense and hybrid experiment did not beat the current keyword baseline on the checked-in
held-out suite.

This follows the governing rule: do not redesign working foundations without evidence; extend
stable contracts rather than replacing the architecture.

## Reproducible inputs

- Model: `BAAI/bge-m3`
- Hugging Face revision: `5617a9f61b028005a4858fdac845db406aefb181`
- Runtime: `sentence-transformers` 5.x in an ephemeral `uv` environment
- Device: Apple Metal (`mps`)
- Dense vector dimension: 1,024
- Corpus: 80 current Chunks authorized to `personal` / `google-drive:me`
- Suite: `examples/personal-golden-questions-retrieval-v1.json`
- Cases: 15, recall and reciprocal rank at 5
- Leakage control: each case's declared risk-register Document exclusion was applied before rank 5

No embeddings were written to Neo4j. The experiment loaded current authorized Chunk text, produced
normalized dense vectors in memory, ranked with exact cosine similarity, and discarded the vectors
when the process exited. Hybrid used the existing bounded reciprocal-rank fusion implementation
over five keyword and five semantic Chunk candidates.

## Result

| Mode | Recall@5 | MRR@5 |
| --- | ---: | ---: |
| Existing keyword | 1.0000 | 0.7744 |
| BGE-M3 dense | 0.9333 | 0.6944 |
| Existing keyword + BGE-M3 RRF | 1.0000 | 0.7489 |

Embedding 80 Chunks and 15 questions took 9.695 seconds after model load on this machine. This is a
small-corpus local measurement, not a general latency claim.

Dense retrieval missed `GQ-015` at rank five. It improved individual ranks for `GQ-005`, `GQ-013`,
and `GQ-014`, but degraded enough other cases that aggregate recall and MRR were lower. The simple
hybrid retained full recall but also reduced MRR relative to keyword.

## Consequence

BGE-M3 remains a viable local-first candidate, not the selected production provider. Do not change
the Neo4j index from 1,536 to 1,024 dimensions on this evidence. A later experiment may test query
instructions, document-title composition, or calibrated fusion, but it must use the same held-out
suite and preserve authorization before any production embedding write or contract change.

## Title and instruction follow-up

The two named low-cost variants were subsequently evaluated against the same fixed model revision,
authorized current Google Drive corpus, risk-document exclusion, and 15 held-out questions. All
vectors remained in memory and no production Chunk was modified.

| Dense input | Recall@5 | MRR@5 |
| --- | ---: | ---: |
| Chunk body, raw question (reproduction) | 0.9333 | 0.6944 |
| Document title + Chunk body, raw question | 0.8000 | 0.6111 |
| Document title + passage label, retrieval-instructed question | 0.8667 | 0.6222 |

The body-only reproduction exactly matched the earlier aggregate result and again missed `GQ-015`.
Title composition additionally missed `GQ-004` and `GQ-014`; the instructed-query variant missed
`GQ-011` and `GQ-015`. Encoding the three corpus/query variants took 18.659 seconds after model
load on the same machine.

These results close the two immediate follow-up hypotheses without selecting a provider. Do not
tune fusion weights on this held-out suite: doing so would turn the evaluation set into training
data and weaken the evidence. A future attempt needs a separately versioned development set or a
different fixed model candidate before this suite is used once for acceptance.
