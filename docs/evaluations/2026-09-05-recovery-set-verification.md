# Local recovery-set verification — 2026-09-05

## Decision

Retain Neo4j and SQLite as the only runtime stores. Use their native backup mechanisms behind
`recovery-manifest-v1`; do not introduce a shadow database, custom logical graph export, queue, or
remote backup service without measured need.

## Executed evidence

- Backup ID: `20260904T172741Z-daf64923` (UTC identifier; verified on 2026-09-05 KST)
- Git commit captured before backup: `cd9b5b44c00b665a081a15d631723e2928801704`
- Git dirty state: `false`
- Capture window: `2026-09-04T17:27:41.185824+00:00` through
  `2026-09-04T17:27:46.018336+00:00`
- Neo4j: Enterprise `2026.07.1`, database `neo4j`
- Live precondition: all 24 Doctor checks passed
- Neo4j artifact: 120,961 bytes,
  SHA-256 `a07c8ad61640c7b75eaef067feb5080e7bd06adea5103d5d55098b0bb8d87a12`
- SQLite artifact: 385,024 bytes,
  SHA-256 `4980d32a391f29f3860898cb85fe1f9fbe450b8d14ec593df6f9810da1f44fdb`
- Verification: both artifact hashes passed; SQLite `PRAGMA integrity_check` passed; Neo4j
  `database check` against the backup artifact passed

The manifest captured 12 Documents, 12 DocumentVersions, 80 Chunks, one Source, one Workspace,
six applied migration checksums, and all relationship counts. SQLite evidence captured counts for
all six application tables, including 92 retrieval traces, 68 evaluations, 11 audit records, and
the intentionally retained retrieval error.

The recovery set is stored under ignored local `data/backups/`; it contains private source content
and is not committed to Git.

## What this proves

The active stores can be backed up online without stopping or mutating the graph. The resulting
files are independently checksummed, the SQLite copy is internally consistent, the Neo4j artifact
passes Neo4j's offline consistency checker, and the set is tied to exact code/contracts and a
bounded cross-store capture interval.

## End-to-end database restore drill

The same recovery set was subsequently restored through Neo4j's official `database restore`
command to the previously nonexistent database `kos-recovery-drill-20260905b`. The source database
was explicitly selected as `neo4j`; the active `neo4j` database was never stopped, overwritten, or
used as the restore target.

Measured results:

- archive restore and transaction recovery completed successfully;
- the restored database registered and reached `online` state;
- all 24 Doctor checks passed with zero violations against the restored graph and a copied
  `ops.db`;
- label counts, relationship counts, and all six migration names/checksums exactly matched the
  recovery manifest;
- the authorization-suite control query returned five results and the unrelated-principal query
  returned zero;
- the exact drill database was dropped with `DESTROY DATA`;
- `SHOW DATABASES` then returned only `knowledge`, `neo4j`, and `system`;
- the active `neo4j` database passed all 24 Doctor checks after cleanup.

This closes the database/application restore-path gap for a second database inside the local
Desktop DBMS. It does not prove recovery after loss of the DBMS installation or host. Separate-host
RTO, credential recovery, encrypted off-device copies, media-loss recovery, and retention policy
remain unmeasured. The runbook continues to forbid overwriting the active database during drills.

## Action-v3 successor recovery set

After the governed execution-claim contract and migrations 007–009 were applied, recovery set
`20260904T220133Z-29b808f6` was created from clean Git commit
`da506fe3af4b57c5e3709cdf99d97f9f47818806`. Its manifest records `action-v3`, all nine migration
checksums, and 28 passing pre-backup Doctor checks. Both SHA-256 checks, SQLite integrity, and the
Neo4j archive consistency check passed. This supersedes the earlier set as the current local
recovery point; the earlier set remains useful evidence for migration-forward restore testing.

After source-v3 atomic manifests, recovery set `20260904T221211Z-e43a78b2` was created from clean
commit `87256e7d4b80b188defc0f34347a6409bddd116e`. Its manifest records source-v3/action-v3, all nine
migrations, and 29 passing Doctor checks. Artifact hashes, SQLite integrity, and Neo4j archive
consistency all passed. This is the current local recovery point.

After retrieval-v3 ranking evidence was committed, recovery set `20260904T221659Z-0d2809dc` was
created from clean commit `a4300188944d9d1fa03b00c544cffe9c881c4add`. It records retrieval-v3,
source-v3, action-v3, and 29 passing Doctor checks. Both artifact hashes, SQLite integrity, and
Neo4j archive consistency passed. This supersedes the prior set as the current local recovery point.

