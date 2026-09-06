import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from knowledge_os.config import get_settings
from knowledge_os.contracts import ContractRegistry

MANIFEST_VERSION = "1"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(command: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True, env=env, cwd=cwd)
    return (result.stdout + result.stderr).strip()


def _java_env(java_home: Path | None) -> dict[str, str]:
    env = os.environ.copy()
    if java_home is not None:
        env["JAVA_HOME"] = str(java_home.resolve())
    return env


def _git_evidence(repository: Path) -> dict:
    try:
        commit = _run(["git", "rev-parse", "HEAD"], cwd=repository).splitlines()[0]
        status = _run(["git", "status", "--porcelain"], cwd=repository)
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": bool(status)}


def _backup_sqlite(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"operations database does not exist: {source}")
    with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as backup_db:
        source_db.backup(backup_db)
    with sqlite3.connect(destination) as backup_db:
        result = backup_db.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite backup integrity check failed: {result}")


def _sqlite_evidence(path: Path) -> dict:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {}
        for table in tables:
            quoted_table = table.replace('"', '""')
            counts[table] = db.execute(f'SELECT count(*) FROM "{quoted_table}"').fetchone()[0]
        return {"table_counts": counts}


def collect_graph_evidence(graph) -> dict:
    with graph.driver.session(database=graph.database) as session:
        labels = {
            row["label"]: row["count"]
            for row in session.run(
                "MATCH (node) UNWIND labels(node) AS label "
                "RETURN label, count(*) AS count ORDER BY label"
            )
        }
        relationships = {
            row["type"]: row["count"]
            for row in session.run(
                "MATCH ()-[relationship]->() "
                "RETURN type(relationship) AS type, count(*) AS count ORDER BY type"
            )
        }
        migrations = session.run(
            "MATCH (migration:SchemaMigration) "
            "RETURN migration.name AS name, migration.checksum AS checksum ORDER BY name"
        ).data()
        components = session.run(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions, edition ORDER BY name"
        ).data()
    return {
        "database": graph.database,
        "components": components,
        "label_counts": labels,
        "relationship_counts": relationships,
        "migrations": migrations,
    }


