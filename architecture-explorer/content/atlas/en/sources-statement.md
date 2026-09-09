## Which statement in the answer needs checking?

```diagram
“Why did the answer assert this connection?”
↓ Choose one statement to inspect
Follow its linked supporting material
```

Choose a particular statement rather than trust an answer as a whole. The repository supports bounded reads of exact records and evidence. This is not a finished feature that automatically maps every sentence in any AI answer.

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
