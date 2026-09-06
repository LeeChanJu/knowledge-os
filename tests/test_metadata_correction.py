import json

import pytest
from test_v01_neo4j_regressions import ROOT, manifest, query, text_request
from test_v01_neo4j_regressions import graph as graph  # noqa: PLC0414 - export shared fixture

from knowledge_os.doctor import audit_metadata_hashes, run_doctor
from knowledge_os.graph import source_metadata_fingerprint
from knowledge_os.metadata_correction import apply_correction, plan_correction


def metadata_check(graph):
    return next(
        c
        for c in run_doctor(graph, ROOT / "migrations")["checks"]
        if c["name"] == "immutable_metadata_hash_matches_persisted_version"
    )


def snapshot(graph):
    return {
        "nodes": query(
            graph,
            "MATCH (n) RETURN n.id AS id, labels(n) AS labels, "
            "properties(n) AS properties ORDER BY id",
        ),
        "edges": query(
            graph,
            "MATCH (a)-[r]->(b) RETURN a.id AS a, type(r) AS type, "
            "b.id AS b, properties(r) AS properties ORDER BY a, type, b",
        ),
    }


@pytest.mark.parametrize("uri", [None, "https://fixture.invalid/문서?x=é"])
def test_ingestion_paths_share_exact_persisted_metadata_contract(graph, uri):
    title = '문서 "제목" é'
    graph.ingest_text(text_request(title=title, document_source_uri=uri))
    record = manifest().records[0].model_dump(mode="json")
    record.update(title=title, document_source_uri=uri)
    graph.ingest_manifest(manifest(records=[record]))
    rows = query(
        graph,
        "MATCH (v:DocumentVersion) RETURN v.title AS title, "
        "v.source_uri AS uri, v.source_metadata_hash AS hash",
    )
    assert len(rows) == 2
    assert rows[0] == rows[1]
    assert rows[0]["uri"] == (uri or "https://fixture.invalid/folder")
    assert metadata_check(graph)["status"] == "PASS"


def test_doctor_hash_check_does_not_trust_ingestion_hasher(monkeypatch):
    row = {
        "id": "version",
        "title": "title",
        "source_uri": None,
        "source_metadata_hash": source_metadata_fingerprint("title", None),
    }
    monkeypatch.setattr("knowledge_os.graph.source_metadata_fingerprint", lambda *a: "bad")
    assert audit_metadata_hashes([row])["status"] == "PASS"
    row["source_metadata_hash"] = "0" * 64
    assert audit_metadata_hashes([row]) == {
        "name": "immutable_metadata_hash_matches_persisted_version",
        "status": "FAIL",
        "violations": 1,
        "samples": ["version"],
    }


def corrupt_history(graph):
    first = graph.ingest_text(text_request())
    graph.ingest_text(
        text_request(
            source_version="v2",
            content="New evidence.",
            expected_current_version_id=first.document_version_id,
        )
    )
    query(
        graph,
        "MATCH (v:DocumentVersion) SET v.source_metadata_hash=$bad",
        bad=source_metadata_fingerprint("Fixture", "https://fixture.invalid/folder"),
    )


def apply(graph, plan):
    return apply_correction(
        graph.driver, graph.database, plan, actor="local-user", reason="F1 reviewed correction"
    )


def test_correction_preserves_history_and_audits_exactly_once(graph):
    corrupt_history(graph)
    before = snapshot(graph)
    assert metadata_check(graph)["violations"] == 2
    plan = plan_correction(graph.driver, graph.database)
    assert snapshot(graph) == before  # Planning and Doctor are read-only.
    assert plan_correction(graph.driver, graph.database) == plan
    assert len(plan["records"]) == 2
    assert apply(graph, plan)["applied"] == 2
    after = snapshot(graph)
    assert apply(graph, plan)["already_applied"] == 2
    assert snapshot(graph) == after
    expected = {r["version_id"]: r["after_hash"] for r in plan["records"]}
    for node in before["nodes"]:
        if node["id"] in expected:
            node["properties"]["source_metadata_hash"] = expected[node["id"]]
    originals = {node["id"] for node in before["nodes"]}
    assert [n for n in after["nodes"] if n["id"] in originals] == before["nodes"]
    assert [e for e in after["edges"] if e["b"] in originals] == before["edges"]
    events = [n["properties"] for n in after["nodes"] if n["id"] not in originals]
    assert len(events) == 2
    for event in events:
        record = next(r for r in plan["records"] if r["version_id"] == event["document_version_id"])
        assert json.loads(event["metadata_snapshot"]) == record
        assert event["before_hash"] == record["before_hash"]
        assert event["after_hash"] == record["after_hash"]
        assert event["actor"] == "local-user"
        assert event["reason"] == "F1 reviewed correction"
        assert event["recorded_at"]
    assert plan_correction(graph.driver, graph.database)["records"] == []
    assert run_doctor(graph, ROOT / "migrations")["status"] == "ok"


@pytest.mark.parametrize("field,value", [("title", "changed"), ("source_metadata_hash", "1" * 64)])
def test_stale_correction_rolls_back_prior_changes_and_audit(graph, field, value):
    corrupt_history(graph)
    plan = plan_correction(graph.driver, graph.database)
    last = plan["records"][-1]["version_id"]
    query(graph, f"MATCH (v:DocumentVersion {{id:$id}}) SET v.{field}=$value", id=last, value=value)
    before = snapshot(graph)
    with pytest.raises(ValueError, match="no longer matches"):
        apply(graph, plan)
    assert snapshot(graph) == before


def test_correction_rejects_tampered_or_wrong_database_plan(graph):
    corrupt_history(graph)
    plan = plan_correction(graph.driver, graph.database)
    before = snapshot(graph)
    plan["records"][0]["after_hash"] = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        apply(graph, plan)
    plan = plan_correction(graph.driver, graph.database)
    with pytest.raises(ValueError, match="database"):
        apply_correction(graph.driver, "different-database", plan, actor="actor", reason="reason")
    assert snapshot(graph) == before
