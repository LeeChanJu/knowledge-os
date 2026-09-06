import argparse
import json
import os
import stat
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import httpx

from knowledge_os.connector_observation import observe_connector_run
from knowledge_os.dependencies import get_graph
from knowledge_os.file_connector import write_state
from knowledge_os.ids import stable_id
from knowledge_os.models import SyncManifest

NOTION_API_VERSION = "2026-03-11"
PARSER_VERSION = f"notion-api-{NOTION_API_VERSION}-block-text-v1"


def notion_token_path() -> Path:
    configured = os.environ.get("NOTION_TOKEN_FILE")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config" / "knowledge-os" / "notion_token"


def resolve_notion_token() -> str:
    """Prefer the process environment, then a local owner-only token file."""
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if token:
        return token

    path = notion_token_path()
    try:
        file_stat = path.lstat()
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Notion credentials were not found; set NOTION_TOKEN or create the owner-only "
            "NOTION_TOKEN_FILE"
        ) from exc
    except OSError as exc:
        raise RuntimeError("Notion token file metadata could not be read") from exc

    if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
        raise RuntimeError("Notion token file must be a regular file, not a symlink")
    if hasattr(os, "getuid") and file_stat.st_uid != os.getuid():
        raise RuntimeError("Notion token file must be owned by the current user")
    if stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise RuntimeError("Notion token file permissions must be 0600 or stricter")
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("Notion token file could not be read") from exc
    if not token:
        raise RuntimeError("Notion token file is empty")
    return token


def normalize_id(value: str) -> str:
    compact = value.replace("-", "").strip().lower()
    if len(compact) != 32 or any(character not in "0123456789abcdef" for character in compact):
        raise ValueError("Notion IDs must be 32 hexadecimal characters, with optional hyphens")
    return f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"


def _plain_text(items: list[dict[str, Any]] | None) -> str:
    return "".join(item.get("plain_text", "") for item in items or []).strip()


def _page_title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return _plain_text(prop.get("title")) or "Untitled"
    return "Untitled"


def _property_text(prop: dict[str, Any]) -> str:
    prop_type = prop.get("type", "unknown")
    value = prop.get(prop_type)
    if prop_type in {"title", "rich_text"}:
        return _plain_text(value)
    if prop_type in {"number", "checkbox", "url", "email", "phone_number"}:
        return "" if value is None else str(value)
    if prop_type in {"select", "status"}:
        return (value or {}).get("name", "")
    if prop_type == "multi_select":
        return ", ".join(item.get("name", "") for item in value or [])
    if prop_type == "date":
        if not value:
            return ""
        return " / ".join(
            str(value[key]) for key in ("start", "end", "time_zone") if value.get(key) is not None
        )
    if prop_type == "people":
        return ", ".join(item.get("name") or item.get("id", "") for item in value or [])
    if prop_type == "relation":
        relations = ", ".join(item.get("id", "") for item in value or [])
        return (
            f"{relations} [additional references not loaded]" if prop.get("has_more") else relations
        )
    if prop_type in {"created_time", "last_edited_time"}:
        return value or ""
    if prop_type in {"created_by", "last_edited_by"}:
        return (value or {}).get("name") or (value or {}).get("id", "")
    if prop_type == "files":
        items = []
        for item in value or []:
            stable_url = item.get("external", {}).get("url")
            items.append(" ".join(part for part in (item.get("name"), stable_url) if part))
        return ", ".join(items)
    if prop_type == "unique_id":
        return f"{(value or {}).get('prefix') or ''}{(value or {}).get('number') or ''}"
    if prop_type in {"formula", "rollup", "verification"}:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"[Unsupported Notion property: {prop_type}]"


def _properties_text(page: dict[str, Any]) -> str:
    lines = []
    for name, prop in sorted(page.get("properties", {}).items()):
        if prop.get("type") == "title":
            continue
        lines.append(f"- {name}: {_property_text(prop)}")
    return "\n".join(lines)


