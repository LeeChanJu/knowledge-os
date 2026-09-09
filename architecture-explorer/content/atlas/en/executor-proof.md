The record below limits verification or unresolved scope to this feature. It does not complete other findings or release acceptance.

<!-- DEPTH -->

### Why this responsibility exists

Keep operational writes behind policy, reviewer, capability, lease, and source-system authorization boundaries.

### Inputs and outputs

Input: Action request, designated reviewers/executors, policy version, explicit approval.

Output: Execution claim, provider operation, and immutable execution evidence.

### What must be preserved

- Action snapshots, review decisions, claim lease and execution records in Neo4j.
- MCP cannot approve or execute. A lease expiry is not takeover permission. External exactly-once delivery is not guaranteed if the provider ignores idempotency. F4/F8 remain open.

### Follow the example

Writing the conclusion back to Notion requires execution policy, authority and outcome records separate from knowledge approval. This site’s controls only navigate documentation.

### Avoid this misconception

MCP cannot approve or execute. A lease expiry is not takeover permission. External exactly-once delivery is not guaranteed if the provider ignores idempotency. F4/F8 remain open.
