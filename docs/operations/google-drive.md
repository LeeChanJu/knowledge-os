# Google Drive ingestion

`knowledge-os-ingest-google-drive` is a read-only source adapter. It lists every non-trashed file
in one explicitly selected folder, follows Google Drive pagination, reads each file's effective
permissions and content, and translates the complete snapshot into the existing atomic
manifest-v2 contract. It never writes to Google Drive.

Use OAuth authorized-user credentials with the minimum read scopes required to read the selected
folder's metadata, content, and permissions. For durable local operation, the connector reads
Application Default Credentials (ADC) from `GOOGLE_APPLICATION_CREDENTIALS` or, by default,
`~/.config/gcloud/application_default_credentials.json`. It exchanges the stored refresh token for
a short-lived access token at process start and explicitly narrows that token to `drive.readonly`,
even if the historical grant contains unrelated scopes. Neither credential is written to Neo4j,
SQLite, the connector state, or logs:

```bash
knowledge-os-ingest-google-drive \
  --folder FOLDER_ID \
  --state data/google-drive-state.json \
  --workspace personal \
  --connector-id google-drive-v1
```

An explicit short-lived token remains available for one-off runs and takes precedence over ADC.
Keep it outside Git and pass it only through the environment:

```bash
export GOOGLE_DRIVE_TOKEN='...'
knowledge-os-ingest-google-drive \
  --folder FOLDER_ID \
  --state data/google-drive-state.json \
  --workspace personal \
  --connector-id google-drive-v1
```

The ignored state file is written atomically only after Neo4j commits all item changes and the
Source checkpoint. An interrupted first run therefore safely replays. Later runs compare against
the committed cursor, tombstone files absent from the complete authorized folder listing, and
retain all prior DocumentVersions and deletion Events.

Google Drive user and group permissions become stable `google-drive:permission:*` principals;
domain and anyone permissions remain explicit. The connected user's own identity is normalized to
`google-drive:me` so the local MCP access context stays stable. Missing or unidentifiable permission
data fails closed instead of inventing access. Each DocumentVersion records its own Drive
`webViewLink`, while the Source retains the folder URI.

The current minimal parser accepts UTF-8 text, Markdown, CSV, JSON, Google Docs, Sheets, and Slides.
Native Google files are exported to deterministic text formats. Unsupported binary MIME types fail
the entire snapshot before ingestion; add a versioned parser only when an actual source requires
it. This preserves the full-listing guarantee and prevents a partial snapshot from falsely
tombstoning documents.

Treat access and refresh tokens as secrets. ADC must be authorized-user credentials containing a
client ID, client secret, and refresh token. Service-account JSON is rejected because silently
changing the source identity would violate the connector binding. Token acquisition and refresh
remain in the host connector boundary, not Neo4j or the graph contract.

The current personal deployment intentionally keeps its external OAuth app in Testing. Google test
authorizations that request Drive scopes expire after seven days, so this mode requires periodic
interactive reauthorization of the same dedicated desktop client and replacement of only the
dedicated ADC file. Do not fall back to global ADC, another account, or another client. Production
branding and domain infrastructure are deferred until unattended operation is a measured need.
When Google reports `invalid_grant`, the connector emits a bounded instruction to reauthorize the
dedicated ADC without including Google's response body, refresh token, or client secret in logs.
