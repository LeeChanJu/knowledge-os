## May we record any kind of connection?

```diagram
Person → works for → Company ✅
PDF → works for → Numerical representation ❌
Rules constrain the allowed kinds of connections
```

These examples explain the role of rules; they are not the repository allowlist. Rules constrain structure, while evidence and review establish support for a particular statement. Validation of value-form statements still has an unresolved finding.

<!-- DEPTH -->

### Why this responsibility exists

Separate extraction from truth and preserve immutable review outcomes. Revalidate evidence access inside the write transaction.

### Inputs and outputs

Input: Typed candidates, creator access context, reviewer identity and decision.

Output: One immutable approval/rejection outcome and, on approval, canonical records.

### What must be preserved

- Proposal identity/payload, SUPPORTED_BY lineage, Approval history.
- MCP cannot approve or reject. A pending proposal cannot acquire conflicting review outcomes. Authorization uses current evidence ACLs.

### Follow the example

A reviewer must be authorized to read the note and compare it with the candidate. The AI submitting through MCP cannot perform this approval.

### Avoid this misconception

MCP cannot approve or reject. A pending proposal cannot acquire conflicting review outcomes. Authorization uses current evidence ACLs.
