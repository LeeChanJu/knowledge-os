## How is a new interpretation accepted?

```diagram
Earlier statement + new support
↓ Submit a proposed correction
Separate review → accept or reject
```

New content must not become accepted knowledge without review. Identify the requested change and its support. The existence of a review path does not prove every correction behavior has completed verification.

The first Telegram notification arrives with the complete change and evidence. Read the attachment, then choose **Approve/Reject** once. Pair your own account and keep the local review process running; plain `/start` is not account pairing. The existing Knowledge Service owns the decision and audit history. Action approval remains separate from execution. With the current foreground deployment, process termination or Mac sleep delays processing.

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
