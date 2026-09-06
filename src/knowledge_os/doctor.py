import hashlib
import json
import sqlite3
from pathlib import Path

from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_graph
from knowledge_os.ids import content_hash

GRAPH_CHECKS = {
    "source_has_connector_binding": """
        MATCH (s:Source)
        WHERE s.connector_id IS NULL OR trim(s.connector_id) = ''
        RETURN count(*) AS violations, collect(s.id)[..10] AS samples
    """,
    "no_self_supersedes": """
        MATCH (n)-[:SUPERSEDES]->(n)
        RETURN count(*) AS violations, collect(n.id)[..10] AS samples
    """,
    "governed_supersession_stays_in_workspace": """
        MATCH (new)-[:SUPERSEDES]->(old)
        WHERE (new:Assertion OR new:Decision OR
               (new:Event AND new.event_class='SEMANTIC'))
          AND (new.workspace_id <> old.workspace_id OR old.status <> 'SUPERSEDED'
            OR (new:Assertion AND NOT old:Assertion)
            OR (new:Decision AND NOT old:Decision)
            OR (new:Event AND NOT (old:Event AND old.event_class='SEMANTIC')))
        RETURN count(*) AS violations, collect(new.id)[..10] AS samples
    """,
    "governed_record_has_at_most_one_successor": """
        MATCH (old)
        WHERE old:Assertion OR old:Decision OR
              (old:Event AND old.event_class='SEMANTIC')
        OPTIONAL MATCH (new)-[:SUPERSEDES]->(old)
        WITH old, count(new) AS n WHERE n > 1
        RETURN count(*) AS violations, collect(old.id)[..10] AS samples
    """,
    "assertion_supersession_preserves_semantic_key": """
        MATCH (new:Assertion)-[:SUPERSEDES]->(old:Assertion),
              (new)-[:SUBJECT]->(new_subject:Entity),
              (old)-[:SUBJECT]->(old_subject:Entity)
        WHERE new.workspace_id <> old.workspace_id
           OR new.predicate <> old.predicate
           OR new_subject.id <> old_subject.id
        RETURN count(*) AS violations, collect(new.id)[..10] AS samples
    """,
    "document_has_one_current_version": """
        MATCH (d:Document)
        OPTIONAL MATCH (d)-[:CURRENT_VERSION]->(v:DocumentVersion)
        WITH d, count(v) AS n WHERE n <> 1
        RETURN count(*) AS violations, collect(d.id)[..10] AS samples
    """,
    "current_version_is_in_history": """
        MATCH (d:Document)-[:CURRENT_VERSION]->(v:DocumentVersion)
        WHERE NOT EXISTS { (d)-[:HAS_VERSION]->(v) }
        RETURN count(*) AS violations, collect(d.id)[..10] AS samples
    """,
    "chunk_has_one_parent_version": """
        MATCH (c:Chunk)
        OPTIONAL MATCH (v:DocumentVersion)-[:HAS_CHUNK]->(c)
        WITH c, count(v) AS n WHERE n <> 1
        RETURN count(*) AS violations, collect(c.id)[..10] AS samples
    """,
    "chunk_activity_matches_document_lifecycle": """
        MATCH (d:Document)-[:CURRENT_VERSION]->(current:DocumentVersion)
        MATCH (d)-[:HAS_VERSION]->(v:DocumentVersion)-[:HAS_CHUNK]->(c:Chunk)
        WHERE (d.status='ACTIVE' AND v=current AND coalesce(c.active, false)=false)
           OR ((d.status <> 'ACTIVE' OR v <> current) AND coalesce(c.active, false)=true)
        RETURN count(DISTINCT c) AS violations, collect(DISTINCT c.id)[..10] AS samples
    """,
    "chunk_embedding_has_complete_provenance": """
        MATCH (c:Chunk)
        WITH c, c.embedding IS NOT NULL AS has_embedding,
             c.embedding_hash IS NOT NULL AND size(c.embedding_hash)=64
             AND c.embedding_model IS NOT NULL AND trim(c.embedding_model) <> ''
             AND c.embedding_version IS NOT NULL AND trim(c.embedding_version) <> ''
             AND c.embedding_created_at IS NOT NULL
             AND c.embedding_created_by IS NOT NULL
             AND trim(c.embedding_created_by) <> '' AS has_provenance
        WHERE has_embedding <> has_provenance
        RETURN count(*) AS violations, collect(c.id)[..10] AS samples
    """,
    "operational_event_has_one_source_parent": """
        MATCH (event:Event)
        WHERE event.event_class IS NULL OR event.event_class <> 'SEMANTIC'
        OPTIONAL MATCH (parent)-[:HAS_EVENT]->(event)
        WITH event, count(parent) AS parent_count, collect(parent)[0] AS parent
        WHERE parent_count <> 1 OR NOT (parent:Source OR parent:Document)
        RETURN count(*) AS violations, collect(event.id)[..10] AS samples
    """,
    "source_has_one_workspace": """
        MATCH (s:Source)
        OPTIONAL MATCH (w:Workspace)-[:OWNS_SOURCE]->(s)
        WITH s, count(w) AS n WHERE n <> 1
        RETURN count(*) AS violations, collect(s.id)[..10] AS samples
    """,
    "atomic_manifest_completion_has_hash": """
        MATCH (event:Event {event_type:'SOURCE_SYNC_COMPLETED'})
        WHERE properties(event)['manifest_version']='2'
          AND properties(event)['manifest_hash'] IS NULL
        RETURN count(*) AS violations, collect(event.id)[..10] AS samples
    """,
    "document_has_one_source": """
        MATCH (d:Document)
        OPTIONAL MATCH (s:Source)-[:HAS_DOCUMENT]->(d)
        WITH d, count(s) AS n WHERE n <> 1
        RETURN count(*) AS violations, collect(d.id)[..10] AS samples
    """,
    "version_has_one_document": """
        MATCH (v:DocumentVersion)
        OPTIONAL MATCH (d:Document)-[:HAS_VERSION]->(v)
        WITH v, count(d) AS n WHERE n <> 1
        RETURN count(*) AS violations, collect(v.id)[..10] AS samples
    """,
    "versioned_source_metadata_is_complete": """
        MATCH (v:DocumentVersion)
        WHERE v.source_contract_version IS NOT NULL
          AND (NOT v.source_contract_version IN
                    ['source-v6', 'source-v7', 'source-v8', 'source-v9', 'source-v10',
                     'source-v11', 'source-v12']
            OR v.title IS NULL OR trim(v.title)=''
            OR v.source_metadata_hash IS NULL OR size(v.source_metadata_hash) <> 64)
        RETURN count(*) AS violations, collect(v.id)[..10] AS samples
    """,
    "proposal_evidence_stays_in_workspace": """
        MATCH (w:Workspace)-[:HAS_PROPOSAL]->(p:Proposal)-[:SUPPORTED_BY]->(c:Chunk)
        WHERE NOT EXISTS {
            (w)-[:OWNS_SOURCE]->(:Source)-[:HAS_DOCUMENT]->(:Document)
               -[:HAS_VERSION]->(:DocumentVersion)-[:HAS_CHUNK]->(c)
        }
        RETURN count(*) AS violations, collect(p.id)[..10] AS samples
    """,
    "proposal_has_one_workspace_and_evidence": """
        MATCH (p:Proposal)
        OPTIONAL MATCH (w:Workspace)-[:HAS_PROPOSAL]->(p)
        OPTIONAL MATCH (p)-[:SUPPORTED_BY]->(c:Chunk)
        WITH p, count(DISTINCT w) AS workspace_count, count(DISTINCT c) AS evidence_count
        WHERE workspace_count <> 1 OR evidence_count < 1
        RETURN count(*) AS violations, collect(p.id)[..10] AS samples
    """,
    "proposal_state_matches_decision_history": """
        MATCH (p:Proposal)
        OPTIONAL MATCH (p)-[:HAS_APPROVAL]->(approval:Approval)
        OPTIONAL MATCH (p)-[:PROMOTED]->(promoted)
        WITH p, count(DISTINCT approval) AS approval_count,
             collect(DISTINCT approval.decision) AS decisions,
             count(DISTINCT promoted) AS promoted_count
        WHERE (p.status='PROPOSED' AND (approval_count <> 0 OR promoted_count <> 0))
           OR (p.status='REJECTED' AND
               (approval_count <> 1 OR promoted_count <> 0 OR NOT 'REJECTED' IN decisions))
           OR (p.status='APPROVED' AND
               (approval_count <> 1 OR promoted_count < 1 OR NOT 'APPROVED' IN decisions))
        RETURN count(*) AS violations, collect(p.id)[..10] AS samples
    """,
    "approval_has_one_governed_parent": """
        MATCH (approval:Approval)
        OPTIONAL MATCH (parent)-[:HAS_APPROVAL]->(approval)
        WITH approval, count(parent) AS parent_count, collect(parent)[0] AS parent
        WHERE parent_count <> 1 OR NOT (parent:Proposal OR parent:Action)
        RETURN count(*) AS violations, collect(approval.id)[..10] AS samples
    """,
    "proposal_has_content_addressed_contract": """
        MATCH (p:Proposal)
        WHERE p.contract_version IS NULL
           OR NOT p.contract_version IN ['governance-v6', 'governance-v7']
           OR p.payload_hash IS NULL OR size(p.payload_hash) <> 64
           OR p.created_access_fingerprint IS NULL
           OR NOT p.created_access_fingerprint STARTS WITH 'access-context:'
           OR size(p.created_access_fingerprint) <> 79
           OR p.created_principal_count IS NULL OR p.created_principal_count < 1
           OR p._creation_marker IS NOT NULL
        RETURN count(*) AS violations, collect(p.id)[..10] AS samples
    """,
    "canonical_evidence_stays_in_workspace": """
        MATCH (c:Chunk)-[:EVIDENCE_FOR]->(knowledge)
        WHERE knowledge.workspace_id IS NOT NULL AND NOT EXISTS {
            (:Workspace {id:knowledge.workspace_id})-[:OWNS_SOURCE]->(:Source)
              -[:HAS_DOCUMENT]->(:Document)-[:HAS_VERSION]->(:DocumentVersion)
              -[:HAS_CHUNK]->(c)
        }
        RETURN count(*) AS violations, collect(knowledge.id)[..10] AS samples
    """,
    "assertion_temporal_interval_is_ordered": """
        MATCH (a:Assertion)
        WHERE a.valid_from IS NOT NULL AND a.valid_to IS NOT NULL
          AND datetime(replace(toString(a.valid_to), ' ', 'T')) <
              datetime(replace(toString(a.valid_from), ' ', 'T'))
        RETURN count(*) AS violations, collect(a.id)[..10] AS samples
    """,
    "decision_temporal_interval_is_ordered": """
        MATCH (d:Decision)
        WHERE (d.valid_from IS NOT NULL AND d.valid_to IS NOT NULL
          AND datetime(d.valid_to) < datetime(d.valid_from))
           OR (d.decided_at_precision IS NOT NULL AND
             (NOT d.decided_at_precision IN ['INSTANT', 'DAY']
              OR (d.decided_at_precision='DAY' AND d.decided_on IS NULL)
              OR (d.decided_at_precision='INSTANT' AND d.decided_on IS NOT NULL)))
        RETURN count(*) AS violations, collect(d.id)[..10] AS samples
    """,
    "event_temporal_interval_is_ordered": """
        MATCH (e:Event {event_class:'SEMANTIC'})
        WHERE e.ended_at IS NOT NULL AND datetime(e.ended_at) < datetime(e.occurred_at)
        RETURN count(*) AS violations, collect(e.id)[..10] AS samples
    """,
    "action_has_one_matching_workspace": """
        MATCH (a:Action)
        OPTIONAL MATCH (w:Workspace)-[:HAS_ACTION]->(a)
        WITH a, collect(DISTINCT w.id) AS workspace_ids
        WHERE size(workspace_ids) <> 1 OR a.workspace_id IS NULL
           OR NOT (a.workspace_id IN workspace_ids)
        RETURN count(*) AS violations, collect(a.id)[..10] AS samples
    """,
    "action_contract_version_is_known": """
        MATCH (action:Action)
        WHERE action.contract_version IS NULL
           OR NOT action.contract_version IN
              ['action-v2', 'action-v3', 'action-v4', 'action-v5', 'action-v6']
           OR (action.contract_version IN ['action-v5', 'action-v6'] AND (
               action.idempotency_key IS NULL OR trim(action.idempotency_key)=''
               OR action.payload_hash IS NULL OR size(action.payload_hash) <> 64
               OR action._creation_marker IS NOT NULL))
           OR (action.contract_version='action-v6' AND (
               action.requested_access_fingerprint IS NULL
               OR NOT action.requested_access_fingerprint STARTS WITH 'access-context:'
               OR size(action.requested_access_fingerprint) <> 79
               OR action.requested_principal_count IS NULL
               OR action.requested_principal_count < 1))
        RETURN count(*) AS violations, collect(action.id)[..10] AS samples
    """,
    "action_state_matches_decision_history": """
        MATCH (action:Action)
        OPTIONAL MATCH (action)-[:HAS_APPROVAL]->(approval:Approval)
        WITH action, count(DISTINCT approval) AS approval_count,
             collect(DISTINCT approval.decision) AS decisions
        WHERE (action.status='PROPOSED' AND approval_count <> 0)
           OR (action.status='REJECTED' AND
               (approval_count <> 1 OR NOT 'REJECTED' IN decisions))
           OR (action.status='APPROVED' AND
               (approval_count <> 1 OR NOT 'APPROVED' IN decisions))
        RETURN count(*) AS violations, collect(action.id)[..10] AS samples
    """,
    "action_execution_matches_capability": """
        MATCH (execution:ActionExecution)
        OPTIONAL MATCH (action:Action)-[:HAS_EXECUTION]->(execution)
        WITH execution, collect(DISTINCT action) AS actions
        WHERE size(actions) <> 1 OR any(action IN actions WHERE
            action.status <> 'APPROVED'
            OR execution.policy_version <> action.policy_version
            OR NOT execution.executed_by IN action.execution_principals)
        RETURN count(*) AS violations, collect(execution.id)[..10] AS samples
    """,
    "action_execution_contract_has_claim": """
        MATCH (execution:ActionExecution)
        OPTIONAL MATCH (claim:ActionExecutionClaim)-[:PRODUCED_EXECUTION]->(execution)
        WITH execution, count(claim) AS claims
        WHERE execution.contract_version IS NULL
           OR NOT execution.contract_version IN
              ['action-v2', 'action-v3', 'action-v4', 'action-v5', 'action-v6']
           OR (execution.contract_version IN ['action-v3', 'action-v4', 'action-v5', 'action-v6']
               AND claims <> 1)
           OR (execution.contract_version='action-v2' AND claims <> 0)
        RETURN count(*) AS violations, collect(execution.id)[..10] AS samples
    """,
    "action_has_at_most_one_success": """
        MATCH (action:Action)
        OPTIONAL MATCH (action)-[:HAS_EXECUTION]->(execution:ActionExecution {status:'SUCCEEDED'})
        WITH action, count(execution) AS successes WHERE successes > 1
        RETURN count(*) AS violations, collect(action.id)[..10] AS samples
    """,
    "action_execution_status_matches_history": """
        MATCH (action:Action)
        OPTIONAL MATCH (action)-[:HAS_EXECUTION]->(execution:ActionExecution)
        WITH action, count(execution) AS attempts,
             count(CASE WHEN execution.status='SUCCEEDED' THEN 1 END) AS successes
        OPTIONAL MATCH (action)-[:HAS_EXECUTION_CLAIM]->(current:ActionExecutionClaim)
        WHERE current.id=action.current_execution_claim_id AND current.status='CLAIMED'
        WITH action, attempts, successes, count(current) AS current_claims
        WHERE (action.execution_status='NOT_EXECUTED' AND attempts <> 0)
           OR (action.execution_status='IN_PROGRESS' AND
               (current_claims <> 1 OR successes <> 0))
           OR (action.execution_status <> 'IN_PROGRESS' AND current_claims <> 0)
           OR (action.execution_status='FAILED' AND (attempts = 0 OR successes <> 0))
           OR (action.execution_status='SUCCEEDED' AND successes <> 1)
        RETURN count(*) AS violations, collect(action.id)[..10] AS samples
    """,
    "action_execution_claim_matches_action": """
        MATCH (claim:ActionExecutionClaim)
        OPTIONAL MATCH (action:Action)-[:HAS_EXECUTION_CLAIM]->(claim)
        WITH claim, collect(DISTINCT action) AS actions
        WHERE size(actions) <> 1 OR any(action IN actions WHERE
            claim.policy_version <> action.policy_version
            OR NOT claim.executed_by IN action.execution_principals
            OR claim.contract_version IS NULL
            OR NOT claim.contract_version IN ['action-v3', 'action-v4', 'action-v5', 'action-v6']
            OR NOT claim.status IN ['CLAIMED', 'COMPLETED']
            OR (claim.status='CLAIMED' AND
                (action.current_execution_claim_id <> claim.id
                 OR action.execution_status <> 'IN_PROGRESS')))
        RETURN count(*) AS violations, collect(claim.id)[..10] AS samples
    """,
    "action_claim_status_matches_execution": """
        MATCH (claim:ActionExecutionClaim)
        OPTIONAL MATCH (claim)-[:PRODUCED_EXECUTION]->(execution:ActionExecution)
        WITH claim, count(execution) AS executions
        WHERE (claim.status='COMPLETED' AND executions <> 1)
           OR (claim.status='CLAIMED' AND executions <> 0)
        RETURN count(*) AS violations, collect(claim.id)[..10] AS samples
    """,
}


