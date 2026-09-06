import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from knowledge_os.connector_observation import observe_connector_run
from knowledge_os.dependencies import get_graph
from knowledge_os.file_connector import write_state
from knowledge_os.ids import stable_id
from knowledge_os.models import SyncManifest

DRIVE_API_BASE_URL = "https://www.googleapis.com/drive/v3"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
PARSER_VERSION = "google-drive-text-v1"
TEXT_MIME_TYPES = {
    "text/markdown",
    "text/plain",
    "text/x-markdown",
    "text/csv",
    "application/json",
}
GOOGLE_EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


@dataclass(frozen=True)
class DriveFileSnapshot:
    file_id: str
    name: str
    mime_type: str
    modified_time: str
    web_view_link: str | None
    content: str
    owner: str | None
    visibility: str
    acl: tuple[str, ...]
    source_checksum: str | None = None


class GoogleDriveAPI:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DRIVE_API_BASE_URL,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        response = self._client.get(path, params=params)
        if response.is_error:
            request_id = response.headers.get("x-guploader-uploadid", "unavailable")
            raise RuntimeError(
                f"Google Drive API returned HTTP {response.status_code} "
                f"(request_id={request_id})"
            )
        return response

    def current_user(self) -> dict[str, Any]:
        return self._get(
            "/about",
            params={"fields": "user(displayName,emailAddress,permissionId)"},
        ).json()["user"]

    def folder_files(self, folder_id: str) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "pageSize": 1000,
                "orderBy": "name",
                "spaces": "drive",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "fields": (
                    "nextPageToken,files(id,name,mimeType,modifiedTime,md5Checksum,headRevisionId,"
                    "size,webViewLink,trashed)"
                ),
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get("/files", params=params).json()
            files.extend(payload.get("files", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return sorted(files, key=lambda item: item["id"])

    def permissions(self, file_id: str) -> list[dict[str, Any]]:
        permissions: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {
                "pageSize": 100,
                "supportsAllDrives": "true",
                "fields": (
                    "nextPageToken,permissions(id,type,emailAddress,domain,role,deleted,"
                    "allowFileDiscovery,pendingOwner,permissionDetails)"
                ),
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get(f"/files/{file_id}/permissions", params=params).json()
            permissions.extend(payload.get("permissions", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return permissions

    def text_content(self, file: dict[str, Any]) -> str:
        mime_type = file["mimeType"]
        if mime_type in TEXT_MIME_TYPES:
            response = self._get(
                f"/files/{file['id']}",
                params={"alt": "media", "supportsAllDrives": "true"},
            )
        elif mime_type in GOOGLE_EXPORT_MIME_TYPES:
            response = self._get(
                f"/files/{file['id']}/export",
                params={"mimeType": GOOGLE_EXPORT_MIME_TYPES[mime_type]},
            )
        else:
            raise ValueError(
                f"unsupported Google Drive MIME type for {file['id']}: {mime_type}"
            )
        try:
            return response.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Google Drive file is not valid UTF-8: {file['id']}") from exc

    def file_revision(self, file_id: str) -> dict[str, Any]:
        return self._get(
            f"/files/{file_id}",
            params={
                "supportsAllDrives": "true",
                "fields": "id,modifiedTime,md5Checksum,headRevisionId,trashed",
            },
        ).json()


def application_default_credentials_path() -> Path:
    configured = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config" / "gcloud" / "application_default_credentials.json"


def refresh_google_access_token(
    credentials_path: Path,
    *,
    transport: httpx.BaseTransport | None = None,
    timeout: float = 30.0,
) -> str:
    """Exchange an ADC authorized-user refresh token without retaining either token."""
    try:
        credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("Google application default credentials were not found") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Google application default credentials could not be read") from exc
    required = ("client_id", "client_secret", "refresh_token")
    if credentials.get("type") != "authorized_user" or any(
        not isinstance(credentials.get(key), str) or not credentials[key] for key in required
    ):
        raise RuntimeError(
            "Google application default credentials must be authorized-user credentials "
            "with a refresh token"
        )
    with httpx.Client(transport=transport, timeout=timeout) as client:
        response = client.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "refresh_token": credentials["refresh_token"],
                "grant_type": "refresh_token",
                "scope": GOOGLE_DRIVE_READONLY_SCOPE,
            },
        )
    if response.is_error:
        try:
            oauth_error = response.json().get("error")
        except (json.JSONDecodeError, AttributeError):
            oauth_error = None
        if oauth_error == "invalid_grant":
            raise RuntimeError(
                "Google OAuth refresh credentials expired or were revoked; "
                "reauthorize the dedicated ADC"
            )
        raise RuntimeError(f"Google OAuth token refresh returned HTTP {response.status_code}")
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("Google OAuth token refresh returned invalid JSON") from exc
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Google OAuth token refresh returned no access token")
    if payload.get("token_type", "Bearer").casefold() != "bearer":
        raise RuntimeError("Google OAuth token refresh returned an unsupported token type")
    return token


def resolve_google_drive_token() -> str:
    """Prefer an explicit short-lived token, otherwise refresh local ADC credentials."""
    token = os.environ.get("GOOGLE_DRIVE_TOKEN")
    if token:
        return token
    return refresh_google_access_token(application_default_credentials_path())


def _permission_principal(permission: dict[str, Any], current_user: dict[str, Any]) -> str:
    if permission.get("id") == current_user.get("permissionId") or (
        permission.get("emailAddress")
        and permission.get("emailAddress") == current_user.get("emailAddress")
    ):
        return "google-drive:me"
    permission_type = permission.get("type")
    if permission_type in {"user", "group"} and permission.get("id"):
        return f"google-drive:permission:{permission['id']}"
    if permission_type == "domain" and permission.get("domain"):
        return f"google-drive:domain:{permission['domain'].casefold()}"
    if permission_type == "anyone":
        return "google-drive:anyone"
    raise ValueError("Google Drive permission lacks a stable authorization identity")


def authorization_snapshot(
    permissions: list[dict[str, Any]], current_user: dict[str, Any]
) -> tuple[str | None, str, tuple[str, ...]]:
    active = [permission for permission in permissions if not permission.get("deleted", False)]
    if not active:
        raise ValueError("Google Drive returned no active permissions; authorization is unknown")
    principals = tuple(sorted({_permission_principal(item, current_user) for item in active}))
    owner_candidates = sorted(
        {
            _permission_principal(item, current_user)
            for item in active
            if item.get("role") == "owner"
        }
    )
    owner = owner_candidates[0] if len(owner_candidates) == 1 else None
    visibility = "PUBLIC" if "google-drive:anyone" in principals else (
        "PRIVATE" if principals == ("google-drive:me",) else "SHARED"
    )
    return owner, visibility, principals


def snapshot_folder(
    api: GoogleDriveAPI, folder_id: str
) -> tuple[str, list[DriveFileSnapshot]]:
    current_user = api.current_user()
    if not current_user.get("permissionId"):
        raise ValueError("Google Drive current user has no stable permissionId")
    snapshots: list[DriveFileSnapshot] = []
    for file in api.folder_files(folder_id):
        if file.get("trashed"):
            raise ValueError(f"trashed file appeared in filtered listing: {file['id']}")
        owner, visibility, acl = authorization_snapshot(api.permissions(file["id"]), current_user)
        content = api.text_content(file)
        observed_revision = api.file_revision(file["id"])
        revision_fields = ("modifiedTime", "md5Checksum", "headRevisionId")
        if any(observed_revision.get(key) != file.get(key) for key in revision_fields) or bool(
            observed_revision.get("trashed")
        ) != bool(file.get("trashed")):
            raise RuntimeError(f"Google Drive file changed during snapshot: {file['id']}")
        # MD5 is compared only to Google's source checksum; SHA-256 remains our identity hash.
        if file.get("md5Checksum") and hashlib.md5(content.encode("utf-8")).hexdigest() != file[
            "md5Checksum"
        ]:
            raise RuntimeError(f"Google Drive content checksum mismatch: {file['id']}")
        snapshots.append(
            DriveFileSnapshot(
                file_id=file["id"],
                name=file["name"],
                mime_type=file["mimeType"],
                modified_time=file["modifiedTime"],
                web_view_link=file.get("webViewLink"),
                content=content,
                owner=owner,
                visibility=visibility,
                acl=acl,
                source_checksum=file.get("md5Checksum"),
            )
        )
    return f"google-drive:permission:{current_user['permissionId']}", snapshots


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "1", "files": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != "1" or not isinstance(data.get("files"), dict):
        raise ValueError(f"unsupported Google Drive connector state: {path}")
    return data


def build_manifest(
    snapshots: list[DriveFileSnapshot],
    state: dict[str, Any],
    *,
    workspace_id: str,
    folder_id: str,
    connection_id: str,
    connector_id: str,
) -> tuple[SyncManifest, dict[str, Any]]:
    for key, value, label in (
        ("folder_id", folder_id, "folder"),
        ("connection_id", connection_id, "connection"),
        ("workspace_id", workspace_id, "workspace"),
        ("connector_id", connector_id, "connector_id"),
    ):
        if state.get(key) and state[key] != value:
            raise ValueError(f"connector state belongs to a different Google Drive {label}")
    ids = [snapshot.file_id for snapshot in snapshots]
    if len(ids) != len(set(ids)):
        raise ValueError("Google Drive snapshot contains duplicate file IDs")

    files: dict[str, dict[str, str]] = {}
    records: list[dict[str, Any]] = []
    for snapshot in sorted(snapshots, key=lambda item: item.file_id):
        content_digest = hashlib.sha256(snapshot.content.encode("utf-8")).hexdigest()
        source_version = stable_id(
            "google-drive-file-version",
            snapshot.file_id,
            snapshot.modified_time,
            snapshot.name,
            snapshot.mime_type,
            snapshot.web_view_link,
            snapshot.source_checksum,
            content_digest,
            snapshot.owner,
            snapshot.visibility,
            snapshot.acl,
            PARSER_VERSION,
        )
        files[snapshot.file_id] = {
            "source_version": source_version,
            "source_updated_at": snapshot.modified_time,
        }
        records.append(
            {
                "operation": "UPSERT",
                "document_external_id": snapshot.file_id,
                "source_version": source_version,
                "source_updated_at": snapshot.modified_time,
                "title": snapshot.name,
                "document_source_uri": snapshot.web_view_link
                or f"https://drive.google.com/open?id={snapshot.file_id}",
                "content": snapshot.content,
                "owner": snapshot.owner,
                "visibility": snapshot.visibility,
                "acl": list(snapshot.acl),
                "parser_version": PARSER_VERSION,
                "chunker_version": "paragraph-v1",
                "chunk_size": 1200,
            }
        )
    cursor = stable_id("google-drive-folder-inventory", folder_id, files)
    previous_cursor = state.get("cursor")
    previous_files = state.get("files", {})
    for file_id in sorted(set(previous_files) - set(files)):
        records.append(
            {
                "operation": "TOMBSTONE",
                "document_external_id": file_id,
                "source_version": stable_id(
                    "google-drive-file-deletion",
                    file_id,
                    previous_files[file_id]["source_version"],
                    cursor,
                ),
                "reason": "file absent from current authorized folder listing",
            }
        )
    manifest = SyncManifest.model_validate(
        {
            "workspace_id": workspace_id,
            "source_type": "google_drive_folder",
            "source_external_id": folder_id,
            "source_uri": f"https://drive.google.com/drive/folders/{folder_id}",
            "sync_run_id": stable_id(
                "google-drive-folder-sync", folder_id, previous_cursor, cursor
            ),
            "cursor": cursor,
            "expected_previous_cursor": previous_cursor,
            "connector_id": connector_id,
            "records": records,
        }
    )
    new_state = {
        "version": "1",
        "folder_id": folder_id,
        "connection_id": connection_id,
        "workspace_id": workspace_id,
        "connector_id": connector_id,
        "cursor": cursor,
        "files": files,
    }
    return manifest, new_state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize one Google Drive folder through atomic manifest-v2"
    )
    parser.add_argument("--folder", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--workspace", default="personal")
    parser.add_argument("--connector-id", default="google-drive-v1")
    args = parser.parse_args()

    try:
        token = resolve_google_drive_token()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    with observe_connector_run(
        "google_drive_connector",
        workspace_id=args.workspace,
        source_type="google_drive_folder",
        connector_id=args.connector_id,
    ):
        api = GoogleDriveAPI(token)
        try:
            connection_id, snapshots = snapshot_folder(api, args.folder)
        finally:
            api.close()
        state = load_state(args.state)
        manifest, new_state = build_manifest(
            snapshots,
            state,
            workspace_id=args.workspace,
            folder_id=args.folder,
            connection_id=connection_id,
            connector_id=args.connector_id,
        )
        graph = get_graph()
        try:
            graph.verify()
            result = graph.ingest_manifest(manifest)
            write_state(args.state, new_state)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            graph.close()


if __name__ == "__main__":
    main()
