## What do we want to connect inside a sentence?

```diagram
📄 Teaching sentence: “Joule Studio is a technology related to SAP.”
Tracked subjects: [Joule Studio] ↔ [SAP]
A statement between them: “related technology” + source support
```

This sentence illustrates connections; it is not verified product information. Distinguish [a tracked subject](term:entity) from [a supported statement](term:assertion) about it. Our example note saying “reviewed both technologies” cannot support the different claim “uses.”

<!-- SCENE -->
## Can anything connect to anything in any way?

```diagram
Person ──works for──→ Company ✅ a sensible kind of connection
PDF ──works for──→ Numerical representation ❌ an odd kind of connection
Who sets the allowed kinds? → Rules for connections
```

These are teaching examples, not the repository's actual allowlist. [Rules for connections](term:ontology) check the kinds of connections. Even a sensible kind still needs evidence and review to establish a particular fact.

<!-- SCENE -->
## How does a connected map differ from its rules?

```diagram
Connected map: what is connected to what?
Connection rules: which kinds of connections are allowed?
Review: does the original really support this particular connection?
```

[A map of connections](term:graph) contains recorded information; rules constrain its allowed structure. Neither proves truth by itself. On the whole flow, we are where candidates are checked and accepted into connected knowledge.

<!-- WHY -->
## Connect this stage to its neighbors

Before this stage, prepare source material and a candidate. Here, check subject and relationship structure and conduct authorized review. Accepted statements link to evidence for later search and source inspection.

## Is passing a structural check enough?

“Joule Studio uses A2A” might have a permitted shape, yet “we reviewed both” does not prove it. A reviewer must be able to reject a structurally valid candidate. Conversely, supported material should not silently bypass rules on allowed structure.

## What does the implementation check today?

The repository checks registered subject types and the types and directions of relationships between subjects. Statements containing a value instead of another subject have an unresolved validation finding; we cannot claim complete validation of every statement. Exact functions and regression references are available in the technical layer.

## Explain it in your own words

```check
The same product appears in two notes making different statements. Why separate the tracked subject from statements about it?
---
The same subject can have different statements with different evidence and applicable times. Keeping identity separate from statements preserves those distinctions.
```

```check
Rules allow a person to work for a company. Does this prove that a particular person works at a particular company?
---
No. Rules determine whether the kind of connection is appropriate. That particular statement needs its own evidence and review.
```

```check
How would you explain the difference between a connected map and its rules to a friend?
---
The map contains the subjects and connections actually recorded. The rules say which kinds of subjects and connections may be recorded. One is the record; the other constrains its form.
```

```check
An AI candidate passed a check, but the original merely mentions two names. Should it be accepted?
---
No. Passing a structural check differs from being supported. Reject a stronger-than-source relationship, or correct it to match the evidence and review it again.
```
