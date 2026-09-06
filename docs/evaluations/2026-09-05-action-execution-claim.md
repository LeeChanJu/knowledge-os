# Governed Action execution-claim verification — 2026-09-05

## Correctness gap

Action-v2 serialized approval and post-call result evidence on the Action node, but it had no
transactional boundary before the external API call. Two authorized connector processes could
therefore both observe an approved, not-yet-executed Action and begin the same mutation before
either recorded its result.

## Decision

Extend the existing Neo4j Action boundary with `ActionExecutionClaim`; do not add a queue, lock
service, workflow engine, or connector-side database. Action-v3 requires a bounded claim before an
external call and binds completion evidence to that claim. The returned external idempotency key
is stable across retries for the same Action and policy.

## Executed integration evidence

Against the live Neo4j transaction implementation, using isolated `it-*` workspaces that were
deleted afterward:

- an approved Action accepted its first claim;
- an identical claim retry returned the same claim as unchanged;
- a different attempt while that lease was live failed with `action execution is already claimed`;
- a failed execution closed the first claim and permitted a second attempt;
- both attempts received the same external idempotency key;
- the second attempt recorded success;
- a third claim after success failed with `action already succeeded`;
- the final audit view contained two completed claims and immutable FAILED/SUCCEEDED executions;
- a forced expired lease rejected takeover and required external-result reconciliation; completion
  of that still-current claim remains allowed so its evidence is never discarded;
- two transactions released from a thread barrier against the same approved Action resolved to
  exactly one `CLAIMED` result and one `action execution is already claimed` conflict; Neo4j
  retried the transient lock deadlock and committed one live claim;
- Action, Claim, and Execution each persisted explicit `action-v3` contract provenance;
- all 28 Doctor checks passed after exact test-workspace cleanup.

## Boundary and remaining risk

The claim prevents two compliant connectors from concurrently starting the call and makes crash
recovery explicit. Expiry fails closed because an earlier call may still be in flight; the connector
must reconcile through the stable external key and close the claim before retrying. The mechanism
cannot manufacture exactly-once semantics in a System of Record that does
not support idempotency or conditional writes. Connectors must use the supplied key through the
authorized external API where supported and record the external request identifier. A future
non-idempotent capability policy requires separate evidence and explicit governance; it must not
be silently treated as safe.
