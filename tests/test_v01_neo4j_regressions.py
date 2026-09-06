"""Opt-in REAL Neo4j regressions; never use the configured application database.

Run: KNOWLEDGE_OS_TEST_NEO4J=1 python -m pytest tests/test_v01_neo4j_regressions.py
Requires CREATE/DROP DATABASE on the existing local Enterprise DBMS. Each test
creates a fresh UUID database and drops ONLY that database in its finalizer.
No production data, external provider APIs, or global service caches are used.
"""

import hashlib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from neo4j import GraphDatabase

from knowledge_os import models
from knowledge_os.config import Settings
from knowledge_os.contracts import ContractRegistry
from knowledge_os.doctor import run_doctor
from knowledge_os.google_drive_connector import DriveFileSnapshot, build_manifest
from knowledge_os.graph import GraphStore
from knowledge_os.models import (
    AccessContext,
    ActionCreate,
    ActionExecutionClaimCreate,
    ProposalCreate,
    SyncManifest,
    TextIngestionRequest,
)
from knowledge_os.ontology import Ontology
from knowledge_os.ops import OpsStore

ROOT = Path(__file__).resolve().parents[1]
ACCESS = AccessContext()


@pytest.fixture
def graph(tmp_path):
    if os.environ.get("KNOWLEDGE_OS_TEST_NEO4J") != "1":
        pytest.skip("set KNOWLEDGE_OS_TEST_NEO4J=1 to create isolated real Neo4j databases")
    settings = Settings()
    database = "kos-v01-regression-" + uuid4().hex
    assert database not in {settings.neo4j_database, "neo4j", "system"}
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        connection_timeout=5,
    )
    store = None
    created = False
    try:
        with driver.session(database="system") as admin:
            existing = admin.run("SHOW DATABASES YIELD name RETURN name").value("name")
            assert database not in existing
            # The identifier is generated internally from a constant + UUID hex.
            admin.run(f"CREATE DATABASE `{database}` WAIT 30 SECONDS").consume()
            created = True
        store = GraphStore(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
            database,
            OpsStore(tmp_path / "ops.db"),
            1536,
            ContractRegistry.load(ROOT / "config/contracts.yaml").contracts,
        )
        store.migrate(ROOT / "migrations")
        with store.driver.session(database=database) as session:
            session.run("CALL db.awaitIndexes(30)").consume()
        assert run_doctor(store, ROOT / "migrations")["status"] == "ok"
        yield store
    finally:
        if store is not None:
            store.close()
        try:
            if created:
                assert database.startswith("kos-v01-regression-")
                with driver.session(database="system") as admin:
                    admin.run(f"DROP DATABASE `{database}` DESTROY DATA WAIT 30 SECONDS").consume()
                    remaining = admin.run("SHOW DATABASES YIELD name RETURN name").value("name")
                    assert database not in remaining
        finally:
            driver.close()


def query(graph, cypher, **params):
    assert graph.database.startswith("kos-v01-regression-")
    with graph.driver.session(database=graph.database) as session:
        return session.run(cypher, **params).data()


def text_request(**updates):
    return TextIngestionRequest.model_validate(
        {
            "source_external_id": "source",
            "document_external_id": "document",
            "source_uri": "https://fixture.invalid/folder",
            "document_source_uri": "https://fixture.invalid/document",
            "source_version": "v1",
            "title": "Fixture",
            "content": "Evidence fixture.",
            **updates,
        }
    )


def manifest(cursor="one", previous=None, records=None):
    return SyncManifest.model_validate(
        {
            "source_type": "file",
            "source_external_id": "manifest-source",
            "source_uri": "https://fixture.invalid/folder",
            "connector_id": "fixture",
            "sync_run_id": "run-" + cursor,
            "cursor": cursor,
            "expected_previous_cursor": previous,
            "records": records
            if records is not None
            else [
                {
                    "operation": "UPSERT",
                    "document_external_id": "a",
                    "source_version": "v1",
                    "title": "Fixture",
                    "content": "Evidence fixture.",
                    "document_source_uri": "https://fixture.invalid/document",
                }
            ],
        }
    )


