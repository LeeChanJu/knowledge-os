## Begin with ownership {#begin}

When a Drive document is edited, which system decides what the original file now contains? Drive does. When Knowledge OS records a statement supported by that file, which system holds the statement's evidence connections? Knowledge OS does. These responsibilities are related but not interchangeable.

A **System of Record** is responsible for an original business record. A **System of Context** preserves connections that help interpret records: meaning, evidence, history and decisions. “Source of truth” here describes responsibility for the original record. It does not mean every sentence in an original document is factually correct.

## What you will learn {#objectives}

**Prerequisite:** read Start Here. You need only the distinction between an original memo and a statement made about it.

After this lesson you should be able to decide which system owns a change, explain why evidence snapshots are retained without replacing Drive, and explain why old permission records cannot authorize today's reads.

## Revisit the same memo {#example}

Our fictional **“Joule Studio and agent communication review memo”**, D1, says we are considering Joule Studio for agent development in the SAP ecosystem. It mentions A2A but explicitly does not establish that Joule Studio uses it. D1, V1 and C1 are educational labels, not actual records.

Drive manages the original file, its provider identity and access controls. The connector observes an authorized state and translates it into the ingestion contract. Knowledge OS records a logical Document, a particular DocumentVersion and exact Chunks. An Assertion can later point to a supporting Chunk through governance.

Think of a library book and a research notebook. The library catalog identifies the book; your notebook records what you learned and the page you cited. Editing your note does not edit the book. The analogy has a limit: Knowledge OS also preserves machine-readable identities and checks source-derived authorization, rather than relying on a reader to remember citation and access rules.

## Two different questions {#comparison}

| Question | Responsible record or boundary |
| --- | --- |
| What is in the original file now? | Drive and its current file state |
| Which exact wording did this assertion use? | Chunk and immutable DocumentVersion |
| Which logical file do V1 and V2 belong to? | Document identity |
| Who accepted a proposed statement? | Proposal/Approval history |
| May this caller inspect the evidence now? | Current source-derived authorization and workspace checks |
| Who may change an external page? | A separately authorized System-of-Record adapter |

A context graph can help answer why a decision was made because a Decision retains supporting evidence and relevant metadata. It does not automatically infer every cause from a folder. A decision trace must be represented by actual records and supported by actual evidence; an appealing diagram cannot create it.

## What happens when the original changes? {#changes}

Suppose the author adds a clarification to D1. It is still the same logical document, but its observed state is now V2. Knowledge OS can preserve V1 and C1 so an older Assertion does not silently change its evidence. Current-version pointers and lifecycle information serve a different purpose from immutable history.

A new document version does not automatically rewrite an accepted Assertion. If a knowledge statement needs correction, a separate governed proposal must identify the appropriate change. This distinction prevents an innocuous source edit from silently altering the system's accepted meaning.

Now suppose D1 disappears from a complete provider snapshot. The connector can report a deletion observation. A tombstone records the lifecycle change; it is not permission to erase every historical record. Current evidence becomes unavailable as required by the read boundary, while historical lineage remains in storage. F2 concerns deterministic replay of that observation, not proof that every provider deletion scenario is solved.

```flow
Drive D1 changes | The original owner changes content or permissions.
Connector observes | An authorized provider snapshot becomes contract input.
Knowledge OS captures V2 | Document identity remains; the previous evidence state is preserved.
Knowledge review, if needed | A separate Proposal may correct accepted meaning; no silent rewrite.
```

## Permission is a current question {#permissions}

Imagine Alice could read V1 yesterday. Today the source owner revokes her access. Keeping yesterday's authorization snapshot is useful for explaining the old observation, but it must not give Alice perpetual access to C1.

The accepted contract distinguishes the original evidence authorization snapshot from the latest authorization used to decide access. Evidence reads check workspace, document lifecycle and current source-derived permissions. An exact evidence bundle fails closed when a requested item cannot be returned; it does not silently present a partial bundle as complete support.

> **Common misconception:** “Immutable history means everyone who once saw it can always retrieve it.” Preservation and authorization answer different questions. A record may remain stored while a caller is no longer allowed to read it.

Provider permissions are also not identical to a complete enterprise authorization model. The repository documents source ACL limitations and defers a full ReBAC engine until measured requirements justify it. Do not infer arbitrary organization-wide relationship permissions from the existence of a graph database.

## Why preserve these boundaries? {#why}

Without clear ownership, the copied file and the original can become competing records. Which one should a user correct? Which permissions win? Which deletion should propagate? The architectural boundary avoids pretending that a derived context store has become the authoritative business application.

This does not mean Knowledge OS stores no text. Exact evidence requires preserved content and version lineage. The distinction is responsibility: captured evidence supports interpretation and audit; it does not take ownership of the original editing workflow.

Likewise, SQLite's operational records are not a second canonical knowledge model. A retrieval trace can describe a request, while Neo4j holds the evidence it accessed. Separate stores have distinct responsibilities and failure modes; they do not imply a distributed transaction.

## Current implementation and limits {#current}

**CURRENT v0.1:** the accepted ADR assigns original records to source systems, semantic context and evidence to Neo4j, and local operations to SQLite. The Source contract describes stable source identity, connector binding and checkpoints. Document and Evidence reads expose bounded catalogs and exact evidence through service adapters.

A bounded Notion Action executor exists. Its ability to create or compensate an external record does not transfer original ownership into Neo4j. The executor must follow the declared policy, approval and execution-claim boundary. General knowledge access is not mutation authority.

**TARGET / DEFERRED:** SAP's broader System of Context vision is conceptual inspiration, not a statement that this repository implements SAP's agent platform, automatic decision learning or enterprise authorization. Production A2A, advanced resolution and ReBAC remain deferred. Open audit findings and the unexecuted release gate continue to limit correctness claims.

## Explain it back {#checks}

```question
If Knowledge OS preserves the text of V1, has it become the System of Record? Explain the difference without saying that it stores no text.
---
No. Preserved text is evidence for historical interpretation. Drive still owns the original file and editing workflow. Ownership and responsibility, rather than the mere presence of a copy, distinguish the roles.
```

```question
An author edits D1 and withdraws a claim. Why are a new Version and a new governed knowledge decision different operations?
---
The Version captures a changed source state. A governed decision determines how accepted meaning should change. Keeping them separate preserves the evidence used before the edit and prevents silent canonical rewrites.
```

```question
Alice's old permission snapshot allows access, but the latest source-derived permission does not. Which should decide today's Evidence request, and why retain the old snapshot?
---
The current permission decides access. The old snapshot remains provenance about what was observed then; it is not a permanent access grant.
```
