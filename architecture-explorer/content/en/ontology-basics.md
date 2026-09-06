## A connection needs a meaning {#begin}

A graph can connect two things. An ontology describes what kinds of things the model recognizes and which relationships are meaningful or allowed between them. These are different responsibilities: being able to store a connection does not establish its meaning, and a permitted connection does not establish its truth.

This lesson starts with a spreadsheet, then returns to our fictional Joule Studio memo. You will see why the same candidate can pass a structural check and still deserve rejection.

## What you will learn {#objectives}

**Prerequisites:** the document journey, especially the difference between evidence, a candidate and an approved statement. If tables are unfamiliar, think of a contact list: each row identifies a contact and each column describes an attribute.

After this lesson you should be able to distinguish Data, Graph, Knowledge Graph and Ontology; explain one accepted and one rejected type combination; and describe the exact limits of this repository's validator.

## Start from a table {#spreadsheet}

Imagine the teaching memo has a fictional author, Min, and mentions an organization, Example Research. These are invented records within the same example, not claims about a real person's employment.

| People | Type | Employer reference |
| --- | --- | --- |
| Min | Person | Example Research |

| Organizations | Type |
| --- | --- |
| Example Research | Organization |

Rows represent individual things. Columns describe their properties. Matching the employer reference to the organization row connects two records. In database language this resembles a join. Turning that connection into a labeled graph gives us “Min WORKS_FOR Example Research.” The drawing helps us see the relationship; it does not by itself define which types may participate.

The spreadsheet analogy is useful for moving from familiar records to objects and links. It is not an exact mapping of every spreadsheet join to a valid semantic relationship. Two cells can contain the same word without describing the same entity, and matching values cannot establish employment.

## Four concepts, four questions {#comparison}

| Concept | Question it answers | Example |
| --- | --- | --- |
| Data | What values were recorded? | The text “Min” and “Example Research” |
| Graph | What is connected, and how? | Two nodes joined by a labeled relationship |
| Knowledge Graph | How is modeled knowledge represented through connected records? | Entities, statements and their evidence context |
| Ontology | What types and relationship rules does this model permit? | Person WORKS_FOR Organization |

Neo4j is the current database technology. It is not itself the ontology. A knowledge graph can use an ontology to constrain its semantic model, but the ontology is not identical to all stored graph data. Document lineage relationships and documentation Explorer edges also have different roles from registered semantic predicates.

```flow
Values in a table | Min; Example Research; employer reference.
A labeled connection | Min → WORKS_FOR → Example Research.
A type-level rule | Person → WORKS_FOR → Organization is registered.
An evidence-backed statement | A governed Assertion must still retain support and review history.
```

## Return to D1, V1 and C1 {#example}

Our fictional **“Joule Studio and agent communication review memo”**, D1, considers Joule Studio for agent development in the SAP ecosystem and mentions A2A. V1 explicitly does not establish that Joule Studio uses A2A. C1 is the exact passage. The names and labels are teaching material, not verified knowledge in your database.

Candidate P1 says **Technology(Joule Studio) USES Technology(A2A)**. In ontology 1.0.0, Technology is registered and USES allows those endpoint types. The candidate can therefore satisfy the relationship-type rule. It must still be rejected as unsupported by C1.

Now compare **Document USES Person**. Both entity types exist, but USES does not allow that endpoint combination. This is a structural rejection before the reviewer considers whether a source supports it. A third example, **Document WORKS_FOR Embedding**, also introduces an unregistered entity type: Embedding is not an entity type in the current ontology.

These examples distinguish three problems: an unsupported meaning, a forbidden type combination and an unregistered type. They should not be collapsed into the vague phrase “bad knowledge.” Different checks and different remediation are needed.

## What the repository actually validates {#implementation}

`Ontology.load` reads the version, entity types and relation rules from `config/ontology.yaml`. `Ontology.validate` first checks the subject type. For an entity object, it checks the object type, finds the registered predicate and checks allowed subject and object endpoints.

