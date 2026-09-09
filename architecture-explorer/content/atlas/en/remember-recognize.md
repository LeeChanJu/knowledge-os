## What do we distinguish in the sentence?

```diagram
[Joule Studio]     [A2A]
↓ Subjects to track consistently
“Reviewed together” → a statement about them
```

A name is different from a statement about it. Different documents or times may support different statements about the same subject. Current identity rules use normalized names, types and workspace, not universal automatic alias merging.

<!-- DEPTH -->

### Why this responsibility exists

Represent inspectable semantic claims and retain correction/supersession history.

### Inputs and outputs

Input: An approved AssertionChange with evidence, predicate and temporal fields.

Output: Canonical Assertion reads and graph relationships.

### What must be preserved

- Claim predicate/value, evidence link, confidence, temporal and extraction provenance.
- Canonical promotion requires approval. A superseding assertion preserves subject and predicate and must not silently erase its predecessor.

### Follow the example

Evidence that two technologies were reviewed together does not establish that one uses the other. Review whether the proposed claim is stronger than its evidence.

### Avoid this misconception

Canonical promotion requires approval. A superseding assertion preserves subject and predicate and must not silently erase its predecessor.
