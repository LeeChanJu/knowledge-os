Check that input order or resubmission does not create different semantic state. Concurrent approval and access enforcement require separate real-database coverage.

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