def _block_text(block: dict[str, Any]) -> str:
    block_type = block.get("type", "unsupported")
    value = block.get(block_type, {})
    text = _plain_text(value.get("rich_text"))
    if block_type.startswith("heading_"):
        level = block_type.removeprefix("heading_")
        return f"{'#' * int(level)} {text}" if text else ""
    if block_type == "bulleted_list_item":
        return f"- {text}"
    if block_type == "numbered_list_item":
        return f"1. {text}"
    if block_type == "to_do":
        return f"- [{'x' if value.get('checked') else ' '}] {text}"
    if block_type == "quote":
        return f"> {text}"
    if block_type == "code":
        language = value.get("language", "")
        return f"```{language}\n{text}\n```"
    if block_type == "equation":
        return value.get("expression", "")
    if block_type == "divider":
        return "---"
    if block_type == "child_page":
        return f"[Child page: {value.get('title', 'Untitled')}]"
    if block_type == "child_database":
        return f"[Child database: {value.get('title', 'Untitled')}]"
    if block_type == "table_row":
        cells = [_plain_text(cell) for cell in value.get("cells", [])]
        return " | ".join(cells)
    if block_type in {"bookmark", "embed", "link_preview"}:
        return text or value.get("url", "")
    if block_type in {"image", "video", "pdf", "file", "audio"}:
        caption = _plain_text(value.get("caption"))
        external_url = value.get("external", {}).get("url")
        detail = " ".join(item for item in (caption, external_url) if item)
        return f"[{block_type}: {detail}]" if detail else f"[{block_type}]"
    if text:
        return text
    if block_type in {"breadcrumb", "table_of_contents", "column_list", "column"}:
        return ""
    return f"[Unsupported Notion block: {block_type}]"


