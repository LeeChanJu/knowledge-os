<!-- stage:prepare -->
## What should be remembered?

```diagram
📄 SAP AI study note
↓ Check that the original may be read
✂️ Prepare a supporting passage
```

We follow a fictional note saying “We reviewed Joule Studio and A2A.” Identify the original, its version and the part used so someone can check the claim later. The original stays in its source system.

<!-- stage:recognize -->
## What do we distinguish in the sentence?

```diagram
[Joule Studio]     [A2A]
↓ Subjects to track consistently
“Reviewed together” → a statement about them
```

A name is different from a statement about it. Different documents or times may support different statements about the same subject. Current identity rules use normalized names, types and workspace, not universal automatic alias merging.

<!-- stage:propose -->
## Should an AI suggestion be accepted immediately?

```diagram
Original: “We reviewed both technologies”
AI: “One technology uses the other” ❌
↓ Stronger than the source → submit and inspect a candidate
```

Two names appearing together do not establish a usage relationship. A submitted candidate carries structure and evidence and is subject to allowed relationship rules. Do not assume an automated extraction provider already performs this entire path.

<!-- stage:review -->
## Who reviews what?

```diagram
Candidate + supporting material
↓ Authorized reviewer
Reject ← Review → Accept
```

The reviewer checks whether the suggestion matches its support. The agent adapter does not perform this approval. Rejected candidates do not become accepted knowledge.

<!-- stage:store -->
## What remains after review?

```diagram
Accepted statement → connected to tracked subjects
↓ Linked to its precise supporting material
Read and check it again for a later question
```

Connect accepted statements, support and review history. Acceptance is not a guarantee of timeless truth; later corrections must preserve the earlier record. Bounded tools return material, while the external AI composes the answer.

<!-- checks -->
## Explain it in your own words
```check
May we infer usage from a note mentioning two names?
---
Co-occurrence is insufficient. Reject or correct a candidate that says more than its support.
```
```check
What separates a request to remember from acceptance?
---
Source support, a candidate and an independently authorized review are needed. One-message automation is a target.
```
