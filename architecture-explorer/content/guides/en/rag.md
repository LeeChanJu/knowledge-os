Providing retrieved evidence to a model before it generates an answer.

## The problem at this stage

An open-book answer can consult a passage instead of relying only on memory. Retrieval makes relevant source context available, but cannot guarantee a correct generated answer.

## Follow one study note

Remembering the word “Joule” can locate a candidate with keyword search. Receiving a result does not establish that its passage answers the question.

## Distinguish the concept from its implementation

Do not confuse retrieval traces with execution of an answer-generation service in this repository.

Knowledge OS supplies retrieval and evidence contracts; a consuming agent or model produces the answer.

## Boundaries the implementation must preserve

These are responsibilities of the referenced **Keyword / Hybrid Retrieval** implementation, not a claim that the concept or learning stage is a separate service.

- Fusion cannot discard authorization requirements.

## Inputs, outputs and data responsibility

These are responsibilities of the referenced **Keyword / Hybrid Retrieval** implementation, not a claim that the concept or learning stage is a separate service.

Inputs: Query, mode, access context and optional vector/model/version.

Outputs: Ranked evidence and trace ID.

Owned data: No additional index service.

## Vector RAG

A RAG approach that uses vector similarity to retrieve evidence. Look for similar meaning, then give the matching passages to a model.

A question about agent tooling retrieves semantically related passages.

This term describes a retrieval pattern, not a separately deployed service or a verified model pipeline.

## Graph RAG

A RAG approach that uses graph relationships to gather context. Follow relevant connections, then explain them using their evidence.

A tool’s related technology and supporting assertions can help explain its place in a project.

The term does not imply global graph summarization or an autonomous reasoning engine.

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
