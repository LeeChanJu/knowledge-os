# Source Authorization Retrieval Evaluation

- Date: 2026-09-05
- Suite: `personal-source-authorization-2026-09-05`
- Suite fingerprint: `4f0b0c9af311eb7c0e2fc13924273a792e9c51377d93d9336133b2cfc323c6b8`
- Evaluator: `source-authorization-policy-v1`
- Retrieval contract: `retrieval-v2`, keyword
- Corpus policy: private Google Drive documents owned by `google-drive:me`

## Result

| Case | Expected | Result |
| --- | --- | --- |
| Authorized source principal | Architecture document retrieved | rank 1 |
| Unrelated principal | No results | pass |
| Correct principal, wrong workspace | No results | pass |

- Positive recall@5: 1.0
- Positive MRR: 1.0
- Policy cases: 2
- Policy pass rate: 1.0
- Overall gate: pass

Each case produced an access-bound retrieval trace and an SQLite evaluation record. Policy cases
use `expected_no_results`; they do not enter recall or reciprocal-rank averages. Any returned result
fails the suite regardless of positive retrieval quality.

## Retrieval-v3 regression

The unchanged authorization suite was rerun after title-aware document-diverse ranking. Positive
recall and MRR remained 1.0, both denial cases returned no results, and policy pass rate remained
1.0. Ranking changes therefore did not weaken the tested workspace/principal boundary.

## Architectural consequence

Current keyword retrieval preserves the tested workspace and source-principal boundaries. There is
no measured need for a separate authorization engine. This suite must remain green when retrieval
ranking, indexing, adapters, or storage implementation changes.

## Limits

This suite covers the current private Google Drive source and keyword retrieval. It does not replace
the graph-level mutation tests, nor does it yet cover public/shared visibility combinations,
semantic/vector retrieval, ACL changes during a request, or identities derived by a production edge
adapter. Those claims require separate evidence.

## Reproduction

```bash
PYTHONPATH=src uv run --no-sync python -m knowledge_os.evaluate \
  examples/personal-authorization-retrieval-v1.json
```
