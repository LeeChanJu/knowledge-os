## Begin with a question {#begin}

You have useful information in Drive, Notion, PDFs and meeting notes. You ask an assistant: “What do we know about Joule Studio, and why did we decide to investigate it?” Finding a paragraph with the product name answers only part of that question. The paragraph may be old. Another paragraph may contradict it. A meeting may explain the decision, but only some people may be allowed to read it.

Knowledge OS exists to preserve these connections: a statement, its evidence, the exact document state, its history and the decisions made around it. It is a local-first **System of Context**. That means it helps people and software interpret records while the original systems remain responsible for those records. It does not make a model infallible, and it does not replace the applications where work happens.

Read this lesson slowly. At each pause, explain the answer in your own words before continuing. You do not need database, graph or AI experience. The later lessons introduce their technical vocabulary one idea at a time.

## What you will learn {#objectives}

**Prerequisites:** none. A folder of documents and a shared notebook are enough to begin.

By the end, you should be able to explain why finding text is different from understanding its context, why an AI suggestion needs review, and how to trace a statement back to a particular document version. You should also be able to identify which parts of the journey are implemented interfaces and which require a separate person or provider.

## One memo for the whole handbook {#example}

Our running example is a fictional Drive document, **“Joule Studio and agent communication review memo.”** Its educational identifier is **D1**. These labels are not runtime IDs or records in your database.

> We are considering Joule Studio for agent development in the SAP ecosystem. A2A concerns communication between agents. This memo alone does not establish that Joule Studio uses A2A.

This is invented teaching material, not a verified statement about either product. We keep this same memo throughout all four lessons. Its first captured state is V1; a passage from that state is C1. A later edit becomes V2, rather than quietly replacing V1.

Imagine an assistant reports “Joule Studio uses A2A.” The names occur together, but the memo explicitly does not establish that relationship. A fluent answer can therefore be unsupported even when it contains all the right nouns. Keep this mistake in mind: we will use it to understand both evidence and governance.

## What a folder cannot tell us by itself {#problem}

A folder organizes files. It does not automatically tell us that two names refer to one thing, that an assertion depends on an older paragraph, or that a decision relied on a now-deleted source. Those connections have to be represented and maintained.

For example, “BTP” and “SAP Business Technology Platform” may refer to the same technology, but similar names do not prove identical identity. Two people can share a name. Current Knowledge OS identity is conservative: workspace, type and a case-folded name contribute to identity. It is not a general fuzzy matching service. The architecture gives us a place to record knowledge; it does not magically settle ambiguous meaning.

Another example is time. If D1 changes tomorrow, yesterday's answer must still identify the passage it used. Reading today's file is insufficient to reconstruct yesterday's evidence. And if access is revoked, preserving a historical permission snapshot must not grant permanent access to the old material.

## Three ways to see the system {#mental-model}

Think of Knowledge OS as a research notebook with three responsibilities. A notebook is a useful analogy because it connects notes and citations. The analogy stops at enforcement: this system has explicit identities, access checks and recorded state transitions that a paper notebook cannot enforce.

```flow
Evidence memory | Where did this statement come from? Source, Document, Version and Chunk preserve the trail.
Semantic context | What does it concern? Entities and Assertions connect meaning to that evidence.
Governed interface | Who may read, propose, approve or act? Contracts keep these responsibilities distinct.
```

These are viewpoints, not three new services. In the implementation, Neo4j stores connected evidence and canonical knowledge. SQLite stores local operational records such as traces, audits and evaluations. Drive remains the original system. There is no additional knowledge database behind this documentation site.

## What Knowledge OS adds {#adds}

| Without an explicit context model | With the intended boundary |
| --- | --- |
| A copied sentence loses its precise origin | A statement points to the exact supporting Chunk and Version |
| Editing a file obscures the old wording | A new version preserves the earlier evidence identity |
| Two names beside each other appear to imply a relationship | An explicit candidate relationship must be supported and reviewed |
| A past permission is mistaken for continuing permission | Reads check current source-derived authorization |
| A plausible AI output becomes an untracked fact | Proposal and Approval retain a reviewable decision |

Evidence is the material used to support a statement. Meaning concerns what the statement says about identifiable things. Relationships connect those things. History records changes. Governance controls what is accepted and who may act. Retrieval finds appropriate context. None of these alone guarantees that the final answer is correct.

