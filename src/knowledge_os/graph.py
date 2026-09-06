import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

from neo4j import GraphDatabase

from knowledge_os.ids import (
    access_fingerprint,
    content_hash,
    document_id,
    processing_fingerprint,
    source_id,
    stable_id,
)
from knowledge_os.models import (
    AccessContext,
    ActionCreate,
    ActionExecutionClaimCreate,
    ActionExecutionCreate,
    CanonicalDatetime,
    DecisionProposalCreate,
    DocumentTombstoneRequest,
    EmbeddingUpsert,
    EventProposalCreate,
    EvidenceBundleRequest,
    IngestionResult,
    ProposalCreate,
    RetrievalQuery,
    SyncCheckpointCommit,
    SyncManifest,
    TextIngestionRequest,
)
from knowledge_os.ontology import Ontology
from knowledge_os.ops import OpsStore


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def split_text(text: str, limit: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > limit:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def literal_fulltext_query(query: str) -> str:
    """Convert user text to literal Lucene terms without exposing query syntax."""
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if not terms:
        return '"__knowledge_os_no_search_terms__"'
    return " ".join(f'"{term}"' for term in terms)


TITLE_STOP_WORDS = {
    "a",
    "an",
    "be",
    "can",
    "does",
    "for",
    "is",
    "of",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "why",
}
KEYWORD_RANKER_VERSION = "lexical-title-diversity-v1"


def embedding_fingerprint(vector: list[float], model: str, model_version: str) -> str:
    """Identify an embedding payload without retaining it in operational records."""
    payload = json.dumps(
        {"model": model, "model_version": model_version, "vector": vector},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return content_hash(payload)


def proposal_identity(kind: str, workspace_id: str, payload: dict) -> tuple[str, str, str]:
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload_hash = content_hash(payload_json)
    return (
        stable_id("proposal", kind, workspace_id, payload_hash),
        payload_hash,
        payload_json,
    )


def source_metadata_fingerprint(title: str, source_uri: str | None) -> str:
    payload = json.dumps(
        {"source_uri": source_uri, "title": title},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return content_hash(payload)


def validate_initial_manifest_inventory(
    *,
    record_count: int,
    existing_active_documents: int,
    current_cursor: str | None,
    expected_previous_cursor: str | None,
) -> None:
    """Refuse an unknowably empty first connector snapshot over existing evidence."""
    if (
        record_count == 0
        and existing_active_documents > 0
        and current_cursor is None
        and expected_previous_cursor is None
    ):
        raise ValueError(
            "empty initial manifest cannot checkpoint an existing non-empty source"
        )


def title_overlap(query: str, title: str) -> int:
    query_terms = set(re.findall(r"\w+", query.casefold(), flags=re.UNICODE)) - TITLE_STOP_WORDS
    title_terms = set(re.findall(r"\w+", title.casefold().replace("_", " "), flags=re.UNICODE))
    return len(query_terms & title_terms)


def rerank_keyword_results(query: str, results: list[dict], limit: int) -> list[dict]:
    reranked = []
    for result in results:
        item = dict(result)
        lexical_score = float(item["score"])
        overlap = title_overlap(query, item.get("title") or "")
        item["lexical_score"] = lexical_score
        item["title_overlap"] = overlap
        item["score"] = lexical_score + 2.0 * overlap
        reranked.append(item)
    ranked = sorted(
        reranked,
        key=lambda item: (-item["score"], -item["lexical_score"], item["chunk_id"]),
    )
    diversified = []
    deferred = []
    document_counts: dict[str, int] = {}
    for item in ranked:
        document = item["document_id"]
        if document_counts.get(document, 0) < 2:
            diversified.append(item)
            document_counts[document] = document_counts.get(document, 0) + 1
        else:
            deferred.append(item)
    return (diversified + deferred)[:limit]


class GraphStore:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str,
        ops: OpsStore,
        embedding_dimensions: int = 1536,
        contract_versions: dict[str, str] | None = None,
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.ops = ops
        self.embedding_dimensions = embedding_dimensions
        self.contract_versions = contract_versions or {"retrieval": "retrieval-v1"}

    def close(self) -> None:
        self.driver.close()

    def verify(self) -> None:
        self.driver.verify_connectivity()

    def migrate(self, directory: Path) -> list[str]:
        applied: list[str] = []
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                CREATE CONSTRAINT schema_migration_name_unique IF NOT EXISTS
                FOR (n:SchemaMigration) REQUIRE n.name IS UNIQUE
                """
            ).consume()
            for path in sorted(directory.glob("*.cypher")):
                migration = path.read_text(encoding="utf-8")
                statements = [s.strip() for s in migration.split(";") if s.strip()]
                was_applied = self._apply_migration(
                    session,
                    path.name,
                    content_hash(migration),
                    statements,
                )
                if was_applied:
                    applied.append(path.name)
        return applied

    @staticmethod
    def _apply_migration(session, name: str, checksum: str, statements: list[str]) -> bool:
        existing = session.run(
            "MATCH (m:SchemaMigration {name:$name}) RETURN m.checksum AS checksum",
            name=name,
        ).single()
        if existing:
            if existing["checksum"] != checksum:
                raise ValueError(
                    f"applied migration {name} has changed; add a new migration instead"
                )
            return False
        for statement in statements:
            # Neo4j forbids mixing schema and data changes in one transaction.
            # Numbered migrations must therefore keep DDL idempotent so a failed
            # application can safely resume before the ledger entry is written.
            session.run(statement).consume()
        session.run(
            """
            CREATE (:SchemaMigration {
                name:$name, checksum:$checksum, applied_at:$applied_at
            })
            """,
            name=name,
            checksum=checksum,
            applied_at=now_iso(),
        ).consume()
        return True

    def ingest_text(self, request: TextIngestionRequest) -> IngestionResult:
        started = perf_counter()
        source_identifier = source_id(
            request.workspace_id, request.source_type, request.source_external_id
        )
        document_identifier = document_id(source_identifier, request.document_external_id)
        digest = content_hash(request.content)
        fingerprint = processing_fingerprint(
            digest,
            request.parser_version,
            request.chunker_version,
            request.chunk_size,
            request.source_version,
            request.source_updated_at.isoformat() if request.source_updated_at else None,
            {
                "owner": request.owner,
                "visibility": request.visibility,
                "acl": request.acl,
            },
        )
        version_id = stable_id("document-version", document_identifier, fingerprint)
        document_source_uri = request.document_source_uri or request.source_uri
        metadata_hash = source_metadata_fingerprint(request.title, document_source_uri)
        chunks = split_text(request.content, request.chunk_size)
        with self.driver.session(database=self.database) as session:
            source = session.run(
                "MATCH (s:Source {id:$id}) RETURN s.connector_id AS connector_id",
                id=source_identifier,
            ).single()
            if source and source["connector_id"] not in (None, request.connector_id):
                raise PermissionError("source is bound to a different connector")
            existing = session.run(
                """
                MATCH (d:Document {id:$id})-[:CURRENT_VERSION]->(v)
                RETURN d.status AS status, v.id AS id,
                       v.processing_fingerprint AS fingerprint,
                       d.title AS title, v.source_uri AS source_uri,
                       v.source_metadata_hash AS source_metadata_hash
                """,
                id=document_identifier,
            ).single()
            if (
                existing
                and existing["status"] == "ACTIVE"
                and existing["fingerprint"] == fingerprint
            ):
                existing_metadata_hash = existing["source_metadata_hash"] or (
                    source_metadata_fingerprint(existing["title"], existing["source_uri"])
                )
                if existing_metadata_hash != metadata_hash:
                    raise ValueError(
                        "source revision is already bound to different document metadata"
                    )
                claimed = session.run(
                    """
                    MATCH (s:Source {id:$source_id})
                    WHERE s.connector_id IS NULL OR s.connector_id=$connector_id
                    SET s.connector_id=coalesce(s.connector_id, $connector_id)
                    SET s.last_seen=$now, s.pending_sync_cursor=$sync_cursor,
                        s.last_item_sync_run_id=$sync_run_id, s.status='ACTIVE'
                    RETURN s.id AS id
                    """,
                    source_id=source_identifier,
                    connector_id=request.connector_id,
                    sync_cursor=request.sync_cursor,
                    sync_run_id=request.sync_run_id,
                    now=now_iso(),
                ).single()
                if not claimed:
                    raise PermissionError("source is bound to a different connector")
                self.ops.telemetry(
                    "ingestion", "UNCHANGED", started, document_id=document_identifier
                )
                return IngestionResult(
                    source_id=source_identifier,
                    document_id=document_identifier,
                    document_version_id=version_id,
                    content_hash=digest,
                    processing_fingerprint=fingerprint,
                    chunks_created=0,
                    unchanged=True,
                )
            if existing is None and request.expected_current_version_id is not None:
                raise ValueError("document has no current version; expected version is stale")
            if existing is not None:
                if request.expected_current_version_id is None:
                    raise ValueError(
                        "expected_current_version_id is required when changing an existing document"
                    )
                if request.expected_current_version_id != existing["id"]:
                    raise ValueError("document current version changed; ingestion request is stale")
            historical = session.run(
                """
                MATCH (:Document {id:$document_id})-[:HAS_VERSION]->(v:DocumentVersion {id:$version_id})
                RETURN v.id AS id
                """,
                document_id=document_identifier,
                version_id=version_id,
            ).single()
            if historical:
                self.ops.telemetry(
                    "ingestion",
                    "AMBIGUOUS_REVERSION",
                    started,
                    document_id=document_identifier,
                    document_version_id=version_id,
                )
                raise ValueError(
                    "document returned to a previously observed state without a distinct "
                    "source_version or source_updated_at"
                )
            session.execute_write(
                self._write_version,
                request,
                source_identifier,
                document_identifier,
                version_id,
                digest,
                fingerprint,
                chunks,
                request.expected_current_version_id,
                False,
                metadata_hash,
                self.contract_versions["source"],
            )
        self.ops.telemetry(
            "ingestion",
            "SUCCESS",
            started,
            document_id=document_identifier,
            chunks=len(chunks),
        )
        return IngestionResult(
            source_id=source_identifier,
            document_id=document_identifier,
            document_version_id=version_id,
            content_hash=digest,
            processing_fingerprint=fingerprint,
            chunks_created=len(chunks),
            unchanged=False,
        )

    @staticmethod
    def _write_version(
        tx,
        req,
        source_id,
        document_id,
        version_id,
        digest,
        fingerprint,
        chunks,
        expected_current_version_id,
        allow_reactivate,
        metadata_hash,
        source_contract_version,
    ):
        timestamp = now_iso()
        bound = tx.run(
            """
            MERGE (w:Workspace {id:$workspace_id})
            ON CREATE SET w.created_at=$now
            MERGE (s:Source {id:$source_id})
            ON CREATE SET s.connector_id=$connector_id
            WITH w, s
            WHERE s.connector_id IS NULL OR s.connector_id=$connector_id
            SET s.connector_id=coalesce(s.connector_id, $connector_id)
            SET s.type=$source_type, s.external_id=$source_external_id,
                s.uri=$source_uri, s.owner=$owner,
                s.visibility=$visibility, s.acl=$acl, s.last_seen=$now,
                s.pending_sync_cursor=$sync_cursor, s.last_item_sync_run_id=$sync_run_id,
                s.status='ACTIVE'
            MERGE (d:Document {id:$document_id})
            ON CREATE SET d.created_at=$now
            MERGE (s)-[:HAS_DOCUMENT]->(d)
            MERGE (w)-[:OWNS_SOURCE]->(s)
            WITH d
            OPTIONAL MATCH (d)-[old:CURRENT_VERSION]->(previous:DocumentVersion)
            WITH d, old, previous
            WHERE (previous IS NULL AND $expected_current_version_id IS NULL)
               OR (previous.id=$expected_current_version_id
                   AND (d.status='ACTIVE' OR $allow_reactivate))
            DELETE old
            SET d.external_id=$document_external_id, d.title=$title,
                d.updated_at=$now, d.status='ACTIVE'
            WITH d, previous
            OPTIONAL MATCH (previous)-[:HAS_CHUNK]->(previous_chunk:Chunk)
            SET previous_chunk.active=false
            WITH DISTINCT d, previous
            MERGE (v:DocumentVersion {id:$version_id})
            SET v.content_hash=$hash, v.parser_version=$parser_version,
                v.chunker_version=$chunker_version, v.chunk_size=$chunk_size,
                v.processing_fingerprint=$fingerprint,
                v.source_version=$source_version, v.source_updated_at=$source_updated_at,
                v.source_uri=$document_source_uri, v.title=$title,
                v.source_metadata_hash=$source_metadata_hash,
                v.source_contract_version=$source_contract_version, v.owner=$owner,
                v.visibility=$visibility, v.acl=$acl,
                v.recorded_at=$now, v.status='ACTIVE'
            MERGE (d)-[:HAS_VERSION]->(v)
            MERGE (d)-[:CURRENT_VERSION]->(v)
            FOREACH (_ IN CASE WHEN previous IS NULL OR previous.id=$version_id THEN [] ELSE [1] END |
                MERGE (v)-[:SUPERSEDES]->(previous))
            RETURN v.id AS id
            """,
            workspace_id=req.workspace_id,
            source_id=source_id,
            connector_id=req.connector_id,
            source_type=req.source_type,
            source_external_id=req.source_external_id,
            source_uri=req.source_uri,
            document_source_uri=req.document_source_uri or req.source_uri,
            owner=req.owner,
            visibility=req.visibility,
            acl=req.acl,
            document_id=document_id,
            document_external_id=req.document_external_id,
            title=req.title,
            version_id=version_id,
            expected_current_version_id=expected_current_version_id,
            allow_reactivate=allow_reactivate,
            source_metadata_hash=metadata_hash,
            source_contract_version=source_contract_version,
            hash=digest,
            fingerprint=fingerprint,
            parser_version=req.parser_version,
            chunker_version=req.chunker_version,
            chunk_size=req.chunk_size,
            source_version=req.source_version,
            source_updated_at=(
                req.source_updated_at.isoformat() if req.source_updated_at else None
            ),
            sync_cursor=req.sync_cursor,
            sync_run_id=req.sync_run_id,
            now=timestamp,
        ).single()
        if not bound:
            raise ValueError("document current version changed; ingestion request is stale")
        rows = []
        for position, text in enumerate(chunks):
            rows.append(
                {
                    "id": stable_id("chunk", version_id, position, content_hash(text)),
                    "position": position,
                    "text": text,
                    "hash": content_hash(text),
                }
            )
        tx.run(
            """
            MATCH (v:DocumentVersion {id:$version_id})
            UNWIND $rows AS row
            MERGE (c:Chunk {id:row.id})
            SET c.position=row.position, c.text=row.text, c.content_hash=row.hash,
                c.active=true, c.created_at=$now, c.embedding_model=null,
                c.embedding_version=null
            MERGE (v)-[:HAS_CHUNK]->(c)
            """,
            version_id=version_id,
            rows=rows,
            now=timestamp,
        ).consume()

    def tombstone_document(self, request: DocumentTombstoneRequest) -> dict:
        started = perf_counter()
        source_identifier = source_id(
            request.workspace_id, request.source_type, request.source_external_id
        )
        document_identifier = document_id(source_identifier, request.document_external_id)
        event_id = stable_id(
            "event", document_identifier, "SOURCE_DOCUMENT_DELETED", request.source_version
        )
        with self.driver.session(database=self.database) as session:
            source = session.run(
                "MATCH (s:Source {id:$id}) RETURN s.connector_id AS connector_id",
                id=source_identifier,
            ).single()
            if not source:
                raise KeyError(document_identifier)
            if source["connector_id"] != request.connector_id:
                raise PermissionError("source is bound to a different connector")
            existing = session.run(
                "MATCH (e:Event {id:$event_id}) RETURN e.id AS id",
                event_id=event_id,
            ).single()
            if existing:
                session.run(
                    """
                    MATCH (s:Source {id:$source_id})
                    WHERE s.connector_id=$connector_id
                    SET s.last_seen=$now, s.pending_sync_cursor=$sync_cursor,
                        s.last_item_sync_run_id=$sync_run_id
                    """,
                    source_id=source_identifier,
                    connector_id=request.connector_id,
                    sync_cursor=request.sync_cursor,
                    sync_run_id=request.sync_run_id,
                    now=now_iso(),
                ).consume()
                self.ops.telemetry(
                    "ingestion_tombstone",
                    "UNCHANGED",
                    started,
                    document_id=document_identifier,
                )
                return {
                    "source_id": source_identifier,
                    "document_id": document_identifier,
                    "event_id": event_id,
                    "status": "DELETED",
                    "unchanged": True,
                }
            current = session.run(
                """
                MATCH (:Source {id:$source_id})-[:HAS_DOCUMENT]->(d:Document {id:$document_id})
                      -[:CURRENT_VERSION]->(v:DocumentVersion)
                RETURN d.status AS status, v.id AS id
                """,
                source_id=source_identifier,
                document_id=document_identifier,
            ).single()
            if not current:
                raise KeyError(document_identifier)
            if request.expected_current_version_id is None:
                raise ValueError("expected_current_version_id is required when deleting a document")
            if request.expected_current_version_id != current["id"]:
                raise ValueError("document current version changed; tombstone request is stale")
            if current["status"] != "ACTIVE":
                raise ValueError("document is no longer active")
            row = session.execute_write(
                self._write_tombstone,
                request,
                source_identifier,
                document_identifier,
                event_id,
                request.expected_current_version_id,
            )
        if not row:
            raise ValueError("document current version changed; tombstone request is stale")
        self.ops.audit(
            request.recorded_by,
            "TOMBSTONE_DOCUMENT",
            document_identifier,
            event_id=event_id,
            source_version=request.source_version,
        )
        self.ops.telemetry(
            "ingestion_tombstone",
            "SUCCESS",
            started,
            document_id=document_identifier,
            event_id=event_id,
        )
        return {
            "source_id": source_identifier,
            "document_id": document_identifier,
            "event_id": event_id,
            "status": "DELETED",
            "unchanged": False,
        }

    @staticmethod
    def _write_tombstone(
        tx,
        request,
        source_identifier,
        document_identifier,
        event_id,
        expected_current_version_id,
    ):
        row = tx.run(
            """
            MATCH (s:Source {id:$source_id})-[:HAS_DOCUMENT]->(d:Document {id:$document_id})
                  -[:CURRENT_VERSION]->(current:DocumentVersion)
            WHERE s.connector_id=$connector_id AND d.status='ACTIVE'
              AND current.id=$expected_current_version_id
            SET s.last_seen=$now, s.pending_sync_cursor=$sync_cursor,
                s.last_item_sync_run_id=$sync_run_id,
                d.status='DELETED', d.deleted_at=$deleted_at,
                d.deletion_source_version=$source_version
            CREATE (e:Event {
                id:$event_id, event_type:'SOURCE_DOCUMENT_DELETED', status:'OBSERVED',
                source_version:$source_version, deleted_at:$deleted_at,
                observation_cursor:$sync_cursor, sync_run_id:$sync_run_id,
                recorded_at:$now, recorded_by:$recorded_by, reason:$reason
            })
            MERGE (d)-[:HAS_EVENT]->(e)
            WITH d, e
            OPTIONAL MATCH (d)-[:CURRENT_VERSION]->(:DocumentVersion)-[:HAS_CHUNK]->(c:Chunk)
            SET c.active=false
            WITH e, c
            OPTIONAL MATCH (c:Chunk)-[:EVIDENCE_FOR]->(a:Assertion)
            SET a.evidence_status='SOURCE_DELETED'
            RETURN e.id AS id
            """,
            source_id=source_identifier,
            connector_id=request.connector_id,
            document_id=document_identifier,
            event_id=event_id,
            expected_current_version_id=expected_current_version_id,
            source_version=request.source_version,
            deleted_at=request.deleted_at.isoformat() if request.deleted_at else None,
            sync_cursor=request.sync_cursor,
            sync_run_id=request.sync_run_id,
            recorded_by=request.recorded_by,
            reason=request.reason,
            now=now_iso(),
        ).single()
        return row.data() if row else None

    def commit_sync_checkpoint(self, checkpoint: SyncCheckpointCommit) -> dict:
        started = perf_counter()
        source_identifier = source_id(
            checkpoint.workspace_id,
            checkpoint.source_type,
            checkpoint.source_external_id,
        )
        event_id = stable_id(
            "event",
            source_identifier,
            "SOURCE_SYNC_COMPLETED",
            checkpoint.sync_run_id,
            checkpoint.cursor,
        )
        with self.driver.session(database=self.database) as session:
            source = session.run(
                """
                MATCH (s:Source {id:$id})
                RETURN s.last_sync_cursor AS cursor,
                       s.last_item_sync_run_id AS last_item_sync_run_id,
                       s.connector_id AS connector_id
                """,
                id=source_identifier,
            ).single()
            if not source:
                raise KeyError(source_identifier)
            if source["connector_id"] != checkpoint.connector_id:
                raise PermissionError("source is bound to a different connector")
            existing = session.run(
                "MATCH (e:Event {id:$id}) RETURN e.id AS id", id=event_id
            ).single()
            if existing:
                return {
                    "source_id": source_identifier,
                    "event_id": event_id,
                    "cursor": checkpoint.cursor,
                    "sync_run_id": checkpoint.sync_run_id,
                    "unchanged": True,
                }
            if (
                not checkpoint.allow_empty_run
                and source["last_item_sync_run_id"] != checkpoint.sync_run_id
            ):
                raise ValueError(
                    "checkpoint sync_run_id does not match the most recently ingested item"
                )
            if (
                checkpoint.expected_previous_cursor is not None
                and source["cursor"] != checkpoint.expected_previous_cursor
            ):
                raise ValueError(
                    "source cursor changed; checkpoint compare-and-set precondition failed"
                )
            committed = session.execute_write(
                self._write_sync_checkpoint,
                source_identifier,
                event_id,
                checkpoint,
            )
        if not committed:
            raise ValueError("source cursor changed before checkpoint commit")
        self.ops.audit(
            checkpoint.committed_by,
            "COMMIT_SYNC_CHECKPOINT",
            source_identifier,
            event_id=event_id,
            sync_run_id=checkpoint.sync_run_id,
            cursor=checkpoint.cursor,
            stats=checkpoint.stats,
        )
        self.ops.telemetry(
            "sync_checkpoint",
            "SUCCESS",
            started,
            source_id=source_identifier,
            sync_run_id=checkpoint.sync_run_id,
        )
        return {
            "source_id": source_identifier,
            "event_id": event_id,
            "cursor": checkpoint.cursor,
            "sync_run_id": checkpoint.sync_run_id,
            "unchanged": False,
        }

    @staticmethod
    def _write_sync_checkpoint(tx, source_identifier, event_id, checkpoint):
        return tx.run(
            """
            MATCH (s:Source {id:$source_id})
            WHERE s.connector_id=$connector_id
              AND (s.last_item_sync_run_id=$sync_run_id OR $allow_empty_run)
            WITH s
            WHERE $expected_previous_cursor IS NULL
               OR s.last_sync_cursor=$expected_previous_cursor
            SET s.last_sync_cursor=$cursor, s.last_sync_run_id=$sync_run_id,
                s.last_sync_completed_at=$completed_at,
                s.pending_sync_cursor=null
            CREATE (e:Event {
                id:$event_id, event_type:'SOURCE_SYNC_COMPLETED', status:'OBSERVED',
                sync_run_id:$sync_run_id, cursor:$cursor,
                observed_at:$completed_at, recorded_at:$now,
                recorded_by:$committed_by, stats_json:$stats_json,
                manifest_hash:$manifest_hash, manifest_version:$manifest_version
            })
            MERGE (s)-[:HAS_EVENT]->(e)
            RETURN e.id AS id
            """,
            source_id=source_identifier,
            connector_id=checkpoint.connector_id,
            event_id=event_id,
            sync_run_id=checkpoint.sync_run_id,
            cursor=checkpoint.cursor,
            expected_previous_cursor=checkpoint.expected_previous_cursor,
            allow_empty_run=checkpoint.allow_empty_run,
            completed_at=checkpoint.completed_at.isoformat(),
            committed_by=checkpoint.committed_by,
            stats_json=json.dumps(checkpoint.stats, sort_keys=True),
            manifest_hash=checkpoint.manifest_hash,
            manifest_version=checkpoint.manifest_version,
            now=now_iso(),
        ).single()

    def ingest_manifest(self, manifest: SyncManifest) -> dict:
        started = perf_counter()
        manifest_hash = stable_id(
            "sync-manifest", manifest.model_dump(mode="json", exclude={"manifest_version"})
        )
        source_identifier = source_id(
            manifest.workspace_id, manifest.source_type, manifest.source_external_id
        )
        checkpoint_event_id = stable_id(
            "event",
            source_identifier,
            "SOURCE_SYNC_COMPLETED",
            manifest.sync_run_id,
            manifest.cursor,
        )
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._write_manifest,
                manifest,
                source_identifier,
                checkpoint_event_id,
                manifest_hash,
                self.contract_versions["source"],
            )
        if not result["unchanged"]:
            for record in result["records"]:
                if record["operation"] == "TOMBSTONE" and not record["unchanged"]:
                    self.ops.audit(
                        manifest.connector_id,
                        "TOMBSTONE_DOCUMENT",
                        record["document_id"],
                        event_id=record["event_id"],
                        sync_run_id=manifest.sync_run_id,
                    )
            self.ops.audit(
                manifest.connector_id,
                "COMMIT_SYNC_MANIFEST",
                source_identifier,
                event_id=checkpoint_event_id,
                sync_run_id=manifest.sync_run_id,
                cursor=manifest.cursor,
                stats=result["stats"],
            )
        self.ops.telemetry(
            "sync_manifest",
            "UNCHANGED" if result["unchanged"] else "SUCCESS",
            started,
            source_id=source_identifier,
            sync_run_id=manifest.sync_run_id,
            records=len(result["records"]),
        )
        return result

    @classmethod
    def _write_manifest(
        cls,
        tx,
        manifest,
        source_identifier,
        checkpoint_event_id,
        manifest_hash,
        source_contract_version,
    ):
        timestamp = now_iso()
        source = tx.run(
            """
            MERGE (w:Workspace {id:$workspace_id})
            ON CREATE SET w.created_at=$now
            MERGE (s:Source {id:$source_id})
            ON CREATE SET s.type=$source_type, s.external_id=$source_external_id,
                s.uri=$source_uri, s.connector_id=$connector_id, s.created_at=$now,
                s.status='ACTIVE'
            SET s._manifest_lock=$sync_run_id,
                s.connector_id=coalesce(s.connector_id, $connector_id)
            MERGE (w)-[:OWNS_SOURCE]->(s)
            REMOVE s._manifest_lock
            RETURN s.connector_id AS connector_id, s.last_sync_cursor AS cursor
            """,
            workspace_id=manifest.workspace_id,
            source_id=source_identifier,
            source_type=manifest.source_type,
            source_external_id=manifest.source_external_id,
            source_uri=manifest.source_uri,
            connector_id=manifest.connector_id,
            sync_run_id=manifest.sync_run_id,
            now=timestamp,
        ).single()
        if source["connector_id"] != manifest.connector_id:
            raise PermissionError("source is bound to a different connector")
        completed = tx.run(
            """
            MATCH (:Source {id:$source_id})-[:HAS_EVENT]->
                  (e:Event {event_type:'SOURCE_SYNC_COMPLETED', sync_run_id:$sync_run_id})
            RETURN e.id AS id, e.cursor AS cursor, e.stats_json AS stats_json,
                   properties(e)['manifest_hash'] AS manifest_hash
            """,
            source_id=source_identifier,
            sync_run_id=manifest.sync_run_id,
        ).single()
        if completed:
            if completed["id"] != checkpoint_event_id or completed["cursor"] != manifest.cursor:
                raise ValueError("sync_run_id is already bound to a different cursor")
            if completed["manifest_hash"] not in (None, manifest_hash) and (
                cls._legacy_deletion_manifest_hash(tx, manifest, source_identifier)
                != completed["manifest_hash"]
            ):
                raise ValueError("sync_run_id is already bound to a different manifest payload")
            stats = json.loads(completed["stats_json"])
            return cls._manifest_result(
                manifest, source_identifier, checkpoint_event_id, [], stats, True
            )
        if source["cursor"] is not None and manifest.expected_previous_cursor is None:
            raise ValueError("manifest must provide expected_previous_cursor after initial sync")
        if source["cursor"] != manifest.expected_previous_cursor:
            raise ValueError("source cursor changed; manifest is stale")
        existing_active_documents = 0
        if not manifest.records and source["cursor"] is None:
            existing_active_documents = tx.run(
                """
                MATCH (:Source {id:$source_id})-[:HAS_DOCUMENT]->(d:Document {status:'ACTIVE'})
                RETURN count(d) AS count
                """,
                source_id=source_identifier,
            ).single()["count"]
        validate_initial_manifest_inventory(
            record_count=len(manifest.records),
            existing_active_documents=existing_active_documents,
            current_cursor=source["cursor"],
            expected_previous_cursor=manifest.expected_previous_cursor,
        )

        results: list[dict] = []
        changed = 0
        unchanged = 0
        tombstoned = 0
        for record in manifest.records:
            if record.operation == "UPSERT":
                request = TextIngestionRequest(
                    connector_id=manifest.connector_id,
                    workspace_id=manifest.workspace_id,
                    source_type=manifest.source_type,
                    source_external_id=manifest.source_external_id,
                    source_uri=manifest.source_uri,
                    document_source_uri=record.document_source_uri,
                    source_version=record.source_version,
                    source_updated_at=record.source_updated_at,
                    sync_cursor=manifest.cursor,
                    sync_run_id=manifest.sync_run_id,
                    document_external_id=record.document_external_id,
                    title=record.title,
                    content=record.content,
                    owner=record.owner,
                    visibility=record.visibility,
                    acl=record.acl,
                    parser_version=record.parser_version,
                    chunker_version=record.chunker_version,
                    chunk_size=record.chunk_size,
                )
                result = cls._write_manifest_upsert(
                    tx, request, source_identifier, source_contract_version
                )
                result["operation"] = "UPSERT"
                if result["unchanged"]:
                    unchanged += 1
                else:
                    changed += 1
            else:
                request = DocumentTombstoneRequest(
                    connector_id=manifest.connector_id,
                    workspace_id=manifest.workspace_id,
                    source_type=manifest.source_type,
                    source_external_id=manifest.source_external_id,
                    document_external_id=record.document_external_id,
                    source_version=record.source_version,
                    deleted_at=record.deleted_at,
                    sync_cursor=manifest.cursor,
                    sync_run_id=manifest.sync_run_id,
                    reason=record.reason,
                    recorded_by=manifest.connector_id,
                )
                result = cls._write_manifest_tombstone(tx, request, source_identifier)
                result["operation"] = "TOMBSTONE"
                if result["unchanged"]:
                    unchanged += 1
                else:
                    tombstoned += 1
            results.append(result)
        stats = {
            "items_seen": len(manifest.records),
            "items_changed": changed,
            "items_unchanged": unchanged,
            "items_tombstoned": tombstoned,
        }
        checkpoint_request = SyncCheckpointCommit(
            connector_id=manifest.connector_id,
            workspace_id=manifest.workspace_id,
            source_type=manifest.source_type,
            source_external_id=manifest.source_external_id,
            sync_run_id=manifest.sync_run_id,
            cursor=manifest.cursor,
            expected_previous_cursor=manifest.expected_previous_cursor,
            allow_empty_run=not manifest.records,
            committed_by=manifest.connector_id,
            stats=stats,
            manifest_hash=manifest_hash,
            manifest_version=manifest.manifest_version,
        )
        checkpoint = cls._write_sync_checkpoint(
            tx, source_identifier, checkpoint_event_id, checkpoint_request
        )
        if not checkpoint:
            raise ValueError("source cursor changed before atomic manifest commit")
        return cls._manifest_result(
            manifest, source_identifier, checkpoint_event_id, results, stats, False
        )

    @classmethod
    def _write_manifest_upsert(cls, tx, request, source_identifier, source_contract_version):
        document_identifier = document_id(source_identifier, request.document_external_id)
        digest = content_hash(request.content)
        fingerprint = processing_fingerprint(
            digest,
            request.parser_version,
            request.chunker_version,
            request.chunk_size,
            request.source_version,
            request.source_updated_at.isoformat() if request.source_updated_at else None,
            {"owner": request.owner, "visibility": request.visibility, "acl": request.acl},
        )
        version_id = stable_id("document-version", document_identifier, fingerprint)
        metadata_hash = source_metadata_fingerprint(
            request.title, request.document_source_uri or request.source_uri
        )
        existing = tx.run(
            """
            MATCH (d:Document {id:$id})-[:CURRENT_VERSION]->(v)
            RETURN d.status AS status, v.id AS id,
                   v.processing_fingerprint AS fingerprint,
                   d.title AS title, v.source_uri AS source_uri,
                   v.source_metadata_hash AS source_metadata_hash
            """,
            id=document_identifier,
        ).single()
        if existing and existing["status"] == "ACTIVE" and existing["fingerprint"] == fingerprint:
            existing_metadata_hash = existing["source_metadata_hash"] or (
                source_metadata_fingerprint(existing["title"], existing["source_uri"])
            )
            if existing_metadata_hash != metadata_hash:
                raise ValueError("source revision is already bound to different document metadata")
            tx.run(
                """
                MATCH (s:Source {id:$source_id})
                SET s.last_seen=$now, s.pending_sync_cursor=$sync_cursor,
                    s.last_item_sync_run_id=$sync_run_id, s.status='ACTIVE'
                """,
                source_id=source_identifier,
                sync_cursor=request.sync_cursor,
                sync_run_id=request.sync_run_id,
                now=now_iso(),
            ).consume()
            return IngestionResult(
                source_id=source_identifier,
                document_id=document_identifier,
                document_version_id=version_id,
                content_hash=digest,
                processing_fingerprint=fingerprint,
                chunks_created=0,
                unchanged=True,
            ).model_dump(mode="json")
        historical = tx.run(
            """
            MATCH (:Document {id:$document_id})-[:HAS_VERSION]->
                  (v:DocumentVersion {id:$version_id})
            RETURN v.id AS id
            """,
            document_id=document_identifier,
            version_id=version_id,
        ).single()
        if historical:
            raise ValueError(
                "document returned to a previously observed state without a distinct "
                "source_version or source_updated_at"
            )
        chunks = split_text(request.content, request.chunk_size)
        cls._write_version(
            tx,
            request,
            source_identifier,
            document_identifier,
            version_id,
            digest,
            fingerprint,
            chunks,
            existing["id"] if existing else None,
            True,
            metadata_hash,
            source_contract_version,
        )
        return IngestionResult(
            source_id=source_identifier,
            document_id=document_identifier,
            document_version_id=version_id,
            content_hash=digest,
            processing_fingerprint=fingerprint,
            chunks_created=len(chunks),
            unchanged=False,
        ).model_dump(mode="json")

    @staticmethod
    def _legacy_deletion_manifest_hash(tx, manifest, source_identifier):
        """Verify an old payload exactly using its persisted pre-F2 observation times.

        Read-only compatibility: never ignore a hash field or rewrite an old ledger.
        Only unknown deletion times may be reconstructed; explicit times remain bound.
        """
        payload = manifest.model_dump(mode="json", exclude={"manifest_version"})
        restored = False
        for record in payload["records"]:
            if record["operation"] != "TOMBSTONE" or record["deleted_at"] is not None:
                continue
            document_identifier = document_id(source_identifier, record["document_external_id"])
            event_id = stable_id(
                "event", document_identifier, "SOURCE_DOCUMENT_DELETED", record["source_version"]
            )
            event = tx.run(
                "MATCH (:Source {id:$source})-[:HAS_DOCUMENT]->(:Document {id:$document})"
                "-[:HAS_EVENT]->(e:Event {id:$event, event_type:'SOURCE_DOCUMENT_DELETED'}) "
                "RETURN properties(e)['observed_at'] AS observed_at",
                source=source_identifier,
                document=document_identifier,
                event=event_id,
            ).single()
            if event is None or event["observed_at"] is None:
                return None
            record["deleted_at"] = event["observed_at"]
            restored = True
        if not restored:
            return None
        # Canonicalize exactly as the original manifest serialization did (UTC/Z).
        canonical = SyncManifest.model_validate(payload).model_dump(
            mode="json", exclude={"manifest_version"}
        )
        return stable_id("sync-manifest", canonical)

    @classmethod
    def _write_manifest_tombstone(cls, tx, request, source_identifier):
        document_identifier = document_id(source_identifier, request.document_external_id)
        # A later snapshot may delete the same content revision after reactivation.
        # Scope the transition to its stable sync, never to a local clock instant.
        event_id = stable_id(
            "event",
            document_identifier,
            "SOURCE_DOCUMENT_DELETED",
            request.source_version,
            request.sync_run_id,
        )
        existing = tx.run(
            "MATCH (e:Event {id:$event_id}) RETURN e.id AS id", event_id=event_id
        ).single()
        if existing:
            tx.run(
                """
                MATCH (s:Source {id:$source_id})
                SET s.last_seen=$now, s.pending_sync_cursor=$sync_cursor,
                    s.last_item_sync_run_id=$sync_run_id
                """,
                source_id=source_identifier,
                sync_cursor=request.sync_cursor,
                sync_run_id=request.sync_run_id,
                now=now_iso(),
            ).consume()
            return {
                "source_id": source_identifier,
                "document_id": document_identifier,
                "event_id": event_id,
                "status": "DELETED",
                "unchanged": True,
            }
        current = tx.run(
            """
            MATCH (:Source {id:$source_id})-[:HAS_DOCUMENT]->(d:Document {id:$document_id})
                  -[:CURRENT_VERSION]->(v:DocumentVersion)
            WHERE d.status='ACTIVE'
            RETURN v.id AS id
            """,
            source_id=source_identifier,
            document_id=document_identifier,
        ).single()
        if not current:
            raise KeyError(document_identifier)
        row = cls._write_tombstone(
            tx,
            request,
            source_identifier,
            document_identifier,
            event_id,
            current["id"],
        )
        if not row:
            raise KeyError(document_identifier)
        return {
            "source_id": source_identifier,
            "document_id": document_identifier,
            "event_id": event_id,
            "status": "DELETED",
            "unchanged": False,
        }

    @staticmethod
    def _manifest_result(
        manifest, source_identifier, checkpoint_event_id, records, stats, unchanged
    ):
        return {
            "manifest_version": manifest.manifest_version,
            "sync_run_id": manifest.sync_run_id,
            "cursor": manifest.cursor,
            "records": records,
            "checkpoint": {
                "source_id": source_identifier,
                "event_id": checkpoint_event_id,
                "cursor": manifest.cursor,
                "sync_run_id": manifest.sync_run_id,
                "unchanged": unchanged,
            },
            "stats": stats,
            "unchanged": unchanged,
        }

    def create_proposal(self, proposal: ProposalCreate) -> dict:
        if proposal.workspace_id != proposal.access.workspace_id:
            raise PermissionError("proposal workspace must match its authenticated access context")
        if proposal.created_by not in proposal.access.principals:
            raise PermissionError("created_by must be one of the authenticated principals")
        payload = proposal.model_dump(mode="json", exclude={"access"})
        proposal_id, payload_hash, _ = proposal_identity(
            "ASSERTION", proposal.workspace_id, payload
        )
        created_at = now_iso()
        evidence_ids = sorted({change.evidence_chunk_id for change in proposal.changes})
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._persist_proposal,
                proposal.workspace_id,
                evidence_ids,
                {
                    "id": proposal_id,
                    "status": "PROPOSED",
                    "proposal_type": "ASSERTION",
                    "changes_json": json.dumps(payload["changes"], ensure_ascii=False),
                    "created_by": proposal.created_by,
                    "reason": proposal.reason,
                    "ontology_version": proposal.ontology_version,
                    "evidence_linkage_version": "1",
                    "workspace_id": proposal.workspace_id,
                    "created_at": created_at,
                    "payload_hash": payload_hash,
                    "contract_version": self.contract_versions["governance"],
                    "created_access_fingerprint": access_fingerprint(
                        proposal.access.workspace_id, proposal.access.principals
                    ),
                    "created_principal_count": len(proposal.access.principals),
                    "_creation_marker": stable_id("proposal-creation", proposal_id, created_at),
                },
                "ASSERTION",
                [
                    change.supersedes_assertion_id
                    for change in proposal.changes
                    if change.supersedes_assertion_id
                ],
                proposal.access.principals,
            )
        if result["created"]:
            self.ops.audit(
                proposal.created_by, "CREATE_PROPOSAL", proposal_id, payload_hash=payload_hash
            )
        return {
            "id": proposal_id,
            "status": result["status"],
            "unchanged": not result["created"],
        }

    def create_decision_proposal(self, proposal: DecisionProposalCreate) -> dict:
        if proposal.workspace_id != proposal.access.workspace_id:
            raise PermissionError("proposal workspace must match its authenticated access context")
        if proposal.proposed_by not in proposal.access.principals:
            raise PermissionError("proposed_by must be one of the authenticated principals")
        payload = proposal.model_dump(mode="json", exclude={"access"})
        proposal_id, payload_hash, payload_json = proposal_identity(
            "DECISION", proposal.workspace_id, payload
        )
        created_at = now_iso()
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._persist_proposal,
                proposal.workspace_id,
                proposal.evidence_chunk_ids,
                {
                    "id": proposal_id,
                    "proposal_type": "DECISION",
                    "status": "PROPOSED",
                    "payload_json": payload_json,
                    "created_by": proposal.proposed_by,
                    "reason": proposal.reason,
                    "ontology_version": proposal.ontology_version,
                    "evidence_linkage_version": "1",
                    "workspace_id": proposal.workspace_id,
                    "created_at": created_at,
                    "payload_hash": payload_hash,
                    "contract_version": self.contract_versions["governance"],
                    "created_access_fingerprint": access_fingerprint(
                        proposal.access.workspace_id, proposal.access.principals
                    ),
                    "created_principal_count": len(proposal.access.principals),
                    "_creation_marker": stable_id("proposal-creation", proposal_id, created_at),
                },
                "DECISION",
                [proposal.supersedes_decision_id] if proposal.supersedes_decision_id else [],
                proposal.access.principals,
            )
        if result["created"]:
            self.ops.audit(
                proposal.proposed_by,
                "CREATE_DECISION_PROPOSAL",
                proposal_id,
                payload_hash=payload_hash,
            )
        return {
            "id": proposal_id,
            "proposal_type": "DECISION",
            "status": result["status"],
            "unchanged": not result["created"],
        }

    def create_event_proposal(self, proposal: EventProposalCreate) -> dict:
        if proposal.workspace_id != proposal.access.workspace_id:
            raise PermissionError("proposal workspace must match its authenticated access context")
        if proposal.proposed_by not in proposal.access.principals:
            raise PermissionError("proposed_by must be one of the authenticated principals")
        payload = proposal.model_dump(mode="json", exclude={"access"})
        proposal_id, payload_hash, payload_json = proposal_identity(
            "EVENT", proposal.workspace_id, payload
        )
        created_at = now_iso()
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._persist_proposal,
                proposal.workspace_id,
                proposal.evidence_chunk_ids,
                {
                    "id": proposal_id,
                    "proposal_type": "EVENT",
                    "status": "PROPOSED",
                    "payload_json": payload_json,
                    "created_by": proposal.proposed_by,
                    "reason": proposal.reason,
                    "ontology_version": proposal.ontology_version,
                    "evidence_linkage_version": "1",
                    "workspace_id": proposal.workspace_id,
                    "created_at": created_at,
                    "payload_hash": payload_hash,
                    "contract_version": self.contract_versions["governance"],
                    "created_access_fingerprint": access_fingerprint(
                        proposal.access.workspace_id, proposal.access.principals
                    ),
                    "created_principal_count": len(proposal.access.principals),
                    "_creation_marker": stable_id("proposal-creation", proposal_id, created_at),
                },
                "EVENT",
                [proposal.supersedes_event_id] if proposal.supersedes_event_id else [],
                proposal.access.principals,
            )
        if result["created"]:
            self.ops.audit(
                proposal.proposed_by,
                "CREATE_EVENT_PROPOSAL",
                proposal_id,
                payload_hash=payload_hash,
            )
        return {
            "id": proposal_id,
            "proposal_type": "EVENT",
            "status": result["status"],
            "unchanged": not result["created"],
        }

    @staticmethod
    def _persist_proposal(
        tx,
        workspace_id,
        evidence_ids,
        properties,
        supersession_kind,
        supersession_ids,
        principals,
    ):
        claimed = tx.run(
            """
            MATCH (w:Workspace {id:$workspace_id})
            MERGE (p:Proposal {id:$proposal_id})
            ON CREATE SET p._creation_marker=$creation_marker
            RETURN p._creation_marker=$creation_marker AS created,
                   p.payload_hash AS payload_hash, p.status AS status
            """,
            workspace_id=workspace_id,
            proposal_id=properties["id"],
            creation_marker=properties["_creation_marker"],
        ).single()
        if not claimed:
            raise ValueError("proposal workspace does not exist")
        if claimed["payload_hash"] not in (None, properties["payload_hash"]):
            raise ValueError("proposal identity is already bound to a different payload")
        missing = tx.run(
            """
            UNWIND $evidence_ids AS evidence_id
            OPTIONAL MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                -[:HAS_DOCUMENT]->(:Document)-[:HAS_VERSION]->(:DocumentVersion)
                -[:HAS_CHUNK]->(c:Chunk {id:evidence_id})
            WITH evidence_id, c WHERE c IS NULL
            RETURN collect(evidence_id) AS ids
            """,
            evidence_ids=evidence_ids,
            workspace_id=workspace_id,
        ).single()["ids"]
        if missing:
            raise ValueError("evidence chunks not found: " + ", ".join(missing))
        inaccessible = tx.run(
            """
            UNWIND $evidence_ids AS evidence_id
            MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                -[:HAS_DOCUMENT]->(d:Document)-[:HAS_VERSION]->(:DocumentVersion)
                -[:HAS_CHUNK]->(c:Chunk {id:evidence_id})
            OPTIONAL MATCH (d)-[:CURRENT_VERSION]->(auth:DocumentVersion)
            WHERE d.status='ACTIVE' AND (
                auth.visibility='PUBLIC' OR auth.owner IN $principals OR
                any(principal IN coalesce(auth.acl, []) WHERE principal IN $principals)
            )
            WITH evidence_id, auth WHERE auth IS NULL
            RETURN collect(evidence_id) AS ids
            """,
            evidence_ids=evidence_ids,
            workspace_id=workspace_id,
            principals=principals,
        ).single()["ids"]
        if inaccessible:
            raise PermissionError(
                "proposal evidence is not active and accessible: " + ", ".join(inaccessible)
            )
        if not claimed["created"]:
            return {"created": False, "status": claimed["status"]}
        if len(supersession_ids) != len(set(supersession_ids)):
            raise ValueError("a canonical record can be superseded only once per proposal")
        unavailable = tx.run(
            """
            UNWIND $ids AS id
            OPTIONAL MATCH (w:Workspace {id:$workspace_id})-[ownership]->(old {id:id})
            WHERE old.workspace_id=$workspace_id AND old.status='VERIFIED'
              AND (($kind='ASSERTION' AND old:Assertion AND type(ownership)='HAS_ASSERTION')
                OR ($kind='DECISION' AND old:Decision AND type(ownership)='HAS_DECISION')
                OR ($kind='EVENT' AND old:Event AND old.event_class='SEMANTIC'
                    AND type(ownership)='HAS_EVENT'))
              AND NOT EXISTS { ()-[:SUPERSEDES]->(old) }
            WITH id, old WHERE old IS NULL
            RETURN collect(id) AS ids
            """,
            ids=supersession_ids,
            kind=supersession_kind,
            workspace_id=workspace_id,
        ).single()["ids"]
        if unavailable:
            raise ValueError(
                "supersession targets are not current in this workspace: " + ", ".join(unavailable)
            )
        tx.run(
            """
            MATCH (w:Workspace {id:$workspace_id})
            MATCH (p:Proposal {id:$proposal_id})
            SET p = $properties
            REMOVE p._creation_marker
            MERGE (w)-[:HAS_PROPOSAL]->(p)
            WITH p
            UNWIND $evidence_ids AS evidence_id
            MATCH (c:Chunk {id:evidence_id})
            MERGE (p)-[:SUPPORTED_BY]->(c)
            """,
            workspace_id=workspace_id,
            proposal_id=properties["id"],
            evidence_ids=evidence_ids,
            properties=properties,
        ).consume()
        return {"created": True, "status": "PROPOSED"}

    def approve_proposal(
        self,
        proposal_id: str,
        reviewer: str,
        reason: str | None,
        ontology: Ontology,
        access: AccessContext,
    ) -> dict:
        if reviewer not in access.principals:
            raise PermissionError("reviewed_by must be one of the authenticated principals")
        with self.driver.session(database=self.database) as session:
            record = session.run(
                """
                MATCH (p:Proposal {id:$id})
                RETURN p.status AS status, p.changes_json AS changes,
                       p.payload_json AS payload,
                       coalesce(p.proposal_type, 'ASSERTION') AS proposal_type,
                       p.ontology_version AS ontology_version,
                       p.workspace_id AS workspace_id
                """,
                id=proposal_id,
            ).single()
            if not record:
                raise KeyError(proposal_id)
            if (
                record["workspace_id"] != access.workspace_id
                or self.proposal(proposal_id, access) is None
            ):
                raise PermissionError("proposal evidence is not accessible to this reviewer")
            if record["status"] != "PROPOSED":
                raise ValueError(f"proposal is {record['status']}")
            if record["ontology_version"] != ontology.version:
                raise ValueError(
                    "proposal ontology version "
                    f"{record['ontology_version']} does not match active version {ontology.version}"
                )
            if record["proposal_type"] == "DECISION":
                proposal = DecisionProposalCreate.model_validate_json(record["payload"])
                decision_trace_id, promoted_id = session.execute_write(
                    self._approve_decision,
                    proposal_id,
                    proposal,
                    reviewer,
                    reason,
                    ontology.version,
                    record["workspace_id"],
                    access.principals,
                )
            elif record["proposal_type"] == "EVENT":
                proposal = EventProposalCreate.model_validate_json(record["payload"])
                decision_trace_id, promoted_id = session.execute_write(
                    self._approve_event,
                    proposal_id,
                    proposal,
                    reviewer,
                    reason,
                    ontology.version,
                    record["workspace_id"],
                    access.principals,
                )
            else:
                proposal = ProposalCreate(
                    changes=json.loads(record["changes"]),
                    workspace_id=record["workspace_id"],
                )
                for change in proposal.changes:
                    ontology.validate(change)
                decision_trace_id = session.execute_write(
                    self._approve,
                    proposal_id,
                    proposal,
                    reviewer,
                    reason,
                    ontology.version,
                    record["workspace_id"],
                    access.principals,
                )
                promoted_id = None
        self.ops.audit(reviewer, "APPROVE_PROPOSAL", proposal_id, reason=reason)
        return {
            "id": proposal_id,
            "status": "APPROVED",
            "decision_trace_id": decision_trace_id,
            "promoted_id": promoted_id,
        }

    @staticmethod
    def _require_approvable_evidence(tx, proposal_id, workspace_id, evidence_ids, principals):
        expected_ids = sorted(set(evidence_ids))
        linked = tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_PROPOSAL]->
                  (p:Proposal {id:$proposal_id})
            OPTIONAL MATCH (p)-[:SUPPORTED_BY]->(c:Chunk)
            RETURN collect(DISTINCT c.id) AS ids
            """,
            proposal_id=proposal_id,
            workspace_id=workspace_id,
        ).single()
        linked_ids = sorted(identifier for identifier in linked["ids"] if identifier)
        if linked_ids != expected_ids:
            raise ValueError("proposal evidence lineage does not match its payload")
        tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                  -[:HAS_DOCUMENT]->(d:Document)-[:HAS_VERSION]->(:DocumentVersion)
                  -[:HAS_CHUNK]->(c:Chunk)
            WHERE c.id IN $evidence_ids
            WITH DISTINCT d ORDER BY d.id
            SET d.governance_read_revision=coalesce(d.governance_read_revision, 0) + 1
            """,
            evidence_ids=expected_ids,
            workspace_id=workspace_id,
        ).consume()
        inaccessible = tx.run(
            """
            UNWIND $evidence_ids AS evidence_id
            OPTIONAL MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                -[:HAS_DOCUMENT]->(d:Document)-[:HAS_VERSION]->(:DocumentVersion)
                -[:HAS_CHUNK]->(c:Chunk {id:evidence_id})
            OPTIONAL MATCH (d)-[:CURRENT_VERSION]->(auth:DocumentVersion)
            WHERE d.status='ACTIVE' AND (
                auth.visibility='PUBLIC' OR auth.owner IN $principals OR
                any(principal IN coalesce(auth.acl, []) WHERE principal IN $principals)
            )
            WITH evidence_id, c, auth WHERE c IS NULL OR auth IS NULL
            RETURN collect(evidence_id) AS ids
            """,
            evidence_ids=expected_ids,
            principals=principals,
            workspace_id=workspace_id,
        ).single()["ids"]
        if inaccessible:
            raise PermissionError(
                "proposal evidence is no longer active and accessible: " + ", ".join(inaccessible)
            )

    @staticmethod
    def _approve_decision(
        tx,
        proposal_id,
        proposal,
        reviewer,
        reason,
        ontology_version,
        workspace_id,
        principals,
    ):
        now = now_iso()
        approval_id = stable_id("approval", proposal_id, reviewer, now)
        decision_id = stable_id("decision", workspace_id, proposal_id)
        GraphStore._require_approvable_evidence(
            tx, proposal_id, workspace_id, proposal.evidence_chunk_ids, principals
        )
        if proposal.supersedes_decision_id:
            previous = tx.run(
                """
                MATCH (:Workspace {id:$workspace_id})-[:HAS_DECISION]->
                      (d:Decision {id:$id, workspace_id:$workspace_id})
                WHERE d.status='VERIFIED'
                  AND NOT EXISTS { (:Decision)-[:SUPERSEDES]->(d) }
                RETURN d.id AS id
                """,
                id=proposal.supersedes_decision_id,
                workspace_id=workspace_id,
            ).single()
            if not previous:
                raise ValueError(
                    f"superseded decision not found: {proposal.supersedes_decision_id}"
                )
        claimed = tx.run(
            """
            MATCH (w:Workspace {id:$workspace_id})-[:HAS_PROPOSAL]->(p:Proposal {id:$proposal_id})
            SET p.governance_revision=coalesce(p.governance_revision, 0) + 1
            WITH w, p
            WHERE p.status='PROPOSED' AND p.proposal_type='DECISION'
            SET p.status='APPROVED', p.reviewed_at=$now, p.reviewed_by=$reviewer
            CREATE (a:Approval {
                id:$approval_id, decision:'APPROVED', scope:'DECISION',
                reason:$reason, reviewed_by:$reviewer, reviewed_at:$now
            })
            CREATE (d:Decision {
                id:$decision_id, title:$title, statement:$statement,
                decided_at:$decided_at, decided_on:$decided_on,
                decided_at_precision:$decided_at_precision,
                valid_from:$valid_from, valid_to:$valid_to,
                participants:$participants, status:'VERIFIED', recorded_at:$now,
                ontology_version:$ontology_version, workspace_id:$workspace_id
            })
            MERGE (p)-[:HAS_APPROVAL]->(a)
            MERGE (p)-[:PROMOTED]->(d)
            MERGE (w)-[:HAS_DECISION]->(d)
            RETURN d.id AS id
            """,
            proposal_id=proposal_id,
            workspace_id=workspace_id,
            approval_id=approval_id,
            decision_id=decision_id,
            reviewer=reviewer,
            reason=reason,
            title=proposal.title,
            statement=proposal.statement,
            decided_at=proposal.decided_at.isoformat(),
            decided_on=proposal.decided_on.isoformat() if proposal.decided_on else None,
            decided_at_precision=proposal.decided_at_precision,
            valid_from=proposal.valid_from.isoformat() if proposal.valid_from else None,
            valid_to=proposal.valid_to.isoformat() if proposal.valid_to else None,
            participants=proposal.participants,
            ontology_version=ontology_version,
            now=now,
        ).single()
        if not claimed:
            raise ValueError("proposal is no longer pending")
        tx.run(
            """
            MATCH (d:Decision {id:$decision_id})
            UNWIND $chunk_ids AS chunk_id
            MATCH (c:Chunk {id:chunk_id})
            MERGE (c)-[:EVIDENCE_FOR]->(d)
            """,
            decision_id=decision_id,
            chunk_ids=proposal.evidence_chunk_ids,
        ).consume()
        if proposal.supersedes_decision_id:
            superseded = tx.run(
                """
                MATCH (d:Decision {id:$decision_id, workspace_id:$workspace_id}),
                      (:Workspace {id:$workspace_id})-[:HAS_DECISION]->
                      (old:Decision {id:$old_id, workspace_id:$workspace_id})
                SET old.governance_revision=coalesce(old.governance_revision, 0) + 1
                WITH d, old
                WHERE old.status='VERIFIED'
                  AND NOT EXISTS { (:Decision)-[:SUPERSEDES]->(old) }
                SET old.status='SUPERSEDED',
                    old.valid_to=coalesce(old.valid_to,$new_valid_from,$now)
                MERGE (d)-[:SUPERSEDES]->(old)
                RETURN old.id AS id
                """,
                decision_id=decision_id,
                old_id=proposal.supersedes_decision_id,
                workspace_id=workspace_id,
                new_valid_from=(proposal.valid_from.isoformat() if proposal.valid_from else None),
                now=now,
            ).single()
            if not superseded:
                raise ValueError("superseded decision is no longer current")
        return approval_id, decision_id

    @staticmethod
    def _approve_event(
        tx,
        proposal_id,
        proposal,
        reviewer,
        reason,
        ontology_version,
        workspace_id,
        principals,
    ):
        now = now_iso()
        approval_id = stable_id("approval", proposal_id, reviewer, now)
        event_id = stable_id("event", "SEMANTIC", workspace_id, proposal_id)
        GraphStore._require_approvable_evidence(
            tx, proposal_id, workspace_id, proposal.evidence_chunk_ids, principals
        )
        if proposal.supersedes_event_id:
            previous = tx.run(
                """
                MATCH (:Workspace {id:$workspace_id})-[:HAS_EVENT]->(e:Event {
                    id:$id, workspace_id:$workspace_id, event_class:'SEMANTIC'})
                WHERE e.status='VERIFIED'
                  AND NOT EXISTS { (:Event)-[:SUPERSEDES]->(e) }
                RETURN e.id AS id
                """,
                id=proposal.supersedes_event_id,
                workspace_id=workspace_id,
            ).single()
            if not previous:
                raise ValueError(f"superseded event not found: {proposal.supersedes_event_id}")
        claimed = tx.run(
            """
            MATCH (w:Workspace {id:$workspace_id})-[:HAS_PROPOSAL]->
                  (p:Proposal {id:$proposal_id})
            SET p.governance_revision=coalesce(p.governance_revision, 0) + 1
            WITH w, p
            WHERE p.status='PROPOSED' AND p.proposal_type='EVENT'
            SET p.status='APPROVED', p.reviewed_at=$now, p.reviewed_by=$reviewer
            CREATE (a:Approval {
                id:$approval_id, decision:'APPROVED', scope:'EVENT',
                reason:$reason, reviewed_by:$reviewer, reviewed_at:$now
            })
            CREATE (e:Event {
                id:$event_id, event_class:'SEMANTIC', event_type:$event_type,
                title:$title, description:$description, occurred_at:$occurred_at,
                ended_at:$ended_at, participants:$participants, status:'VERIFIED',
                recorded_at:$now, ontology_version:$ontology_version,
                workspace_id:$workspace_id
            })
            MERGE (p)-[:HAS_APPROVAL]->(a)
            MERGE (p)-[:PROMOTED]->(e)
            MERGE (w)-[:HAS_EVENT]->(e)
            RETURN e.id AS id
            """,
            proposal_id=proposal_id,
            workspace_id=workspace_id,
            approval_id=approval_id,
            event_id=event_id,
            reviewer=reviewer,
            reason=reason,
            event_type=proposal.event_type,
            title=proposal.title,
            description=proposal.description,
            occurred_at=proposal.occurred_at.isoformat(),
            ended_at=proposal.ended_at.isoformat() if proposal.ended_at else None,
            participants=proposal.participants,
            ontology_version=ontology_version,
            now=now,
        ).single()
        if not claimed:
            raise ValueError("proposal is no longer pending")
        tx.run(
            """
            MATCH (e:Event {id:$event_id, event_class:'SEMANTIC'})
            UNWIND $chunk_ids AS chunk_id
            MATCH (c:Chunk {id:chunk_id})
            MERGE (c)-[:EVIDENCE_FOR]->(e)
            """,
            event_id=event_id,
            chunk_ids=proposal.evidence_chunk_ids,
        ).consume()
        if proposal.supersedes_event_id:
            superseded = tx.run(
                """
                MATCH (e:Event {
                        id:$event_id, workspace_id:$workspace_id, event_class:'SEMANTIC'
                      }),
                      (:Workspace {id:$workspace_id})-[:HAS_EVENT]->(old:Event {
                        id:$old_id, workspace_id:$workspace_id, event_class:'SEMANTIC'
                      })
                SET old.governance_revision=coalesce(old.governance_revision, 0) + 1
                WITH e, old
                WHERE old.status='VERIFIED'
                  AND NOT EXISTS { (:Event)-[:SUPERSEDES]->(old) }
                SET old.status='SUPERSEDED', old.ended_at=coalesce(old.ended_at,$occurred_at)
                MERGE (e)-[:SUPERSEDES]->(old)
                RETURN old.id AS id
                """,
                event_id=event_id,
                old_id=proposal.supersedes_event_id,
                workspace_id=workspace_id,
                occurred_at=proposal.occurred_at.isoformat(),
            ).single()
            if not superseded:
                raise ValueError("superseded event is no longer current")
        return approval_id, event_id

    @staticmethod
    def _approve(
        tx,
        proposal_id,
        proposal,
        reviewer,
        reason,
        ontology_version,
        workspace_id,
        principals,
    ):
        now = now_iso()
        approval_id = stable_id("approval", proposal_id, reviewer, now)
        evidence_ids = sorted({change.evidence_chunk_id for change in proposal.changes})
        GraphStore._require_approvable_evidence(
            tx, proposal_id, workspace_id, evidence_ids, principals
        )
        for change in proposal.changes:
            if not change.supersedes_assertion_id:
                continue
            expected_subject_id = stable_id(
                "entity",
                workspace_id,
                change.subject.entity_type,
                change.subject.name.casefold(),
            )
            previous = tx.run(
                """
                MATCH (:Workspace {id:$workspace_id})-[:HAS_ASSERTION]->
                      (old:Assertion {id:$old_id, workspace_id:$workspace_id})
                      -[:SUBJECT]->(subject:Entity)
                WHERE old.status='VERIFIED'
                  AND NOT EXISTS { (:Assertion)-[:SUPERSEDES]->(old) }
                RETURN old.predicate AS predicate, subject.id AS subject_id
                """,
                workspace_id=workspace_id,
                old_id=change.supersedes_assertion_id,
            ).single()
            if not previous:
                raise ValueError(
                    f"superseded assertion is not current: {change.supersedes_assertion_id}"
                )
            if (
                previous["predicate"] != change.predicate
                or previous["subject_id"] != expected_subject_id
            ):
                raise ValueError("a superseding assertion must preserve subject and predicate")
        claimed = tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_PROPOSAL]->(p:Proposal {id:$proposal_id})
            SET p.governance_revision=coalesce(p.governance_revision, 0) + 1
            WITH p
            WHERE p.status='PROPOSED'
            SET p.status='APPROVED', p.reviewed_at=$now, p.reviewed_by=$reviewer
            CREATE (a:Approval {id:$approval_id, decision:'APPROVED', reason:$reason,
                reviewed_by:$reviewer, reviewed_at:$now})
            MERGE (p)-[:HAS_APPROVAL]->(a)
            RETURN p.id AS id
            """,
            proposal_id=proposal_id,
            workspace_id=workspace_id,
            approval_id=approval_id,
            reviewer=reviewer,
            reason=reason,
            now=now,
        ).single()
        if not claimed:
            raise ValueError("proposal is no longer pending")
        for index, change in enumerate(proposal.changes):
            subject_id = stable_id(
                "entity",
                workspace_id,
                change.subject.entity_type,
                change.subject.name.casefold(),
            )
            object_id = None
            if change.object:
                object_id = stable_id(
                    "entity",
                    workspace_id,
                    change.object.entity_type,
                    change.object.name.casefold(),
                )
            assertion_id = stable_id("assertion", proposal_id, index)
            tx.run(
                """
                MATCH (w:Workspace {id:$workspace_id})-[:HAS_PROPOSAL]->(p:Proposal {id:$proposal_id}),
                      (c:Chunk {id:$chunk_id})
                MERGE (s:Entity {id:$subject_id})
                ON CREATE SET s.created_at=$now
                SET s.name=$subject_name, s.entity_type=$subject_type,
                    s.aliases=$subject_aliases, s.updated_at=$now, s.status='VERIFIED',
                    s.workspace_id=$workspace_id
                MERGE (a:Assertion {id:$assertion_id})
                SET a.predicate=$predicate, a.value=$value, a.confidence=$confidence,
                    a.status='VERIFIED', a.observed_at=$observed_at, a.valid_from=$valid_from,
                    a.valid_to=$valid_to, a.recorded_at=$now, a.extractor_version=$extractor_version,
                    a.ontology_version=$ontology_version
                SET a.workspace_id=$workspace_id
                MERGE (c)-[:EVIDENCE_FOR]->(a)
                MERGE (a)-[:SUBJECT]->(s)
                MERGE (p)-[:PROMOTED]->(a)
                MERGE (w)-[:HAS_ENTITY]->(s)
                MERGE (w)-[:HAS_ASSERTION]->(a)
                """,
                proposal_id=proposal_id,
                workspace_id=workspace_id,
                chunk_id=change.evidence_chunk_id,
                subject_id=subject_id,
                subject_name=change.subject.name,
                subject_type=change.subject.entity_type,
                subject_aliases=change.subject.aliases,
                assertion_id=assertion_id,
                predicate=change.predicate,
                value=change.value,
                confidence=change.confidence,
                observed_at=(change.observed_at.isoformat() if change.observed_at else None),
                valid_from=(change.valid_from.isoformat() if change.valid_from else None),
                valid_to=(change.valid_to.isoformat() if change.valid_to else None),
                extractor_version=change.extractor_version,
                ontology_version=ontology_version,
                now=now,
            ).consume()
            if change.object:
                tx.run(
                    """
                    MATCH (w:Workspace {id:$workspace_id}),
                          (a:Assertion {id:$assertion_id}), (s:Entity {id:$subject_id})
                    MERGE (o:Entity {id:$object_id})
                    ON CREATE SET o.created_at=$now
                    SET o.name=$object_name, o.entity_type=$object_type,
                        o.aliases=$object_aliases, o.updated_at=$now, o.status='VERIFIED',
                        o.workspace_id=$workspace_id
                    MERGE (a)-[:OBJECT]->(o)
                    MERGE (s)-[:RELATED {predicate:$predicate, assertion_id:$assertion_id}]->(o)
                    MERGE (w)-[:HAS_ENTITY]->(o)
                    """,
                    assertion_id=assertion_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    object_id=object_id,
                    object_name=change.object.name,
                    object_type=change.object.entity_type,
                    object_aliases=change.object.aliases,
                    predicate=change.predicate,
                    now=now,
                ).consume()
            if change.supersedes_assertion_id:
                superseded = tx.run(
                    """
                    MATCH (a:Assertion {id:$new_id, workspace_id:$workspace_id}),
                          (:Workspace {id:$workspace_id})-[:HAS_ASSERTION]->
                          (old:Assertion {id:$old_id, workspace_id:$workspace_id})
                    SET old.governance_revision=coalesce(old.governance_revision, 0) + 1
                    WITH a, old
                    WHERE old.status='VERIFIED'
                      AND NOT EXISTS { (:Assertion)-[:SUPERSEDES]->(old) }
                    SET old.status='SUPERSEDED',
                        old.valid_to=coalesce(old.valid_to,$new_valid_from,$now)
                    MERGE (a)-[:SUPERSEDES]->(old)
                    RETURN old.id AS id
                    """,
                    new_id=assertion_id,
                    old_id=change.supersedes_assertion_id,
                    workspace_id=workspace_id,
                    new_valid_from=(change.valid_from.isoformat() if change.valid_from else None),
                    now=now,
                ).single()
                if not superseded:
                    raise ValueError("superseded assertion is no longer current")
        return approval_id

    def reject_proposal(
        self,
        proposal_id: str,
        reviewer: str,
        reason: str | None,
        access: AccessContext,
    ) -> dict:
        if reviewer not in access.principals:
            raise PermissionError("reviewed_by must be one of the authenticated principals")
        with self.driver.session(database=self.database) as session:
            exists = session.run(
                """
                MATCH (p:Proposal {id:$id})
                RETURN p.workspace_id AS workspace_id,
                       coalesce(p.proposal_type, 'ASSERTION') AS proposal_type,
                       p.changes_json AS changes_json, p.payload_json AS payload_json
                """,
                id=proposal_id,
            ).single()
        if not exists:
            raise KeyError(proposal_id)
        if (
            exists["workspace_id"] != access.workspace_id
            or self.proposal(proposal_id, access) is None
        ):
            raise PermissionError("proposal evidence is not accessible to this reviewer")
        if exists["proposal_type"] == "ASSERTION":
            evidence_ids = sorted(
                {change["evidence_chunk_id"] for change in json.loads(exists["changes_json"])}
            )
        else:
            evidence_ids = sorted(set(json.loads(exists["payload_json"])["evidence_chunk_ids"]))
        reviewed_at = now_iso()
        approval_id = stable_id("approval", proposal_id, reviewer, reviewed_at)
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._reject_proposal,
                proposal_id,
                access.workspace_id,
                evidence_ids,
                access.principals,
                approval_id,
                reviewed_at,
                reviewer,
                reason,
            )
        if not result:
            raise KeyError(proposal_id)
        self.ops.audit(reviewer, "REJECT_PROPOSAL", proposal_id, reason=reason)
        return {
            "id": proposal_id,
            "status": "REJECTED",
            "decision_trace_id": approval_id,
        }

    @staticmethod
    def _reject_proposal(
        tx,
        proposal_id,
        workspace_id,
        evidence_ids,
        principals,
        approval_id,
        reviewed_at,
        reviewer,
        reason,
    ):
        GraphStore._require_approvable_evidence(
            tx, proposal_id, workspace_id, evidence_ids, principals
        )
        return tx.run(
            """
                MATCH (:Workspace {id:$workspace_id})-[:HAS_PROPOSAL]->
                      (p:Proposal {id:$id})
                SET p.governance_revision=coalesce(p.governance_revision, 0) + 1
                WITH p
                WHERE p.status='PROPOSED'
                SET p.status='REJECTED', p.reviewed_at=$now, p.reviewed_by=$reviewer,
                    p.review_reason=$reason
                CREATE (a:Approval {id:$approval_id, decision:'REJECTED', reason:$reason,
                    reviewed_by:$reviewer, reviewed_at:$now})
                MERGE (p)-[:HAS_APPROVAL]->(a)
                RETURN p.id AS id
                """,
            id=proposal_id,
            workspace_id=workspace_id,
            approval_id=approval_id,
            now=reviewed_at,
            reviewer=reviewer,
            reason=reason,
        ).single()

    @staticmethod
    def _decode_proposal(record) -> dict:
        result = record.data()
        proposal = result["proposal"]
        changes_json = proposal.pop("changes_json", None)
        payload_json = proposal.pop("payload_json", None)
        if changes_json is not None:
            result["payload"] = {"changes": json.loads(changes_json)}
        elif payload_json is not None:
            result["payload"] = json.loads(payload_json)
        else:
            result["payload"] = None
        return result

    def proposal(self, proposal_id: str, access: AccessContext) -> dict | None:
        with self.driver.session(database=self.database) as session:
            row = session.run(
                """
                MATCH (p:Proposal {id:$id, workspace_id:$workspace_id})-[:SUPPORTED_BY]->(c:Chunk)
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(document:Document)
                      -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(c)
                MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                      any(principal IN coalesce(auth_version.acl, [])
                          WHERE principal IN $principals)
                WITH p, collect(DISTINCT {
                    chunk_id:c.id, document_id:document.id,
                    document_version_id:evidence_version.id,
                    authorization:{owner:evidence_version.owner,
                                   visibility:evidence_version.visibility,
                                   acl:evidence_version.acl},
                    current_authorization:{owner:auth_version.owner,
                                           visibility:auth_version.visibility,
                                           acl:auth_version.acl}
                }) AS evidence, count(DISTINCT c) AS accessible_count
                WHERE accessible_count = COUNT { (p)-[:SUPPORTED_BY]->(:Chunk) }
                OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
                RETURN properties(p) AS proposal, evidence,
                       collect(DISTINCT properties(approval)) AS approvals
                """,
                id=proposal_id,
                workspace_id=access.workspace_id,
                principals=access.principals,
            ).single()
        return self._decode_proposal(row) if row else None

    def proposals(
        self,
        access: AccessContext,
        status: str | None = "PROPOSED",
        proposal_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            rows = session.run(
                """
                MATCH (p:Proposal {workspace_id:$workspace_id})-[:SUPPORTED_BY]->(c:Chunk)
                WHERE ($status IS NULL OR p.status=$status)
                  AND ($proposal_type IS NULL OR p.proposal_type=$proposal_type)
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(document:Document)
                      -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(c)
                MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                      any(principal IN coalesce(auth_version.acl, [])
                          WHERE principal IN $principals)
                WITH p, collect(DISTINCT {
                    chunk_id:c.id, document_id:document.id,
                    document_version_id:evidence_version.id,
                    authorization:{owner:evidence_version.owner,
                                   visibility:evidence_version.visibility,
                                   acl:evidence_version.acl},
                    current_authorization:{owner:auth_version.owner,
                                           visibility:auth_version.visibility,
                                           acl:auth_version.acl}
                }) AS evidence, count(DISTINCT c) AS accessible_count
                WHERE accessible_count = COUNT { (p)-[:SUPPORTED_BY]->(:Chunk) }
                OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
                WITH p, evidence, collect(DISTINCT properties(approval)) AS approvals
                ORDER BY p.created_at DESC, p.id DESC
                LIMIT $limit
                RETURN properties(p) AS proposal, evidence, approvals
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
                status=status,
                proposal_type=proposal_type,
                limit=limit,
            )
            return [self._decode_proposal(row) for row in rows]

    def create_action(self, action: ActionCreate) -> dict:
        if action.workspace_id != action.access.workspace_id:
            raise PermissionError("action workspace must match its authenticated access context")
        if action.requested_by not in action.access.principals:
            raise PermissionError("requested_by must be one of the authenticated principals")
        payload = action.model_dump(mode="json", exclude={"idempotency_key", "access"})
        payload_json = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        payload_hash = content_hash(payload_json)
        action_id = stable_id(
            "action", action.workspace_id, action.requested_by, action.idempotency_key
        )
        creation_marker = stable_id("action-creation", action_id, now_iso())
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._write_action,
                action,
                action_id,
                payload_hash,
                creation_marker,
                self.contract_versions["action"],
                access_fingerprint(action.access.workspace_id, action.access.principals),
                len(action.access.principals),
            )
        if not result["created"]:
            return {"id": action_id, "status": result["status"], "unchanged": True}
        self.ops.audit(action.requested_by, "CREATE_ACTION", action_id, payload_hash=payload_hash)
        return {"id": action_id, "status": "PROPOSED", "unchanged": False}

    @staticmethod
    def _write_action(
        tx,
        action,
        action_id,
        payload_hash,
        creation_marker,
        contract_version,
        requested_access_fingerprint,
        requested_principal_count,
    ):
        timestamp = now_iso()
        row = tx.run(
            """
            MERGE (w:Workspace {id:$workspace_id})
            ON CREATE SET w.created_at=$now
            MERGE (a:Action {id:$id})
            ON CREATE SET a.action_type=$action_type, a.target=$target,
                a.parameters_json=$parameters_json, a.payload_hash=$payload_hash,
                a.idempotency_key=$idempotency_key, a.requested_by=$requested_by,
                a.requested_at=$now, a.reason=$reason, a.policy_version=$policy_version,
                a.approval_required=$approval_required, a.status='PROPOSED',
                a.execution_status='NOT_EXECUTED', a.workspace_id=$workspace_id,
                a.review_principals=$review_principals,
                a.execution_principals=$execution_principals,
                a.contract_version=$contract_version,
                a.requested_access_fingerprint=$requested_access_fingerprint,
                a.requested_principal_count=$requested_principal_count,
                a._creation_marker=$creation_marker
            WITH w, a, a._creation_marker=$creation_marker AS created
            REMOVE a._creation_marker
            MERGE (w)-[:HAS_ACTION]->(a)
            RETURN a, created,
                   a.payload_hash AS payload_hash, a.status AS status
            """,
            workspace_id=action.workspace_id,
            id=action_id,
            action_type=action.action_type,
            target=action.target,
            parameters_json=json.dumps(action.parameters, ensure_ascii=False, sort_keys=True),
            payload_hash=payload_hash,
            idempotency_key=action.idempotency_key,
            requested_by=action.requested_by,
            reason=action.reason,
            policy_version=action.policy_version,
            approval_required=action.approval_required,
            review_principals=action.review_principals,
            execution_principals=action.execution_principals,
            creation_marker=creation_marker,
            contract_version=contract_version,
            requested_access_fingerprint=requested_access_fingerprint,
            requested_principal_count=requested_principal_count,
            now=timestamp,
        ).single()
        if row["payload_hash"] != payload_hash:
            raise ValueError("idempotency key is already bound to a different action payload")
        return {"created": row["created"], "status": row["status"]}

    def decide_action(
        self,
        action_id: str,
        decision: str,
        reviewer: str,
        reason: str | None,
        access: AccessContext,
    ) -> dict:
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValueError(f"unsupported action decision: {decision}")
        if reviewer not in access.principals:
            raise PermissionError("reviewed_by must be one of the authenticated principals")
        with self.driver.session(database=self.database) as session:
            current = session.run(
                """
                MATCH (w:Workspace)-[:HAS_ACTION]->(a:Action {id:$id})
                RETURN w.id AS workspace_id, a.status AS status,
                       a.review_principals AS review_principals
                """,
                id=action_id,
            ).single()
        if not current:
            raise KeyError(action_id)
        if (
            current["workspace_id"] != access.workspace_id
            or reviewer not in current["review_principals"]
        ):
            raise PermissionError("reviewer is not authorized for this action")
        if current["status"] != "PROPOSED":
            raise ValueError(f"action is {current['status']}")
        reviewed_at = now_iso()
        approval_id = stable_id("approval", action_id, reviewer, decision, reviewed_at)
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._write_action_decision,
                action_id,
                access.workspace_id,
                decision,
                approval_id,
                reviewer,
                reason,
                reviewed_at,
            )
        if not result:
            raise ValueError("action is no longer pending")
        self.ops.audit(reviewer, f"{decision}_ACTION", action_id, reason=reason)
        return {
            "id": action_id,
            "status": decision,
            "execution_status": "NOT_EXECUTED",
            "decision_trace_id": approval_id,
        }

    @staticmethod
    def _write_action_decision(
        tx, action_id, workspace_id, decision, approval_id, reviewer, reason, reviewed_at
    ):
        return tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(action:Action {id:$id})
            SET action.governance_revision=coalesce(action.governance_revision, 0) + 1
            WITH action
            WHERE action.status='PROPOSED' AND $reviewer IN action.review_principals
            SET action.status=$decision, action.reviewed_at=$now,
                action.reviewed_by=$reviewer, action.review_reason=$reason
            CREATE (approval:Approval {
                id:$approval_id, decision:$decision, reason:$reason,
                reviewed_by:$reviewer, reviewed_at:$now, scope:'ACTION'
            })
            MERGE (action)-[:HAS_APPROVAL]->(approval)
            RETURN action.id AS id
            """,
            id=action_id,
            workspace_id=workspace_id,
            decision=decision,
            approval_id=approval_id,
            reviewer=reviewer,
            reason=reason,
            now=reviewed_at,
        ).single()

    def claim_action_execution(self, action_id: str, claim: ActionExecutionClaimCreate) -> dict:
        if claim.executed_by not in claim.access.principals:
            raise PermissionError("executed_by must be one of the authenticated principals")
        payload = claim.model_dump(mode="json", exclude={"access"})
        payload_hash = content_hash(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        claim_id = stable_id(
            "action-execution-claim", action_id, claim.connector, claim.idempotency_key
        )
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=claim.lease_seconds)
        external_idempotency_key = stable_id("external-action", action_id, claim.policy_version)
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._write_action_execution_claim,
                action_id,
                claim_id,
                claim,
                payload_hash,
                external_idempotency_key,
                now.isoformat(),
                lease_until.isoformat(),
                self.contract_versions["action"],
            )
        if result["outcome"] == "MISSING":
            raise KeyError(action_id)
        if result["outcome"] == "DENIED":
            raise PermissionError("connector is not authorized for this action")
        if result["outcome"] == "CONFLICT":
            raise ValueError(result["reason"])
        if not result["unchanged"]:
            self.ops.audit(
                claim.executed_by,
                "CLAIM_ACTION_EXECUTION",
                action_id,
                claim_id=claim_id,
                connector=claim.connector,
                authorization_ref=claim.authorization_ref,
                lease_until=lease_until.isoformat(),
            )
        return {
            "id": claim_id,
            "action_id": action_id,
            "status": "CLAIMED",
            "lease_until": result["lease_until"],
            "external_idempotency_key": external_idempotency_key,
            "unchanged": result["unchanged"],
        }

    @staticmethod
    def _write_action_execution_claim(
        tx,
        action_id,
        claim_id,
        claim,
        payload_hash,
        external_idempotency_key,
        claimed_at,
        lease_until,
        contract_version,
    ):
        action = tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(a:Action {id:$action_id})
            SET a.execution_revision=coalesce(a.execution_revision, 0) + 1
            RETURN a.status AS status, a.execution_status AS execution_status,
                   a.policy_version AS policy_version,
                   a.execution_principals AS execution_principals,
                   a.current_execution_claim_id AS current_claim_id
            """,
            workspace_id=claim.access.workspace_id,
            action_id=action_id,
        ).single()
        if not action:
            exists = tx.run("MATCH (a:Action {id:$id}) RETURN a.id AS id", id=action_id).single()
            return {"outcome": "DENIED" if exists else "MISSING"}
        if claim.executed_by not in action["execution_principals"]:
            return {"outcome": "DENIED"}
        if action["status"] != "APPROVED":
            return {"outcome": "CONFLICT", "reason": "action must be approved before execution"}
        if action["execution_status"] == "SUCCEEDED":
            return {"outcome": "CONFLICT", "reason": "action already succeeded"}
        if action["policy_version"] != claim.policy_version:
            return {
                "outcome": "CONFLICT",
                "reason": "claim policy does not match the approved action policy",
            }
        existing = tx.run(
            """
            MATCH (:Action {id:$action_id})-[:HAS_EXECUTION_CLAIM]->
                  (claim:ActionExecutionClaim {id:$claim_id})
            RETURN claim.payload_hash AS payload_hash, claim.status AS status,
                   claim.lease_until AS lease_until
            """,
            action_id=action_id,
            claim_id=claim_id,
        ).single()
        if existing:
            if existing["payload_hash"] != payload_hash:
                return {
                    "outcome": "CONFLICT",
                    "reason": "idempotency key is already bound to a different claim payload",
                }
            if existing["status"] != "CLAIMED":
                return {
                    "outcome": "CONFLICT",
                    "reason": f"execution claim is {existing['status']}",
                }
            active = tx.run(
                "RETURN datetime($lease_until) > datetime($now) AS active",
                lease_until=existing["lease_until"],
                now=claimed_at,
            ).single()["active"]
            if not active:
                return {
                    "outcome": "CONFLICT",
                    "reason": "execution claim lease expired; reconcile its external result",
                }
            return {
                "outcome": "OK",
                "unchanged": True,
                "lease_until": existing["lease_until"],
            }
        if action["current_claim_id"]:
            current = tx.run(
                """
                MATCH (a:Action {id:$action_id})-[:HAS_EXECUTION_CLAIM]->
                      (claim:ActionExecutionClaim)
                WHERE claim.id=a.current_execution_claim_id
                RETURN claim.id AS id, claim.status AS status,
                       datetime(claim.lease_until) > datetime($now) AS active
                """,
                action_id=action_id,
                now=claimed_at,
            ).single()
            if current and current["status"] == "CLAIMED" and current["active"]:
                return {"outcome": "CONFLICT", "reason": "action execution is already claimed"}
            if current and current["status"] == "CLAIMED":
                return {
                    "outcome": "CONFLICT",
                    "reason": "execution claim lease expired; reconcile its external result",
                }
        tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(a:Action {id:$action_id})
            CREATE (claim:ActionExecutionClaim {
                id:$claim_id, status:'CLAIMED', executed_by:$executed_by,
                connector:$connector, authorization_ref:$authorization_ref,
                policy_version:$policy_version, idempotency_key:$idempotency_key,
                payload_hash:$payload_hash, claimed_at:$claimed_at,
                lease_until:$lease_until,
                external_idempotency_key:$external_idempotency_key,
                contract_version:$contract_version
            })
            SET a.current_execution_claim_id=$claim_id, a.execution_status='IN_PROGRESS'
            MERGE (a)-[:HAS_EXECUTION_CLAIM]->(claim)
            """,
            workspace_id=claim.access.workspace_id,
            action_id=action_id,
            claim_id=claim_id,
            executed_by=claim.executed_by,
            connector=claim.connector,
            authorization_ref=claim.authorization_ref,
            policy_version=claim.policy_version,
            idempotency_key=claim.idempotency_key,
            payload_hash=payload_hash,
            claimed_at=claimed_at,
            lease_until=lease_until,
            external_idempotency_key=external_idempotency_key,
            contract_version=contract_version,
        ).consume()
        return {"outcome": "OK", "unchanged": False, "lease_until": lease_until}

    def record_action_execution(self, action_id: str, execution: ActionExecutionCreate) -> dict:
        if execution.executed_by not in execution.access.principals:
            raise PermissionError("executed_by must be one of the authenticated principals")
        payload = execution.model_dump(mode="json", exclude={"idempotency_key", "access"})
        payload_json = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        payload_hash = content_hash(payload_json)
        execution_id = stable_id("action-execution", action_id, execution.claim_id)
        with self.driver.session(database=self.database) as session:
            result = session.execute_write(
                self._write_action_execution,
                action_id,
                execution_id,
                execution,
                payload_json,
                payload_hash,
                execution.access.workspace_id,
                self.contract_versions["action"],
            )
        if result["unchanged"]:
            return {
                "id": execution_id,
                "action_id": action_id,
                "status": result["status"],
                "unchanged": True,
            }
        self.ops.audit(
            execution.executed_by,
            "RECORD_ACTION_EXECUTION",
            action_id,
            execution_id=execution_id,
            connector=execution.connector,
            authorization_ref=execution.authorization_ref,
            status=execution.status,
        )
        return {
            "id": execution_id,
            "action_id": action_id,
            "status": execution.status,
            "unchanged": False,
        }

    @staticmethod
    def _write_action_execution(
        tx,
        action_id,
        execution_id,
        execution,
        payload_json,
        payload_hash,
        workspace_id,
        contract_version,
    ):
        action = tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(a:Action {id:$action_id})
            SET a.execution_revision=coalesce(a.execution_revision, 0) + 1
            RETURN a.status AS status, a.execution_status AS execution_status,
                   a.policy_version AS policy_version,
                   a.execution_principals AS execution_principals,
                   a.current_execution_claim_id AS current_claim_id
            """,
            action_id=action_id,
            workspace_id=workspace_id,
        ).single()
        if not action:
            exists = tx.run("MATCH (a:Action {id:$id}) RETURN a.id AS id", id=action_id).single()
            if not exists:
                raise KeyError(action_id)
            raise PermissionError("connector is not authorized for this action")
        if execution.executed_by not in action["execution_principals"]:
            raise PermissionError("connector is not authorized for this action")
        existing = tx.run(
            """
            MATCH (:Action {id:$action_id})-[:HAS_EXECUTION]->
                  (e:ActionExecution {id:$execution_id})
            RETURN e.payload_hash AS payload_hash, e.status AS status
            """,
            action_id=action_id,
            execution_id=execution_id,
        ).single()
        if existing:
            if existing["payload_hash"] != payload_hash:
                raise ValueError(
                    "idempotency key is already bound to a different execution payload"
                )
            return {"status": existing["status"], "unchanged": True}
        if action["status"] != "APPROVED":
            raise ValueError("action must be approved before execution evidence is recorded")
        if action["execution_status"] == "SUCCEEDED":
            raise ValueError(
                "action already succeeded; a new execution attempt requires a new governed action"
            )
        if action["policy_version"] != execution.policy_version:
            raise ValueError(
                f"execution policy {execution.policy_version} does not match approved "
                f"action policy {action['policy_version']}"
            )
        claim = tx.run(
            """
            MATCH (:Action {id:$action_id})-[:HAS_EXECUTION_CLAIM]->
                  (claim:ActionExecutionClaim {id:$claim_id})
            RETURN claim.status AS status, claim.executed_by AS executed_by,
                   claim.connector AS connector,
                   claim.authorization_ref AS authorization_ref,
                   claim.policy_version AS policy_version,
                   claim.idempotency_key AS idempotency_key,
                   claim.external_idempotency_key AS external_idempotency_key
            """,
            action_id=action_id,
            claim_id=execution.claim_id,
        ).single()
        if not claim or action["current_claim_id"] != execution.claim_id:
            raise ValueError("execution must complete the action's current claim")
        if claim["status"] != "CLAIMED":
            raise ValueError(f"execution claim is {claim['status']}")
        if (
            claim["executed_by"] != execution.executed_by
            or claim["connector"] != execution.connector
            or claim["authorization_ref"] != execution.authorization_ref
            or claim["policy_version"] != execution.policy_version
        ):
            raise ValueError("execution evidence does not match its claim capability")
        if claim["idempotency_key"] != execution.idempotency_key:
            raise ValueError("execution idempotency key does not match its claim")
        if claim["external_idempotency_key"] != execution.external_idempotency_key:
            raise ValueError("external idempotency key does not match its claim")
        row = tx.run(
            """
            MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(a:Action {id:$action_id})
                  -[:HAS_EXECUTION_CLAIM]->(claim:ActionExecutionClaim {id:$claim_id})
            CREATE (e:ActionExecution {
                id:$execution_id, status:$status, executed_by:$executed_by,
                connector:$connector, external_api:$external_api,
                authorization_ref:$authorization_ref, policy_version:$policy_version,
                external_request_id:$external_request_id, executed_at:$executed_at,
                payload_json:$payload_json, payload_hash:$payload_hash,
                rollback_ref:$rollback_ref, recorded_at:$recorded_at,
                claim_id:$claim_id, external_idempotency_key:$external_idempotency_key,
                contract_version:$contract_version
            })
            SET a.execution_status=$status, a.last_execution_at=$executed_at,
                a.current_execution_claim_id=null,
                claim.status='COMPLETED', claim.completed_at=$recorded_at
            MERGE (a)-[:HAS_EXECUTION]->(e)
            MERGE (claim)-[:PRODUCED_EXECUTION]->(e)
            RETURN e.id AS id
            """,
            action_id=action_id,
            workspace_id=workspace_id,
            execution_id=execution_id,
            claim_id=execution.claim_id,
            status=execution.status,
            executed_by=execution.executed_by,
            connector=execution.connector,
            external_api=execution.external_api,
            authorization_ref=execution.authorization_ref,
            policy_version=execution.policy_version,
            external_request_id=execution.external_request_id,
            executed_at=execution.executed_at.isoformat(),
            payload_json=payload_json,
            payload_hash=payload_hash,
            rollback_ref=execution.rollback_ref,
            external_idempotency_key=execution.external_idempotency_key,
            contract_version=contract_version,
            recorded_at=now_iso(),
        ).single()
        if not row:
            raise ValueError("action is no longer approved")
        return {"status": execution.status, "unchanged": False}

    def action(self, action_id: str, access: AccessContext | None = None) -> dict | None:
        with self.driver.session(database=self.database) as session:
            if access is not None:
                row = session.run(
                    """
                    MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(a:Action {id:$id})
                    WHERE any(principal IN $principals WHERE
                        principal=a.requested_by OR
                        principal IN coalesce(a.review_principals, []) OR
                        principal IN coalesce(a.execution_principals, []))
                    OPTIONAL MATCH (a)-[:HAS_APPROVAL]->(approval:Approval)
                    OPTIONAL MATCH (a)-[:HAS_EXECUTION]->(execution:ActionExecution)
                    OPTIONAL MATCH (a)-[:HAS_EXECUTION_CLAIM]->(claim:ActionExecutionClaim)
                    RETURN properties(a) AS action,
                           collect(DISTINCT properties(approval)) AS decisions,
                           collect(DISTINCT properties(execution)) AS executions,
                           collect(DISTINCT properties(claim)) AS execution_claims
                    """,
                    id=action_id,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                ).single()
            else:
                row = session.run(
                    """
                    MATCH (a:Action {id:$id})
                OPTIONAL MATCH (a)-[:HAS_APPROVAL]->(approval:Approval)
                OPTIONAL MATCH (a)-[:HAS_EXECUTION]->(execution:ActionExecution)
                OPTIONAL MATCH (a)-[:HAS_EXECUTION_CLAIM]->(claim:ActionExecutionClaim)
                RETURN properties(a) AS action,
                       collect(DISTINCT properties(approval)) AS decisions,
                       collect(DISTINCT properties(execution)) AS executions,
                       collect(DISTINCT properties(claim)) AS execution_claims
                    """,
                    id=action_id,
                ).single()
        if not row:
            return None
        result = row.data()
        result["action"]["parameters"] = json.loads(result["action"].pop("parameters_json"))
        for execution in result["executions"]:
            execution["payload"] = json.loads(execution.pop("payload_json"))
        return result

    def actions(
        self,
        access: AccessContext,
        *,
        status: str | None = None,
        action_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            rows = session.run(
                """
                MATCH (:Workspace {id:$workspace_id})-[:HAS_ACTION]->(a:Action)
                WHERE ($status IS NULL OR a.status=$status)
                  AND ($action_type IS NULL OR a.action_type=$action_type)
                  AND any(principal IN $principals WHERE
                    principal=a.requested_by OR
                    principal IN coalesce(a.review_principals, []) OR
                    principal IN coalesce(a.execution_principals, []))
                RETURN a.id AS id, a.action_type AS action_type, a.target AS target,
                       a.status AS status, a.execution_status AS execution_status,
                       a.requested_by AS requested_by, a.requested_at AS requested_at,
                       a.reason AS reason, a.policy_version AS policy_version,
                       a.approval_required AS approval_required
                ORDER BY a.requested_at DESC, a.id DESC
                LIMIT $limit
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
                status=status,
                action_type=action_type,
                limit=limit,
            )
            return [row.data() for row in rows]

    def sources(self, access: AccessContext, limit: int = 100) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            rows = session.run(
                """
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(s:Source)
                      -[:HAS_DOCUMENT]->(d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                WHERE v.visibility='PUBLIC' OR v.owner IN $principals OR
                      any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                WITH s, count(DISTINCT d) AS accessible_document_count
                ORDER BY s.type, s.external_id, s.id
                LIMIT $limit
                RETURN s.id AS id, s.type AS type, s.external_id AS external_id,
                       s.uri AS uri, s.connector_id AS connector_id,
                       s.status AS status, s.last_seen AS last_seen,
                       properties(s)['last_sync_cursor'] AS last_sync_cursor,
                       properties(s)['last_sync_run_id'] AS last_sync_run_id,
                       properties(s)['last_sync_completed_at'] AS last_sync_completed_at,
                       accessible_document_count
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
                limit=limit,
            )
            return [row.data() for row in rows]

    def source(self, source_id: str, access: AccessContext) -> dict | None:
        with self.driver.session(database=self.database) as session:
            row = session.run(
                """
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(s:Source {id:$id})
                      -[:HAS_DOCUMENT]->(d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                WHERE v.visibility='PUBLIC' OR v.owner IN $principals OR
                      any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                WITH s, collect(DISTINCT {
                    id:d.id, external_id:d.external_id, title:d.title, status:d.status,
                    updated_at:d.updated_at, current_version_id:v.id,
                    current_authorization:{owner:v.owner, visibility:v.visibility, acl:v.acl}
                }) AS documents
                RETURN {
                    id:s.id, type:s.type, external_id:s.external_id, uri:s.uri,
                    connector_id:s.connector_id,
                    status:s.status, last_seen:s.last_seen,
                    last_sync_cursor:properties(s)['last_sync_cursor'],
                    last_sync_run_id:properties(s)['last_sync_run_id'],
                    last_sync_completed_at:properties(s)['last_sync_completed_at']
                } AS source, documents
                """,
                id=source_id,
                workspace_id=access.workspace_id,
                principals=access.principals,
            ).single()
            return row.data() if row else None

    def documents(
        self, access: AccessContext, source_id: str | None = None, limit: int = 100
    ) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            rows = session.run(
                """
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(s:Source)
                      -[:HAS_DOCUMENT]->(d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                WHERE ($source_id IS NULL OR s.id=$source_id) AND (
                    v.visibility='PUBLIC' OR v.owner IN $principals OR
                    any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                )
                RETURN d.id AS id, d.external_id AS external_id, d.title AS title,
                       d.status AS status, d.updated_at AS updated_at,
                       s.id AS source_id, s.type AS source_type,
                       v.id AS current_version_id,
                       {owner:v.owner, visibility:v.visibility, acl:v.acl}
                           AS current_authorization
                ORDER BY d.updated_at DESC, d.id
                LIMIT $limit
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
                source_id=source_id,
                limit=limit,
            )
            return [row.data() for row in rows]

    def document(
        self, document_id: str, access: AccessContext, include_chunks: bool = False
    ) -> dict | None:
        with self.driver.session(database=self.database) as session:
            rows = list(
                session.run(
                    """
                    MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(s:Source)
                          -[:HAS_DOCUMENT]->(d:Document {id:$id})
                          -[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                    WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                          any(principal IN coalesce(auth_version.acl, [])
                              WHERE principal IN $principals)
                    MATCH (d)-[:HAS_VERSION]->(version:DocumentVersion)
                    OPTIONAL MATCH (version)-[:HAS_CHUNK]->(chunk:Chunk)
                    WHERE $include_chunks
                    WITH s, d, auth_version, version, chunk
                    ORDER BY version.recorded_at DESC, chunk.position
                    WITH s, d, auth_version, version,
                         collect(CASE WHEN chunk IS NULL THEN null ELSE {
                             id:chunk.id, position:chunk.position, text:chunk.text,
                             content_hash:chunk.content_hash, active:chunk.active,
                             created_at:chunk.created_at,
                             embedding_model:properties(chunk)['embedding_model'],
                             embedding_version:properties(chunk)['embedding_version']
                         } END) AS chunks
                    RETURN {
                        id:s.id, type:s.type, external_id:s.external_id, uri:s.uri,
                        status:s.status
                    } AS source,
                    properties(d) AS document,
                    properties(version) AS version,
                    version.id=auth_version.id AS is_current,
                    {owner:auth_version.owner, visibility:auth_version.visibility,
                     acl:auth_version.acl} AS current_authorization,
                    chunks
                    ORDER BY version.recorded_at DESC
                    """,
                    id=document_id,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    include_chunks=include_chunks,
                )
            )
        if not rows:
            return None
        first = rows[0]
        return {
            "source": first["source"],
            "document": first["document"],
            "current_authorization": first["current_authorization"],
            "versions": [
                {
                    "version": row["version"],
                    "is_current": row["is_current"],
                    "chunks": row["chunks"] if include_chunks else None,
                }
                for row in rows
            ],
        }

    def evidence_bundle(self, request: EvidenceBundleRequest) -> list[dict] | None:
        with self.driver.session(database=self.database) as session:
            row = session.run(
                """
                UNWIND $chunk_ids AS chunk_id
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(source:Source)
                      -[:HAS_DOCUMENT]->(document:Document)
                      -[:HAS_VERSION]->(version:DocumentVersion)-[:HAS_CHUNK]->
                      (chunk:Chunk {id:chunk_id})
                MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                WHERE document.status='ACTIVE' AND (
                    auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                    any(principal IN coalesce(auth_version.acl, [])
                        WHERE principal IN $principals)
                )
                WITH chunk, version, document, source, auth_version
                ORDER BY chunk.id
                WITH collect({
                    chunk:{id:chunk.id, text:chunk.text, position:chunk.position,
                           content_hash:chunk.content_hash, active:chunk.active,
                           created_at:chunk.created_at},
                    document:{id:document.id, external_id:document.external_id,
                              title:document.title, status:document.status},
                    document_version:{id:version.id, content_hash:version.content_hash,
                                      source_version:version.source_version,
                                      source_updated_at:version.source_updated_at,
                                      parser_version:version.parser_version,
                                      chunker_version:version.chunker_version,
                                      recorded_at:version.recorded_at,
                                      source_uri:version.source_uri,
                                      source_metadata_hash:version.source_metadata_hash,
                                      source_contract_version:version.source_contract_version},
                    source:{id:source.id, type:source.type, external_id:source.external_id,
                            uri:source.uri, status:source.status,
                            connector_id:source.connector_id},
                    authorization:{owner:version.owner, visibility:version.visibility,
                                   acl:version.acl},
                    current_authorization:{owner:auth_version.owner,
                                           visibility:auth_version.visibility,
                                           acl:auth_version.acl}
                }) AS evidence, count(DISTINCT chunk) AS accessible_count
                WHERE accessible_count=size($chunk_ids)
                RETURN evidence
                """,
                chunk_ids=request.chunk_ids,
                workspace_id=request.access.workspace_id,
                principals=request.access.principals,
            ).single()
        return row["evidence"] if row else None

    def assertion(
        self,
        assertion_id: str,
        access: AccessContext,
        as_of: CanonicalDatetime | None = None,
    ) -> dict | None:
        as_of_value = as_of.isoformat() if as_of else None
        with self.driver.session(database=self.database) as session:
            row = session.run(
                """
                MATCH (assertion:Assertion {id:$id, workspace_id:$workspace_id})
                      -[:SUBJECT]->(subject:Entity {workspace_id:$workspace_id})
                WHERE $as_of IS NULL OR (
                    assertion.status IN ['VERIFIED', 'SUPERSEDED']
                    AND (assertion.valid_from IS NULL OR
                         datetime(replace(toString(assertion.valid_from), ' ', 'T'))
                            <= datetime($as_of))
                    AND (assertion.valid_to IS NULL OR
                         datetime($as_of) <
                            datetime(replace(toString(assertion.valid_to), ' ', 'T')))
                )
                MATCH (chunk:Chunk)-[:EVIDENCE_FOR]->(assertion)
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(document:Document)
                      -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(chunk)
                MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                      any(principal IN coalesce(auth_version.acl, [])
                          WHERE principal IN $principals)
                WITH assertion, subject,
                     collect(DISTINCT {
                         chunk_id:chunk.id, document_id:document.id,
                         document_version_id:evidence_version.id,
                         authorization:{owner:evidence_version.owner,
                                        visibility:evidence_version.visibility,
                                        acl:evidence_version.acl},
                         current_authorization:{owner:auth_version.owner,
                                                visibility:auth_version.visibility,
                                                acl:auth_version.acl}
                     }) AS evidence, count(DISTINCT chunk) AS accessible_count
                WHERE accessible_count = COUNT { (c:Chunk)-[:EVIDENCE_FOR]->(assertion) }
                OPTIONAL MATCH (assertion)-[:OBJECT]->(object:Entity {workspace_id:$workspace_id})
                OPTIONAL MATCH (proposal:Proposal)-[:PROMOTED]->(assertion)
                OPTIONAL MATCH (proposal)-[:HAS_APPROVAL]->(approval:Approval)
                RETURN properties(assertion) AS assertion, properties(subject) AS subject,
                       CASE WHEN object IS NULL THEN null ELSE properties(object) END AS object,
                       evidence, collect(DISTINCT properties(approval)) AS approvals
                """,
                id=assertion_id,
                workspace_id=access.workspace_id,
                principals=access.principals,
                as_of=as_of_value,
            ).single()
        return row.data() if row else None

    def decision(
        self,
        decision_id: str,
        access: AccessContext | None = None,
        as_of: CanonicalDatetime | None = None,
    ) -> dict | None:
        as_of_value = as_of.isoformat() if as_of else None
        with self.driver.session(database=self.database) as session:
            if access is not None:
                row = session.run(
                    """
                    MATCH (d:Decision {id:$id, workspace_id:$workspace_id})
                    WHERE $as_of IS NULL OR (
                        (d.valid_from IS NULL OR datetime(d.valid_from) <= datetime($as_of))
                        AND (d.valid_to IS NULL OR datetime($as_of) < datetime(d.valid_to))
                    )
                    MATCH (c:Chunk)-[:EVIDENCE_FOR]->(d)
                    MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(document:Document)
                          -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(c)
                    MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                    WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                          any(principal IN coalesce(auth_version.acl, [])
                              WHERE principal IN $principals)
                    WITH d, collect(DISTINCT {
                        chunk_id:c.id, document_id:document.id,
                        document_version_id:evidence_version.id,
                        authorization:{owner:evidence_version.owner,
                                       visibility:evidence_version.visibility,
                                       acl:evidence_version.acl},
                        current_authorization:{owner:auth_version.owner,
                                               visibility:auth_version.visibility,
                                               acl:auth_version.acl}
                    }) AS evidence, count(DISTINCT c) AS accessible_count
                    WHERE accessible_count = COUNT { (c:Chunk)-[:EVIDENCE_FOR]->(d) }
                    OPTIONAL MATCH (p:Proposal)-[:PROMOTED]->(d)
                    OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
                    RETURN properties(d) AS decision, evidence,
                        collect(DISTINCT properties(approval)) AS approvals
                    """,
                    id=decision_id,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    as_of=as_of_value,
                ).single()
                return row.data() if row else None
            row = session.run(
                """
                MATCH (d:Decision {id:$id})
                WHERE $as_of IS NULL OR (
                    (d.valid_from IS NULL OR datetime(d.valid_from) <= datetime($as_of))
                    AND (d.valid_to IS NULL OR datetime($as_of) < datetime(d.valid_to))
                )
                OPTIONAL MATCH (c:Chunk)-[:EVIDENCE_FOR]->(d)
                OPTIONAL MATCH (v:DocumentVersion)-[:HAS_CHUNK]->(c)
                OPTIONAL MATCH (document:Document)-[:HAS_VERSION]->(v)
                OPTIONAL MATCH (p:Proposal)-[:PROMOTED]->(d)
                OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
                RETURN properties(d) AS decision,
                    collect(DISTINCT {
                        chunk_id:c.id, document_id:document.id, document_version_id:v.id,
                        authorization:{owner:v.owner, visibility:v.visibility, acl:v.acl}
                    }) AS evidence,
                    collect(DISTINCT properties(approval)) AS approvals
                """,
                id=decision_id,
                as_of=as_of_value,
            ).single()
            return row.data() if row else None

    def event(
        self,
        event_id: str,
        access: AccessContext | None = None,
        as_of: CanonicalDatetime | None = None,
    ) -> dict | None:
        as_of_value = as_of.isoformat() if as_of else None
        with self.driver.session(database=self.database) as session:
            if access is not None:
                row = session.run(
                    """
                    MATCH (e:Event {
                        id:$id, event_class:'SEMANTIC', workspace_id:$workspace_id
                    })
                    WHERE $as_of IS NULL OR datetime(e.occurred_at) <= datetime($as_of)
                    MATCH (c:Chunk)-[:EVIDENCE_FOR]->(e)
                    MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(document:Document)
                          -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(c)
                    MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                    WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                          any(principal IN coalesce(auth_version.acl, [])
                              WHERE principal IN $principals)
                    WITH e, collect(DISTINCT {
                        chunk_id:c.id, document_id:document.id,
                        document_version_id:evidence_version.id,
                        authorization:{owner:evidence_version.owner,
                                       visibility:evidence_version.visibility,
                                       acl:evidence_version.acl},
                        current_authorization:{owner:auth_version.owner,
                                               visibility:auth_version.visibility,
                                               acl:auth_version.acl}
                    }) AS evidence, count(DISTINCT c) AS accessible_count
                    WHERE accessible_count = COUNT { (c:Chunk)-[:EVIDENCE_FOR]->(e) }
                    OPTIONAL MATCH (p:Proposal)-[:PROMOTED]->(e)
                    OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
                    RETURN properties(e) AS event, evidence,
                        collect(DISTINCT properties(approval)) AS approvals
                    """,
                    id=event_id,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    as_of=as_of_value,
                ).single()
                return row.data() if row else None
            row = session.run(
                """
                MATCH (e:Event {id:$id, event_class:'SEMANTIC'})
                WHERE $as_of IS NULL OR datetime(e.occurred_at) <= datetime($as_of)
                OPTIONAL MATCH (c:Chunk)-[:EVIDENCE_FOR]->(e)
                OPTIONAL MATCH (v:DocumentVersion)-[:HAS_CHUNK]->(c)
                OPTIONAL MATCH (document:Document)-[:HAS_VERSION]->(v)
                OPTIONAL MATCH (p:Proposal)-[:PROMOTED]->(e)
                OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
                RETURN properties(e) AS event,
                    collect(DISTINCT {
                        chunk_id:c.id, document_id:document.id, document_version_id:v.id,
                        authorization:{owner:v.owner, visibility:v.visibility, acl:v.acl}
                    }) AS evidence,
                    collect(DISTINCT properties(approval)) AS approvals
                """,
                id=event_id,
                as_of=as_of_value,
            ).single()
            return row.data() if row else None

    def search(
        self, query: str, limit: int = 10, access: AccessContext | None = None
    ) -> list[dict]:
        search_query = literal_fulltext_query(query)
        candidate_limit = min(max(limit * 5, 25), 100)
        with self.driver.session(database=self.database) as session:
            if access is not None:
                records = session.run(
                    """
                    CALL db.index.fulltext.queryNodes('chunk_text_fulltext', $search_query)
                    YIELD node, score
                    MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                          -[:HAS_CHUNK]->(node)
                    WHERE node.active = true AND (
                        v.visibility='PUBLIC' OR v.owner IN $principals OR
                        any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                    )
                    RETURN node.id AS chunk_id, node.text AS text, d.id AS document_id,
                           d.title AS title, score,
                           {owner:v.owner, visibility:v.visibility, acl:v.acl} AS authorization
                    ORDER BY score DESC LIMIT $limit
                    """,
                    search_query=search_query,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    limit=candidate_limit,
                )
                return rerank_keyword_results(query, [record.data() for record in records], limit)
            records = session.run(
                """
                CALL db.index.fulltext.queryNodes('chunk_text_fulltext', $search_query)
                YIELD node, score
                MATCH (v:DocumentVersion)-[:HAS_CHUNK]->(node)
                MATCH (d:Document)-[:CURRENT_VERSION]->(v)
                WHERE node.active = true
                RETURN node.id AS chunk_id, node.text AS text, d.id AS document_id,
                       d.title AS title, score,
                       {owner:v.owner, visibility:v.visibility, acl:v.acl} AS authorization
                ORDER BY score DESC LIMIT $limit
                """,
                search_query=search_query,
                limit=candidate_limit,
            )
            return rerank_keyword_results(query, [record.data() for record in records], limit)

    def upsert_chunk_embedding(self, chunk_id: str, embedding: EmbeddingUpsert) -> dict:
        if len(embedding.vector) != self.embedding_dimensions:
            raise ValueError(
                f"embedding has {len(embedding.vector)} dimensions; "
                f"expected {self.embedding_dimensions}"
            )
        if embedding.created_by not in embedding.access.principals:
            raise PermissionError("created_by must be one of the authenticated principals")
        fingerprint = embedding_fingerprint(
            embedding.vector, embedding.model, embedding.model_version
        )
        started = perf_counter()
        with self.driver.session(database=self.database) as session:
            row = session.run(
                """
                MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                      -[:HAS_CHUNK]->(c:Chunk {id:$chunk_id})
                WHERE c.active=true AND (
                    v.visibility='PUBLIC' OR v.owner IN $principals OR
                    any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                )
                WITH c, c.embedding_hash AS previous_hash
                WHERE c.embedding IS NULL OR c.embedding_hash=$embedding_hash
                SET c.embedding=$vector, c.embedding_model=$model,
                    c.embedding_version=$model_version,
                    c.embedding_hash=$embedding_hash,
                    c.embedding_created_at=coalesce(c.embedding_created_at, $now),
                    c.embedding_created_by=coalesce(c.embedding_created_by, $created_by)
                RETURN c.id AS id,
                       CASE WHEN previous_hash IS NULL THEN 'CREATED' ELSE 'UNCHANGED' END AS status
                """,
                chunk_id=chunk_id,
                vector=embedding.vector,
                model=embedding.model,
                model_version=embedding.model_version,
                workspace_id=embedding.access.workspace_id,
                principals=embedding.access.principals,
                embedding_hash=fingerprint,
                created_by=embedding.created_by,
                now=now_iso(),
            ).single()
        if not row:
            with self.driver.session(database=self.database) as session:
                state = session.run(
                    """
                    OPTIONAL MATCH (candidate:Chunk {id:$id})
                    OPTIONAL MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                          -[:HAS_CHUNK]->(c:Chunk {id:$id})
                    WHERE c.active=true AND (
                        v.visibility='PUBLIC' OR v.owner IN $principals OR
                        any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                    )
                    RETURN candidate IS NOT NULL AS exists,
                           c IS NOT NULL AS accessible,
                           c.embedding_hash AS embedding_hash
                    """,
                    id=chunk_id,
                    workspace_id=embedding.access.workspace_id,
                    principals=embedding.access.principals,
                ).single()
            if not state or not state["exists"]:
                raise KeyError(chunk_id)
            if state["accessible"] and state["embedding_hash"] != fingerprint:
                raise ValueError(
                    "chunk already has a different embedding; replacement requires an explicit "
                    "versioned re-embedding contract"
                )
            raise PermissionError("current active chunk is not accessible to this adapter")
        self.ops.audit(
            embedding.created_by,
            "UPSERT_CHUNK_EMBEDDING",
            chunk_id,
            model=embedding.model,
            model_version=embedding.model_version,
            embedding_hash=fingerprint,
            status=row["status"],
        )
        self.ops.telemetry(
            "embedding_upsert",
            "SUCCESS",
            started,
            chunk_id=chunk_id,
            model=embedding.model,
            model_version=embedding.model_version,
        )
        return {
            "chunk_id": chunk_id,
            "model": embedding.model,
            "model_version": embedding.model_version,
            "dimensions": len(embedding.vector),
            "embedding_hash": fingerprint,
            "status": row["status"],
        }

    def semantic_search(
        self,
        embedding: list[float],
        model: str,
        model_version: str,
        limit: int = 10,
        access: AccessContext | None = None,
    ) -> list[dict]:
        if len(embedding) != self.embedding_dimensions:
            raise ValueError(
                f"query embedding has {len(embedding)} dimensions; "
                f"expected {self.embedding_dimensions}"
            )
        candidate_limit = min(max(limit * 20, 100), 1000) if access else limit
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (node:Chunk)
                  SEARCH node IN (
                    VECTOR INDEX chunk_embedding_vector
                    FOR $embedding
                    WHERE node.active=true AND node.embedding_model=$model
                        AND node.embedding_version=$model_version
                    LIMIT $candidate_limit
                  ) SCORE AS score
                MATCH (w:Workspace)-[:OWNS_SOURCE]->(:Source)-[:HAS_DOCUMENT]->(d:Document)
                      -[:CURRENT_VERSION]->(v:DocumentVersion)-[:HAS_CHUNK]->(node)
                WHERE $workspace_id IS NULL OR (
                    w.id=$workspace_id AND (
                        v.visibility='PUBLIC' OR v.owner IN $principals OR
                        any(principal IN coalesce(v.acl, []) WHERE principal IN $principals)
                    )
                )
                RETURN node.id AS chunk_id, node.text AS text, d.id AS document_id,
                       d.title AS title, score,
                       {owner:v.owner, visibility:v.visibility, acl:v.acl} AS authorization
                ORDER BY score DESC LIMIT $limit
                """,
                embedding=embedding,
                model=model,
                model_version=model_version,
                candidate_limit=candidate_limit,
                limit=limit,
                workspace_id=access.workspace_id if access else None,
                principals=access.principals if access else [],
            )
            return [record.data() for record in records]

    def retrieval_capabilities(self, access: AccessContext) -> dict:
        with self.driver.session(database=self.database) as session:
            counts = session.run(
                """
                MATCH (:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                      -[:HAS_CHUNK]->(c:Chunk)
                WHERE c.active=true AND (v.visibility='PUBLIC' OR v.owner IN $principals OR
                    any(principal IN coalesce(v.acl, []) WHERE principal IN $principals))
                RETURN count(DISTINCT c) AS accessible_chunks,
                       count(DISTINCT CASE WHEN c.embedding IS NOT NULL THEN c END)
                           AS embedded_chunks
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
            ).single()
            models = session.run(
                """
                MATCH (:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
                      -[:HAS_CHUNK]->(c:Chunk)
                WHERE c.active=true AND c.embedding IS NOT NULL
                  AND (v.visibility='PUBLIC' OR v.owner IN $principals OR
                    any(principal IN coalesce(v.acl, []) WHERE principal IN $principals))
                RETURN c.embedding_model AS model, c.embedding_version AS version,
                       count(DISTINCT c) AS embedded_chunks
                ORDER BY model, version
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
            ).data()
            entity_counts = session.run(
                """
                MATCH (entity:Entity {workspace_id:$workspace_id})
                      <-[:SUBJECT|OBJECT]-(assertion:Assertion {workspace_id:$workspace_id})
                MATCH (chunk:Chunk)-[:EVIDENCE_FOR]->(assertion)
                MATCH (:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                      -[:HAS_DOCUMENT]->(document:Document)
                      -[:HAS_VERSION]->(:DocumentVersion)-[:HAS_CHUNK]->(chunk)
                MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                      any(principal IN coalesce(auth_version.acl, [])
                          WHERE principal IN $principals)
                WITH entity, assertion, count(DISTINCT chunk) AS accessible_count
                WHERE accessible_count =
                      COUNT { (evidence:Chunk)-[:EVIDENCE_FOR]->(assertion) }
                RETURN count(DISTINCT entity) AS accessible_entities
                """,
                workspace_id=access.workspace_id,
                principals=access.principals,
            ).single()
        accessible_chunks = int(counts["accessible_chunks"]) if counts else 0
        embedded_chunks = int(counts["embedded_chunks"]) if counts else 0
        accessible_entities = int(entity_counts["accessible_entities"]) if entity_counts else 0
        return {
            "contract_version": self.contract_versions["retrieval"],
            "modes": ["keyword", "semantic", "hybrid", "graph"],
            "embedding_dimensions": self.embedding_dimensions,
            "accessible_chunks": accessible_chunks,
            "embedded_chunks": embedded_chunks,
            "semantic_available": embedded_chunks > 0,
            "embedding_models": [dict(row) for row in models],
            "accessible_entities": accessible_entities,
            "graph_available": accessible_entities > 0,
        }

    @staticmethod
    def fuse_results(
        keyword_results: list[dict], semantic_results: list[dict], limit: int
    ) -> list[dict]:
        fused: dict[str, dict] = {}
        for mode, results in (("keyword", keyword_results), ("semantic", semantic_results)):
            for rank, result in enumerate(results, start=1):
                chunk_id = result["chunk_id"]
                item = fused.setdefault(
                    chunk_id,
                    {**result, "score": 0.0, "keyword_score": None, "semantic_score": None},
                )
                item["score"] += 1.0 / (60 + rank)
                item[f"{mode}_score"] = result["score"]
        return sorted(fused.values(), key=lambda item: (-item["score"], item["chunk_id"]))[:limit]

    def retrieve(self, request: RetrievalQuery) -> dict:
        started = perf_counter()
        try:
            keyword_results = (
                self.search(request.query, request.limit, request.access)
                if request.mode != "semantic"
                else []
            )
            semantic_results = (
                self.semantic_search(
                    request.embedding or [],
                    request.embedding_model or "",
                    request.embedding_version or "",
                    request.limit,
                    request.access,
                )
                if request.mode != "keyword"
                else []
            )
            if request.mode == "keyword":
                results = keyword_results
            elif request.mode == "semantic":
                results = semantic_results
            else:
                results = self.fuse_results(keyword_results, semantic_results, request.limit)
        except Exception as exc:
            error_id = self.ops.error(
                "retrieval",
                exc,
                safe_message="retrieval failed",
                query_hash=content_hash(request.query),
                mode=request.mode,
                workspace_id=request.access.workspace_id,
            )
            self.ops.telemetry("retrieval", "ERROR", started, error_id=error_id)
            raise
        trace_id = self.ops.retrieval_trace(
            request.query,
            request.mode,
            started,
            [result["chunk_id"] for result in results],
            contract_version=self.contract_versions["retrieval"],
            embedding_model=request.embedding_model,
            embedding_version=request.embedding_version,
            limit=request.limit,
            workspace_id=request.access.workspace_id,
            principal_count=len(request.access.principals),
            access_fingerprint=access_fingerprint(
                request.access.workspace_id, request.access.principals
            ),
            keyword_ranker=(
                KEYWORD_RANKER_VERSION if request.mode in {"keyword", "hybrid"} else None
            ),
        )
        self.ops.telemetry("retrieval", "SUCCESS", started, trace_id=trace_id, results=len(results))
        return {
            "trace_id": trace_id,
            "query": request.query,
            "mode": request.mode,
            "contract_version": self.contract_versions["retrieval"],
            "results": results,
        }

    def search_traced(
        self, query: str, limit: int = 10, access: AccessContext | None = None
    ) -> dict:
        started = perf_counter()
        try:
            results = self.search(query, limit, access)
        except Exception as exc:
            error_id = self.ops.error(
                "retrieval",
                exc,
                safe_message="retrieval failed",
                query_hash=content_hash(query),
                mode="keyword",
                workspace_id=access.workspace_id if access else None,
            )
            self.ops.telemetry("retrieval", "ERROR", started, error_id=error_id)
            raise
        trace_id = self.ops.retrieval_trace(
            query,
            "keyword",
            started,
            [result["chunk_id"] for result in results],
            contract_version=self.contract_versions["retrieval"],
            limit=limit,
            workspace_id=access.workspace_id if access else None,
            principal_count=len(access.principals) if access else None,
            access_fingerprint=(
                access_fingerprint(access.workspace_id, access.principals) if access else None
            ),
            keyword_ranker=KEYWORD_RANKER_VERSION,
        )
        self.ops.telemetry("retrieval", "SUCCESS", started, trace_id=trace_id, results=len(results))
        return {
            "trace_id": trace_id,
            "query": query,
            "mode": "keyword",
            "contract_version": self.contract_versions["retrieval"],
            "results": results,
        }

    def search_entities(
        self,
        query: str,
        limit: int,
        access: AccessContext,
        as_of: CanonicalDatetime | None = None,
    ) -> dict:
        started = perf_counter()
        search_query = literal_fulltext_query(query)
        candidate_limit = min(max(limit * 5, 25), 100)
        as_of_value = as_of.isoformat() if as_of else None
        try:
            with self.driver.session(database=self.database) as session:
                rows = session.run(
                    """
                    CALL db.index.fulltext.queryNodes('entity_name_fulltext', $search_query)
                    YIELD node, score
                    WHERE node.workspace_id=$workspace_id
                    WITH node AS entity, score
                    ORDER BY score DESC LIMIT $candidate_limit
                    MATCH (assertion:Assertion)-[:SUBJECT|OBJECT]->(entity)
                    WHERE $as_of IS NULL OR (
                        assertion.status IN ['VERIFIED', 'SUPERSEDED']
                        AND (assertion.valid_from IS NULL OR
                             datetime(replace(toString(assertion.valid_from), ' ', 'T'))
                                <= datetime($as_of))
                        AND (assertion.valid_to IS NULL OR
                             datetime($as_of) <
                                datetime(replace(toString(assertion.valid_to), ' ', 'T')))
                    )
                    MATCH (chunk:Chunk)-[:EVIDENCE_FOR]->(assertion)
                    MATCH (:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(document:Document)
                          -[:HAS_VERSION]->(:DocumentVersion)-[:HAS_CHUNK]->(chunk)
                    MATCH (document)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                    WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                          any(principal IN coalesce(auth_version.acl, [])
                              WHERE principal IN $principals)
                    WITH entity, score, assertion, count(DISTINCT chunk) AS accessible_count
                    WHERE accessible_count =
                          COUNT { (evidence:Chunk)-[:EVIDENCE_FOR]->(assertion) }
                    WITH entity, max(score) AS score,
                         count(DISTINCT assertion) AS accessible_assertion_count
                    RETURN entity.id AS id, entity.name AS name,
                           entity.entity_type AS entity_type, entity.aliases AS aliases,
                           entity.status AS status, score, accessible_assertion_count
                    ORDER BY score DESC, name, id LIMIT $limit
                    """,
                    search_query=search_query,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    candidate_limit=candidate_limit,
                    limit=limit,
                    as_of=as_of_value,
                )
                results = [row.data() for row in rows]
        except Exception as exc:
            error_id = self.ops.error(
                "entity_search",
                exc,
                safe_message="entity search failed",
                query_hash=content_hash(query),
                workspace_id=access.workspace_id,
            )
            self.ops.telemetry("entity_search", "ERROR", started, error_id=error_id)
            raise
        trace_id = self.ops.retrieval_trace(
            query,
            "graph",
            started,
            [result["id"] for result in results],
            contract_version=self.contract_versions["retrieval"],
            limit=limit,
            workspace_id=access.workspace_id,
            principal_count=len(access.principals),
            access_fingerprint=access_fingerprint(access.workspace_id, access.principals),
            graph_ranker="entity-fulltext-v1",
            as_of=as_of_value,
        )
        self.ops.telemetry(
            "entity_search", "SUCCESS", started, trace_id=trace_id, results=len(results)
        )
        return {
            "trace_id": trace_id,
            "query": query,
            "mode": "graph",
            "contract_version": self.contract_versions["retrieval"],
            "results": results,
        }

    def entity(
        self,
        entity_id: str,
        access: AccessContext | None = None,
        as_of: CanonicalDatetime | None = None,
    ) -> dict | None:
        as_of_value = as_of.isoformat() if as_of else None
        with self.driver.session(database=self.database) as session:
            if access is not None:
                row = session.run(
                    """
                    MATCH (e:Entity {id:$id, workspace_id:$workspace_id})
                    MATCH (a:Assertion)-[:SUBJECT|OBJECT]->(e)
                    MATCH (c:Chunk)-[:EVIDENCE_FOR]->(a)
                    MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(d:Document)
                          -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(c)
                    MATCH (d)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                    WHERE (auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                           any(principal IN coalesce(auth_version.acl, [])
                               WHERE principal IN $principals))
                      AND ($as_of IS NULL OR (
                          a.status IN ['VERIFIED', 'SUPERSEDED']
                          AND (a.valid_from IS NULL OR
                               datetime(replace(toString(a.valid_from), ' ', 'T')) <= datetime($as_of))
                          AND (a.valid_to IS NULL OR
                               datetime($as_of) < datetime(replace(toString(a.valid_to), ' ', 'T')))
                      ))
                    RETURN properties(e) AS entity,
                        collect(DISTINCT {
                            assertion:properties(a), chunk_id:c.id,
                            document_id:d.id, document_version_id:evidence_version.id,
                            authorization:{owner:evidence_version.owner,
                                           visibility:evidence_version.visibility,
                                           acl:evidence_version.acl},
                            current_authorization:{owner:auth_version.owner,
                                                   visibility:auth_version.visibility,
                                                   acl:auth_version.acl}
                        }) AS evidence
                    """,
                    id=entity_id,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    as_of=as_of_value,
                ).single()
                return row.data() if row else None
            row = session.run(
                """
                MATCH (e:Entity {id:$id})
                OPTIONAL MATCH (a:Assertion)-[:SUBJECT|OBJECT]->(e)
                WHERE $as_of IS NULL OR (
                    a.status IN ['VERIFIED', 'SUPERSEDED']
                    AND (a.valid_from IS NULL OR
                         datetime(replace(toString(a.valid_from), ' ', 'T')) <= datetime($as_of))
                    AND (a.valid_to IS NULL OR
                         datetime($as_of) < datetime(replace(toString(a.valid_to), ' ', 'T')))
                )
                OPTIONAL MATCH (c:Chunk)-[:EVIDENCE_FOR]->(a)
                OPTIONAL MATCH (v:DocumentVersion)-[:HAS_CHUNK]->(c)
                OPTIONAL MATCH (d:Document)-[:HAS_VERSION]->(v)
                RETURN properties(e) AS entity,
                    collect(DISTINCT {
                        assertion:properties(a), chunk_id:c.id,
                        document_id:d.id, document_version_id:v.id,
                        authorization:{owner:v.owner, visibility:v.visibility, acl:v.acl}
                    }) AS evidence
                """,
                id=entity_id,
                as_of=as_of_value,
            ).single()
            return row.data() if row else None

    def neighbors(
        self,
        entity_id: str,
        limit: int = 50,
        access: AccessContext | None = None,
        as_of: CanonicalDatetime | None = None,
    ) -> list[dict]:
        as_of_value = as_of.isoformat() if as_of else None
        with self.driver.session(database=self.database) as session:
            if access is not None:
                rows = session.run(
                    """
                    MATCH (e:Entity {id:$id, workspace_id:$workspace_id})
                          -[r:RELATED]-(other:Entity {workspace_id:$workspace_id})
                    MATCH (a:Assertion {id:r.assertion_id, workspace_id:$workspace_id})
                    WHERE $as_of IS NULL OR (
                        a.status IN ['VERIFIED', 'SUPERSEDED']
                        AND (a.valid_from IS NULL OR
                             datetime(replace(toString(a.valid_from), ' ', 'T')) <= datetime($as_of))
                        AND (a.valid_to IS NULL OR
                             datetime($as_of) < datetime(replace(toString(a.valid_to), ' ', 'T')))
                    )
                    MATCH (c:Chunk)-[:EVIDENCE_FOR]->(a)
                    MATCH (w:Workspace {id:$workspace_id})-[:OWNS_SOURCE]->(:Source)
                          -[:HAS_DOCUMENT]->(d:Document)
                          -[:HAS_VERSION]->(evidence_version:DocumentVersion)-[:HAS_CHUNK]->(c)
                    MATCH (d)-[:CURRENT_VERSION]->(auth_version:DocumentVersion)
                    WHERE auth_version.visibility='PUBLIC' OR auth_version.owner IN $principals OR
                          any(principal IN coalesce(auth_version.acl, [])
                              WHERE principal IN $principals)
                    RETURN properties(other) AS entity, r.predicate AS predicate,
                        r.assertion_id AS assertion_id, c.id AS evidence_chunk_id,
                        {owner:evidence_version.owner, visibility:evidence_version.visibility,
                         acl:evidence_version.acl} AS authorization,
                        {owner:auth_version.owner, visibility:auth_version.visibility,
                         acl:auth_version.acl} AS current_authorization
                    LIMIT $limit
                    """,
                    id=entity_id,
                    workspace_id=access.workspace_id,
                    principals=access.principals,
                    limit=limit,
                    as_of=as_of_value,
                )
                return [row.data() for row in rows]
            rows = session.run(
                """
                MATCH (e:Entity {id:$id})-[r:RELATED]-(other:Entity)
                OPTIONAL MATCH (a:Assertion {id:r.assertion_id})
                WHERE $as_of IS NULL OR (
                    a.status IN ['VERIFIED', 'SUPERSEDED']
                    AND (a.valid_from IS NULL OR
                         datetime(replace(toString(a.valid_from), ' ', 'T')) <= datetime($as_of))
                    AND (a.valid_to IS NULL OR
                         datetime($as_of) < datetime(replace(toString(a.valid_to), ' ', 'T')))
                )
                OPTIONAL MATCH (c:Chunk)-[:EVIDENCE_FOR]->(a)
                OPTIONAL MATCH (v:DocumentVersion)-[:HAS_CHUNK]->(c)
                RETURN properties(other) AS entity, r.predicate AS predicate,
                    r.assertion_id AS assertion_id, c.id AS evidence_chunk_id,
                    {owner:v.owner, visibility:v.visibility, acl:v.acl} AS authorization
                LIMIT $limit
                """,
                id=entity_id,
                limit=limit,
                as_of=as_of_value,
            )
            return [r.data() for r in rows]
