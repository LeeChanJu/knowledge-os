"""Explicit, audited F1 correction; never invoked by ingestion or schema migration.

From the checkout (use the active project Python environment):
Preview: PYTHONPATH=src python -m knowledge_os.metadata_correction > reviewed-plan.json
Apply: PYTHONPATH=src python -m knowledge_os.metadata_correction --apply-plan reviewed-plan.json \
    --actor local-user --reason 'F1 remediation'

Review the database, version IDs and before/after hashes before applying. A stale
plan fails atomically. Reapplying the same plan is a no-op. Existing DocumentVersion
IDs, metadata, timestamps, chunks and lineage are preserved; only the derived hash
changes. Its original value and metadata snapshot remain in an immutable operational
Event attached to the owning Document, committed in the same Neo4j transaction.
"""

import argparse
import json
from pathlib import Path

from neo4j import GraphDatabase

from knowledge_os.config import Settings
from knowledge_os.doctor import persisted_metadata_hash
from knowledge_os.graph import now_iso
from knowledge_os.ids import content_hash, stable_id

CORRECTION_VERSION = "document-version-metadata-hash-v1"


def _plan_hash(plan):
    return content_hash(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def plan_correction(driver, database):
    """Read only; bind an explicit plan to the exact affected persisted metadata."""
    records = []
    with driver.session(database=database) as session:
        rows = session.run(
            "MATCH (v:DocumentVersion) "
            "WHERE v.source_contract_version IS NOT NULL OR v.source_metadata_hash IS NOT NULL "
            "OPTIONAL MATCH (d:Document)-[:HAS_VERSION]->(v) "
            "RETURN v.id AS id, v.title AS title, v.source_uri AS source_uri, "
            "v.source_contract_version AS source_contract_version, "
            "v.source_metadata_hash AS before_hash, collect(d.id) AS documents ORDER BY id"
        )
        for row in rows:
            after = persisted_metadata_hash(row["title"], row["source_uri"])
            if row["before_hash"] == after:
                continue
            if not isinstance(row["title"], str) or not row["title"].strip():
                raise ValueError(f"Cannot correct missing immutable title: {row['id']}")
            if len(row["documents"]) != 1:
                raise ValueError(f"Cannot correct ambiguous document lineage: {row['id']}")
            records.append(
                {
                    "version_id": row["id"],
                    "document_id": row["documents"][0],
                    "title": row["title"],
                    "source_uri": row["source_uri"],
                    "source_contract_version": row["source_contract_version"],
                    "before_hash": row["before_hash"],
                    "after_hash": after,
                }
            )
    plan = {"correction_version": CORRECTION_VERSION, "database": database, "records": records}
    return {**plan, "plan_hash": _plan_hash(plan)}


def apply_correction(driver, database, plan, *, actor, reason):
    """Apply a reviewed plan and its audit events atomically, including on retry."""
    body = {key: value for key, value in plan.items() if key != "plan_hash"}
    if (
        plan.get("correction_version") != CORRECTION_VERSION
        or plan.get("database") != database
        or plan.get("plan_hash") != _plan_hash(body)
    ):
        raise ValueError("Correction plan version, database or digest mismatch")
    if not actor.strip() or not reason.strip():
        raise ValueError("Correction requires an actor and reason")
    if len({r["version_id"] for r in plan["records"]}) != len(plan["records"]):
        raise ValueError("Duplicate correction version ID")
    with driver.session(database=database) as session:
        return session.execute_write(_apply, plan, actor, reason)


def _apply(tx, plan, actor, reason):
    applied = 0
    for record in sorted(plan["records"], key=lambda row: row["version_id"]):
        event_id = stable_id("event", CORRECTION_VERSION, plan["plan_hash"], record["version_id"])
        # A property-dependent SET acquires the version write lock before reading.
        row = tx.run(
            "MATCH (v:DocumentVersion {id:$id}) "
            "SET v.source_metadata_hash=v.source_metadata_hash "
            "WITH v OPTIONAL MATCH (d:Document)-[:HAS_VERSION]->(v) "
            "RETURN v.title AS title, v.source_uri AS source_uri, "
            "v.source_contract_version AS source_contract_version, "
            "v.source_metadata_hash AS hash, collect(d.id) AS documents",
            id=record["version_id"],
        ).single()
        if (
            row is None
            or row["title"] != record["title"]
            or row["source_uri"] != record["source_uri"]
            or row["source_contract_version"] != record["source_contract_version"]
            or row["documents"] != [record["document_id"]]
            or record["after_hash"] != persisted_metadata_hash(row["title"], row["source_uri"])
        ):
            raise ValueError("Correction plan no longer matches immutable metadata or lineage")
        previous = tx.run(
            "MATCH (d:Document {id:$document})-[:HAS_EVENT]->(e:Event {id:$id}) "
            "RETURN e.plan_hash AS plan_hash, e.after_hash AS after_hash",
            document=record["document_id"],
            id=event_id,
        ).single()
        if previous:
            if (
                previous["plan_hash"] != plan["plan_hash"]
                or previous["after_hash"] != record["after_hash"]
                or row["hash"] != record["after_hash"]
            ):
                raise ValueError("Correction audit or corrected hash has changed")
            continue
        if row["hash"] != record["before_hash"]:
            raise ValueError("Correction plan no longer matches stored hash")
        tx.run(
            "MATCH (d:Document {id:$document}), (v:DocumentVersion {id:$version}) "
            "CREATE (e:Event {id:$event, event_type:'DOCUMENT_METADATA_HASH_CORRECTED', "
            "event_class:'OPERATIONAL', correction_version:$correction, plan_hash:$plan_hash, "
            "document_version_id:$version, before_hash:$before, after_hash:$after, "
            "metadata_snapshot:$snapshot, actor:$actor, reason:$reason, recorded_at:$now}) "
            "CREATE (d)-[:HAS_EVENT]->(e) SET v.source_metadata_hash=$after",
            document=record["document_id"],
            version=record["version_id"],
            event=event_id,
            correction=CORRECTION_VERSION,
            plan_hash=plan["plan_hash"],
            before=record["before_hash"],
            after=record["after_hash"],
            snapshot=json.dumps(record, ensure_ascii=False, sort_keys=True),
            actor=actor,
            reason=reason,
            now=now_iso(),
        ).consume()
        applied += 1
    return {
        "correction_version": CORRECTION_VERSION,
        "plan_hash": plan["plan_hash"],
        "applied": applied,
        "already_applied": len(plan["records"]) - applied,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-plan", type=Path)
    parser.add_argument("--actor")
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.apply_plan and (not args.actor or not args.reason):
        parser.error("--apply-plan requires --actor and --reason")
    settings = Settings()
    with GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    ) as driver:
        if args.apply_plan:
            report = apply_correction(
                driver,
                settings.neo4j_database,
                json.loads(args.apply_plan.read_text(encoding="utf-8")),
                actor=args.actor,
                reason=args.reason,
            )
        else:
            report = plan_correction(driver, settings.neo4j_database)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