After canonical UTC input contracts were committed, recovery set
`20260904T222517Z-efe7d098` was created from clean commit
`4e6bc914d8bd190f499805dfef76c6276ee506ab`. Its manifest records source-v4, governance-v4,
retrieval-v4, action-v4, the unchanged evidence-v1 and knowledge-v1 contracts, and a bounded
capture window of approximately 5.34 seconds. Both artifact hashes, SQLite integrity, and Neo4j
archive consistency passed verification; the live Doctor separately passed all 30 checks before
capture. This supersedes the prior set as the current local recovery point.

After direct document mutation compare-and-set was committed, recovery set
`20260904T223122Z-a31b407e` was created from clean commit
`53bdcdaaf1fc6875d43185eb4416de28a17f9904`. Its manifest records source-v5 and the existing
governance-v4, retrieval-v4, action-v4, evidence-v1, and knowledge-v1 contracts. The bounded
capture window was approximately 5.30 seconds; both artifact hashes, SQLite integrity, and Neo4j
archive consistency passed verification. This supersedes the prior set as the current local
recovery point.

After content-addressed governance Proposals were committed, recovery set
`20260904T223520Z-5729b00a` was created from clean commit
`905b24d93c8575da302ebc8427bd304d10231b73`. Its manifest records governance-v5, source-v5,
retrieval-v4, action-v4, evidence-v1, and knowledge-v1. The bounded capture window was
approximately 5.17 seconds; both artifact hashes, SQLite integrity, and Neo4j archive consistency
passed verification. This supersedes the prior set as the current local recovery point.

After mandatory Action creation idempotency was committed, recovery set
`20260904T223804Z-d5f7f950` was created from clean commit
`f403ea0db429fb5241efbd0268c5ff4bb6179138`. Its manifest records action-v5, governance-v5,
source-v5, retrieval-v4, evidence-v1, and knowledge-v1. The bounded capture window was
approximately 5.39 seconds; both artifact hashes, SQLite integrity, and Neo4j archive consistency
passed verification. This supersedes the prior set as the current local recovery point.

After authenticated Proposal and Action creation boundaries were committed, recovery set
`20260905T030328Z-c635a3b9` was created from clean commit
`1c04f3758d7c89894f60b94f7fa9e3550c2dc7f1`. Its manifest records governance-v6, action-v6,
source-v5, retrieval-v4, evidence-v1, and knowledge-v1. The bounded capture window was
approximately 5.05 seconds; both artifact hashes, SQLite integrity, and Neo4j archive consistency
passed verification. This supersedes the prior set as the current local recovery point.

After versioned source metadata provenance was committed, recovery set
`20260905T030840Z-ea40be5f` was created from clean commit
`426c4e634d38be038cc1f25c35d7cf7923fc9a82`. Its manifest records source-v6, governance-v6,
action-v6, retrieval-v4, evidence-v1, and knowledge-v1. The bounded capture window was
approximately 5.18 seconds; both artifact hashes, SQLite integrity, and Neo4j archive consistency
passed verification. This supersedes the prior set as the current local recovery point.

After temporal as-of knowledge reads were committed, recovery set
`20260905T032041Z-5909234b` was created from clean commit
`af72f7f491c3b0b41ad926388806a1aae0b1e01c`. Its manifest records knowledge-v2, source-v6,
governance-v6, action-v6, retrieval-v4, and evidence-v1, with all 35 Doctor checks passing before
capture. The bounded capture window was approximately 5.39 seconds; both artifact hashes, SQLite
integrity, and Neo4j archive consistency passed verification. This supersedes the prior set as the
current local recovery point.

After runtime migration-path deployment was made explicit, recovery set
`20260905T032629Z-a4c49701` was created from clean commit
`abbffdafda1332d397efd72fe9199049de353cd1`. The core contracts remain knowledge-v2, source-v6,
governance-v6, action-v6, retrieval-v4, and evidence-v1 because this was an operational
configuration extension rather than a data-contract change. All 35 Doctor checks passed before
capture. The bounded capture window was approximately 5.10 seconds; both artifact hashes, SQLite
integrity, and Neo4j archive consistency passed verification. This supersedes the prior set as the
current local recovery point.

After the governed extraction-context service was committed, recovery set
`20260905T033123Z-2a57a891` was created from clean commit
`82f94eb00122a9982691e1db7a5558d10b6f205d`. Its manifest records knowledge-v3, source-v6,
governance-v6, action-v6, retrieval-v4, and evidence-v1, with all 35 Doctor checks passing before
capture. The bounded capture window was approximately 4.76 seconds; both artifact hashes, SQLite
integrity, and Neo4j archive consistency passed verification. This supersedes the prior set as the
current local recovery point.

