proposal_identity and _persist_proposal derive identity from candidate content and evidence. Approval is a separate GraphStore boundary that rechecks current evidence authorization.

<!-- DEPTH -->

### Why this responsibility exists

Preserve proposed payload and complete evidence before human review.

### Inputs and outputs

Input: Candidate, creator identity, ontology version.

Output: Reviewable immutable candidate identity.

### What must be preserved

- Payload hash and SUPPORTED_BY Chunk links.
- Retries do not reopen approved or rejected payloads.

### Follow the example

A statement drafted from the note enters as an evidence-backed candidate. Resubmission must not erase rejection history or manufacture another approval.

### Avoid this misconception

Retries do not reopen approved or rejected payloads.
