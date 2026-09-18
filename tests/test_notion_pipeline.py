"""Pipeline failure/replay boundaries against disposable real Neo4j databases."""

import pytest
from test_v01_neo4j_regressions import ROOT, graph, query, text_request  # noqa: F401

from knowledge_os.doctor import run_doctor
from knowledge_os.models import AccessContext
from knowledge_os.notion_pipeline import Extraction, Pipeline
from knowledge_os.ontology import Ontology
from knowledge_os.prompts import PromptRegistry


def setup(graph, tmp_path):  # noqa: F811
    request = text_request(
        source_type="notion_page_tree",
        source_external_id="root",
        owner="notion:connection:fixture",
        acl=["notion:connection:fixture"],
        content="Knowledge OS uses Neo4j. This is verified source text.",
    )
    graph.ingest_text(request)
    worker = Pipeline(
        graph,
        Ontology.load(ROOT / "config/ontology.yaml"),
        PromptRegistry.load(ROOT / "config/prompts.yaml"),
        tmp_path / "state.json",
        "root",
        "fixture",
        "personal",
    )
    job = worker.prepare()["jobs"][0]
    chunk = job["chunks"][0]["id"]
    result = Extraction.model_validate(
        {
            "job_id": job["job_id"],
            "candidates": [
                {
                    "kind": "ASSERTION",
                    "payload": {
                        "subject": {"name": "Knowledge OS", "entity_type": "Project"},
                        "predicate": "USES",
                        "object": {"name": "Neo4j", "entity_type": "Technology"},
                        "evidence_chunk_id": chunk,
                    },
                    "quotes": {chunk: "Knowledge OS uses Neo4j."},
                }
            ],
        }
    )
    return worker, request, result


def test_replay_stays_pending_until_human_approval(graph, tmp_path):  # noqa: F811
    worker, _, result = setup(graph, tmp_path)
    receipt = worker.apply(result)
    assert receipt[0]["status"] == "PROPOSED"
    assert worker.apply(result) == receipt
    assert worker.prepare()["jobs"] == []
    assert query(graph, "MATCH (p:Proposal) RETURN count(p) AS n")[0]["n"] == 1
    assert query(graph, "MATCH (a:Assertion) RETURN count(a) AS n")[0]["n"] == 0
    assert query(graph, "MATCH (a:Approval) RETURN count(a) AS n")[0]["n"] == 0
    graph.approve_proposal(
        receipt[0]["id"],
        "human:fixture",
        "explicit test reviewer",
        worker.ontology,
        AccessContext(principals=["human:fixture", "notion:connection:fixture"]),
    )
    assert query(graph, "MATCH (a:Assertion) RETURN count(a) AS n")[0]["n"] == 1
    assert worker.apply(result) == receipt


def test_crash_after_graph_commit_reuses_sealed_payload(graph, tmp_path, monkeypatch):  # noqa: F811
    worker, _, result = setup(graph, tmp_path)
    original = graph.create_proposal

    def crash(payload):
        original(payload)
        raise RuntimeError("simulated interruption after commit")

    monkeypatch.setattr(graph, "create_proposal", crash)
    with pytest.raises(RuntimeError):
        worker.apply(result)
    monkeypatch.setattr(graph, "create_proposal", original)
    restarted = Pipeline(
        graph, worker.ontology, worker.prompts, worker.path, "root", "fixture", "personal"
    )
    assert restarted.prepare()["jobs"] == []
    assert query(graph, "MATCH (p:Proposal) RETURN count(p) AS n")[0]["n"] == 1
    altered = result.model_copy(deep=True)
    altered.candidates[0].payload["confidence"] = 0.7
    with pytest.raises(ValueError, match="sealed"):
        restarted.apply(altered)


