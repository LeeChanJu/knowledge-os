import hashlib
import json


def stable_id(namespace: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def source_id(workspace_id: str, source_type: str, external_id: str) -> str:
    """Scope source identity to a workspace without trusting delimiter-safe external IDs."""
    return stable_id("source", workspace_id, source_type, external_id)


def document_id(source_identifier: str, external_id: str) -> str:
    return stable_id("document", source_identifier, external_id)


def access_fingerprint(workspace_id: str, principals: list[str]) -> str:
    """Bind operational records to a canonical access context without storing raw principals."""
    return stable_id("access-context", workspace_id, sorted(set(principals)))


def processing_fingerprint(
    content_digest: str,
    parser_version: str,
    chunker_version: str,
    chunk_size: int,
    source_version: str | None = None,
    source_updated_at: str | None = None,
    authorization: dict[str, object] | None = None,
) -> str:
    """Identify content, processing, source revision, and authorization snapshot."""
    return stable_id(
        "processing",
        content_digest,
        parser_version,
        chunker_version,
        chunk_size,
        source_version,
        source_updated_at,
        authorization or {},
    )
