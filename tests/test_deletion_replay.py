import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime

import pytest
from test_metadata_correction import snapshot
from test_v01_correctness_regressions import clock as clock  # noqa: PLC0414 - shared fixture
from test_v01_neo4j_regressions import ROOT, query
from test_v01_neo4j_regressions import graph as graph  # noqa: PLC0414 - isolated fixture

from knowledge_os import file_connector, google_drive_connector, notion_connector
from knowledge_os.doctor import run_doctor
from knowledge_os.ids import stable_id
from knowledge_os.models import SyncManifest

CONNECTORS = ["filesystem", "google_drive", "notion"]


@pytest.fixture(params=CONNECTORS)
def connector(request, tmp_path):
    kind = request.param
    root = tmp_path / "documents"
    root.mkdir()
    ids = ["aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"]
    options = {"workspace_id": "personal", "connector_id": kind}
    if kind == "filesystem":
        module = file_connector
        options.update(
            source_external_id="folder", owner="local-user", visibility="PRIVATE", acl=[]
        )
    elif kind == "google_drive":
        module = google_drive_connector
        options.update(folder_id="folder", connection_id="connection")
    else:
        module = notion_connector
        options.update(
            root_page_id="11111111-1111-4111-8111-111111111111",
            connection_id="22222222-2222-4222-8222-222222222222",
        )

    def remote(present, revision=1):
        if kind == "filesystem":
            for i in range(2):
                path = root / f"{i}.txt"
                if i in present:
                    path.write_text(f"Evidence {i}.")
                    # Same content, new mtime: even this revision must get a fresh deletion.
                    stamp = 1788220800 + (revision if i == 0 else 1)
                    os.utime(path, (stamp, stamp))
                elif path.exists():
                    path.unlink()
            return str(root)
        result = []
        for i in present:
            stamp = f"2026-09-0{revision if i == 0 else 1}T00:00:00Z"
            if kind == "google_drive":
                item = google_drive_connector.DriveFileSnapshot(
                    ids[i],
                    f"Fixture {i}",
                    "text/plain",
                    stamp,
                    f"https://fixture.invalid/{i}",
                    f"Evidence {i}.",
                    "local-user",
                    "PRIVATE",
                    (),
                )
            else:
                item = notion_connector.NotionPageSnapshot(
                    ids[i], f"Fixture {i}", stamp, f"Evidence {i}."
                )
            result.append(asdict(item))
        return result

    def build(remote_state, state, *, restarted=False):
        # Serialize everything needed to reconstruct; no live provider or pending manifest.
        payload = {"kind": kind, "remote": remote_state, "state": state, "options": options}
        if restarted:
            script = """
import json, sys
from pathlib import Path
from knowledge_os import file_connector, google_drive_connector, notion_connector
p=json.load(sys.stdin)
if p['kind']=='filesystem':
    m,s=file_connector.build_manifest(Path(p['remote']),p['state'],**p['options'])
elif p['kind']=='google_drive':
    m,s=google_drive_connector.build_manifest([google_drive_connector.DriveFileSnapshot(**r) for r in p['remote']],p['state'],**p['options'])
else:
    m,s=notion_connector.build_manifest([notion_connector.NotionPageSnapshot(**r) for r in p['remote']],p['state'],**p['options'])
print(json.dumps({'manifest':m.model_dump(mode='json'),'state':s}))
"""
            proc = subprocess.run(
                [sys.executable, "-B", "-c", script],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
                timeout=30,
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
            )
            result = json.loads(proc.stdout)
            return SyncManifest.model_validate(result["manifest"]), result["state"]
        if kind == "filesystem":
            from pathlib import Path

            data = Path(remote_state)
        elif kind == "google_drive":
            data = [google_drive_connector.DriveFileSnapshot(**r) for r in remote_state]
        else:
            data = [notion_connector.NotionPageSnapshot(**r) for r in remote_state]
        return module.build_manifest(data, state, **options)

    return remote, build, module.load_state, tmp_path / "checkpoint.json"