def create_backup(
    *,
    output_root: Path,
    neo4j_admin: Path,
    database: str,
    ops_db: Path,
    contracts_path: Path,
    repository: Path,
    java_home: Path | None = None,
    graph_evidence: dict | None = None,
) -> Path:
    if not neo4j_admin.is_file():
        raise FileNotFoundError(f"neo4j-admin does not exist: {neo4j_admin}")
    if not database or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for character in database
    ):
        raise ValueError("database must contain only lowercase letters, digits, dots, or hyphens")

    output_root.mkdir(parents=True, exist_ok=True)
    backup_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid4().hex[:8]}"
    staging = output_root / f".{backup_id}.staging"
    destination = output_root / backup_id
    staging.mkdir()
    started_at = _now()
    try:
        neo4j_dir = staging / "neo4j"
        neo4j_dir.mkdir()
        backup_output = _run(
            [
                str(neo4j_admin),
                "database",
                "backup",
                database,
                f"--to-path={neo4j_dir}",
                "--type=FULL",
                "--compress=true",
            ],
            env=_java_env(java_home),
        )
        artifacts = sorted(neo4j_dir.glob("*.backup"))
        if len(artifacts) != 1:
            raise RuntimeError(f"expected one Neo4j backup artifact, found {len(artifacts)}")

        sqlite_path = staging / "ops.db"
        _backup_sqlite(ops_db, sqlite_path)
        registry = ContractRegistry.load(contracts_path)
        files = {
            str(path.relative_to(staging)): {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in (artifacts[0], sqlite_path)
        }
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "backup_id": backup_id,
            "capture_started_at": started_at,
            "capture_completed_at": _now(),
            "consistency": "BOUNDED_CAPTURE_WINDOW",
            "neo4j": {
                "database": database,
                "artifact": str(artifacts[0].relative_to(staging)),
                "command_result": backup_output.splitlines()[-1] if backup_output else None,
                "evidence": graph_evidence,
            },
            "sqlite": {"artifact": "ops.db", "evidence": _sqlite_evidence(sqlite_path)},
            "contracts": {
                "registry_version": registry.version,
                "versions": registry.contracts,
                "registry_sha256": _sha256(contracts_path),
            },
            "git": _git_evidence(repository),
            "files": files,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination


def verify_backup(backup_dir: Path, *, neo4j_admin: Path, java_home: Path | None = None) -> dict:
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise ValueError("unsupported recovery manifest version")

    checks = []
    backup_root = backup_dir.resolve()

    def artifact_path(relative: str) -> Path:
        path = (backup_root / relative).resolve()
        if not path.is_relative_to(backup_root):
            raise ValueError("backup manifest artifact escapes its recovery directory")
        return path

    for relative, expected in manifest["files"].items():
        path = artifact_path(relative)
        actual = _sha256(path) if path.is_file() else None
        checks.append(
            {
                "name": f"sha256:{relative}",
                "status": "PASS" if actual == expected["sha256"] else "FAIL",
            }
        )

    sqlite_path = artifact_path(manifest["sqlite"]["artifact"])
    sqlite_result = None
    if sqlite_path.is_file():
        with sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True) as db:
            sqlite_result = db.execute("PRAGMA integrity_check").fetchone()[0]
    checks.append(
        {
            "name": "sqlite_integrity",
            "status": "PASS" if sqlite_result == "ok" else "FAIL",
        }
    )

    artifact = artifact_path(manifest["neo4j"]["artifact"])
    try:
        with tempfile.TemporaryDirectory(prefix="knowledge-os-recovery-check-") as temp:
            _run(
                [
                    str(neo4j_admin),
                    "database",
                    "check",
                    manifest["neo4j"]["database"],
                    f"--from-path={artifact}",
                    f"--temp-path={temp}",
                    f"--report-path={temp}",
                ],
                env=_java_env(java_home),
            )
        neo4j_ok = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        neo4j_ok = False
    checks.append({"name": "neo4j_archive_consistency", "status": "PASS" if neo4j_ok else "FAIL"})
    passed = all(check["status"] == "PASS" for check in checks)
    return {
        "status": "ok" if passed else "error",
        "backup_id": manifest["backup_id"],
        "capture_started_at": manifest["capture_started_at"],
        "capture_completed_at": manifest["capture_completed_at"],
        "checks": checks,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or verify a Knowledge OS recovery set")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "verify"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--neo4j-admin", type=Path, required=True)
        subparser.add_argument("--java-home", type=Path)
    create = subparsers.choices["create"]
    create.add_argument("--output", type=Path, default=Path("data/backups"))
    create.add_argument("--database", default=get_settings().neo4j_database)
    create.add_argument("--ops-db", type=Path, default=get_settings().ops_db_path)
    create.add_argument("--contracts", type=Path, default=get_settings().contracts_path)
    verify = subparsers.choices["verify"]
    verify.add_argument("backup", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "create":
        from knowledge_os.dependencies import get_graph
        from knowledge_os.doctor import run_doctor

        graph = get_graph()
        try:
            if args.database != graph.database:
                raise ValueError(
                    "--database must match the configured Knowledge OS database so live "
                    "integrity evidence cannot describe a different store"
                )
            graph.verify()
            doctor = run_doctor(graph)
            if doctor["status"] != "ok":
                raise RuntimeError("live integrity Doctor failed; refusing to create backup")
            graph_evidence = collect_graph_evidence(graph)
            graph_evidence["doctor_check_count"] = doctor["check_count"]
            backup = create_backup(
                output_root=args.output,
                neo4j_admin=args.neo4j_admin,
                database=args.database,
                ops_db=args.ops_db,
                contracts_path=args.contracts,
                repository=Path.cwd(),
                java_home=args.java_home,
                graph_evidence=graph_evidence,
            )
        finally:
            graph.close()
        print(json.dumps({"status": "ok", "backup": str(backup)}, indent=2))
        return
    report = verify_backup(args.backup, neo4j_admin=args.neo4j_admin, java_home=args.java_home)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
