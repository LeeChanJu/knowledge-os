# Personal Google Drive Keyword Retrieval Baseline

- Date: 2026-09-05
- Suite: `personal-google-drive-baseline-2026-09-05`
- Suite fingerprint: `4780846fa2e39a76d5d1b6226d4d29c4f6abd08037a757ad30e7308c15208061`
- Evaluator: `human-grounded-keyword-v1`
- Corpus: 11 current documents, 72 chunks, one `google-drive-v1` Source
- Access context: workspace `personal`, principal `google-drive:me`
- Retrieval contract: keyword, limit 5

## Result

| Metric | Result | Gate |
| --- | ---: | ---: |
| Cases | 10 | 10 |
| Mean recall@5 | 1.0 | 0.9 |
| Mean reciprocal rank | 1.0 | reported |
| Passed | yes | yes |

Every expected document ranked first. The run wrote ten access-bound retrieval traces and ten
evaluation records to the existing SQLite operations store.

## Architectural consequence

This corpus provides no measured reason to replace Neo4j full-text retrieval or add another search
database, vector store, or retrieval framework. Keyword retrieval remains the baseline. Semantic
and hybrid retrieval should be compared only after reproducible embeddings and a harder paraphrase
suite exist.

## Retrieval v2 regression

Natural-language Golden Question `GQ-008` contains `Note/Concept`. Under retrieval v1 the slash was
passed to Lucene syntax and produced `Neo.ClientError.Procedure.ProcedureCallFailed`, recorded as
`error:2d547445-585c-4852-904f-bc0df6c4691b`. Retrieval v2 converts input to quoted literal Unicode
terms. The same question then completed normally, and this ten-case suite retained recall@5 1.0 and
MRR 1.0 with the unchanged suite fingerprint.

An exploratory run of all 15 source-defined Golden Questions was not promoted into a regression
suite. The questions and expected-answer criteria occur verbatim in `12_Known_Risks.md`, causing
that document to rank first for most cases. This is benchmark leakage rather than proof of broad
question-answer retrieval quality. A future suite must keep natural-language questions outside the
indexed corpus or use independently paraphrased held-out questions.

Retrieval-v3 later added the measured `lexical-title-diversity-v1` ranker without changing this
suite or its fingerprint. Its rerun retained recall@5 1.0 and MRR 1.0, so the harder held-out-suite
improvement did not regress these phrase-rich cases.

## Limits

This is a document-retrieval evaluation, not an answer-quality evaluation. The cases use distinctive
English concepts grounded in the current seed documents. It does not yet prove semantic recall,
cross-language recall, temporal answer selection, citation completeness, prompt-injection safety,
or authorization denial. Those require separate versioned cases and must not be inferred from this
passing result.

## Reproduction

```bash
PYTHONPATH=src uv run --no-sync python -m knowledge_os.evaluate \
  examples/personal-google-drive-retrieval-eval-v1.json
```
