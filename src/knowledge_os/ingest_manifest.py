import json
from pathlib import Path

from knowledge_os.dependencies import get_graph
from knowledge_os.models import SyncManifest


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest a connector-neutral Knowledge OS sync manifest"
    )
    parser.add_argument("manifest", type=Path, help="Path to a supported versioned JSON manifest")
    args = parser.parse_args()

    manifest = SyncManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
    graph = get_graph()
    try:
        graph.verify()
        result = graph.ingest_manifest(manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        graph.close()


if __name__ == "__main__":
    main()
