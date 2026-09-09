An authorized reviewer checks the candidate against evidence and rules. MCP cannot approve; successful ingestion does not imply approval.

<!-- DEPTH -->

### Why this responsibility exists

Record the authenticated human decision and its provenance.

### Inputs and outputs

Input: Review identity, decision, reason and authorized evidence.

Output: One approval/rejection outcome.

### What must be preserved

- Decision record with exactly one governance parent.
- Approval does not itself execute an external Action.

### Follow the example

A reviewer must be authorized to read the note and compare it with the candidate. The AI submitting through MCP cannot perform this approval.

### Avoid this misconception

Approval does not itself execute an external Action.
