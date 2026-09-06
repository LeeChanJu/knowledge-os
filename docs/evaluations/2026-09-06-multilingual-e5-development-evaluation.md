# Multilingual E5 development retrieval evaluation — 2026-09-06

## Decision

Do not promote `intfloat/multilingual-e5-large` to the production embedding contract and do not
evaluate it on the 15-case held-out suite. It preserved development recall but ranked the expected
SAP roadmap evidence below the working keyword baseline in both dense and hybrid modes.

This applies the governing rule: do not redesign working foundations without evidence; extend
stable contracts rather than replacing the architecture.

## Evaluation boundary

- Development suite: `examples/personal-google-drive-retrieval-eval-v1.json`
- Suite fingerprint: `42eec3ad9eca31a2d21d764f5472450da51147f4501e8e276efc8f047bcc542a`
- Cases: 10 human-grounded phrase-rich questions
- Acceptance suite withheld: `personal-held-out-golden-questions-2026-09-05`
- Corpus: 80 current Google Drive Chunks authorized to `personal` / `google-drive:me`
- Model: `intfloat/multilingual-e5-large`
- Hugging Face revision: `3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3`
- Runtime: ephemeral `sentence-transformers` 5.x environment on Apple Metal (`mps`)
- Dimension: 1,024
- Input contract: `query: ` for questions and `passage: ` for Chunks

The input prefixes follow the model publisher's asymmetric-retrieval instructions. The model card
is at <https://huggingface.co/intfloat/multilingual-e5-large>; its training rationale is described
in <https://arxiv.org/abs/2402.05672>.

Vectors and dependencies were used only in the isolated process. No embedding was written to
Neo4j, no index was changed, and no production dependency or provider configuration was added.

## Reproduced result

| Mode | Recall@5 | MRR@5 | Degraded case |
|---|---:|---:|---|
| Existing keyword | 1.0000 | 1.0000 | none |
| multilingual-E5-large dense | 1.0000 | 0.9250 | `sap-roadmap-gate`, rank 4 |
| Existing keyword + E5 RRF | 1.0000 | 0.9500 | `sap-roadmap-gate`, rank 2 |

After the model was cached, load took 6.823 seconds and encoding 80 passages plus 10 questions took
6.573 seconds. These timings describe only this machine and corpus.

## Consequence

On this English development view alone, the candidate failed the ranking gate. A later, separately
versioned Korean cross-lingual development suite exposed a material keyword gap and selected this
same fixed E5 revision for one held-out acceptance run. That run still failed the recall gate. The
full chronology and final rejection are recorded in
[`2026-09-06-cross-lingual-semantic-selection.md`](2026-09-06-cross-lingual-semantic-selection.md).
