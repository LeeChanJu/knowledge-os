## Is a decision already an external change?

```diagram
“We decided to do this” → a decision record
“Apply it to the source” → a separate change request
A request does not execute itself
```

Deciding what to do differs from changing an outside system. A change request must identify its target and intended operation. Submitting it through connection tools does not grant approval authority.

<!-- DEPTH -->

### Why this responsibility exists

Let agent clients consume context and request review without receiving direct database authority.

### Inputs and outputs

Input: Bounded MCP tool arguments plus host-owned workspace/principals.

Output: Knowledge Service results or governed request receipts.

### What must be preserved

- Host adapter configuration only; no independent knowledge store.
- No direct Cypher, ingestion, approval, Action execution or external mutation tools. MCP is not entirely read-only: it can submit governed requests.

### Follow the example

When Claude/GPT asks about the note, MCP carries a bounded read. Connection does not grant arbitrary Cypher, knowledge approval or external execution authority.

### Avoid this misconception

No direct Cypher, ingestion, approval, Action execution or external mutation tools. MCP is not entirely read-only: it can submit governed requests.