After authorized exact-Chunk bundles were committed, recovery set
`20260905T033906Z-e5d21355` was created from clean commit
`fe4419d15a9d5183f4c39012031f7d63074737eb`. Its manifest records evidence-v2, knowledge-v3,
source-v6, governance-v6, action-v6, and retrieval-v4, with all 35 Doctor checks passing before
capture. The bounded capture window was approximately 4.87 seconds; both artifact hashes, SQLite
integrity, and Neo4j archive consistency passed verification. This supersedes the prior set as the
current local recovery point.

After the read-only local MCP adapter was committed, recovery set
`20260905T034502Z-9c268be2` was created from clean commit
`c4658563c808b4439d7eb9c71dd379a7fce168eb`. The core contracts remain evidence-v2,
knowledge-v3, source-v6, governance-v6, action-v6, and retrieval-v4 because MCP is a replaceable
adapter over those contracts. All 35 Doctor checks passed before capture. The bounded capture
window was approximately 5.35 seconds; both artifact hashes, SQLite integrity, and Neo4j archive
consistency passed verification. This supersedes the prior set as the current local recovery point.

After the MCP adapter adopted a host-owned in-process Knowledge Service lifecycle, recovery set
`20260905T064421Z-16710650` was created from clean commit
`9957672208b2d61ee4f54cbbe94ce2e32c54f277`. The six core contracts remain unchanged because this
is an adapter deployment correction, not a contract redesign. All 35 Doctor checks passed before
capture. The bounded capture window was approximately 5.50 seconds; both artifact hashes, SQLite
integrity, and Neo4j archive consistency passed verification. This supersedes the prior set as the
current local recovery point.

After the deterministic Notion page-tree connector was committed, recovery set
`20260905T064849Z-ee1f3552` was created from clean commit
`af16d0788e9ae91ccbbe291ce5c2b54ca7f68c32`. The Source and Evidence contracts remain unchanged
because the connector translates the provider API into manifest-v2. All 35 Doctor checks passed
before capture. The bounded capture window was approximately 4.86 seconds; both artifact hashes,
SQLite integrity, and Neo4j archive consistency passed verification. This supersedes the prior set
as the current local recovery point.

After the connector added complete child data-source pagination and row-property evidence,
recovery set `20260905T065222Z-8b2bc2e5` was created from clean commit
`62048d1e6a82be34232c751a68aa2b6c1e2e617a`. The core contracts remain unchanged because this is
another provider translation extension over manifest-v2. All 35 Doctor checks passed before
capture. The bounded capture window was approximately 5.16 seconds; both artifact hashes, SQLite
integrity, and Neo4j archive consistency passed verification. This supersedes the prior set as the
current local recovery point.

After paginated title, rich-text, and relation properties replaced Notion's truncated page-object
projection, recovery set `20260905T065428Z-ee0e352c` was created from clean commit
`776bca7695a975f2c9ebbbbaeae53e07c440c978`. The core contracts remain unchanged. All 35 Doctor
checks passed before capture. The bounded capture window was approximately 5.07 seconds; both
artifact hashes, SQLite integrity, and Neo4j archive consistency passed verification. This
supersedes the prior set as the current local recovery point.

After governed assertion, Decision, and Event Proposal entry was exposed through MCP, recovery set
`20260905T114729Z-c2258427` was created from clean commit
`f458be390d3c02f5aa2c7423df549008f4427c30`. Governance-v6 remains unchanged because the adapter
injects authenticated identity into the existing content-addressed service contracts and exposes no
review or promotion operation. All 35 Doctor checks passed before capture. The bounded capture
window was approximately 5.27 seconds; both artifact hashes, SQLite integrity, and Neo4j archive
consistency passed verification. This supersedes the prior set as the current local recovery point.

After the local human review CLI was committed, recovery set
`20260905T115052Z-ba053527` was created from clean commit
`dd28381be438b0c5a83b45649c06e7d564692bb0`. Governance-v6 remains unchanged because the CLI
calls the existing Evidence and decision routes and adds no alternate promotion path. All 35 Doctor
checks passed before capture. The bounded capture window was approximately 4.85 seconds; both
artifact hashes, SQLite integrity, and Neo4j archive consistency passed verification. This
supersedes the prior set as the current local recovery point.

After meeting transcript ingestion and connector replay identity were corrected, recovery set
`20260905T115505Z-f49ed5d3` was created from clean commit
`8227fd07f6c9f3019dcba6449f37cb014c7fd9ac`. Source-v6 remains unchanged because both connectors
still produce manifest-v2; only their deterministic run-identity inputs and supported evidence
formats changed. All 35 Doctor checks passed before capture. The bounded capture window was
approximately 5.10 seconds; both artifact hashes, SQLite integrity, and Neo4j archive consistency
passed verification. This supersedes the prior set as the current local recovery point.
