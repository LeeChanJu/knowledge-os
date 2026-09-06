# Google Drive ADC refresh boundary — 2026-09-06

## Decision

Extend the read-only Google Drive adapter to exchange an existing local authorized-user Application
Default Credentials refresh token for a short-lived access token at connector startup. This is a
source-v10 adapter extension; manifest-v2, Source identity, evidence, ACL, checkpoint, and recovery
contracts are unchanged.

`GOOGLE_DRIVE_TOKEN` remains a backward-compatible one-run override. Otherwise the adapter reads
`GOOGLE_APPLICATION_CREDENTIALS` or gcloud's standard local ADC path. It accepts only
`authorized_user` credentials with a client ID, client secret, and refresh token, and posts them
only to Google's fixed HTTPS token endpoint. OAuth response bodies are excluded from errors, and no
credential is persisted in graph, operations, or connector state.

## Evidence

- The local ADC file contains a refresh token and matches the installed Desktop OAuth client.
- A short-lived token was obtained without printing it; token introspection reported a Google Drive
  scope capable of content access.
- Unit tests prove refresh form submission, explicit-token precedence, rejection of non-refreshable
  credentials, and secret-free error messages.
- A provider-authenticated folder call exposed an invalid `files.list` order key in the fixture-only
  implementation. Removing unsupported `id` from `orderBy` fixed the real HTTP 400 while preserving
  deterministic local ID sorting; the mock test now locks the supported request.

## Account-bound source gate

The subsequent folder listing returned zero items. A direct metadata check proved that the ADC
Drive identity cannot access the Source's bound folder, and its Drive user does not match the ADC
account recorded in the credential file. The zero-item manifest touched no Documents and created no
tombstones. Its checkpoint Event was removed under exact zero-item and sync-run preconditions, the
generated state was quarantined, and Doctor passed 40/40 afterward.

Therefore this run proves durable token refresh and live Google API transport, but not a complete
personal-folder refresh. The remaining gate is to authorize ADC with the Google account that can
open the bound folder, or explicitly share that folder with the current ADC account. Do not rebind
the existing Source to another account implicitly.

## Source-v11 integrity follow-up

The wrong-account run also demonstrated that an empty first connector inventory could checkpoint
an existing Source whose Documents predated connector state. Source-v11 now rejects that exact
combination: zero manifest records, one or more existing active Documents, no current Source cursor,
and no expected previous cursor. A genuinely new empty Source and a later empty snapshot with a
compare-and-set cursor remain valid. This general manifest-v2 guard protects every source adapter,
not only Google Drive.

## Provider-authenticated replay

The dedicated Knowledge OS ADC subsequently accessed the already bound folder. The first complete
snapshot read 12 files and promoted 12 source-v11 current DocumentVersions while retaining the old
versions as history. The next run reported 12 unchanged items, zero changed items, zero tombstones,
and zero new Chunks. Once the previous cursor was stable, the third identical run reused the same
sync-run and checkpoint Event and returned manifest-level `unchanged=true` with zero result records.

The first promotion exposed a Neo4j driver cardinality warning: deactivating every Chunk on a prior
version carried one row per Chunk into the new-version merge, so the transaction returned the same
version ID multiple times. The graph remained valid, but the write now uses `WITH DISTINCT` before
the merge. This removes redundant writes and guarantees the single-record result expected by the
driver without changing version identity or lineage.

## OAuth long-term operation audit

The Google Auth Platform Audience page for the dedicated project reported an external app in
`Testing`, with one test user. Publishing was disabled because Google considered the OAuth app
configuration incomplete. The Branding page retained the app name, support email, and developer
contact, while the Data Access page listed no declared scopes.

A live token introspection of the dedicated ADC showed `drive.readonly`, `openid`, and identity
scopes, but also the unrelated broad `cloud-platform` scope. The current token remains usable for
bounded ingestion, but it is not accepted as the unattended long-term credential: Testing-mode
refresh tokens for non-basic scopes have a seven-day lifetime, and the broad cloud scope violates
the connector's minimum-sufficient-access policy. The corrective gate is to declare the required
Drive scope in Google Auth Platform, reauthorize the dedicated desktop client without
`cloud-platform`, repeat the provider snapshot/replay checks, and only then decide whether to move
the personal app to Production. No console setting or credential was changed during this audit.

## Source-v12 access-token narrowing

Google's token endpoint permits a refresh request to ask for a subset of the scopes in the original
authorization. A live bounded experiment added only `drive.readonly` to the refresh form; token
introspection then returned exactly that one scope, with no `cloud-platform` or identity scopes.
Source-v12 makes this restriction mandatory for every ADC refresh. This immediately limits the
bearer token used by ingestion while leaving Source identity, manifest-v2, evidence, ACL, and
checkpoint contracts unchanged. Reauthorization is still required to remove the historical broad
grant itself, and Testing-mode expiry remains unresolved until the consent configuration is fixed.
The installed source-v12 connector then completed a provider-authenticated replay of all 12 files:
all were unchanged, no record or tombstone was created, the existing sync-run/checkpoint was reused,
and introspection of the connector-issued token returned exactly `drive.readonly`.

## Local secret-boundary audit

The dedicated ADC is owned by the local user with mode `0600` and is outside Git. `.env`, the Drive
state, and the Notion state are all ignored. A bounded scan of tracked files found no Google access
token or Notion integration-token signatures. This check validates repository hygiene, not host
encryption or credential revocation policy.

## Consent configuration update

With explicit owner authorization, the Google Auth Platform Data Access configuration was updated
to declare only `https://www.googleapis.com/auth/drive.readonly`; the console classified it as a
restricted Drive scope. No logo, fabricated URL, or unrelated scope was added. The Audience page
continued to disable publishing and directed the owner to complete Branding. The saved app name,
support email, and developer contact are present, but no application homepage, privacy-policy URL,
or authorized domain exists. Google's production policy requires a public homepage and privacy
policy on a verified domain owned by the operator. No owned/verifiable domain was discoverable in
the local project configuration, so Production publication and the subsequent long-lived
reauthorization remain gated rather than substituting a third-party or false domain.

## Accepted personal operating mode

The owner explicitly selected the minimum personal-use option: keep the dedicated OAuth app in
Testing and reauthorize when Google's seven-day test authorization expires. Production branding,
domain acquisition, logo creation, and verification are intentionally out of scope for the current
personal deployment. This is an accepted operational limitation, not evidence of unattended
credential durability. The connector remains read-only and narrows every refreshed access token to
`drive.readonly`; the dedicated ADC path and provider replay evidence remain unchanged.
