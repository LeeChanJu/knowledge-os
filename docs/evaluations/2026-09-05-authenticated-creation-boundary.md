# Authenticated creation boundary — 2026-09-05

## Authorization gap

Proposal creation checked that evidence IDs existed in the workspace but did not verify that the
declared creator could currently read their source documents. Proposal and Action creation also
accepted actor strings without binding them to an authenticated principal. This allowed false
provenance and unauthorized review-queue or capability creation, even though later approval and
execution boundaries remained protected.

## Contract extension

Governance-v6 and Action-v6 reuse the existing `AccessContext`; no authorization service or ReBAC
engine is introduced. The declared actor must be one authenticated principal and the request
workspace must match the context. Proposal creation checks every supporting document's current ACL
inside its creation transaction. Exact retries repeat that authorization check, so revoked access
does not disclose an existing content-addressed Proposal.

Neo4j stores the canonical access fingerprint and principal count as creation provenance while raw
principal lists remain outside the graph and operational logs.

## Live verification

An isolated private document accepted a Proposal from its owner and rejected an unrelated
principal, a spoofed creator, and a mismatched workspace. An Action accepted its authenticated
requester and rejected actor and workspace mismatches. The two authorized records stored the same
canonical `access-context:` fingerprint and principal count of two; raw principals were not stored.
An exact Proposal retry under a still-authorized subset returned unchanged. Temporary graph and
exact operational records were removed after verification.
