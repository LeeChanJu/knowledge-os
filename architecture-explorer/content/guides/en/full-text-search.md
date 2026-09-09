Finding text using words indexed from the content.

## The problem at this stage

Like a book index, it helps locate passages mentioning a term. Exact names and distinctive terms often provide useful retrieval signals.

## Follow one study note

Remembering the word “Joule” can locate a candidate with keyword search. Receiving a result does not establish that its passage answers the question.

## Distinguish the concept from its implementation

User text is treated as literal terms, not arbitrary Lucene syntax. Keyword ranking also includes title signals and early document diversity.

Neo4j full-text candidates are permission-filtered and ranked by the existing retrieval path.

## Boundaries the implementation must preserve

- Fusion cannot discard authorization requirements.

## Inputs, outputs and data responsibility

- Query, mode, access context and optional vector/model/version.
- Ranked evidence and trace ID.
- No additional index service.

## Compare nearby concepts

| Distinction | Question / role | Boundary |
|---|---|---|
| Keyword | Search remembered wording | Terms and access filtering |
| Semantic | Search similar meaning | Compatible embeddings and populated material |
| Graph | Follow recorded relationships | Recorded relations and evidence scope |

<!-- CHECKS -->

### Does a vector index mean every note is ready for semantic search?

No. Compatible models, embedded material and accepted provider selection are separate requirements. Inspect current population and provider deferrals.

### Is the existence of code or a test file sufficient to trust the feature?

No. Inspect recorded outcomes, revisions, environments and verification scope. Account for open issues and deferrals; browsing this guide does not execute production tests.
