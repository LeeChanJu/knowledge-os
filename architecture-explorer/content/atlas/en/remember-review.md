## Who reviews what?

```diagram
Candidate + supporting material
↓ Authorized reviewer
Reject ← Review → Accept
```

The reviewer checks whether the suggestion matches its support. The agent adapter does not perform this approval. Rejected candidates do not become accepted knowledge.

In Telegram, open **Review**, read the complete change and evidence, then choose **Approve/Reject**. Pair your own account and keep the local review process running; plain `/start` is not account pairing. The existing Knowledge Service owns the decision and audit history. Action approval remains separate from execution. With the current foreground deployment, process termination or Mac sleep delays processing.

A Codex schedule in the personal deployment connects Notion ingestion and proposal extraction every 15 minutes. Version-scoped receipts prevent repeated submissions; the owner reviews and approves in Telegram. Keep the Mac, Codex, Neo4j, and review process running.

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
