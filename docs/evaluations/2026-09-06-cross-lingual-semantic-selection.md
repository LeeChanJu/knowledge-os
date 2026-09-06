# Cross-lingual semantic development and E5 acceptance — 2026-09-06

## Measured need

The personal source corpus is predominantly English while the owner normally asks questions in
Korean. The existing English development suite had keyword recall/MRR of 1.0/1.0, leaving no room
to measure whether a multilingual embedding improved this real cross-language use case.

## Versioned development suite

`examples/personal-multilingual-development-retrieval-v1.json` contains ten natural Korean queries
grounded in the same ten human-labeled facts as the existing phrase-rich development suite. It is
explicitly a model-selection set, not an independent acceptance set. Its queries have zero exact
overlap with the 15 English held-out queries.

- suite ID: `personal-cross-lingual-development-2026-09-06`
- evaluator fingerprint: `6ab8f35001beb97d09096d5d82b3944349d299fcf7d018942d02d341db5373dd`
- file SHA-256: `67708c4bd9397e304456b1dd9fe58d741614e2b63b5c3fb42a0be17a2491a4e8`
- corpus: 80 current Google Drive Chunks authorized to `personal` / `google-drive:me`
- metric: document-deduplicated recall and reciprocal rank at five

The checked-in evaluator recorded the keyword baseline and ten per-case evaluation/trace records:

| Mode | Recall@5 | MRR@5 |
|---|---:|---:|
| Existing keyword | 0.8000 | 0.6750 |

Keyword returned no result for `KO-DEV-001` and `KO-DEV-007`; the expected documents ranked second
for `KO-DEV-008` and fourth for `KO-DEV-010`.

## In-memory candidate comparison

Both fixed models encoded the same corpus and questions on Apple Metal. BGE-M3 used raw passage and
query text, matching its earlier best variant. Multilingual E5 used the publisher-required
`passage: ` and `query: ` prefixes.

| Candidate | Dense recall/MRR | Hybrid recall/MRR |
|---|---:|---:|
| BGE-M3 `5617a9f...` | 1.0000 / 0.9500 | 1.0000 / 1.0000 |
| multilingual-E5-large `3d7cfbd...` | 1.0000 / 1.0000 | 1.0000 / 1.0000 |

E5 was selected for one acceptance run because its dense mode alone ranked every expected document
first. This new cross-lingual evidence superseded the earlier decision to stop after its weaker
English development result; it did not erase that negative result.

## One-time held-out acceptance

The selected E5 revision was evaluated once against
`personal-held-out-golden-questions-2026-09-05` (file SHA-256
`158ad689764014666494c7cdb7d164591a745946afaa6eb2abc66723ab7c44ad`). Each case's declared
risk-register Document was excluded before rank five.

| Mode | Recall@5 | MRR@5 |
|---|---:|---:|
| Existing keyword | 1.0000 | 0.8000 |
| E5 dense | 0.9333 | 0.7667 |
| Existing keyword + E5 RRF | 0.9333 | 0.8333 |

Dense and hybrid both missed `GQ-005`. Hybrid improved MRR but lost the keyword baseline's complete
recall, so the candidate fails acceptance.

## Decision

Do not install E5 as the production embedding provider, do not change the 1,536-dimensional Neo4j
index, and do not write any candidate vectors. BGE-M3 and multilingual-E5-large remain measured
negative evidence. The Korean suite may guide later candidates, but the used held-out suite must not
be treated as unseen again; a future trustworthy acceptance decision requires newly authored,
human-reviewed holdout questions or a materially new corpus.

This decision evidence is included in verified recovery set `20260905T182720Z-de66d6f7`, captured
from clean commit `4e9974b`. Its hashes, SQLite integrity, and Neo4j archive consistency passed. The
prior recovery generation retains the latest isolated restore-drill evidence; no schema, contract,
or DBMS change justified repeating that destructive-path exercise for this evaluation-only delta.
