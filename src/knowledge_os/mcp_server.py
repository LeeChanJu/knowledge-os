from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from urllib.parse import quote

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from knowledge_os.api import app
from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_graph
from knowledge_os.models import AssertionChange


@asynccontextmanager
async def _knowledge_service_lifespan(_: MCPServer) -> AsyncIterator[None]:
    """Own the local ASGI service once for the lifetime of a stdio session."""
    if get_settings().mcp_base_url:
        yield
        return
    try:
        async with app.router.lifespan_context(app):
            yield
    finally:
        # FastAPI closes the cached GraphStore at shutdown. Forget that closed
        # instance so a later in-process session recreates it.
        get_graph.cache_clear()


mcp = MCPServer(
    "Knowledge OS",
    instructions=(
        "Read governed knowledge and create review-only Proposals and Action requests through "
        "the Knowledge Service. "
        "Sources remain systems of record; this server exposes no direct Cypher, canonical "
        "promotion, Action execution, ingestion, or external-system mutation."
    ),
    lifespan=_knowledge_service_lifespan,
)


def _access_params() -> list[tuple[str, str]]:
    settings = get_settings()
    principals = sorted(
        {item.strip() for item in settings.mcp_principals.split(",") if item.strip()}
    )
    if not principals:
        raise ValueError("MCP_PRINCIPALS must contain at least one principal")
    return [("workspace_id", settings.mcp_workspace_id), *[("principal", p) for p in principals]]


def _access_payload() -> dict[str, Any]:
    settings = get_settings()
    principals = [value for key, value in _access_params() if key == "principal"]
    return {"workspace_id": settings.mcp_workspace_id, "principals": principals}


def _actor() -> str:
    settings = get_settings()
    principals = _access_payload()["principals"]
    if settings.mcp_actor:
        if settings.mcp_actor not in principals:
            raise ValueError("MCP_ACTOR must be one of MCP_PRINCIPALS")
        return settings.mcp_actor
    if len(principals) != 1:
        raise ValueError("MCP_ACTOR is required when MCP_PRINCIPALS contains multiple identities")
    return principals[0]


def _path_segment(value: str) -> str:
    return quote(value, safe=":")


def _configured_action_principals(value: str, setting_name: str) -> list[str]:
    principals = sorted({item.strip() for item in value.split(",") if item.strip()})
    if not principals:
        raise ValueError(f"{setting_name} must contain at least one principal")
    return principals


def _action_policy_version(action_type: str) -> str:
    settings = get_settings()
    configured = settings.mcp_action_policy_versions.strip()
    if not configured:
        return settings.mcp_action_policy_version
    policies: dict[str, str] = {}
    for item in configured.split(","):
        action, separator, version = item.strip().partition("=")
        if (
            separator != "="
            or not action
            or not version
            or action in policies
            or not action.replace("_", "").isalnum()
            or action != action.upper()
        ):
            raise ValueError("MCP_ACTION_POLICY_VERSIONS must contain unique ACTION_TYPE=version")
        policies[action] = version
    if action_type not in policies:
        raise ValueError(f"no configured Action policy for {action_type}")
    return policies[action_type]


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    settings = get_settings()
    if settings.mcp_base_url:
        transport = None
        base_url = settings.mcp_base_url.rstrip("/")
    else:
        transport = httpx.ASGITransport(app=app)
        base_url = "http://knowledge-os.local"
    async with httpx.AsyncClient(
        transport=transport,
        base_url=base_url,
        timeout=settings.mcp_timeout_seconds,
    ) as client:
        response = await client.request(method, path, **kwargs)
    if response.is_error:
        raise ToolError(f"Knowledge Service returned HTTP {response.status_code}")
    return response.json()


@mcp.tool()
async def search_knowledge(
    query: Annotated[str, Field(min_length=1)],
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
) -> dict:
    """Search authorized evidence using the stable keyword retrieval contract."""
    return await _request(
        "GET", "/v1/search", params=[("q", query), ("limit", str(limit)), *_access_params()]
    )


