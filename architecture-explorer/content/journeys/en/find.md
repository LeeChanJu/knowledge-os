<!-- stage:words -->
## Do you remember a name?

```diagram
“Notes containing the word A2A”
↓ Find matching words
Relevant passages the reader may access
```

Matching words is a useful starting point when you remember an exact name. Results must still pass current read-access checks. Finding a name does not prove a particular relationship.

<!-- stage:meaning -->
## What if you ask with different words?

```diagram
“What I studied about communicating programs”
↓ Numerical representations for comparison
Find candidates with similar meaning
```

This approach aims to find related material despite different wording. It needs numerical representations, and production provider activation remains deferred. Similarity suggests material to inspect; it does not establish truth.

<!-- stage:connections -->
## Do you want to follow a connection?

```diagram
Find the tracked subject A2A
↓ Read bounded recorded relationships
Inspect related subjects and their support
```

Here we read recorded connections rather than find similar text. Relationship access is bounded and distinct from keyword/meaning search. Do not assume unrestricted conversion of natural-language questions into reasoning over every connection.

<!-- stage:answer -->
## Is returned material already an answer?

```diagram
Passages + source references
↓ Knowledge OS returns material
Claude/GPT consults it and answers → me
```

Finding material and composing an answer are different responsibilities. The external AI should not make stronger claims than the returned support. Insufficient evidence should remain visible as a limitation.

<!-- checks -->
## Explain it in your own words
```check
Does finding similar text establish a relationship?
---
No. Similarity is a retrieval signal; inspect whether the original actually supports the relationship.
```
```check
How does what Knowledge OS returns differ from what Claude/GPT creates?
---
Knowledge OS returns readable material and connections. Claude/GPT consults them to compose an answer.
```