def seed_proposal(graph, **change_updates):
    graph.ingest_text(text_request())
    chunk = query(graph, "MATCH (c:Chunk) RETURN c.id AS id")[0]["id"]
    return graph.create_proposal(
        ProposalCreate.model_validate(
            {
                "changes": [
                    {
                        "subject": {"name": "Fixture", "entity_type": "Concept"},
                        "predicate": "RELATED_TO",
                        "object": {"name": "Other", "entity_type": "Concept"},
                        "evidence_chunk_id": chunk,
                        **change_updates,
                    }
                ]
            }
        )
    )["id"]


def approve(graph, proposal):
    return graph.approve_proposal(
        proposal,
        "local-user",
        "fixture review",
        Ontology.load(ROOT / "config/ontology.yaml"),
        ACCESS,
    )


def race(*operations):
    barrier = Barrier(len(operations))

    def invoke(operation):
        barrier.wait(timeout=20)
        try:
            return ("ok", operation())
        except (ValueError, KeyError, PermissionError) as exc:
            return ("conflict", type(exc).__name__)

    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        futures = [pool.submit(invoke, operation) for operation in operations]
        return [future.result(timeout=60) for future in futures]


def test_f1_manifest_hash_matches_immutable_document_metadata(graph):
    graph.ingest_manifest(manifest())
    row = query(
        graph,
        "MATCH (v:DocumentVersion) RETURN v.title AS title, "
        "v.source_uri AS uri, v.source_metadata_hash AS hash",
    )[0]
    expected = hashlib.sha256(
        json.dumps(
            {"title": row["title"], "source_uri": row["uri"]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    assert row["hash"] == expected


def test_f1_manifest_rejects_document_uri_drift_under_same_revision(graph):
    first = manifest()
    graph.ingest_manifest(first)
    record = first.records[0].model_dump(mode="json")
    record["document_source_uri"] = "https://fixture.invalid/changed-document"
    with pytest.raises(ValueError):
        graph.ingest_manifest(manifest("two", "one", [record]))
    assert (
        query(graph, "MATCH (s:Source) RETURN s.last_sync_cursor AS cursor")[0]["cursor"] == "one"
    )


def test_f2_replay_after_graph_commit_before_checkpoint_file(graph, monkeypatch):
    class Clock(datetime):
        instant = datetime(2026, 9, 1, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)

    monkeypatch.setattr(models, "datetime", Clock)
    options = {
        "workspace_id": "personal",
        "folder_id": "folder",
        "connection_id": "connection",
        "connector_id": "drive",
    }
    snapshot = DriveFileSnapshot(
        "file",
        "Fixture",
        "text/plain",
        "2026-09-01T00:00:00Z",
        "https://fixture.invalid/file",
        "Fixture body",
        "local-user",
        "PRIVATE",
        (),
    )
    initial, saved_state = build_manifest([snapshot], {"version": "1", "files": {}}, **options)
    graph.ingest_manifest(initial)
    deletion, _ = build_manifest([], saved_state, **options)
    graph.ingest_manifest(deletion)
    # Simulate process loss: keep ONLY the old on-disk connector checkpoint.
    Clock.instant = datetime(2026, 9, 2, tzinfo=UTC)
    retry, _ = build_manifest([], saved_state, **options)
    result = graph.ingest_manifest(retry)
    assert result["unchanged"] is True
    assert query(graph, "MATCH (d:Document) RETURN d.status AS status")[0]["status"] == "DELETED"
    assert (
        query(graph, "MATCH (e:Event {event_type:'SOURCE_DOCUMENT_DELETED'}) RETURN count(e) AS n")[
            0
        ]["n"]
        == 1
    )


def test_f3_doctor_accepts_proposal_with_current_governance_contract(graph):
    proposal = seed_proposal(graph)
    assert (
        query(
            graph, "MATCH (p:Proposal {id:$id}) RETURN p.contract_version AS version", id=proposal
        )[0]["version"]
        == graph.contract_versions["governance"]
    )
    report = run_doctor(graph, ROOT / "migrations")
    assert report["status"] == "ok", [c for c in report["checks"] if c["status"] != "PASS"]


def test_f3_doctor_detects_corrupted_metadata_hash(graph):
    graph.ingest_text(text_request())
    assert run_doctor(graph, ROOT / "migrations")["status"] == "ok"
    query(graph, "MATCH (v:DocumentVersion) SET v.source_metadata_hash=$bad", bad="0" * 64)
    assert run_doctor(graph, ROOT / "migrations")["status"] == "error"


@pytest.mark.parametrize(
    "kind,name",
    [
        ("CONSTRAINT", "source_id_unique"),
        ("CONSTRAINT", "action_contract_version_required"),
        ("INDEX", "chunk_text_fulltext"),
        ("INDEX", "entity_name_fulltext"),
        ("INDEX", "action_execution_claim_status"),
        ("INDEX", "chunk_embedding_vector"),
    ],
)
def test_f3_doctor_detects_missing_schema_object(graph, kind, name):
    # Constants above only; this database is dropped after the test, not repaired.
    query(graph, f"DROP {kind} {name}")
    assert run_doctor(graph, ROOT / "migrations")["status"] == "error", name


def test_f3_doctor_detects_multi_node_supersession_cycle(graph):
    first = graph.ingest_text(text_request())
    graph.ingest_text(
        text_request(
            source_version="v2",
            content="Changed evidence.",
            expected_current_version_id=first.document_version_id,
        )
    )
    assert run_doctor(graph, ROOT / "migrations")["status"] == "ok"
    query(
        graph,
        "MATCH (new:DocumentVersion)-[:SUPERSEDES]->(old:DocumentVersion) "
        "CREATE (old)-[:SUPERSEDES]->(new)",
    )
    assert run_doctor(graph, ROOT / "migrations")["status"] == "error"


def test_manifest_failure_rolls_back_prior_record_and_checkpoint(graph):
    graph.ingest_manifest(manifest())
    before = query(graph, "MATCH (v:DocumentVersion) RETURN count(v) AS n")[0]["n"]
    bad = manifest(
        "two",
        "one",
        [
            {
                "operation": "UPSERT",
                "document_external_id": "a",
                "source_version": "v2",
                "title": "Changed",
                "content": "Changed evidence",
            },
            {
                "operation": "TOMBSTONE",
                "document_external_id": "z-unknown",
                "source_version": "deleted",
                "deleted_at": "2026-09-01T00:00:00Z",
            },
        ],
    )
    with pytest.raises((KeyError, ValueError)):
        graph.ingest_manifest(bad)
    assert query(graph, "MATCH (v:DocumentVersion) RETURN count(v) AS n")[0]["n"] == before
    assert (
        query(graph, "MATCH (s:Source) RETURN s.last_sync_cursor AS cursor")[0]["cursor"] == "one"
    )


def test_concurrent_stale_document_updates_have_one_winner(graph):
    first = graph.ingest_text(text_request())
    requests = [
        text_request(
            source_version=f"v{i}",
            content=f"Update {i}",
            expected_current_version_id=first.document_version_id,
        )
        for i in (2, 3)
    ]
    outcomes = race(*(lambda request=r: graph.ingest_text(request) for r in requests))
    assert sorted(outcome[0] for outcome in outcomes) == ["conflict", "ok"]
    assert (
        query(graph, "MATCH (:Document)-[r:CURRENT_VERSION]->() RETURN count(r) AS n")[0]["n"] == 1
    )
    assert query(graph, "MATCH (v:DocumentVersion) RETURN count(v) AS n")[0]["n"] == 2


def test_concurrent_approve_reject_has_one_immutable_outcome(graph):
    proposal = seed_proposal(graph)
    outcomes = race(
        lambda: approve(graph, proposal),
        lambda: graph.reject_proposal(
            proposal,
            "local-user",
            "fixture rejection",
            ACCESS,
        ),
    )
    assert sorted(outcome[0] for outcome in outcomes) == ["conflict", "ok"]
    row = query(
        graph,
        "MATCH (p:Proposal {id:$id}) "
        "OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(a:Approval) "
        "OPTIONAL MATCH (p)-[:PROMOTED]->(n) "
        "RETURN p.status AS status, count(DISTINCT a) AS approvals, "
        "count(DISTINCT n) AS promoted",
        id=proposal,
    )[0]
    assert row["approvals"] == 1
    assert row["promoted"] == (1 if row["status"] == "APPROVED" else 0)


@pytest.mark.parametrize(
    "replacement_start,old_end",
    [("2026-09-01T00:00:00Z", None), ("2026-09-20T00:00:00Z", "2026-09-30T00:00:00Z")],
    ids=["inverted-old-interval", "overlapping-intervals"],
)
def test_supersession_cannot_invert_or_overlap_validity(graph, replacement_start, old_end):
    old_proposal = seed_proposal(graph, valid_from="2026-09-10T00:00:00Z", valid_to=old_end)
    approve(graph, old_proposal)
    old = query(graph, "MATCH (a:Assertion) RETURN a.id AS id")[0]["id"]
    new_proposal = seed_proposal(graph, valid_from=replacement_start, supersedes_assertion_id=old)
    try:
        approve(graph, new_proposal)
    except ValueError:
        # Rejecting an invalid temporal transition atomically is acceptable.
        assert (
            query(graph, "MATCH (p:Proposal {id:$id}) RETURN p.status AS status", id=new_proposal)[
                0
            ]["status"]
            == "PROPOSED"
        )
        return
    row = query(
        graph,
        "MATCH (new:Assertion)-[:SUPERSEDES]->(old:Assertion) "
        "RETURN datetime(old.valid_from)<=datetime(old.valid_to) AS ordered, "
        "datetime(old.valid_to)<=datetime(new.valid_from) AS nonoverlapping",
    )[0]
    assert row == {"ordered": True, "nonoverlapping": True}


def action_request():
    return ActionCreate(
        action_type="REGRESSION",
        target="fixture",
        requested_by="local-user",
        idempotency_key="fixture",
        review_principals=["local-user"],
        execution_principals=["local-connector"],
    )


def test_action_execution_claim_is_exclusive(graph):
    action = graph.create_action(action_request())["id"]
    graph.decide_action(action, "APPROVED", "local-user", "fixture", ACCESS)
    claims = [
        ActionExecutionClaimCreate(
            executed_by="local-connector",
            connector="fixture",
            authorization_ref="fixture",
            policy_version="action-policy-v1",
            idempotency_key=f"attempt-{i}",
            access=AccessContext(principals=["local-connector"]),
        )
        for i in (1, 2)
    ]
    outcomes = race(*(lambda claim=c: graph.claim_action_execution(action, claim) for c in claims))
    assert sorted(outcome[0] for outcome in outcomes) == ["conflict", "ok"]
    assert (
        query(graph, "MATCH (c:ActionExecutionClaim {status:'CLAIMED'}) RETURN count(c) AS n")[0][
            "n"
        ]
        == 1
    )


def test_f8_retry_reconciles_audit_missing_after_graph_commit(graph, monkeypatch):
    request = action_request()
    original = graph.ops.audit

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError("injected audit-store outage")

    monkeypatch.setattr(graph.ops, "audit", unavailable)
    failure = None
    try:
        graph.create_action(request)
    except Exception as exc:  # noqa: BLE001 - independently inspect post-commit state
        failure = exc
    assert query(graph, "MATCH (a:Action) RETURN count(a) AS n")[0]["n"] == 1, repr(failure)
    monkeypatch.setattr(graph.ops, "audit", original)
    result = graph.create_action(request)
    graph.create_action(request)  # Reconciliation must itself be idempotent.
    with graph.ops.connect() as db:
        count = db.execute(
            "SELECT count(*) FROM audit_log WHERE action='CREATE_ACTION' AND target=?",
            (result["id"],),
        ).fetchone()[0]
    assert count == 1, "Committed creation must not permanently lose its operational audit"


def test_f8_committed_mutation_is_not_reported_as_unqualified_sqlite_failure(graph, monkeypatch):
    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError("injected telemetry-store outage")

    monkeypatch.setattr(graph.ops, "telemetry", unavailable)
    error = None
    try:
        graph.ingest_text(text_request())
    except Exception as exc:  # noqa: BLE001 - distinguish committed outcome from any error
        error = exc
    assert query(graph, "MATCH (v:DocumentVersion) RETURN count(v) AS n")[0]["n"] == 1
    # Either return committed success (possibly with a warning), or explicitly
    # distinguish a committed result on the exception. A bare storage failure
    # gives callers no way to distinguish rollback from post-commit failure.
    assert error is None or getattr(error, "committed", False) is True, repr(error)
