from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from knowledge_os.dependencies import get_ops


@contextmanager
def observe_connector_run(
    operation: str,
    *,
    workspace_id: str,
    source_type: str,
    connector_id: str,
) -> Iterator[None]:
    """Record a source-adapter boundary without retaining source IDs or content."""
    started = perf_counter()
    ops = get_ops()
    context = {
        "workspace_id": workspace_id,
        "source_type": source_type,
        "connector_id": connector_id,
        "adapter_contract": "source-adapter-observation-v1",
    }
    try:
        yield
    except Exception as exc:
        error_id = ops.error(
            operation,
            exc,
            safe_message="source adapter run failed",
            **context,
        )
        ops.telemetry(operation, "ERROR", started, error_id=error_id, **context)
        exc.add_note(f"Recorded connector error: {error_id}")
        raise
    else:
        ops.telemetry(operation, "SUCCESS", started, **context)
