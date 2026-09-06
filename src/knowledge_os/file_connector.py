import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from knowledge_os.connector_observation import observe_connector_run
from knowledge_os.dependencies import get_graph
from knowledge_os.ids import stable_id
from knowledge_os.models import SyncManifest

SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".pdf", ".docx", ".vtt", ".srt"}


def extract_file(path: Path) -> tuple[str, str]:
    suffix = path.suffix.casefold()
    if suffix in {".txt", ".md", ".markdown", ".rst", ".vtt", ".srt"}:
        return path.read_text(encoding="utf-8"), f"{suffix.removeprefix('.')}-utf8-v1"
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF ingestion requires: uv sync --extra connectors") from exc
        reader = PdfReader(path)
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            raise ValueError(f"PDF contains no extractable text: {path}")
        return text, "pypdf-text-v1"
    if suffix == ".docx":
        try:
            from docx import Document as DocxDocument
        except ImportError as exc:
            raise RuntimeError("DOCX ingestion requires: uv sync --extra connectors") from exc
        document = DocxDocument(path)
        text = "\n\n".join(
            paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()
        )
        if not text:
            raise ValueError(f"DOCX contains no extractable text: {path}")
        return text, "python-docx-text-v1"
    raise ValueError(f"unsupported file type: {path.suffix}")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "1", "files": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != "1" or not isinstance(data.get("files"), dict):
        raise ValueError(f"unsupported connector state: {path}")
    return data


def build_manifest(
    root: Path,
    state: dict[str, Any],
    *,
    workspace_id: str,
    source_external_id: str,
    connector_id: str,
    owner: str | None,
    visibility: str,
    acl: list[str],
    source_type: str = "filesystem",
) -> tuple[SyncManifest, dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"document root is not a directory: {root}")
    if state.get("root") and Path(state["root"]).resolve() != root:
        raise ValueError("connector state belongs to a different document root")
    if state.get("source_external_id") and state["source_external_id"] != source_external_id:
        raise ValueError("connector state belongs to a different source_external_id")
    if state.get("workspace_id") and state["workspace_id"] != workspace_id:
        raise ValueError("connector state belongs to a different workspace")
    if state.get("source_type") and state["source_type"] != source_type:
        raise ValueError("connector state belongs to a different source_type")
    if state.get("connector_id") and state["connector_id"] != connector_id:
        raise ValueError("connector state belongs to a different connector_id")
    files: dict[str, dict[str, str]] = {}
    records: list[dict[str, Any]] = []
    paths = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        raw_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        text, parser_version = extract_file(path)
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
        files[relative] = {
            "source_version": raw_digest,
            "source_updated_at": updated_at,
        }
        records.append(
            {
                "operation": "UPSERT",
                "document_external_id": relative,
                "source_version": raw_digest,
                "source_updated_at": updated_at,
                "title": path.stem,
                "document_source_uri": path.as_uri(),
                "content": text,
                "owner": owner,
                "visibility": visibility,
                "acl": sorted(set(acl)),
                "parser_version": parser_version,
                "chunker_version": "paragraph-v1",
                "chunk_size": 1200,
            }
        )
    cursor = stable_id("file-inventory", source_external_id, files)
    previous_cursor = state.get("cursor")
    previous_files = state.get("files", {})
    for relative in sorted(set(previous_files) - set(files)):
        records.append(
            {
                "operation": "TOMBSTONE",
                "document_external_id": relative,
                "source_version": stable_id(
                    "file-deletion",
                    relative,
                    previous_files[relative]["source_version"],
                    cursor,
                ),
                "reason": "file absent from current directory snapshot",
            }
        )
    manifest = SyncManifest.model_validate(
        {
            "workspace_id": workspace_id,
            "source_type": source_type,
            "source_external_id": source_external_id,
            "source_uri": root.as_uri(),
            "sync_run_id": stable_id("file-sync-run", source_external_id, previous_cursor, cursor),
            "cursor": cursor,
            "expected_previous_cursor": previous_cursor,
            "connector_id": connector_id,
            "records": records,
        }
    )
    new_state = {
        "version": "1",
        "root": str(root),
        "workspace_id": workspace_id,
        "source_type": source_type,
        "source_external_id": source_external_id,
        "connector_id": connector_id,
        "cursor": cursor,
        "files": files,
    }
    return manifest, new_state


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize a local document directory through atomic manifest-v2"
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--workspace", default="personal")
    parser.add_argument("--source-id")
    parser.add_argument("--source-type", default="filesystem")
    parser.add_argument("--connector-id", default="filesystem-connector-v1")
    parser.add_argument("--owner", default="local-user")
    parser.add_argument("--visibility", default="PRIVATE")
    parser.add_argument("--acl", action="append", default=[])
    args = parser.parse_args()

    with observe_connector_run(
        "filesystem_connector",
        workspace_id=args.workspace,
        source_type=args.source_type,
        connector_id=args.connector_id,
    ):
        root = args.root.resolve()
        source_external_id = args.source_id or str(root)
        state = load_state(args.state)
        manifest, new_state = build_manifest(
            root,
            state,
            workspace_id=args.workspace,
            source_external_id=source_external_id,
            connector_id=args.connector_id,
            owner=args.owner,
            visibility=args.visibility,
            acl=args.acl,
            source_type=args.source_type,
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