@mcp.tool()
async def search_entities(
    query: Annotated[str, Field(min_length=1)],
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
    as_of: str | None = None,
) -> dict:
    """Discover authorized Entity IDs through traced graph retrieval."""
    params = [("q", query), ("limit", str(limit)), *_access_params()]
    if as_of is not None:
        params.append(("as_of", as_of))
    return await _request("GET", "/v1/entities/search", params=params)


@mcp.tool()
async def retrieve_knowledge(
    query: Annotated[str, Field(min_length=1)],
    mode: Annotated[str, Field(pattern=r"^(keyword|semantic|hybrid)$")] = "keyword",
    embedding: Annotated[list[float], Field(min_length=1, max_length=4096)] | None = None,
    embedding_model: str | None = None,
    embedding_version: str | None = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
) -> dict:
    """Run the stable keyword, semantic, or hybrid contract with adapter-supplied embeddings."""
    return await _request(
        "POST",
        "/v1/retrieval/query",
        json={
            "query": query,
            "mode": mode,
            "embedding": embedding,
            "embedding_model": embedding_model,
            "embedding_version": embedding_version,
            "limit": limit,
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def get_retrieval_capabilities() -> dict:
    """Discover authorized retrieval modes, dimensions, and available embedding versions."""
    return await _request("GET", "/v1/retrieval/capabilities", params=_access_params())


@mcp.tool()
async def get_retrieval_trace(
    trace_id: Annotated[str, Field(min_length=1)],
) -> dict:
    """Read one retrieval trace when it belongs to this MCP server's fixed access context."""
    return await _request("GET", f"/v1/traces/{_path_segment(trace_id)}", params=_access_params())


@mcp.tool()
async def record_retrieval_feedback(
    trace_id: Annotated[str, Field(min_length=1)],
    rating: Annotated[int, Field(ge=-1, le=1)] | None = None,
    comment: Annotated[str, Field(min_length=1, max_length=4000)] | None = None,
) -> dict:
    """Attach bounded feedback to an authorized trace without changing canonical knowledge."""
    if rating is None and comment is None:
        raise ValueError("rating or comment is required")
    return await _request(
        "POST",
        "/v1/feedback",
        json={
            "trace_id": trace_id,
            "rating": rating,
            "comment": comment,
            "actor": _actor(),
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def list_sources(
    limit: Annotated[int, Field(ge=1, le=100)] = 100,
) -> list[dict]:
    """List authorized Sources and their sync status through the stable Source contract."""
    return await _request("GET", "/v1/sources", params=[("limit", str(limit)), *_access_params()])


@mcp.tool()
async def get_source(source_id: Annotated[str, Field(min_length=1)]) -> dict:
    """Read one authorized Source with its current Document catalog and checkpoint metadata."""
    return await _request("GET", f"/v1/sources/{_path_segment(source_id)}", params=_access_params())


@mcp.tool()
async def list_documents(
    source_id: str | None = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 100,
) -> list[dict]:
    """List authorized current Documents, optionally restricted to one Source."""
    params = [("limit", str(limit)), *_access_params()]
    if source_id is not None:
        params.append(("source_id", source_id))
    return await _request("GET", "/v1/documents", params=params)


@mcp.tool()
async def get_document(document_id: Annotated[str, Field(min_length=1)]) -> dict:
    """Read authorized immutable DocumentVersion metadata without bulk Chunk bodies."""
    return await _request(
        "GET",
        f"/v1/documents/{_path_segment(document_id)}",
        params=[("include_chunks", "false"), *_access_params()],
    )


@mcp.tool()
async def get_evidence(
    chunk_ids: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1, max_length=100)
    ],
) -> dict:
    """Fetch an all-or-nothing authorized bundle of exact evidence Chunks."""
    return await _request(
        "POST",
        "/v1/evidence/bundle",
        json={
            "chunk_ids": chunk_ids,
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def get_entity(
    entity_id: Annotated[str, Field(min_length=1)], as_of: str | None = None
) -> dict:
    """Read an authorized Entity and its evidence, optionally at an ISO-8601 instant."""
    params = _access_params()
    if as_of is not None:
        params.append(("as_of", as_of))
    return await _request("GET", f"/v1/entities/{_path_segment(entity_id)}", params=params)


@mcp.tool()
async def get_neighbors(
    entity_id: Annotated[str, Field(min_length=1)],
    limit: Annotated[int, Field(ge=1, le=200)] = 50,
    as_of: str | None = None,
) -> list[dict]:
    """Read authorized graph neighbors without exposing Cypher."""
    params = [("limit", str(limit)), *_access_params()]
    if as_of is not None:
        params.append(("as_of", as_of))
    return await _request(
        "GET", f"/v1/entities/{_path_segment(entity_id)}/neighbors", params=params
    )


@mcp.tool()
async def get_assertion(
    assertion_id: Annotated[str, Field(min_length=1)], as_of: str | None = None
) -> dict:
    """Read an authorized canonical Assertion and evidence, optionally at an ISO-8601 instant."""
    params = _access_params()
    if as_of is not None:
        params.append(("as_of", as_of))
    return await _request("GET", f"/v1/assertions/{_path_segment(assertion_id)}", params=params)


@mcp.tool()
async def get_decision(
    decision_id: Annotated[str, Field(min_length=1)], as_of: str | None = None
) -> dict:
    """Read an authorized canonical Decision and evidence, optionally at an ISO-8601 instant."""
    params = _access_params()
    if as_of is not None:
        params.append(("as_of", as_of))
    return await _request("GET", f"/v1/decisions/{_path_segment(decision_id)}", params=params)


@mcp.tool()
async def get_event(
    event_id: Annotated[str, Field(min_length=1)], as_of: str | None = None
) -> dict:
    """Read an authorized canonical semantic Event, optionally at an ISO-8601 instant."""
    params = _access_params()
    if as_of is not None:
        params.append(("as_of", as_of))
    return await _request("GET", f"/v1/events/{_path_segment(event_id)}", params=params)


@mcp.tool()
async def get_ontology() -> dict:
    """Return the active versioned ontology used for governed proposals."""
    return await _request("GET", "/v1/ontology")


@mcp.tool()
async def get_contracts() -> dict:
    """Discover stable contract versions and evidence-backed change-control rules."""
    return await _request("GET", "/v1/contracts")


@mcp.tool()
async def get_extraction_prompt(name: Annotated[str, Field(min_length=1)]) -> dict:
    """Return one checksum-verified extraction prompt and its output contract."""
    return await _request("GET", f"/v1/prompts/{_path_segment(name)}")


@mcp.tool()
async def propose_assertions(
    changes: Annotated[list[AssertionChange], Field(min_length=1, max_length=50)],
    reason: str | None = None,
    ontology_version: Annotated[str, Field(min_length=1)] = "1.0.0",
) -> dict:
    """Create an evidence-linked assertion Proposal; this never creates canonical knowledge."""
    settings = get_settings()
    return await _request(
        "POST",
        "/v1/proposals",
        json={
            "changes": [change.model_dump(mode="json") for change in changes],
            "workspace_id": settings.mcp_workspace_id,
            "created_by": _actor(),
            "reason": reason,
            "ontology_version": ontology_version,
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def propose_decision(
    title: Annotated[str, Field(min_length=1)],
    statement: Annotated[str, Field(min_length=1)],
    evidence_chunk_ids: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1, max_length=100)
    ],
    decided_at: str | None = None,
    decided_on: str | None = None,
    participants: Annotated[list[Annotated[str, Field(min_length=1)]], Field(max_length=100)]
    | None = None,
    reason: str | None = None,
    ontology_version: Annotated[str, Field(min_length=1)] = "1.0.0",
    valid_from: str | None = None,
    valid_to: str | None = None,
    supersedes_decision_id: str | None = None,
) -> dict:
    """Create an evidence-linked Decision Proposal; approval remains outside this adapter."""
    settings = get_settings()
    return await _request(
        "POST",
        "/v1/decisions/proposals",
        json={
            "workspace_id": settings.mcp_workspace_id,
            "title": title,
            "statement": statement,
            "decided_at": decided_at,
            "decided_on": decided_on,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "evidence_chunk_ids": evidence_chunk_ids,
            "participants": participants or [],
            "proposed_by": _actor(),
            "reason": reason,
            "ontology_version": ontology_version,
            "supersedes_decision_id": supersedes_decision_id,
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def propose_event(
    title: Annotated[str, Field(min_length=1)],
    description: Annotated[str, Field(min_length=1)],
    event_type: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]*$")],
    occurred_at: Annotated[str, Field(min_length=1)],
    evidence_chunk_ids: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1, max_length=100)
    ],
    participants: Annotated[list[Annotated[str, Field(min_length=1)]], Field(max_length=100)]
    | None = None,
    reason: str | None = None,
    ontology_version: Annotated[str, Field(min_length=1)] = "1.0.0",
    ended_at: str | None = None,
    supersedes_event_id: str | None = None,
) -> dict:
    """Create an evidence-linked Event Proposal; approval remains outside this adapter."""
    settings = get_settings()
    return await _request(
        "POST",
        "/v1/events/proposals",
        json={
            "workspace_id": settings.mcp_workspace_id,
            "title": title,
            "description": description,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "ended_at": ended_at,
            "evidence_chunk_ids": evidence_chunk_ids,
            "participants": participants or [],
            "proposed_by": _actor(),
            "reason": reason,
            "ontology_version": ontology_version,
            "supersedes_event_id": supersedes_event_id,
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def list_proposals(
    status: Annotated[str | None, Field(pattern=r"^(PROPOSED|APPROVED|REJECTED)$")] = "PROPOSED",
    proposal_type: Annotated[str | None, Field(pattern=r"^(ASSERTION|DECISION|EVENT)$")] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> list[dict]:
    """List only Proposals whose complete Evidence remains authorized."""
    params = [("limit", str(limit)), *_access_params()]
    if status is not None:
        params.append(("status", status))
    if proposal_type is not None:
        params.append(("proposal_type", proposal_type))
    return await _request("GET", "/v1/proposals", params=params)


@mcp.tool()
async def get_proposal(proposal_id: Annotated[str, Field(min_length=1)]) -> dict:
    """Read one authorized Proposal, Evidence lineage, and immutable review history."""
    return await _request(
        "GET", f"/v1/proposals/{_path_segment(proposal_id)}", params=_access_params()
    )


@mcp.tool()
async def request_action(
    action_type: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]*$")],
    target: Annotated[str, Field(min_length=1)],
    idempotency_key: Annotated[str, Field(min_length=1, max_length=200)],
    parameters: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict:
    """Create a review-required Action request; this never approves or executes it."""
    settings = get_settings()
    review_principals = _configured_action_principals(
        settings.mcp_action_review_principals, "MCP_ACTION_REVIEW_PRINCIPALS"
    )
    execution_principals = _configured_action_principals(
        settings.mcp_action_execution_principals, "MCP_ACTION_EXECUTION_PRINCIPALS"
    )
    return await _request(
        "POST",
        "/v1/actions",
        json={
            "action_type": action_type,
            "target": target,
            "parameters": parameters or {},
            "requested_by": _actor(),
            "workspace_id": settings.mcp_workspace_id,
            "reason": reason,
            "policy_version": _action_policy_version(action_type),
            "approval_required": True,
            "review_principals": review_principals,
            "execution_principals": execution_principals,
            "idempotency_key": idempotency_key,
            "access": _access_payload(),
        },
    )


@mcp.tool()
async def list_actions(
    status: Annotated[str | None, Field(pattern=r"^(PROPOSED|APPROVED|REJECTED)$")] = None,
    action_type: Annotated[str | None, Field(pattern=r"^[A-Z][A-Z0-9_]*$")] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> list[dict]:
    """List authorized governed Actions without exposing approval or execution capabilities."""
    params = [("limit", str(limit)), *_access_params()]
    if status is not None:
        params.append(("status", status))
    if action_type is not None:
        params.append(("action_type", action_type))
    return await _request("GET", "/v1/actions", params=params)


@mcp.tool()
async def get_action(action_id: Annotated[str, Field(min_length=1)]) -> dict:
    """Read one authorized Action and its immutable decision and execution history."""
    return await _request("GET", f"/v1/actions/{_path_segment(action_id)}", params=_access_params())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