@pytest.mark.parametrize("invalid", ["quote", "actor", "ontology", "other_chunk"])
def test_invalid_output_never_persists(graph, tmp_path, invalid):  # noqa: F811
    worker, _, result = setup(graph, tmp_path)
    candidate = result.candidates[0]
    if invalid == "quote":
        candidate.quotes = {key: "invented evidence" for key in candidate.quotes}
    elif invalid == "actor":
        candidate.payload["created_by"] = "human:owner"
    elif invalid == "ontology":
        candidate.payload["predicate"] = "INVENTED"
    else:
        candidate.payload["evidence_chunk_id"] = "another-document"
        candidate.quotes = {"another-document": "Knowledge OS uses Neo4j."}
    with pytest.raises(ValueError):
        worker.apply(result)
    assert query(graph, "MATCH (p:Proposal) RETURN count(p) AS n")[0]["n"] == 0


@pytest.mark.parametrize("revoked", [False, True])
def test_changed_or_revoked_evidence_requires_new_preparation(graph, tmp_path, revoked):  # noqa: F811
    worker, request, result = setup(graph, tmp_path)
    old = next(iter(worker.state["jobs"].values()))["version_id"]
    graph.ingest_text(
        request.model_copy(
            update={
                "source_version": "v2",
                "expected_current_version_id": old,
                "content": "Knowledge OS now uses a different tool.",
                **({"owner": "other", "acl": []} if revoked else {}),
            }
        )
    )
    with pytest.raises(ValueError):
        worker.apply(result)
    assert query(graph, "MATCH (p:Proposal) RETURN count(p) AS n")[0]["n"] == 0
    jobs = worker.prepare()["jobs"]
    assert len(jobs) == (0 if revoked else 1)
    if jobs:
        assert jobs[0]["job_id"] != result.job_id


def test_empty_extraction_is_checkpointed_without_fake_proposals(graph, tmp_path):  # noqa: F811
    worker, _, result = setup(graph, tmp_path)
    result.candidates = []
    with pytest.raises(ValueError, match="explanation"):
        worker.apply(result)
    result.no_candidates_reason = "Navigation-only page, no substantive supported claim."
    assert worker.apply(result) == []
    assert worker.prepare()["jobs"] == []
    assert query(graph, "MATCH (p:Proposal) RETURN count(p) AS n")[0]["n"] == 0


@pytest.mark.parametrize("kind", ["DECISION", "EVENT"])
def test_temporal_candidates_use_governed_proposals(graph, tmp_path, kind):  # noqa: F811
    worker, request, old_result = setup(graph, tmp_path)
    version = worker.state["jobs"][old_result.job_id]["version_id"]
    evidence = "Decision on 2026-09-19: use Neo4j. Launch occurred at 2026-09-19T00:00:00Z."
    graph.ingest_text(
        request.model_copy(
            update={
                "source_version": "v2",
                "expected_current_version_id": version,
                "content": evidence,
            }
        )
    )
    job = worker.prepare()["jobs"][0]
    chunk = job["chunks"][0]["id"]
    payload = {"title": "Fixture", "evidence_chunk_ids": [chunk]}
    if kind == "DECISION":
        payload.update(statement="Use Neo4j", decided_on="2026-09-19")
    else:
        payload.update(
            description="Launch occurred", event_type="LAUNCH", occurred_at="2026-09-19T00:00:00Z"
        )
    result = Extraction.model_validate(
        {
            "job_id": job["job_id"],
            "candidates": [{"kind": kind, "payload": payload, "quotes": {chunk: evidence}}],
        }
    )
    assert worker.apply(result)[0]["status"] == "PROPOSED"
    assert query(graph, "MATCH (p:Proposal) RETURN p.proposal_type AS kind")[0]["kind"] == kind
    assert query(graph, "MATCH (a:Approval) RETURN count(a) AS n")[0]["n"] == 0


def test_doctor_accepts_current_governance_but_rejects_unknown_contract(graph, tmp_path):  # noqa: F811
    worker, _, result = setup(graph, tmp_path)
    worker.apply(result)
    assert run_doctor(graph, ROOT / "migrations")["status"] == "ok"
    query(graph, "MATCH (p:Proposal) SET p.contract_version='governance-unknown'")
    checks = run_doctor(graph, ROOT / "migrations")["checks"]
    check = next(c for c in checks if c["name"] == "proposal_has_content_addressed_contract")
    assert check["violations"] == 1