The registered WORKS_FOR rule allows Person as subject and Organization as object. USES permits specified types, including the Technology-to-Technology combination above. RUNS_ON and Platform are not registered in ontology 1.0.0; introducing them in a diagram as current supported vocabulary would invent architecture.

There is an important current gap. When the change has no entity object and instead carries a scalar value, the validator returns early after checking the subject. F5 records the unresolved predicate-validation gap for that path. Do not generalize the entity-object behavior to all assertions, and do not call the validator complete merely because one invalid relationship test exists.

The rule model is deliberately narrow. It does not establish product facts, automatically merge aliases, solve ambiguous names, or infer every valid relationship. An Entity's workspace/type/name identity and alias fields are a separate concern. Adding “BTP” as an alias must not be described as proof that all variants are automatically resolved to one canonical entity.

## Why keep the rule separate from storage? {#why}

Without explicit rules, one contributor could use WORKS_FOR for employment, another for software compatibility, and a third for a document's subject. A graph could store all three while the reader could no longer interpret them consistently. A shared rule makes at least the allowed vocabulary and endpoints explicit and versioned.

With the rule, the system can reject a forbidden type combination and adapters can discover the same extraction context. The rule still cannot decide whether the fictional author really works for the organization. That needs evidence and governance. Separating these responsibilities makes failures explainable: was the candidate malformed, unsupported, unauthorized or incorrectly approved?

> **Common misconception:** “If the ontology permits it, it is true.” Permission in a type model is about expressibility, not factual truth. The P1 example passes a type rule while failing the evidence question.

> **Common misconception:** “Ontology is another name for Neo4j.” Neo4j stores the graph. This repository's ontology configuration defines a narrower vocabulary and validator. The Explorer is yet another graph: a map of documentation.

## Learn from Palantir without claiming its capabilities {#conceptual}

Palantir's Foundry Ontology includes objects, properties, links and operational Actions, with associated functions and permissions. Its table-to-object explanation is useful pedagogy. Its operational platform is broader than this repository's YAML rules and validator.

Do not map a Palantir Action directly onto the entire Knowledge OS implementation. Knowledge OS has its own Action contract, policy snapshots, review and executor boundary. The conceptual comparison helps explain responsibility; it does not certify feature equivalence or imply this repository includes Foundry's services.

## Current implementation and limits {#current}

**CURRENT v0.1:** a versioned YAML ontology, entity-object validation, discoverable extraction context and governed candidate paths exist. The evidence links below identify the exact configuration, qualified validator and regression selectors. Their presence is not a passing execution result for F5.

**TARGET / DEFERRED:** automated extraction providers and advanced entity resolution are not supplied by the ontology. Enterprise authorization and a broad operational ontology platform are not inferred from it. F5 remains KNOWN ISSUE; other unresolved audit findings and release acceptance remain open.

## Explain it back {#checks}

```question
Why can P1 be structurally valid while still requiring rejection? Name the two different responsibilities involved.
---
Technology USES Technology is allowed by the type rules, but C1 does not support that factual relationship. Ontology validation checks structure; evidence review and governance decide whether the candidate should be accepted.
```

```question
How do “Document USES Person” and “Document WORKS_FOR Embedding” fail differently in this model?
---
The first uses registered types with forbidden USES endpoints. The second includes an unregistered object type, Embedding, as well as a nonsensical employment example. Exact validation order matters when diagnosing the rejection.
```

```question
Would a passing entity-object test prove that scalar assertions validate every predicate? Use the current implementation to explain.
---
No. Ontology.validate returns early when there is no entity object. F5 documents that predicate-validation gap. A test of another branch cannot close it.
```

```question
If Neo4j can store a new relationship, is that sufficient to call it part of the current ontology?
---
No. Storage capability, registered semantic rules, supporting evidence and governed acceptance are separate. A new predicate needs an explicit model change; this documentation task makes no such change.
```
