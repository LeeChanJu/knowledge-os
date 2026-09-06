# Local human review

`knowledge-os-review` is a local-first terminal surface over the existing Governance, Evidence,
and Action service contracts. It adds no review database, web framework, or alternate promotion
logic.

Configure the source-derived identities available to the reviewer process. With more than one
principal, select exactly one actor:

```bash
export REVIEW_WORKSPACE_ID=personal
export REVIEW_PRINCIPALS='google-drive:me'
# export REVIEW_ACTOR='google-drive:me'  # required only for multiple principals
```

Review pending work in this order:

```bash
knowledge-os-review list --status PROPOSED
knowledge-os-review show PROPOSAL_ID
knowledge-os-review approve PROPOSAL_ID --reason 'Evidence verified' --yes
# or
knowledge-os-review reject PROPOSAL_ID --reason 'Claim is not supported' --yes
```

Review governed Action requests separately. `action-show` exposes the target, exact parameters,
policy, designated reviewers and executors, decisions, claims, and execution history before a
human confirms a lifecycle decision:

```bash
knowledge-os-review action-list --status PROPOSED
knowledge-os-review action-show ACTION_ID
knowledge-os-review action-approve ACTION_ID --reason 'Capability and target verified' --yes
# or
knowledge-os-review action-reject ACTION_ID --reason 'Target is not authorized' --yes
```

`show` first reads the authorization-filtered Proposal and then requests one all-or-nothing exact
Evidence bundle, including Chunk text, source identity, DocumentVersion, historical authorization,
and current authorization. Approval and rejection refuse to make a request without `--yes`.
The Knowledge Service then repeats current ACL, Evidence lineage, lifecycle, ontology, temporal, and
supersession checks inside the write transaction. Every decision creates an immutable Approval node
and audit record; rejection never creates canonical knowledge.

Action approval and rejection also refuse to call the service without `--yes`. Approval creates an
immutable Approval record but performs no external operation. MCP has no approval or execution
tool, and the review CLI has no execution-claim or execution-result command. A separately
authenticated connector must still satisfy the Action policy before any System-of-Record API call.

The default runs the FastAPI application in-process, like the MCP adapter. Set `REVIEW_BASE_URL`
only for an intentionally supervised separate service.

This is a personal local-machine trust boundary, not multi-user authentication or enterprise ReBAC.
Anyone able to alter the process environment and local Neo4j credentials is already inside that
boundary. Do not expose this CLI or an unauthenticated Knowledge Service over a network. A future
customer-facing UI must derive the same access and actor fields from authenticated sessions while
preserving the stable Governance contract.