class NotionAPI:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.notion.com/v1",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            },
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, *, params: dict[str, str | int] | None = None) -> dict[str, Any]:
        response = self._client.get(path, params=params)
        if response.is_error:
            request_id = response.headers.get("x-request-id", "unavailable")
            raise RuntimeError(
                f"Notion API returned HTTP {response.status_code} (request_id={request_id})"
            )
        return response.json()

    def _post(self, path: str, *, json_body: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=json_body)
        if response.is_error:
            request_id = response.headers.get("x-request-id", "unavailable")
            raise RuntimeError(
                f"Notion API returned HTTP {response.status_code} (request_id={request_id})"
            )
        return response.json()

    def connection(self) -> dict[str, Any]:
        return self._get("/users/me")

    def page(self, page_id: str) -> dict[str, Any]:
        return self._get(f"/pages/{normalize_id(page_id)}")

    def page_property_items(self, page_id: str, property_id: str) -> list[dict[str, Any]]:
        encoded_property_id = quote(unquote(property_id), safe="")
        path = f"/pages/{normalize_id(page_id)}/properties/{encoded_property_id}"
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params: dict[str, str | int] = {"page_size": 100}
            if cursor is not None:
                params["start_cursor"] = cursor
            payload = self._get(path, params=params)
            if payload.get("object") != "list":
                return [payload]
            results.extend(payload.get("results", []))
            if not payload.get("has_more"):
                return results
            cursor = payload.get("next_cursor")
            if not cursor:
                raise RuntimeError("Notion pagination declared more results without a cursor")

    def database(self, database_id: str) -> dict[str, Any]:
        return self._get(f"/databases/{normalize_id(database_id)}")

    def block_children(self, block_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params: dict[str, str | int] = {"page_size": 100}
            if cursor is not None:
                params["start_cursor"] = cursor
            payload = self._get(f"/blocks/{normalize_id(block_id)}/children", params=params)
            results.extend(payload.get("results", []))
            if not payload.get("has_more"):
                return results
            cursor = payload.get("next_cursor")
            if not cursor:
                raise RuntimeError("Notion pagination declared more results without a cursor")

    def data_source_pages(self, data_source_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100, "result_type": "page"}
            if cursor is not None:
                body["start_cursor"] = cursor
            payload = self._post(
                f"/data_sources/{normalize_id(data_source_id)}/query", json_body=body
            )
            page_results = [
                item for item in payload.get("results", []) if item.get("object") == "page"
            ]
            results.extend(page_results)
            if len(results) >= 10_000:
                raise RuntimeError(
                    "Notion data source reached the 10,000-result API completeness limit"
                )
            if not payload.get("has_more"):
                return results
            cursor = payload.get("next_cursor")
            if not cursor:
                raise RuntimeError("Notion pagination declared more results without a cursor")


@dataclass(frozen=True)
class NotionPageSnapshot:
    page_id: str
    title: str
    last_edited_time: str
    content: str


def _complete_page_properties(api: NotionAPI, page: dict[str, Any]) -> dict[str, Any]:
    completed = deepcopy(page)
    for prop in completed.get("properties", {}).values():
        prop_type = prop.get("type")
        property_id = prop.get("id")
        if prop_type not in {"title", "rich_text", "relation"} or not property_id:
            continue
        items = api.page_property_items(page["id"], property_id)
        values = [item[prop_type] for item in items if item.get("type") == prop_type]
        prop[prop_type] = values
        if prop_type == "relation":
            prop["has_more"] = False
    return completed


def _page_content(api: NotionAPI, page_id: str) -> tuple[str, set[str], set[str]]:
    lines: list[str] = []
    child_pages: set[str] = set()
    child_databases: set[str] = set()
    seen_blocks: set[str] = set()

    def visit(parent_id: str, depth: int) -> None:
        for block in api.block_children(parent_id):
            block_type = block.get("type")
            block_id = normalize_id(block["id"])
            if block_id in seen_blocks:
                continue
            seen_blocks.add(block_id)
            rendered = _block_text(block)
            if rendered:
                lines.append(f"{'  ' * depth}{rendered}")
            if block_type == "child_page":
                child_pages.add(block_id)
            elif block_type == "child_database":
                child_databases.add(block_id)
            elif block.get("has_children") and block_type != "child_database":
                visit(block_id, depth + 1)

    visit(page_id, 0)
    return "\n\n".join(lines).strip(), child_pages, child_databases


def snapshot_page_tree(api: NotionAPI, root_page_id: str) -> list[NotionPageSnapshot]:
    pending = [normalize_id(root_page_id)]
    seen: set[str] = set()
    pending_databases: set[str] = set()
    seen_databases: set[str] = set()
    snapshots: list[NotionPageSnapshot] = []
    while pending or pending_databases:
        while pending:
            page_id = pending.pop(0)
            if page_id in seen:
                continue
            page = _complete_page_properties(api, api.page(page_id))
            canonical_id = normalize_id(page["id"])
            if canonical_id != page_id:
                raise RuntimeError("Notion returned a different page identity")
            content, children, child_databases = _page_content(api, page_id)
            title = _page_title(page)
            properties = _properties_text(page)
            sections = [f"# {title}"]
            if properties:
                sections.extend(["## Properties", properties])
            if content:
                sections.append(content)
            snapshots.append(
                NotionPageSnapshot(
                    page_id=page_id,
                    title=title,
                    last_edited_time=page["last_edited_time"],
                    content="\n\n".join(sections),
                )
            )
            pending.extend(sorted(children - seen))
            pending_databases.update(child_databases - seen_databases)
            seen.add(page_id)
        if pending_databases:
            database_id = min(pending_databases)
            pending_databases.remove(database_id)
            if database_id in seen_databases:
                continue
            database = api.database(database_id)
            for data_source in sorted(
                database.get("data_sources", []), key=lambda item: item["id"]
            ):
                for page in api.data_source_pages(data_source["id"]):
                    page_id = normalize_id(page["id"])
                    if page_id not in seen:
                        pending.append(page_id)
            seen_databases.add(database_id)
    return sorted(snapshots, key=lambda item: item.page_id)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "1", "pages": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != "1" or not isinstance(data.get("pages"), dict):
        raise ValueError(f"unsupported Notion connector state: {path}")
    return data


def build_manifest(
    snapshots: list[NotionPageSnapshot],
    state: dict[str, Any],
    *,
    workspace_id: str,
    root_page_id: str,
    connection_id: str,
    connector_id: str,
) -> tuple[SyncManifest, dict[str, Any]]:
    root_page_id = normalize_id(root_page_id)
    connection_id = normalize_id(connection_id)
    if state.get("root_page_id") and state["root_page_id"] != root_page_id:
        raise ValueError("connector state belongs to a different Notion root page")
    if state.get("connection_id") and state["connection_id"] != connection_id:
        raise ValueError("connector state belongs to a different Notion connection")
    principal = f"notion:connection:{connection_id}"
    pages: dict[str, dict[str, str]] = {}
    records: list[dict[str, Any]] = []
    for page in sorted(snapshots, key=lambda item: item.page_id):
        source_version = stable_id(
            "notion-page-version",
            page.page_id,
            page.last_edited_time,
            page.title,
            page.content,
            PARSER_VERSION,
        )
        pages[page.page_id] = {
            "source_version": source_version,
            "source_updated_at": page.last_edited_time,
        }
        records.append(
            {
                "operation": "UPSERT",
                "document_external_id": page.page_id,
                "source_version": source_version,
                "source_updated_at": page.last_edited_time,
                "title": page.title,
                "document_source_uri": (
                    f"https://www.notion.so/{page.page_id.replace('-', '')}"
                ),
                "content": page.content,
                "owner": principal,
                "visibility": "PRIVATE",
                "acl": [principal],
                "parser_version": PARSER_VERSION,
                "chunker_version": "paragraph-v1",
                "chunk_size": 1200,
            }
        )
    cursor = stable_id("notion-page-tree-inventory", root_page_id, pages)
    previous_cursor = state.get("cursor")
    previous_pages = state.get("pages", {})
    for page_id in sorted(set(previous_pages) - set(pages)):
        records.append(
            {
                "operation": "TOMBSTONE",
                "document_external_id": page_id,
                "source_version": stable_id(
                    "notion-page-deletion",
                    page_id,
                    previous_pages[page_id]["source_version"],
                    cursor,
                ),
                "reason": "page absent from current authorized root-page traversal",
            }
        )
    manifest = SyncManifest.model_validate(
        {
            "workspace_id": workspace_id,
            "source_type": "notion_page_tree",
            "source_external_id": root_page_id,
            "source_uri": f"https://www.notion.so/{root_page_id.replace('-', '')}",
            "sync_run_id": stable_id(
                "notion-page-tree-sync", root_page_id, previous_cursor, cursor
            ),
            "cursor": cursor,
            "expected_previous_cursor": previous_cursor,
            "connector_id": connector_id,
            "records": records,
        }
    )
    new_state = {
        "version": "1",
        "root_page_id": root_page_id,
        "connection_id": connection_id,
        "cursor": cursor,
        "pages": pages,
    }
    return manifest, new_state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize an authorized Notion page tree through atomic manifest-v2"
    )
    parser.add_argument("--root-page", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--workspace", default="personal")
    parser.add_argument("--connector-id", default="notion-api-personal-v1")
    args = parser.parse_args()

    try:
        token = resolve_notion_token()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    with observe_connector_run(
        "notion_connector",
        workspace_id=args.workspace,
        source_type="notion_page_tree",
        connector_id=args.connector_id,
    ):
        api = NotionAPI(token)
        try:
            connection = api.connection()
            connection_id = normalize_id(connection["id"])
            snapshots = snapshot_page_tree(api, args.root_page)
        finally:
            api.close()

        state = load_state(args.state)
        manifest, new_state = build_manifest(
            snapshots,
            state,
            workspace_id=args.workspace,
            root_page_id=args.root_page,
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
