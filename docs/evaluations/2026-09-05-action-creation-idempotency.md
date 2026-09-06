# Action creation idempotency — 2026-09-05

## Correctness gap

Action creation previously accepted a missing idempotency key and then included call time in the
Action ID. A transport retry could therefore create a second independently approvable capability.
Each capability's later execution claim was safe in isolation, but the pair could still authorize
two external System-of-Record mutations.

The live graph contained zero Actions and zero ActionExecutions, so tightening the creation contract
required no data migration.

## Action-v5 extension

Every Action now requires a non-empty idempotency key. Its ID remains scoped by workspace,
requester, and that key. The existing transaction stores a canonical payload hash, returns the
current lifecycle state for an exact retry, and rejects reuse of the key for a different payload.

This preserves intentional repeated actions: the caller supplies a new key for a genuinely new
intent. It adds no scheduler, queue, connector, or external mutation path.

## Live verification

Sixteen concurrent submissions with one key and payload produced one Action ID and exactly one
creation. Reusing the key for different parameters was rejected. After one approval, submitting
the original request returned the same Action in `APPROVED` state with `unchanged=true`; the graph
contained one Action and one Approval. The Action carried action-v5, its payload hash, and no
transient creation marker. Doctor checks these properties for every action-v5 record. The isolated
workspace and exact audit rows were removed after verification.
