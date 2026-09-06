from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_graph


def main() -> None:
    graph = get_graph()
    try:
        graph.verify()
        applied = graph.migrate(get_settings().migrations_path)
        if applied:
            print(f"Neo4j migrations applied: {', '.join(applied)}")
        else:
            print("Neo4j migrations already current")
    finally:
        graph.close()


if __name__ == "__main__":
    main()
