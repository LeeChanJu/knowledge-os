# Learn IA migration audit

Learn has one entry map and six capability journeys. Existing text is preserved.

| Existing page | Role | Canonical route | Attached capability |
| --- | --- | --- | --- |
| knowledge-os | EXPLANATION | `reference/explanations/knowledge-os` | remember |
| system-of-record | EXPLANATION | `reference/explanations/system-of-record` | sources |
| system-of-context | EXPLANATION | `reference/explanations/system-of-context` | remember |
| knowledge-graph | DEEP DIVE | `reference/deep-dives/knowledge-graph` | relationships |
| ontology | DEEP DIVE | `reference/deep-dives/ontology` | relationships |
| entity | DEEP DIVE | `reference/deep-dives/entity` | remember |
| relationship | DEEP DIVE | `reference/deep-dives/relationship` | relationships |
| assertion | DEEP DIVE | `reference/deep-dives/assertion` | remember |
| claim | EXPLANATION | `reference/explanations/claim` | remember |
| evidence | DEEP DIVE | `reference/deep-dives/evidence` | sources |
| provenance | DEEP DIVE | `reference/deep-dives/provenance` | sources |
| document | DEEP DIVE | `reference/deep-dives/document` | sources |
| document-version | DEEP DIVE | `reference/deep-dives/document-version` | sources |
| chunk | DEEP DIVE | `reference/deep-dives/chunk` | sources |
| embedding | DEEP DIVE | `reference/deep-dives/embedding` | find |
| vector-search | DEEP DIVE | `reference/deep-dives/vector-search` | find |
| full-text-search | DEEP DIVE | `reference/deep-dives/full-text-search` | find |
| graph-traversal | DEEP DIVE | `reference/deep-dives/graph-traversal` | relationships |
| rag | EXPLANATION | `reference/explanations/rag` | find |
| vector-rag | EXPLANATION | `reference/explanations/vector-rag` | find |
| graph-rag | EXPLANATION | `reference/explanations/graph-rag` | find |
| hybrid-retrieval | DEEP DIVE | `reference/deep-dives/hybrid-retrieval` | find |
| proposal | DEEP DIVE | `reference/deep-dives/proposal` | remember |
| approval | DEEP DIVE | `reference/deep-dives/approval` | remember |
| governance | EXPLANATION | `reference/explanations/governance` | remember |
| temporal-validity | DEEP DIVE | `reference/deep-dives/temporal-validity` | correct |
| valid-from | REFERENCE | `reference/concepts/valid-from` | correct |
| valid-to | REFERENCE | `reference/concepts/valid-to` | correct |
| observed-at | REFERENCE | `reference/concepts/observed-at` | correct |
| recorded-at | REFERENCE | `reference/concepts/recorded-at` | correct |
| supersession | DEEP DIVE | `reference/deep-dives/supersession` | correct |
| mcp | REFERENCE | `reference/concepts/mcp` | find |
| knowledge-api | REFERENCE | `reference/concepts/knowledge-api` | find |
| agent | DEEP DIVE | `reference/deep-dives/agent` | find |
| action | DEEP DIVE | `reference/deep-dives/action` | act |
| telemetry | REFERENCE | `reference/concepts/telemetry` | remember |
| evaluation | REFERENCE | `reference/concepts/evaluation` | remember |
| source | REFERENCE | `reference/concepts/source` | remember |
| connectors | REFERENCE | `reference/concepts/connectors` | remember |
| parsing | REFERENCE | `reference/concepts/parsing` | remember |
| chunking | REFERENCE | `reference/concepts/chunking` | remember |
| extraction | REFERENCE | `reference/concepts/extraction` | remember |
| resolution | REFERENCE | `reference/concepts/resolution` | remember |
| event | REFERENCE | `reference/concepts/event` | correct |
| decision | REFERENCE | `reference/concepts/decision` | act |
| sqlite | REFERENCE | `reference/concepts/sqlite` | correct |
| doctor | REFERENCE | `reference/concepts/doctor` | correct |
| migration | REFERENCE | `reference/concepts/migration` | correct |
| recovery | REFERENCE | `reference/concepts/recovery` | correct |
| a2a | REFERENCE | `reference/concepts/a2a` | act |
| verification | REFERENCE | `reference/concepts/verification` | correct |
| start-here | FLOW LESSON | `learn/start-here` | remember, find |
| source-of-truth | EXPLANATION | `reference/explanations/source-of-truth` | sources |
| document-journey | DEEP DIVE | `reference/deep-dives/document-journey` | sources |
| graph-basics | DEEP DIVE | `reference/deep-dives/graph-basics` | relationships |
| ontology-basics | DEEP DIVE | `reference/deep-dives/ontology-basics` | relationships |
| entity-assertion | DEEP DIVE | `reference/deep-dives/entity-assertion` | remember |
| review-before-trust | DEEP DIVE | `reference/deep-dives/review-before-trust` | remember |
| search-methods | DEEP DIVE | `reference/deep-dives/search-methods` | find |
| agent-access | DEEP DIVE | `reference/deep-dives/agent-access` | find |
| read-the-map | EXPLANATION | `reference/explanations/read-the-map` | relationships |
| new-document | DEEP DIVE | `reference/deep-dives/new-document` | remember |
| document-changes | DEEP DIVE | `reference/deep-dives/document-changes` | correct |
| document-deletion | DEEP DIVE | `reference/deep-dives/document-deletion` | correct |
| knowledge-changes | DEEP DIVE | `reference/deep-dives/knowledge-changes` | correct |
| agent-question | DEEP DIVE | `reference/deep-dives/agent-question` | find |
| agent-action | DEEP DIVE | `reference/deep-dives/agent-action` | act |
| storage-boundaries | EXPLANATION | `reference/explanations/storage-boundaries` | remember |
| keep-originals | EXPLANATION | `reference/explanations/keep-originals` | sources |
| keep-versions | EXPLANATION | `reference/explanations/keep-versions` | correct |
| keep-assertions | EXPLANATION | `reference/explanations/keep-assertions` | remember |
| review-gate | EXPLANATION | `reference/explanations/review-gate` | remember |
| local-vector | EXPLANATION | `reference/explanations/local-vector` | find |
| search-complementarity | EXPLANATION | `reference/explanations/search-complementarity` | find |
| adapter-boundary | EXPLANATION | `reference/explanations/adapter-boundary` | find |
| deferred-platforms | EXPLANATION | `reference/explanations/deferred-platforms` | act |
| stable-contracts | REFERENCE | `reference/concepts/stable-contracts` | remember |

No destructive merges are performed. All 76 former non-entry Learn routes are aliases to their classified reference/explanation/deep-dive routes. Operational introductions remain REFERENCE because their preserved content does not supply sufficient steps for a HOW-TO.

## Verification references

Capability-to-finding links were reviewed against the explicit scopes in
`data/verification.json`, not inferred from commit messages. Remember/source paths
link F1 metadata binding, F2 deletion replay and F6 chunk sizing; remember also
links F5 proposal validation and F8 audit persistence. Find links F7 denied-result
evaluation. Relationships links F5. Correction links F1/F2 history, F3 doctor and
supersession checks, F5 validation and F8 audit. Action links F4 exact reviewer and
F8 audit. Every capability links the unexecuted release gate. These navigation
links neither change states nor imply that whole capabilities are verified.