def test_crash_restart_replay_and_later_deletion(graph, connector, clock):
    remote, build, load, checkpoint = connector
    initial, state = build(remote([0, 1]), load(checkpoint))
    graph.ingest_manifest(initial)
    file_connector.write_state(checkpoint, state)
    old_checkpoint = checkpoint.read_bytes()
    absent = remote([1])
    deletion, next_state = build(absent, load(checkpoint))
    deleted = next(r for r in deletion.records if r.operation == "TOMBSTONE")
    assert deleted.deleted_at is None
    graph.ingest_manifest(deletion)
    committed = snapshot(graph)
    # Crash window: graph committed, old checkpoint still on disk, all builder
    # objects discarded. A new Python process reconstructs from that old file.
    clock.instant = datetime(2026, 9, 30, tzinfo=UTC)
    replay, recovered = build(absent, load(checkpoint), restarted=True)
    assert checkpoint.read_bytes() == old_checkpoint
    assert replay.model_dump_json() == deletion.model_dump_json()
    assert recovered == next_state
    for _ in range(3):
        assert graph.ingest_manifest(replay)["unchanged"] is True
        assert snapshot(graph) == committed
    rows = query(graph, "MATCH (d:Document) RETURN d.external_id AS id, d.status AS status")
    assert {r["id"] for r in rows if r["status"] == "DELETED"} == {deleted.document_external_id}
    assert sum(r["status"] == "ACTIVE" for r in rows) == 1
    assert query(graph, "MATCH (v:DocumentVersion) RETURN count(v) AS n")[0]["n"] == 2
    event = query(
        graph, "MATCH (e:Event {event_type:'SOURCE_DOCUMENT_DELETED'}) RETURN properties(e) AS e"
    )
    assert len(event) == 1
    assert event[0]["e"].get("deleted_at") is None
    assert event[0]["e"].get("observed_at") is None
    assert event[0]["e"]["observation_cursor"] == deletion.cursor
    assert event[0]["e"]["sync_run_id"] == deletion.sync_run_id
    assert event[0]["e"]["recorded_at"]
    file_connector.write_state(checkpoint, recovered)
    assert (
        load(checkpoint)["cursor"]
        == query(graph, "MATCH (s:Source) RETURN s.last_sync_cursor AS cursor")[0]["cursor"]
    )
    restored, state = build(remote([0, 1], revision=2), load(checkpoint))
    graph.ingest_manifest(restored)
    file_connector.write_state(checkpoint, state)
    later, _ = build(remote([1]), load(checkpoint))
    assert later.sync_run_id != deletion.sync_run_id
    assert graph.ingest_manifest(later)["unchanged"] is False
    assert (
        query(graph, "MATCH (e:Event {event_type:'SOURCE_DOCUMENT_DELETED'}) RETURN count(e) AS n")[
            0
        ]["n"]
        == 2
    )
    assert query(graph, "MATCH (v:DocumentVersion) RETURN count(v) AS n")[0]["n"] == 3
    assert query(graph, "MATCH (d:Document {status:'ACTIVE'}) RETURN count(d) AS n")[0]["n"] == 1
    after = snapshot(graph)
    assert graph.ingest_manifest(later)["unchanged"] is True
    assert snapshot(graph) == after
    assert run_doctor(graph, ROOT / "migrations")["status"] == "ok"


def test_legacy_replay_requires_exact_original_full_hash(graph, connector):
    remote, build, load, checkpoint = connector
    initial, state = build(remote([0, 1]), load(checkpoint))
    graph.ingest_manifest(initial)
    replay, _ = build(remote([1]), state)
    payload = replay.model_dump(mode="json")
    deleted = next(r for r in payload["records"] if r["operation"] == "TOMBSTONE")
    deleted["deleted_at"] = "2026-09-01T09:00:00+09:00"
    old = SyncManifest.model_validate(payload)
    graph.ingest_manifest(old)
    # Reproduce the exact pre-F2 persisted event shape and ID, not a permissive mock.
    row = query(
        graph,
        "MATCH (d:Document)-[:HAS_EVENT]->(e:Event {event_type:'SOURCE_DOCUMENT_DELETED'}) RETURN d.id AS document, e.id AS event",
    )[0]
    old_id = stable_id(
        "event", row["document"], "SOURCE_DOCUMENT_DELETED", deleted["source_version"]
    )
    query(
        graph,
        "MATCH (e:Event {id:$id}) SET e.id=$legacy, e.observed_at=e.deleted_at "
        "REMOVE e.deleted_at, e.observation_cursor, e.sync_run_id",
        id=row["event"],
        legacy=old_id,
    )
    before = snapshot(graph)
    assert graph.ingest_manifest(replay)["unchanged"] is True
    assert graph.ingest_manifest(replay)["unchanged"] is True
    assert snapshot(graph) == before
    for field, value in [("reason", "different reason"), ("deleted_at", "2026-09-02T00:00:00Z")]:
        changed = replay.model_dump(mode="json")
        next(r for r in changed["records"] if r["operation"] == "TOMBSTONE")[field] = value
        with pytest.raises(ValueError, match="different manifest payload"):
            graph.ingest_manifest(SyncManifest.model_validate(changed))
        assert snapshot(graph) == before


def test_source_deletion_time_is_preserved_and_bound_to_hash(graph):
    from test_v01_neo4j_regressions import manifest

    graph.ingest_manifest(manifest())
    record = {
        "operation": "TOMBSTONE",
        "document_external_id": "a",
        "source_version": "deleted-v2",
        "deleted_at": "2026-09-01T09:00:00+09:00",
    }
    deletion = manifest("two", "one", [record])
    graph.ingest_manifest(deletion)
    row = query(
        graph,
        "MATCH (d:Document)-[:HAS_EVENT]->(e:Event {event_type:'SOURCE_DOCUMENT_DELETED'}) RETURN d.deleted_at AS effective, e.deleted_at AS event_effective, properties(e)['observed_at'] AS observation",
    )[0]
    assert row == {
        "effective": "2026-09-01T00:00:00+00:00",
        "event_effective": "2026-09-01T00:00:00+00:00",
        "observation": None,
    }
    record["deleted_at"] = "2026-09-02T00:00:00Z"
    with pytest.raises(ValueError, match="different manifest payload"):
        graph.ingest_manifest(manifest("two", "one", [record]))