## Why use a graph, and why not only vector RAG? {#retrieval}

A graph represents things and their connections. Starting from a statement, we can ask which passage supports it, which document version contains that passage and which source owns that document. Neo4j currently stores this connected model, plus native full-text and vector indexes. The accepted architecture keeps these together until measured requirements justify another storage choice; it does not claim Neo4j wins every workload.

Full-text retrieval helps with names such as “Joule Studio.” Vector retrieval compares numerical representations of text, which can help when the question uses different words. A graph lookup follows explicitly recorded relationships. These answer different questions: “Where is this name mentioned?”, “Which passage is similar in meaning?”, and “What evidence supports this connection?”

RAG means giving retrieved context to a model before it generates an answer. Vector RAG is one way to retrieve that context. Similarity cannot by itself establish the USES relationship in our memo. Current hybrid retrieval combines keyword and semantic results; bounded graph reads are separate. Production embedding population remains inactive in the documented evidence. Do not read the diagram as an already running three-way retrieval-and-answer pipeline.

## Why an AI does not write canonical knowledge directly {#governance}

The false candidate “Joule Studio USES A2A” can be structurally valid while unsupported by C1. An ontology checks permitted types and relationships; it cannot turn an unsupported statement into truth. A reviewer must examine the evidence.

The candidate enters a **Proposal**. A permitted review records approval or rejection. Only the approved path creates canonical knowledge. “Canonical” means an accepted record in this system, not a universal guarantee of truth. Later corrections preserve history rather than silently rewriting what was accepted.

An agent is an external software consumer that can call tools. It may read authorized evidence and submit governed requests. The MCP adapter does not approve or execute Actions. An Action that changes a System of Record needs its own policy, approval and independently authorized executor. Reading a document does not confer permission to edit it.

## Follow the full journey {#journey}

```flow
Original memo D1 | Drive owns the original record and its permissions.
Observed evidence V1 / C1 | A connector prepares input; ingestion preserves a version and identifiable passages.
Candidate proposal P1 | A separate author or provider proposes meaning with exact evidence.
Review | Validation and authorized approval or rejection decide what becomes canonical.
Entity and Assertion | Neo4j retains accepted statements, their subjects and evidence lineage.
Retrieval and external use | API or MCP returns bounded context; a person or external model uses it.
Governed Action, if requested | A separately approved, authorized adapter may change the original system and record the outcome.
```

The arrows describe responsibilities. Extraction, reasoning and Action execution are not automatic consequences of ingestion. You can stop after capturing evidence and still have a useful system.

## Current implementation and limits {#current}

**CURRENT v0.1:** source adapters, immutable evidence lineage, Proposal/Approval, canonical reads, keyword/semantic retrieval interfaces, bounded graph reads, REST/MCP adapters and local operational records exist. F1 metadata integrity and F2 deletion replay have narrowly scoped executed evidence. They do not verify every stage above.

**TARGET / DEFERRED:** automatic extraction providers, production embedding population, advanced entity resolution, enterprise ReBAC and A2A production integration are not assumed active. Action support includes a bounded Notion executor; it is not general autonomous action. F3–F8 and the release acceptance gate remain open.

> **Common misconception:** “Capturing a document automatically creates accepted knowledge.” Ingestion preserves evidence. A separate candidate and authorized review are required for canonical statements.

## Explain it back {#checks}

```question
D1 contains both names. Why is “Joule Studio USES A2A” still a bad conclusion, even if the ontology allows it?
---
Co-occurrence is not evidence of use. The ontology checks permitted structure; C1 does not support that meaning. The reviewer should reject the candidate rather than promote a structurally valid but unsupported statement.
```

```question
D1 changes tomorrow. What must yesterday's answer retain, and what permission should a new reader need?
---
It must identify the exact old Chunk and DocumentVersion. Historical evidence remains traceable, but current source-derived authorization still controls access; old ACL snapshots do not provide permanent grants.
```

```question
An agent can retrieve C1. Can it now create a Notion page without further steps?
---
No. Retrieval permission is separate from a governed Action request, approval and execution by an authorized adapter. MCP cannot approve or execute the Action itself.
```
