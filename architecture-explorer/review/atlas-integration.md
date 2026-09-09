# Complete Atlas documentation integration

## Scope

All 77 source documents now have canonical dispositions: 68 guides, seven merges,
and two map redirects. Both languages contain all 68 Markdown guides and expanded
explanations for all 116 roadmap nodes. The 145 roadmap edges are unchanged.
The separate repository Architecture graph remains 214 nodes / 372 edges.

The original source articles remain available in an explicitly marked archive.
Merged topics preserve their distinct explanations inside the owning guide.
The whole-flow position strip and ancestor trail remain available while reading;
implementation references preserve the original `atlas` route for returning.

## Review routes

- `/#/ko-KR/runtime?node=version&root=support&open=support,version`
- `/#/ko-KR/reference/guide/document-version`
- `/#/ko-KR/reference/guide/assertion` (includes Claim)
- `/#/ko-KR/reference/guide/rag` (includes vector and graph RAG)
- `/#/ko-KR/reference` (68 canonical guides; merged-title search)
- `/#/ko-KR/archive/document/claim` (preserved original)

Replace `ko-KR` with `en` for English. Browser screenshots are generated at
`test-results/integrated-guide-{ko-KR,en}.png` and `test-results/guide-mobile.png`.

## Validation boundaries

Integration tests reject missing merge members, duplicate aliases, broken evidence,
unreachable map locations, wrong-language files and stale source reconciliation.
Browser coverage opens all 77 canonical/alias mappings in both languages, checks
comparison tables, answers, search/filter/empty states, archives, back/forward,
exact origin preservation, themes, mobile width and glossary navigation.
Existing Atlas journey and architecture interaction regressions remain in scope.
No production tests or database writes are part of this documentation change.

## Remaining limits

This completes the implementation backlog for the approved IA. It does not prove
that a first-time reader can explain the system in one minute; that requires a
real reader review. It does not close F3–F8 or execute the release acceptance gate.
Educational source/translation reconciliation is not production verification.