def audit_migrations(ledger: list[dict], directory: Path) -> dict:
    recorded = {row["name"]: row["checksum"] for row in ledger}
    files = {
        path.name: content_hash(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.cypher"))
    }
    missing = sorted(set(files) - set(recorded))
    unexpected = sorted(set(recorded) - set(files))
    changed = sorted(
        name for name in files.keys() & recorded.keys() if files[name] != recorded[name]
    )
    violations = len(missing) + len(unexpected) + len(changed)
    return {
        "name": "migration_ledger_matches_git",
        "status": "PASS" if violations == 0 else "FAIL",
        "violations": violations,
        "details": {"missing": missing, "unexpected": unexpected, "changed": changed},
    }


def audit_vector_index(rows: list[dict], expected_dimensions: int) -> dict:
    expected = {
        "name": "chunk_embedding_vector",
        "type": "VECTOR",
        "state": "ONLINE",
        "dimensions": expected_dimensions,
        "similarity": "COSINE",
    }
    actual = []
    for row in rows:
        config = (row.get("options") or {}).get("indexConfig", {})
        actual.append(
            {
                "name": row.get("name"),
                "type": row.get("type"),
                "state": row.get("state"),
                "dimensions": config.get("vector.dimensions"),
                "similarity": config.get("vector.similarity_function"),
            }
        )
    violations = 0 if actual == [expected] else 1
    return {
        "name": "vector_index_matches_embedding_contract",
        "status": "PASS" if violations == 0 else "FAIL",
        "violations": violations,
        "details": {"expected": expected, "actual": actual},
    }


def audit_evaluation_access(db: sqlite3.Connection) -> dict:
    samples = [
        row[0]
        for row in db.execute(
            """
            SELECT id FROM evaluations
            WHERE workspace_id IS NULL OR trim(workspace_id) = ''
               OR access_fingerprint IS NULL OR trim(access_fingerprint) = ''
            ORDER BY id LIMIT 10
            """
        ).fetchall()
    ]
    violations = db.execute(
        """
        SELECT count(*) FROM evaluations
        WHERE workspace_id IS NULL OR trim(workspace_id) = ''
           OR access_fingerprint IS NULL OR trim(access_fingerprint) = ''
        """
    ).fetchone()[0]
    return {
        "name": "evaluation_has_access_provenance",
        "status": "PASS" if violations == 0 else "FAIL",
        "violations": violations,
        "samples": samples,
    }


def audit_feedback_access(db: sqlite3.Connection) -> dict:
    samples = [
        row[0]
        for row in db.execute(
            """
            SELECT id FROM feedback
            WHERE workspace_id IS NULL OR trim(workspace_id) = ''
               OR access_fingerprint IS NULL OR trim(access_fingerprint) = ''
            ORDER BY id LIMIT 10
            """
        ).fetchall()
    ]
    violations = db.execute(
        """
        SELECT count(*) FROM feedback
        WHERE workspace_id IS NULL OR trim(workspace_id) = ''
           OR access_fingerprint IS NULL OR trim(access_fingerprint) = ''
        """
    ).fetchone()[0]
    return {
        "name": "feedback_has_access_provenance",
        "status": "PASS" if violations == 0 else "FAIL",
        "violations": violations,
        "samples": samples,
    }


def persisted_metadata_hash(title: str, source_uri: str | None) -> str:
    """Independently verify the persisted title/URI contract, not ingestion output."""
    canonical = json.dumps(
        {"title": title, "source_uri": source_uri},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def audit_metadata_hashes(rows) -> dict:
    violations = 0
    samples = []
    for row in rows:
        if row["source_metadata_hash"] != persisted_metadata_hash(row["title"], row["source_uri"]):
            violations += 1
            if len(samples) < 10:
                samples.append(row["id"])
    return {
        "name": "immutable_metadata_hash_matches_persisted_version",
        "status": "PASS" if violations == 0 else "FAIL",
        "violations": violations,
        "samples": samples,
    }


def run_doctor(graph, migrations: Path | None = None) -> dict:
    migrations = migrations or get_settings().migrations_path
    checks = []
    with graph.driver.session(database=graph.database) as session:
        checks.append(
            audit_metadata_hashes(
                session.run(
                    "MATCH (v:DocumentVersion) "
                    "WHERE v.source_contract_version IS NOT NULL OR v.source_metadata_hash IS NOT NULL "
                    "RETURN v.id AS id, v.title AS title, v.source_uri AS source_uri, "
                    "v.source_metadata_hash AS source_metadata_hash"
                )
            )
        )
        for name, query in GRAPH_CHECKS.items():
            row = session.run(query).single()
            violations = int(row["violations"])
            checks.append(
                {
                    "name": name,
                    "status": "PASS" if violations == 0 else "FAIL",
                    "violations": violations,
                    "samples": row["samples"],
                }
            )
        ledger = session.run(
            "MATCH (m:SchemaMigration) RETURN m.name AS name, m.checksum AS checksum"
        ).data()
        offline = session.run(
            "SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE' "
            "RETURN name, state ORDER BY name"
        ).data()
        vector_indexes = session.run(
            "SHOW INDEXES YIELD name, type, state, options "
            "WHERE name='chunk_embedding_vector' RETURN name, type, state, options"
        ).data()
    checks.append(audit_migrations(ledger, migrations))
    checks.append(audit_vector_index(vector_indexes, graph.embedding_dimensions))
    checks.append(
        {
            "name": "neo4j_indexes_online",
            "status": "PASS" if not offline else "FAIL",
            "violations": len(offline),
            "details": offline,
        }
    )
    with graph.ops.connect() as db:
        sqlite_result = db.execute("PRAGMA integrity_check").fetchone()[0]
        evaluation_access = audit_evaluation_access(db)
        feedback_access = audit_feedback_access(db)
    checks.append(evaluation_access)
    checks.append(feedback_access)
    checks.append(
        {
            "name": "sqlite_integrity",
            "status": "PASS" if sqlite_result == "ok" else "FAIL",
            "violations": 0 if sqlite_result == "ok" else 1,
            "details": sqlite_result,
        }
    )
    violations = sum(check["violations"] for check in checks)
    return {
        "status": "ok" if violations == 0 else "error",
        "check_count": len(checks),
        "violation_count": violations,
        "checks": checks,
    }


def main() -> None:
    graph = get_graph()
    try:
        graph.verify()
        report = run_doctor(graph)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        graph.close()
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
