import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest
from mcp import Client
from pydantic import ValidationError

import knowledge_os.api as api_module
import knowledge_os.connector_observation as connector_observation_module
import knowledge_os.mcp_server as mcp_module
import knowledge_os.review_cli as review_module
from knowledge_os.config import get_settings
from knowledge_os.connector_observation import observe_connector_run
from knowledge_os.contracts import ContractRegistry
from knowledge_os.doctor import (
    GRAPH_CHECKS,
    audit_evaluation_access,
    audit_feedback_access,
    audit_migrations,
    audit_vector_index,
)
from knowledge_os.evaluate import run_suite, suite_fingerprint
from knowledge_os.file_connector import build_manifest, extract_file, load_state, write_state
from knowledge_os.google_drive_connector import (
    DriveFileSnapshot,
    GoogleDriveAPI,
    application_default_credentials_path,
    authorization_snapshot,
    refresh_google_access_token,
    resolve_google_drive_token,
    snapshot_folder,
)
from knowledge_os.google_drive_connector import (
    build_manifest as build_google_drive_manifest,
)
from knowledge_os.graph import (
    GraphStore,
    embedding_fingerprint,
    literal_fulltext_query,
    proposal_identity,
    rerank_keyword_results,
    source_metadata_fingerprint,
    validate_initial_manifest_inventory,
)
from knowledge_os.ids import (
    access_fingerprint,
    content_hash,
    document_id,
    processing_fingerprint,
    source_id,
    stable_id,
)
from knowledge_os.models import (
    AccessContext,
    ActionCreate,
    ActionExecutionClaimCreate,
    ActionExecutionCreate,
    AssertionChange,
    DecisionProposalCreate,
    DocumentTombstoneRequest,
    EmbeddingUpsert,
    EntityRef,
    EventProposalCreate,
    EvidenceBundleRequest,
    FeedbackCreate,
    ProposalDecision,
    RetrievalEvaluationCase,
    RetrievalEvaluationSuite,
    RetrievalQuery,
    SyncCheckpointCommit,
    SyncManifest,
    TextIngestionRequest,
)
from knowledge_os.notion_connector import (
    NOTION_API_VERSION,
    NotionAPI,
    NotionPageSnapshot,
    notion_token_path,
    resolve_notion_token,
    snapshot_page_tree,
)
from knowledge_os.notion_connector import (
    build_manifest as build_notion_manifest,
)
from knowledge_os.notion_connector import (
    normalize_id as normalize_notion_id,
)
from knowledge_os.ontology import Ontology
from knowledge_os.ops import OpsStore
from knowledge_os.prompts import PromptRegistry
from knowledge_os.recovery import _backup_sqlite, create_backup, verify_backup


@pytest.fixture
def ontology() -> Ontology:
    return Ontology.load(__import__("pathlib").Path("config/ontology.yaml"))


def test_stable_contract_registry_is_complete():
    registry = ContractRegistry.load(__import__("pathlib").Path("config/contracts.yaml"))
    assert set(registry.contracts) == {
        "source",
        "evidence",
        "knowledge",
        "governance",
        "retrieval",
        "action",
    }
    assert registry.change_control["highest_order_rule"].startswith(
        "Do not redesign working foundations without evidence."
    )
    assert registry.version == "1.37.0"
    assert registry.contracts["source"] == "source-v12"
    assert registry.contracts["evidence"] == "evidence-v2"
    assert registry.contracts["knowledge"] == "knowledge-v5"
    assert registry.contracts["governance"] == "governance-v8"
    assert registry.contracts["action"] == "action-v6"
    assert registry.contracts["retrieval"] == "retrieval-v11"


def test_migration_path_is_part_of_runtime_settings(monkeypatch, tmp_path):
    from knowledge_os.config import Settings

    migrations = tmp_path / "versioned-migrations"
    monkeypatch.setenv("MIGRATIONS_PATH", str(migrations))

    assert Settings().migrations_path == migrations


def test_evidence_bundle_request_is_bounded_and_deterministic():
    request = EvidenceBundleRequest(
        chunk_ids=["chunk:b", "chunk:a", "chunk:b"],
        access=AccessContext(workspace_id="personal", principals=["local-user"]),
    )
    assert request.chunk_ids == ["chunk:a", "chunk:b"]
    with pytest.raises(ValidationError):
        EvidenceBundleRequest(chunk_ids=[])
    with pytest.raises(ValidationError):
        EvidenceBundleRequest(chunk_ids=[""])


def test_doctor_requires_exactly_one_governed_parent_per_approval():
    check = GRAPH_CHECKS["approval_has_one_governed_parent"]
    assert "parent_count <> 1" in check
    assert "parent:Proposal OR parent:Action" in check


def test_doctor_requires_exactly_one_source_parent_per_operational_event():
    check = GRAPH_CHECKS["operational_event_has_one_source_parent"]
    assert "event.event_class <> 'SEMANTIC'" in check
    assert "parent_count <> 1" in check
    assert "parent:Source OR parent:Document" in check


def test_source_metadata_integrity_check_accepts_current_contract():
    check = GRAPH_CHECKS["versioned_source_metadata_is_complete"]
    assert "source-v12" in check
    assert "source_metadata_hash" in check


def test_empty_initial_manifest_cannot_checkpoint_existing_active_documents():
    with pytest.raises(ValueError, match="empty initial manifest"):
        validate_initial_manifest_inventory(
            record_count=0,
            existing_active_documents=12,
            current_cursor=None,
            expected_previous_cursor=None,
        )
    for values in (
        {
            "record_count": 1,
            "existing_active_documents": 12,
            "current_cursor": None,
            "expected_previous_cursor": None,
        },
        {
            "record_count": 0,
            "existing_active_documents": 0,
            "current_cursor": None,
            "expected_previous_cursor": None,
        },
        {
            "record_count": 0,
            "existing_active_documents": 12,
            "current_cursor": "cursor:old",
            "expected_previous_cursor": "cursor:old",
        },
    ):
        validate_initial_manifest_inventory(**values)


def test_version_write_collapses_previous_chunk_rows_before_single_result():
    import inspect

    query_source = inspect.getsource(GraphStore._write_version)
    assert "SET previous_chunk.active=false\n            WITH DISTINCT d, previous" in query_source


def test_mcp_adapter_exposes_only_bounded_reads_and_governed_requests(monkeypatch):
    async def inspect():
        async with Client(mcp_module.mcp) as client:
            result = await client.list_tools()
            return {tool.name: tool for tool in result.tools}

    # Tool discovery must remain independent of a live Neo4j instance.
    monkeypatch.setenv("MCP_BASE_URL", "http://unused.invalid")
    get_settings.cache_clear()
    try:
        tools = asyncio.run(inspect())
    finally:
        get_settings.cache_clear()
    assert set(tools) == {
        "search_knowledge",
        "search_entities",
        "retrieve_knowledge",
        "get_retrieval_capabilities",
        "get_retrieval_trace",
        "record_retrieval_feedback",
        "list_sources",
        "get_source",
        "list_documents",
        "get_document",
        "get_evidence",
        "get_entity",
        "get_neighbors",
        "get_assertion",
        "get_decision",
        "get_event",
        "get_ontology",
        "get_contracts",
        "get_extraction_prompt",
        "propose_assertions",
        "propose_decision",
        "propose_event",
        "list_proposals",
        "get_proposal",
        "request_action",
        "list_actions",
        "get_action",
    }
    assert tools["get_evidence"].input_schema["properties"]["chunk_ids"]["maxItems"] == 100
    assert tools["list_sources"].input_schema["properties"]["limit"]["maximum"] == 100
    assert tools["list_documents"].input_schema["properties"]["limit"]["maximum"] == 100
    assert (
        tools["retrieve_knowledge"].input_schema["properties"]["embedding"]["anyOf"][0]["maxItems"]
        == 4096
    )
    assert (
        tools["record_retrieval_feedback"].input_schema["properties"]["comment"]["anyOf"][0][
            "maxLength"
        ]
        == 4000
    )
    assert tools["propose_assertions"].input_schema["properties"]["changes"]["maxItems"] == 50
    assert not any(
        word in name
        for name in tools
        for word in ("approve", "reject", "execute", "ingest", "tombstone")
    )


def test_mcp_defaults_to_host_owned_in_process_knowledge_service():
    from knowledge_os.config import Settings

    assert Settings(_env_file=None).mcp_base_url is None


def test_mcp_request_uses_in_process_asgi_by_default(monkeypatch):
    from fastapi import FastAPI

    local_app = FastAPI()

    @local_app.get("/proof")
    def proof():
        return {"transport": "asgi"}

    monkeypatch.delenv("MCP_BASE_URL", raising=False)
    monkeypatch.setattr(mcp_module, "app", local_app)
    get_settings.cache_clear()
    try:
        result = asyncio.run(mcp_module._request("GET", "/proof"))
    finally:
        get_settings.cache_clear()
    assert result == {"transport": "asgi"}


def test_mcp_maps_expected_service_denials_to_deliberate_tool_errors(monkeypatch):
    from fastapi import FastAPI
    from mcp.server.mcpserver.exceptions import ToolError

    local_app = FastAPI()

    @local_app.get("/denied")
    def denied():
        return __import__("fastapi").responses.JSONResponse(
            status_code=404, content={"private_detail": "must-not-cross-adapter"}
        )

    monkeypatch.delenv("MCP_BASE_URL", raising=False)
    monkeypatch.setattr(mcp_module, "app", local_app)
    get_settings.cache_clear()
    try:
        with pytest.raises(ToolError) as exc_info:
            asyncio.run(mcp_module._request("GET", "/denied"))
    finally:
        get_settings.cache_clear()
    assert str(exc_info.value) == "Knowledge Service returned HTTP 404"
    assert "private_detail" not in str(exc_info.value)


def test_dynamic_adapter_ids_cannot_escape_their_url_path_segment():
    assert mcp_module._path_segment("source:abc") == "source:abc"
    assert mcp_module._path_segment("../../health") == "..%2F..%2Fhealth"
    assert mcp_module._path_segment("%2e%2e/health") == "%252e%252e%2Fhealth"
    assert review_module._path_segment("action:abc/approve") == "action:abc%2Fapprove"

    for base, value, encoder in (
        ("/v1/sources/", "../../health", mcp_module._path_segment),
        ("/v1/actions/", "../proposal", review_module._path_segment),
    ):
        request = httpx.Request("GET", f"http://knowledge-os.local{base}{encoder(value)}")
        assert request.url.raw_path.decode().startswith(base)


def test_mcp_access_context_comes_from_server_environment(monkeypatch):
    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "principal:b, principal:a,principal:b")
    get_settings.cache_clear()
    try:
        assert mcp_module._access_params() == [
            ("workspace_id", "customer-a"),
            ("principal", "principal:a"),
            ("principal", "principal:b"),
        ]
    finally:
        get_settings.cache_clear()


def test_mcp_retrieval_modes_preserve_adapter_embedding_and_fixed_access(monkeypatch):
    captured = {}

    async def request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {"mode": "hybrid", "results": []}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "source:user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        result = asyncio.run(
            mcp_module.retrieve_knowledge(
                "context graph",
                mode="hybrid",
                embedding=[0.1, 0.2],
                embedding_model="replaceable-model",
                embedding_version="2026-09-05",
                limit=7,
            )
        )
    finally:
        get_settings.cache_clear()
    assert result == {"mode": "hybrid", "results": []}
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/retrieval/query"
    assert captured["json"] == {
        "query": "context graph",
        "mode": "hybrid",
        "embedding": [0.1, 0.2],
        "embedding_model": "replaceable-model",
        "embedding_version": "2026-09-05",
        "limit": 7,
        "access": {"workspace_id": "customer-a", "principals": ["source:user:alice"]},
    }


def test_mcp_entity_search_is_traced_and_scoped_by_fixed_access(monkeypatch):
    captured = {}

    async def request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {"mode": "graph", "results": []}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        result = asyncio.run(
            mcp_module.search_entities("Neo4j", limit=7, as_of="2026-09-05T00:00:00Z")
        )
    finally:
        get_settings.cache_clear()

    assert result == {"mode": "graph", "results": []}
    assert captured == {
        "method": "GET",
        "path": "/v1/entities/search",
        "params": [
            ("q", "Neo4j"),
            ("limit", "7"),
            ("workspace_id", "customer-a"),
            ("principal", "user:alice"),
            ("as_of", "2026-09-05T00:00:00Z"),
        ],
    }


def test_mcp_retrieval_capabilities_are_scoped_by_fixed_access(monkeypatch):
    captured = {}

    async def request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {
            "semantic_available": False,
            "embedded_chunks": 0,
            "graph_available": False,
            "accessible_entities": 0,
        }

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "source:user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        result = asyncio.run(mcp_module.get_retrieval_capabilities())
    finally:
        get_settings.cache_clear()
    assert result == {
        "semantic_available": False,
        "embedded_chunks": 0,
        "graph_available": False,
        "accessible_entities": 0,
    }
    assert captured == {
        "method": "GET",
        "path": "/v1/retrieval/capabilities",
        "params": [
            ("workspace_id", "customer-a"),
            ("principal", "source:user:alice"),
        ],
    }


def test_mcp_contract_discovery_uses_stable_service_endpoint(monkeypatch):
    captured = {}

    async def request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {"version": "1.32.0"}

    monkeypatch.setattr(mcp_module, "_request", request)
    result = asyncio.run(mcp_module.get_contracts())

    assert result == {"version": "1.32.0"}
    assert captured == {"method": "GET", "path": "/v1/contracts"}


def test_mcp_retrieval_trace_and_feedback_use_fixed_identity(monkeypatch):
    requests = []

    async def request(method, path, **kwargs):
        requests.append({"method": method, "path": path, **kwargs})
        return {"trace_id": "trace:one"}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "source:user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        trace = asyncio.run(mcp_module.get_retrieval_trace("trace:one"))
        feedback = asyncio.run(
            mcp_module.record_retrieval_feedback(
                "trace:one", rating=-1, comment="The supporting source was missing."
            )
        )
        with pytest.raises(ValueError, match="rating or comment"):
            asyncio.run(mcp_module.record_retrieval_feedback("trace:one"))
    finally:
        get_settings.cache_clear()

    assert trace == {"trace_id": "trace:one"}
    assert feedback == {"trace_id": "trace:one"}
    assert requests == [
        {
            "method": "GET",
            "path": "/v1/traces/trace:one",
            "params": [
                ("workspace_id", "customer-a"),
                ("principal", "source:user:alice"),
            ],
        },
        {
            "method": "POST",
            "path": "/v1/feedback",
            "json": {
                "trace_id": "trace:one",
                "rating": -1,
                "comment": "The supporting source was missing.",
                "actor": "source:user:alice",
                "access": {
                    "workspace_id": "customer-a",
                    "principals": ["source:user:alice"],
                },
            },
        },
    ]


def test_mcp_source_and_document_catalogs_use_fixed_access(monkeypatch):
    requests = []

    async def request(method, path, **kwargs):
        requests.append({"method": method, "path": path, **kwargs})
        return {"path": path}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        asyncio.run(mcp_module.list_sources(limit=7))
        asyncio.run(mcp_module.get_source("source:one"))
        asyncio.run(mcp_module.list_documents(source_id="source:one", limit=8))
        asyncio.run(mcp_module.get_document("document:one"))
    finally:
        get_settings.cache_clear()

    access = [("workspace_id", "customer-a"), ("principal", "user:alice")]
    assert requests == [
        {"method": "GET", "path": "/v1/sources", "params": [("limit", "7"), *access]},
        {"method": "GET", "path": "/v1/sources/source:one", "params": access},
        {
            "method": "GET",
            "path": "/v1/documents",
            "params": [("limit", "8"), *access, ("source_id", "source:one")],
        },
        {
            "method": "GET",
            "path": "/v1/documents/document:one",
            "params": [("include_chunks", "false"), *access],
        },
    ]


def test_mcp_canonical_reads_use_fixed_access_and_as_of(monkeypatch):
    requests = []

    async def request(method, path, **kwargs):
        requests.append({"method": method, "path": path, **kwargs})
        return {"path": path}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        asyncio.run(mcp_module.get_assertion("assertion:one"))
        asyncio.run(mcp_module.get_decision("decision:one", as_of="2026-09-05T00:00:00Z"))
        asyncio.run(mcp_module.get_event("event:one"))
    finally:
        get_settings.cache_clear()

    access = [("workspace_id", "customer-a"), ("principal", "user:alice")]
    assert requests == [
        {"method": "GET", "path": "/v1/assertions/assertion:one", "params": access},
        {
            "method": "GET",
            "path": "/v1/decisions/decision:one",
            "params": [*access, ("as_of", "2026-09-05T00:00:00Z")],
        },
        {"method": "GET", "path": "/v1/events/event:one", "params": access},
    ]


def test_feedback_actor_is_derived_from_or_bound_to_access_context():
    access = AccessContext(workspace_id="personal", principals=["user:alice"])
    derived = FeedbackCreate(trace_id="trace:one", rating=1, access=access)
    explicit = FeedbackCreate(
        trace_id="trace:one", comment="Useful evidence", actor="user:alice", access=access
    )

    assert derived.actor == "user:alice"
    assert explicit.actor == "user:alice"

    with pytest.raises(ValidationError, match="actor must be one of access principals"):
        FeedbackCreate(trace_id="trace:one", rating=-1, actor="user:mallory", access=access)
    with pytest.raises(ValidationError, match="actor is required"):
        FeedbackCreate(
            trace_id="trace:one",
            rating=0,
            access=AccessContext(principals=["group:delivery", "user:alice"]),
        )
    with pytest.raises(ValidationError):
        FeedbackCreate(trace_id="trace:one", comment="x" * 4001, access=access)


def test_mcp_proposal_injects_single_authenticated_actor(monkeypatch):
    captured = {}

    async def request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {"status": "PROPOSED"}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "source:user:alice")
    monkeypatch.delenv("MCP_ACTOR", raising=False)
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        result = asyncio.run(
            mcp_module.propose_assertions(
                [
                    AssertionChange(
                        subject=EntityRef(name="Knowledge OS", entity_type="Project"),
                        predicate="USES",
                        object=EntityRef(name="Neo4j", entity_type="Technology"),
                        evidence_chunk_id="chunk:1",
                        extractor_version="agent:model:prompt-v1",
                    )
                ],
                reason="Evidence-backed extraction",
            )
        )
    finally:
        get_settings.cache_clear()
    assert result == {"status": "PROPOSED"}
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/proposals"
    assert captured["json"]["workspace_id"] == "customer-a"
    assert captured["json"]["created_by"] == "source:user:alice"
    assert captured["json"]["access"] == {
        "workspace_id": "customer-a",
        "principals": ["source:user:alice"],
    }


def test_mcp_actor_fails_closed_when_identity_is_ambiguous_or_unbound(monkeypatch):
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice,group:delivery")
    monkeypatch.delenv("MCP_ACTOR", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="required"):
        mcp_module._actor()

    monkeypatch.setenv("MCP_ACTOR", "user:mallory")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="must be one of"):
            mcp_module._actor()
    finally:
        get_settings.cache_clear()


def test_mcp_decision_and_event_proposals_inject_access_and_never_review(monkeypatch):
    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"status": "PROPOSED"}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice,group:delivery")
    monkeypatch.setenv("MCP_ACTOR", "user:alice")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        decision = asyncio.run(
            mcp_module.propose_decision(
                title="Architecture boundary",
                statement="Neo4j remains the System of Context.",
                decided_at="2026-09-05T06:00:00Z",
                evidence_chunk_ids=["chunk:1"],
                participants=["user:alice"],
            )
        )
        event = asyncio.run(
            mcp_module.propose_event(
                title="Review completed",
                description="The architecture proposal entered review.",
                event_type="REVIEW_COMPLETED",
                occurred_at="2026-09-05T06:30:00Z",
                evidence_chunk_ids=["chunk:1"],
            )
        )
    finally:
        get_settings.cache_clear()
    assert decision["status"] == event["status"] == "PROPOSED"
    assert [call[1] for call in calls] == [
        "/v1/decisions/proposals",
        "/v1/events/proposals",
    ]
    for method, _, kwargs in calls:
        assert method == "POST"
        assert kwargs["json"]["proposed_by"] == "user:alice"
        assert kwargs["json"]["access"] == {
            "workspace_id": "customer-a",
            "principals": ["group:delivery", "user:alice"],
        }


def test_mcp_action_request_injects_host_policy_and_never_approves(monkeypatch):
    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"id": "action:1", "status": "PROPOSED"}

    monkeypatch.setenv("MCP_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice,group:delivery")
    monkeypatch.setenv("MCP_ACTOR", "user:alice")
    monkeypatch.setenv("MCP_ACTION_REVIEW_PRINCIPALS", "reviewer:b,reviewer:a")
    monkeypatch.setenv("MCP_ACTION_EXECUTION_PRINCIPALS", "connector:notion")
    monkeypatch.setenv("MCP_ACTION_POLICY_VERSION", "customer-action-policy-v3")
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        result = asyncio.run(
            mcp_module.request_action(
                "NOTION_CREATE_PAGE",
                "notion:database:123",
                "agent-request-123",
                {"title": "Draft"},
                "Prepare for human review",
            )
        )
        listed = asyncio.run(mcp_module.list_actions(status="PROPOSED", limit=10))
        detail = asyncio.run(mcp_module.get_action("action:1"))
    finally:
        get_settings.cache_clear()
    assert result == {"id": "action:1", "status": "PROPOSED"}
    action = calls[0][2]["json"]
    assert action["requested_by"] == "user:alice"
    assert action["workspace_id"] == "customer-a"
    assert action["approval_required"] is True
    assert action["review_principals"] == ["reviewer:a", "reviewer:b"]
    assert action["execution_principals"] == ["connector:notion"]
    assert action["policy_version"] == "customer-action-policy-v3"
    assert [call[0:2] for call in calls] == [
        ("POST", "/v1/actions"),
        ("GET", "/v1/actions"),
        ("GET", "/v1/actions/action:1"),
    ]
    for response in (listed, detail):
        assert response == {"id": "action:1", "status": "PROPOSED"}
    assert ("principal", "group:delivery") in calls[1][2]["params"]
    assert ("principal", "user:alice") in calls[2][2]["params"]


def test_mcp_action_request_fails_closed_without_host_capability_policy(monkeypatch):
    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice")
    monkeypatch.delenv("MCP_ACTION_REVIEW_PRINCIPALS", raising=False)
    monkeypatch.delenv("MCP_ACTION_EXECUTION_PRINCIPALS", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="MCP_ACTION_REVIEW_PRINCIPALS"):
            asyncio.run(
                mcp_module.request_action(
                    "NOTION_CREATE_PAGE", "notion:database:123", "agent-request-123"
                )
            )
    finally:
        get_settings.cache_clear()


def test_mcp_action_request_selects_exact_capability_policy(monkeypatch):
    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"id": "action:1", "status": "PROPOSED"}

    monkeypatch.setenv("MCP_PRINCIPALS", "user:alice")
    monkeypatch.setenv("MCP_ACTION_REVIEW_PRINCIPALS", "human:owner")
    monkeypatch.setenv("MCP_ACTION_EXECUTION_PRINCIPALS", "connector:notion")
    monkeypatch.setenv(
        "MCP_ACTION_POLICY_VERSIONS",
        "NOTION_CREATE_PAGE=notion-create-page-policy-v1,"
        "NOTION_ARCHIVE_PAGE=notion-archive-page-policy-v1",
    )
    monkeypatch.setattr(mcp_module, "_request", request)
    get_settings.cache_clear()
    try:
        asyncio.run(
            mcp_module.request_action(
                "NOTION_ARCHIVE_PAGE",
                "notion:page:aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                "archive-request-1",
                {"creation_action_id": "action:create"},
            )
        )
        with pytest.raises(ValueError, match="no configured Action policy"):
            asyncio.run(mcp_module.request_action("UNDECLARED_ACTION", "target", "request-2"))
    finally:
        get_settings.cache_clear()
    assert calls[0][2]["json"]["policy_version"] == "notion-archive-page-policy-v1"


def test_review_cli_requires_explicit_confirmation_before_governance_decision(monkeypatch):
    from argparse import Namespace

    called = False

    async def request(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(review_module, "_request", request)
    args = Namespace(
        command="approve",
        proposal_id="proposal:1",
        reason="Reviewed",
        yes=False,
    )
    with pytest.raises(ValueError, match="require --yes"):
        asyncio.run(review_module._execute(args))
    assert called is False


def test_review_cli_fetches_exact_evidence_and_injects_reviewer(monkeypatch):
    from argparse import Namespace

    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/v1/proposals/proposal:1":
            return {
                "proposal": {"id": "proposal:1", "status": "PROPOSED"},
                "evidence": [{"chunk_id": "chunk:2"}, {"chunk_id": "chunk:1"}],
            }
        if path == "/v1/evidence/bundle":
            return {"evidence": [{"chunk": {"id": "chunk:1"}}]}
        return {"status": "APPROVED"}

    monkeypatch.setenv("REVIEW_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("REVIEW_PRINCIPALS", "group:reviewers,user:alice")
    monkeypatch.setenv("REVIEW_ACTOR", "user:alice")
    monkeypatch.setattr(review_module, "_request", request)
    get_settings.cache_clear()
    try:
        shown = asyncio.run(review_module._proposal("proposal:1", include_text=True))
        approved = asyncio.run(
            review_module._execute(
                Namespace(
                    command="approve",
                    proposal_id="proposal:1",
                    reason="Evidence verified",
                    yes=True,
                )
            )
        )
    finally:
        get_settings.cache_clear()
    assert shown["evidence_bundle"] == [{"chunk": {"id": "chunk:1"}}]
    assert approved == {"status": "APPROVED"}
    assert calls[1][2]["json"]["chunk_ids"] == ["chunk:1", "chunk:2"]
    decision = calls[2][2]["json"]
    assert decision["reviewed_by"] == "user:alice"
    assert decision["access"] == {
        "workspace_id": "customer-a",
        "principals": ["group:reviewers", "user:alice"],
    }


def test_review_cli_reviewer_identity_fails_closed(monkeypatch):
    monkeypatch.setenv("REVIEW_PRINCIPALS", "user:alice,group:reviewers")
    monkeypatch.delenv("REVIEW_ACTOR", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="required"):
        review_module._actor()
    monkeypatch.setenv("REVIEW_ACTOR", "user:mallory")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="must be one of"):
            review_module._actor()
    finally:
        get_settings.cache_clear()


def test_review_cli_actions_use_same_fixed_human_identity_and_confirmation(monkeypatch):
    from argparse import Namespace

    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if method == "GET" and path == "/v1/actions":
            return [{"id": "action:1", "status": "PROPOSED"}]
        if method == "GET":
            return {"action": {"id": "action:1", "status": "PROPOSED"}}
        return {"id": "action:1", "status": "APPROVED"}

    monkeypatch.setenv("REVIEW_WORKSPACE_ID", "customer-a")
    monkeypatch.setenv("REVIEW_PRINCIPALS", "human:owner,group:reviewers")
    monkeypatch.setenv("REVIEW_ACTOR", "human:owner")
    monkeypatch.setattr(review_module, "_request", request)
    get_settings.cache_clear()
    try:
        listed = asyncio.run(
            review_module._execute(
                Namespace(command="action-list", status="PROPOSED", type=None, limit=10)
            )
        )
        shown = asyncio.run(
            review_module._execute(Namespace(command="action-show", action_id="action:1"))
        )
        with pytest.raises(ValueError, match="require --yes"):
            asyncio.run(
                review_module._execute(
                    Namespace(
                        command="action-approve",
                        action_id="action:1",
                        reason="Reviewed",
                        yes=False,
                    )
                )
            )
        approved = asyncio.run(
            review_module._execute(
                Namespace(
                    command="action-approve",
                    action_id="action:1",
                    reason="Capability and target verified",
                    yes=True,
                )
            )
        )
    finally:
        get_settings.cache_clear()
    assert listed == [{"id": "action:1", "status": "PROPOSED"}]
    assert shown["action"]["id"] == "action:1"
    assert approved["status"] == "APPROVED"
    assert [call[0:2] for call in calls] == [
        ("GET", "/v1/actions"),
        ("GET", "/v1/actions/action:1"),
        ("POST", "/v1/actions/action:1/approve"),
    ]
    assert calls[2][2]["json"] == {
        "reviewed_by": "human:owner",
        "reason": "Capability and target verified",
        "access": {
            "workspace_id": "customer-a",
            "principals": ["group:reviewers", "human:owner"],
        },
    }


def test_doctor_checks_embedding_provenance_completeness():
    check = GRAPH_CHECKS["chunk_embedding_has_complete_provenance"]
    for field in (
        "embedding_hash",
        "embedding_model",
        "embedding_version",
        "embedding_created_at",
        "embedding_created_by",
    ):
        assert field in check


def test_doctor_matches_vector_index_to_configured_embedding_contract():
    row = {
        "name": "chunk_embedding_vector",
        "type": "VECTOR",
        "state": "ONLINE",
        "options": {
            "indexConfig": {
                "vector.dimensions": 1536,
                "vector.similarity_function": "COSINE",
            }
        },
    }
    assert audit_vector_index([row], 1536)["status"] == "PASS"
    mismatch = audit_vector_index([row], 768)
    assert mismatch["status"] == "FAIL"
    assert mismatch["details"]["expected"]["dimensions"] == 768
    assert audit_vector_index([], 1536)["status"] == "FAIL"


def test_contract_timestamps_require_timezone_and_normalize_to_utc():
    with pytest.raises(ValidationError, match="timezone info"):
        TextIngestionRequest(
            source_external_id="source",
            document_external_id="document",
            title="Title",
            content="Content",
            source_updated_at="2026-09-05T12:00:00",
        )
    with pytest.raises(ValidationError, match="timezone info"):
        DecisionProposalCreate(
            title="Decision",
            statement="Statement",
            decided_at="2026-09-05T12:00:00",
            evidence_chunk_ids=["chunk:1"],
            proposed_by="user:1",
        )
    with pytest.raises(ValidationError, match="timezone info"):
        ActionExecutionCreate(
            claim_id="claim:1",
            external_idempotency_key="external:1",
            status="SUCCEEDED",
            executed_by="connector:1",
            connector="connector-v1",
            external_api="api.call",
            authorization_ref="credential:1",
            policy_version="policy-v1",
            idempotency_key="attempt:1",
            executed_at="2026-09-05T12:00:00",
        )

    request = TextIngestionRequest(
        source_external_id="source",
        document_external_id="document",
        title="Title",
        content="Content",
        source_updated_at="2026-09-05T21:00:00+09:00",
    )
    assert request.source_updated_at.isoformat() == "2026-09-05T12:00:00+00:00"
    equivalent = TextIngestionRequest(
        source_external_id="source",
        document_external_id="document",
        title="Title",
        content="Content",
        source_updated_at="2026-09-05T12:00:00Z",
    )
    assert request.model_dump(mode="json") == equivalent.model_dump(mode="json")


def test_http_adapter_records_bounded_operational_telemetry(tmp_path, monkeypatch):
    import json

    ops = OpsStore(tmp_path / "http-ops.db")
    monkeypatch.setattr(api_module, "get_ops", lambda: ops)

    async def exercise():
        transport = httpx.ASGITransport(app=api_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return (
                await client.get("/v1/contracts"),
                await client.get("/not-a-real-route"),
                await client.post("/v1/ingestion/text", json={}),
            )

    success, missing, invalid = __import__("asyncio").run(exercise())

    assert success.status_code == 200
    assert success.headers["X-Request-ID"].startswith("request:")
    assert missing.status_code == 404
    assert invalid.status_code == 422
    with ops.connect() as db:
        rows = db.execute(
            "SELECT status, context_json FROM telemetry WHERE operation='http_adapter' ORDER BY id"
        ).fetchall()
    assert [row[0] for row in rows] == ["SUCCESS", "NOT_FOUND", "CLIENT_ERROR"]
    contexts = [json.loads(row[1]) for row in rows]
    assert contexts[0]["route"] == "/v1/contracts"
    assert contexts[1]["route"] == "UNMATCHED"
    assert contexts[2]["route"] == "/v1/ingestion/text"
    assert all("principal" not in context and "body" not in context for context in contexts)


def test_http_adapter_records_unexpected_error_without_request_body(tmp_path, monkeypatch):
    import json

    ops = OpsStore(tmp_path / "http-errors.db")
    monkeypatch.setattr(api_module, "get_ops", lambda: ops)
    monkeypatch.setattr(
        api_module,
        "get_contracts",
        lambda: (_ for _ in ()).throw(RuntimeError("synthetic adapter failure")),
    )

    async def exercise():
        transport = httpx.ASGITransport(app=api_module.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/v1/contracts")

    response = __import__("asyncio").run(exercise())

    assert response.status_code == 500
    with ops.connect() as db:
        error = db.execute(
            "SELECT operation, error_type, message, context_json FROM errors"
        ).fetchone()
        telemetry = db.execute(
            "SELECT status, context_json FROM telemetry WHERE operation='http_adapter'"
        ).fetchone()
    assert error[:2] == ("http_adapter", "RuntimeError")
    assert error[2] == "unhandled HTTP adapter failure"
    assert "synthetic" not in response.text
    assert response.json()["error_id"].startswith("error:")
    assert response.headers["X-Request-ID"] == response.json()["request_id"]
    error_context = json.loads(error[3])
    telemetry_context = json.loads(telemetry[1])
    assert error_context["route"] == "/v1/contracts"
    assert telemetry[0] == "ERROR"
    assert telemetry_context["error_id"].startswith("error:")
    assert "body" not in error_context


def test_retrieval_failure_records_query_hash_not_raw_query(tmp_path, monkeypatch):
    import json

    ops = OpsStore(tmp_path / "retrieval-errors.db")
    graph = GraphStore("bolt://localhost:1", "neo4j", "unused", "neo4j", ops)
    secret_query = "private project codename and customer detail"
    monkeypatch.setattr(
        graph,
        "search",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("driver leaked detail")),
    )
    try:
        with pytest.raises(RuntimeError, match="driver leaked detail"):
            graph.search_traced(
                secret_query,
                access=AccessContext(workspace_id="personal", principals=["local-user"]),
            )
    finally:
        graph.close()

    with ops.connect() as db:
        message, context_json = db.execute("SELECT message, context_json FROM errors").fetchone()
    context = json.loads(context_json)
    assert message == "retrieval failed"
    assert context["query_hash"] == content_hash(secret_query)
    assert secret_query not in context_json
    assert "local-user" not in context_json


def test_recovery_sqlite_backup_is_independent_and_valid(tmp_path):
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"
    with __import__("sqlite3").connect(source) as db:
        db.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
        db.execute("INSERT INTO evidence VALUES ('preserved')")

    _backup_sqlite(source, destination)

    with __import__("sqlite3").connect(destination) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT value FROM evidence").fetchone()[0] == "preserved"


def test_recovery_set_records_contract_git_and_store_evidence(tmp_path, monkeypatch):
    import json

    ops = tmp_path / "ops.db"
    with __import__("sqlite3").connect(ops) as db:
        db.execute("CREATE TABLE audit_log(value TEXT)")
        db.execute("INSERT INTO audit_log VALUES ('kept')")
    admin = tmp_path / "neo4j-admin"
    admin.write_text("placeholder", encoding="utf-8")

    def fake_run(command, env=None, cwd=None):
        if "backup" in command:
            output = next(
                item.split("=", 1)[1] for item in command if item.startswith("--to-path=")
            )
            (__import__("pathlib").Path(output) / "neo4j.backup").write_bytes(b"graph")
            return "Backup command completed."
        if command[1:3] == ["rev-parse", "HEAD"]:
            return "abc123"
        if command[1:3] == ["status", "--porcelain"]:
            return ""
        raise AssertionError(command)

    monkeypatch.setattr("knowledge_os.recovery._run", fake_run)
    destination = create_backup(
        output_root=tmp_path / "backups",
        neo4j_admin=admin,
        database="neo4j",
        ops_db=ops,
        contracts_path=__import__("pathlib").Path("config/contracts.yaml"),
        repository=__import__("pathlib").Path.cwd(),
        graph_evidence={"label_counts": {"Document": 2}},
    )

    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["git"] == {"commit": "abc123", "dirty": False}
    assert manifest["contracts"]["versions"]["source"] == "source-v12"
    assert manifest["neo4j"]["evidence"]["label_counts"] == {"Document": 2}
    assert manifest["sqlite"]["evidence"]["table_counts"] == {"audit_log": 1}
    assert not list((tmp_path / "backups").glob(".*.staging"))


def test_recovery_verifier_detects_tampering(tmp_path, monkeypatch):
    backup = tmp_path / "backup"
    neo4j_dir = backup / "neo4j"
    neo4j_dir.mkdir(parents=True)
    graph = neo4j_dir / "neo4j.backup"
    graph.write_bytes(b"graph")
    ops = backup / "ops.db"
    with __import__("sqlite3").connect(ops) as db:
        db.execute("CREATE TABLE audit(value TEXT)")
    import hashlib
    import json

    manifest = {
        "manifest_version": "1",
        "backup_id": "test",
        "capture_started_at": "2026-09-05T00:00:00+00:00",
        "capture_completed_at": "2026-09-05T00:00:01+00:00",
        "neo4j": {"database": "neo4j", "artifact": "neo4j/neo4j.backup"},
        "sqlite": {"artifact": "ops.db"},
        "files": {
            "neo4j/neo4j.backup": {"sha256": hashlib.sha256(graph.read_bytes()).hexdigest()},
            "ops.db": {"sha256": hashlib.sha256(ops.read_bytes()).hexdigest()},
        },
    }
    (backup / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr("knowledge_os.recovery._run", lambda *args, **kwargs: "consistent")

    assert verify_backup(backup, neo4j_admin=tmp_path / "admin")["status"] == "ok"
    graph.write_bytes(b"tampered")
    report = verify_backup(backup, neo4j_admin=tmp_path / "admin")
    assert report["status"] == "error"
    assert report["checks"][0]["status"] == "FAIL"


def test_recovery_verifier_rejects_manifest_path_escape(tmp_path):
    backup = tmp_path / "backup"
    backup.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("secret", encoding="utf-8")
    import json

    (backup / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "1",
                "backup_id": "test",
                "capture_started_at": "start",
                "capture_completed_at": "end",
                "neo4j": {"database": "neo4j", "artifact": "../outside"},
                "sqlite": {"artifact": "../outside"},
                "files": {"../outside": {"sha256": "irrelevant"}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escapes"):
        verify_backup(backup, neo4j_admin=tmp_path / "admin")


def test_prompt_registry_verifies_versioned_governance_prompts():
    registry = PromptRegistry.load(__import__("pathlib").Path("config/prompts.yaml"))
    assert registry.version == "1.2.0"
    assert set(registry.prompts) == {
        "assertion_extraction",
        "decision_extraction",
        "event_extraction",
    }
    assert registry.prompts["assertion_extraction"].output_contract == "ProposalCreate"
    assert (
        "never mark knowledge verified" in registry.prompts["assertion_extraction"].read_verified()
    )
    assert "reviewer must approve" in registry.prompts["decision_extraction"].read_verified()
    assert "Never invent a" in registry.prompts["decision_extraction"].read_verified()
    assert "canonical semantic `Event`" in registry.prompts["event_extraction"].read_verified()


def test_extraction_context_is_deterministic_and_verified():
    ontology = Ontology.load(__import__("pathlib").Path("config/ontology.yaml"))
    ontology_payload = ontology.as_dict()
    assert ontology_payload["entity_types"] == sorted(ontology_payload["entity_types"])
    assert list(ontology_payload["relation_types"]) == sorted(ontology_payload["relation_types"])

    registry = PromptRegistry.load(__import__("pathlib").Path("config/prompts.yaml"))
    prompt = registry.prompt("assertion_extraction")
    assert prompt["sha256"] == registry.prompts["assertion_extraction"].sha256
    assert prompt["output_contract"] == "ProposalCreate"
    assert "canonical facts" in prompt["content"]
    with pytest.raises(KeyError):
        registry.prompt("missing")


def test_stable_id_is_deterministic():
    assert stable_id("chunk", "doc", 1) == stable_id("chunk", "doc", 1)
    assert stable_id("chunk", "doc", 1) != stable_id("chunk", "doc", 2)


def test_doctor_detects_missing_changed_and_unexpected_migrations(tmp_path):
    first = tmp_path / "001_first.cypher"
    second = tmp_path / "002_second.cypher"
    first.write_text("RETURN 1;")
    second.write_text("RETURN 2;")
    ledger = [
        {"name": first.name, "checksum": content_hash("changed")},
        {"name": "000_removed.cypher", "checksum": content_hash("removed")},
    ]
    result = audit_migrations(ledger, tmp_path)
    assert result["status"] == "FAIL"
    assert result["violations"] == 3
    assert result["details"] == {
        "missing": [second.name],
        "unexpected": ["000_removed.cypher"],
        "changed": [first.name],
    }


def test_source_and_document_identity_is_workspace_scoped_and_delimiter_safe():
    first = source_id("workspace-a", "notion", "same-external-id")
    second = source_id("workspace-b", "notion", "same-external-id")
    assert first != second
    assert document_id(first, "a:b") != document_id(source_id("workspace-a", "notion:a", "b"), "b")


def test_access_fingerprint_is_canonical_and_workspace_scoped():
    first = access_fingerprint("workspace-a", ["user:alice", "group:team", "user:alice"])
    assert first.startswith("access-context:") and len(first) == 79
    assert first == access_fingerprint("workspace-a", ["group:team", "user:alice"])
    assert first != access_fingerprint("workspace-b", ["group:team", "user:alice"])


def test_processing_fingerprint_versions_all_deterministic_inputs():
    baseline = processing_fingerprint("content-hash", "parser-v1", "chunker-v1", 1200)
    assert baseline == processing_fingerprint("content-hash", "parser-v1", "chunker-v1", 1200)
    assert baseline != processing_fingerprint("content-hash", "parser-v2", "chunker-v1", 1200)
    assert baseline != processing_fingerprint("content-hash", "parser-v1", "chunker-v2", 1200)
    assert baseline != processing_fingerprint("content-hash", "parser-v1", "chunker-v1", 800)
    assert baseline != processing_fingerprint(
        "content-hash", "parser-v1", "chunker-v1", 1200, source_version="revision-2"
    )
    assert baseline != processing_fingerprint(
        "content-hash",
        "parser-v1",
        "chunker-v1",
        1200,
        authorization={"visibility": "SHARED", "acl": ["user:1"]},
    )


def test_source_metadata_fingerprint_binds_title_and_uri_canonically():
    first = source_metadata_fingerprint("Architecture", "gdrive://document/1")
    assert first == source_metadata_fingerprint("Architecture", "gdrive://document/1")
    assert first != source_metadata_fingerprint("Renamed architecture", "gdrive://document/1")
    assert first != source_metadata_fingerprint("Architecture", "gdrive://document/2")
    assert len(first) == 64


def test_ingestion_acl_is_canonicalized_for_deterministic_identity():
    request = TextIngestionRequest(
        source_external_id="source",
        document_external_id="document",
        title="Document",
        content="Evidence",
        acl=["user:2", "user:1", "user:2"],
    )
    assert request.acl == ["user:1", "user:2"]
    assert request.connector_id == "local-ingestion"


def test_direct_source_mutations_expose_document_version_cas():
    update = TextIngestionRequest(
        source_external_id="source",
        document_external_id="document",
        title="Document",
        content="Changed evidence",
        expected_current_version_id="document-version:known",
    )
    deletion = DocumentTombstoneRequest(
        source_external_id="source",
        document_external_id="document",
        source_version="deleted-1",
        expected_current_version_id="document-version:known",
    )
    assert update.expected_current_version_id == "document-version:known"
    assert deletion.expected_current_version_id == "document-version:known"


def test_proposal_identity_is_canonical_workspace_scoped_and_content_addressed():
    first = proposal_identity("ASSERTION", "workspace-a", {"b": 2, "a": 1})
    reordered = proposal_identity("ASSERTION", "workspace-a", {"a": 1, "b": 2})
    assert first == reordered
    assert first[0] != proposal_identity("EVENT", "workspace-a", {"a": 1, "b": 2})[0]
    assert first[0] != proposal_identity("ASSERTION", "workspace-b", {"a": 1, "b": 2})[0]
    assert first[0] != proposal_identity("ASSERTION", "workspace-a", {"a": 1, "b": 3})[0]
    assert len(first[1]) == 64


def test_user_search_text_cannot_become_lucene_query_syntax():
    assert literal_fulltext_query("Note/Concept ontology?") == '"Note" "Concept" "ontology"'
    assert literal_fulltext_query("title:(Neo4j OR *)") == '"title" "Neo4j" "OR"'
    assert literal_fulltext_query("지식 그래프") == '"지식" "그래프"'
    assert literal_fulltext_query("///") == '"__knowledge_os_no_search_terms__"'


def test_keyword_reranking_adds_bounded_explainable_title_signal():
    results = [
        {
            "chunk_id": "other",
            "document_id": "other-doc",
            "title": "Known_Risks.md",
            "score": 5.0,
        },
        {
            "chunk_id": "target",
            "document_id": "target-doc",
            "title": "Knowledge_OS_Architecture.md",
            "score": 2.0,
        },
    ]
    reranked = rerank_keyword_results("What is the primary goal of the Knowledge OS?", results, 2)
    assert [result["chunk_id"] for result in reranked] == ["target", "other"]
    assert reranked[0]["lexical_score"] == 2.0
    assert reranked[0]["title_overlap"] == 2
    assert results[1] == {
        "chunk_id": "target",
        "document_id": "target-doc",
        "title": "Knowledge_OS_Architecture.md",
        "score": 2.0,
    }


def test_keyword_reranking_diversifies_early_results_without_dropping_chunks():
    results = [
        {"chunk_id": f"a-{index}", "document_id": "a", "title": "A", "score": 10 - index}
        for index in range(4)
    ] + [{"chunk_id": "b-1", "document_id": "b", "title": "B", "score": 1.0}]
    reranked = rerank_keyword_results("unrelated", results, 5)
    assert [result["chunk_id"] for result in reranked] == ["a-0", "a-1", "b-1", "a-2", "a-3"]


def test_source_mutations_require_a_nonempty_connector_identity():
    with pytest.raises(ValidationError):
        TextIngestionRequest(
            connector_id="",
            source_external_id="source",
            document_external_id="document",
            title="Document",
            content="Evidence",
        )


def test_access_context_is_workspace_scoped_and_principals_are_canonicalized():
    access = AccessContext(
        workspace_id="customer-a",
        principals=["group:delivery", "user:alice", "group:delivery"],
    )
    assert access.workspace_id == "customer-a"
    assert access.principals == ["group:delivery", "user:alice"]


def test_proposal_decision_carries_explicit_access_context():
    decision = ProposalDecision(
        reviewed_by="user:alice",
        access=AccessContext(
            workspace_id="customer-a",
            principals=["group:reviewers", "user:alice"],
        ),
    )
    assert decision.access.workspace_id == "customer-a"
    assert decision.reviewed_by in decision.access.principals


def test_ingestion_rejects_unknown_visibility():
    with pytest.raises(ValidationError):
        TextIngestionRequest(
            source_external_id="source",
            document_external_id="document",
            title="Document",
            content="Evidence",
            visibility="INTERNAL",
        )


def test_sync_checkpoint_rejects_impossible_negative_stats():
    with pytest.raises(ValidationError, match="must be nonnegative"):
        SyncCheckpointCommit(
            source_type="notion",
            source_external_id="source",
            sync_run_id="run-1",
            cursor="cursor-1",
            stats={"items_seen": -1},
        )


def test_versioned_sync_manifest_is_provider_neutral_and_discriminated():
    manifest = SyncManifest.model_validate_json(
        __import__("pathlib").Path("examples/sync-manifest-v2.json").read_text()
    )
    assert manifest.manifest_version == "2"
    assert manifest.records[0].operation == "UPSERT"
    assert manifest.records[0].parser_version == "notion-export-v1"


def test_sync_manifest_rejects_multiple_operations_for_one_document():
    with pytest.raises(ValidationError, match="unique document_external_id"):
        SyncManifest.model_validate(
            {
                "manifest_version": "2",
                "source_type": "filesystem",
                "source_external_id": "source",
                "sync_run_id": "run",
                "cursor": "cursor",
                "connector_id": "connector",
                "records": [
                    {
                        "operation": "UPSERT",
                        "document_external_id": "same.md",
                        "source_version": "1",
                        "title": "same",
                        "content": "content",
                    },
                    {
                        "operation": "TOMBSTONE",
                        "document_external_id": "same.md",
                        "source_version": "2",
                    },
                ],
            }
        )


def test_sync_manifest_v1_remains_read_compatible():
    manifest = SyncManifest(
        manifest_version="1",
        source_type="legacy",
        source_external_id="source",
        sync_run_id="run",
        cursor="cursor",
        connector_id="connector",
    )
    assert manifest.manifest_version == "1"


def test_sync_manifest_canonicalizes_record_order():
    records = [
        {
            "operation": "UPSERT",
            "document_external_id": name,
            "source_version": "1",
            "title": name,
            "content": name,
        }
        for name in ["z.md", "a.md"]
    ]
    manifest = SyncManifest(
        source_type="filesystem",
        source_external_id="source",
        sync_run_id="run",
        cursor="cursor",
        connector_id="connector",
        records=records,
    )
    assert [record.document_external_id for record in manifest.records] == ["a.md", "z.md"]

    with pytest.raises(ValidationError):
        SyncManifest.model_validate(
            {
                "source_type": "future-system",
                "source_external_id": "source",
                "sync_run_id": "run",
                "cursor": "cursor",
                "connector_id": "adapter",
                "records": [{"operation": "DELETE_WITHOUT_EVIDENCE"}],
            }
        )


def test_filesystem_connector_builds_deterministic_upserts_and_tombstones(tmp_path):
    root = tmp_path / "documents"
    root.mkdir()
    (root / "architecture.md").write_text("# Architecture\n\nNeo4j is context.")
    (root / "meeting.txt").write_text("Decision: preserve source systems.")
    empty_state = {"version": "1", "files": {}}
    options = {
        "workspace_id": "personal",
        "source_external_id": "local-documents",
        "connector_id": "filesystem-v1",
        "owner": "user:owner",
        "visibility": "PRIVATE",
        "acl": ["user:owner"],
    }
    first, first_state = build_manifest(root, empty_state, **options)
    repeated, _ = build_manifest(root, empty_state, **options)
    assert first.cursor == repeated.cursor
    assert first.sync_run_id == repeated.sync_run_id
    assert [record.operation for record in first.records] == ["UPSERT", "UPSERT"]

    unchanged, unchanged_state = build_manifest(root, first_state, **options)
    unchanged_retry, _ = build_manifest(root, first_state, **options)
    assert unchanged.cursor == first.cursor
    assert unchanged.expected_previous_cursor == first.cursor
    assert unchanged.sync_run_id != first.sync_run_id
    assert unchanged.sync_run_id == unchanged_retry.sync_run_id
    assert unchanged_state == first_state

    (root / "meeting.txt").unlink()
    second, second_state = build_manifest(root, first_state, **options)
    assert [record.operation for record in second.records] == ["UPSERT", "TOMBSTONE"]
    assert second.expected_previous_cursor == first.cursor

    state_path = tmp_path / "state" / "files.json"
    write_state(state_path, second_state)
    assert load_state(state_path) == second_state

    with pytest.raises(ValueError, match="different document root"):
        build_manifest(tmp_path, second_state, **options)


def test_meeting_transcripts_preserve_raw_timestamps_and_source_identity(tmp_path):
    root = tmp_path / "meetings"
    root.mkdir()
    vtt = root / "architecture-review.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nAlice: Keep Neo4j as context.\n",
        encoding="utf-8",
    )
    srt = root / "decision.srt"
    srt.write_text(
        "1\n00:00:04,000 --> 00:00:06,000\nBob: Approved after review.\n",
        encoding="utf-8",
    )
    assert extract_file(vtt) == (vtt.read_text(), "vtt-utf8-v1")
    assert extract_file(srt) == (srt.read_text(), "srt-utf8-v1")

    options = {
        "workspace_id": "personal",
        "source_external_id": "meeting-transcripts",
        "connector_id": "meeting-transcript-files-v1",
        "owner": "user:owner",
        "visibility": "PRIVATE",
        "acl": ["user:owner"],
        "source_type": "meeting_transcripts",
    }
    manifest, state = build_manifest(root, {"version": "1", "files": {}}, **options)
    assert manifest.source_type == "meeting_transcripts"
    assert [record.parser_version for record in manifest.records] == [
        "vtt-utf8-v1",
        "srt-utf8-v1",
    ]
    assert "00:00:01.000" in manifest.records[0].content
    assert state["workspace_id"] == "personal"
    assert state["source_type"] == "meeting_transcripts"
    assert state["connector_id"] == "meeting-transcript-files-v1"

    for key, changed, message in (
        ("workspace_id", "customer-b", "workspace"),
        ("source_type", "filesystem", "source_type"),
        ("connector_id", "other-connector", "connector_id"),
    ):
        changed_options = {**options, key: changed}
        with pytest.raises(ValueError, match=message):
            build_manifest(root, state, **changed_options)


def test_google_drive_api_paginates_downloads_and_preserves_authorization():
    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer secret"
        if request.url.path.endswith("/about"):
            return httpx.Response(
                200,
                json={"user": {"permissionId": "owner-id", "emailAddress": "me@example.test"}},
            )
        if request.url.path.endswith("/files"):
            assert request.url.params["orderBy"] == "name"
            if request.url.params.get("pageToken") is None:
                return httpx.Response(
                    200,
                    json={
                        "files": [
                            {
                                "id": "file-b",
                                "name": "B.md",
                                "mimeType": "text/markdown",
                                "modifiedTime": "2026-09-05T01:00:00Z",
                                "webViewLink": "https://drive.test/file-b",
                            }
                        ],
                        "nextPageToken": "next",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "files": [
                        {
                            "id": "file-a",
                            "name": "A.md",
                            "mimeType": "text/markdown",
                            "modifiedTime": "2026-09-05T00:00:00Z",
                            "webViewLink": "https://drive.test/file-a",
                        }
                    ]
                },
            )
        if request.url.path.endswith("/permissions"):
            return httpx.Response(
                200,
                json={"permissions": [{"id": "owner-id", "type": "user", "role": "owner"}]},
            )
        if request.url.params.get("alt") == "media":
            return httpx.Response(200, content=f"# {request.url.path[-1]}".encode())
        if request.url.path.endswith("file-a"):
            return httpx.Response(
                200,
                json={
                    "id": "file-a",
                    "modifiedTime": "2026-09-05T00:00:00Z",
                    "trashed": False,
                },
            )
        if request.url.path.endswith("file-b"):
            return httpx.Response(
                200,
                json={
                    "id": "file-b",
                    "modifiedTime": "2026-09-05T01:00:00Z",
                    "trashed": False,
                },
            )
        raise AssertionError(str(request.url))

    api = GoogleDriveAPI("secret", transport=httpx.MockTransport(handler))
    try:
        connection_id, snapshots = snapshot_folder(api, "folder-id")
    finally:
        api.close()
    assert connection_id == "google-drive:permission:owner-id"
    assert [snapshot.file_id for snapshot in snapshots] == ["file-a", "file-b"]
    assert all(snapshot.owner == "google-drive:me" for snapshot in snapshots)
    assert all(snapshot.visibility == "PRIVATE" for snapshot in snapshots)
    assert all(snapshot.acl == ("google-drive:me",) for snapshot in snapshots)
    assert any(request.url.params.get("pageToken") == "next" for request in requests)


def test_google_drive_refreshes_authorized_user_adc_without_leaking_credentials(
    tmp_path, monkeypatch
):
    credentials_path = tmp_path / "application_default_credentials.json"
    credentials_path.write_text(
        json.dumps(
            {
                "type": "authorized_user",
                "client_id": "client-secret-id",
                "client_secret": "client-secret-value",
                "refresh_token": "refresh-secret-value",
            }
        ),
        encoding="utf-8",
    )
    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        assert request.url == "https://oauth2.googleapis.com/token"
        assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
        assert b"grant_type=refresh_token" in request.content
        assert b"scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.readonly" in request.content
        assert b"refresh-secret-value" in request.content
        return httpx.Response(
            200,
            json={"access_token": "short-lived-access", "token_type": "Bearer", "expires_in": 3600},
        )

    token = refresh_google_access_token(
        credentials_path, transport=httpx.MockTransport(handler)
    )
    assert token == "short-lived-access"
    assert len(requests) == 1

    def denied(_request: httpx.Request):
        return httpx.Response(400, json={"error_description": "refresh-secret-value"})

    with pytest.raises(RuntimeError) as exc_info:
        refresh_google_access_token(credentials_path, transport=httpx.MockTransport(denied))
    assert "HTTP 400" in str(exc_info.value)
    assert "refresh-secret-value" not in str(exc_info.value)

    def expired(_request: httpx.Request):
        return httpx.Response(
            400,
            json={"error": "invalid_grant", "error_description": "refresh-secret-value"},
        )

    with pytest.raises(RuntimeError, match="reauthorize the dedicated ADC") as exc_info:
        refresh_google_access_token(credentials_path, transport=httpx.MockTransport(expired))
    assert "refresh-secret-value" not in str(exc_info.value)

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(credentials_path))
    assert application_default_credentials_path() == credentials_path


def test_google_drive_explicit_access_token_takes_precedence(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_TOKEN", "explicit-short-lived-token")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/does/not/exist")
    assert resolve_google_drive_token() == "explicit-short-lived-token"


def test_google_drive_rejects_non_refreshable_adc(tmp_path):
    credentials_path = tmp_path / "service-account.json"
    credentials_path.write_text(
        json.dumps({"type": "service_account", "client_id": "x"}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="authorized-user credentials"):
        refresh_google_access_token(credentials_path)


def test_google_drive_authorization_maps_shared_and_public_permissions():
    current_user = {"permissionId": "me-id", "emailAddress": "me@example.test"}
    owner, visibility, acl = authorization_snapshot(
        [
            {"id": "me-id", "type": "user", "role": "owner"},
            {"id": "group-id", "type": "group", "role": "reader"},
        ],
        current_user,
    )
    assert owner == "google-drive:me"
    assert visibility == "SHARED"
    assert acl == ("google-drive:me", "google-drive:permission:group-id")

    _, visibility, acl = authorization_snapshot(
        [{"id": "anyone", "type": "anyone", "role": "reader"}], current_user
    )
    assert visibility == "PUBLIC"
    assert acl == ("google-drive:anyone",)

    with pytest.raises(ValueError, match="authorization is unknown"):
        authorization_snapshot([], current_user)


def test_google_drive_snapshot_fails_if_a_file_changes_during_capture():
    class ChangingAPI:
        def current_user(self):
            return {"permissionId": "owner-id"}

        def folder_files(self, folder_id):
            assert folder_id == "folder-id"
            return [
                {
                    "id": "file-a",
                    "name": "A.md",
                    "mimeType": "text/markdown",
                    "modifiedTime": "2026-09-05T00:00:00Z",
                }
            ]

        def permissions(self, file_id):
            return [{"id": "owner-id", "type": "user", "role": "owner"}]

        def text_content(self, file):
            return "# changed"

        def file_revision(self, file_id):
            return {"id": file_id, "modifiedTime": "2026-09-05T00:01:00Z"}

    with pytest.raises(RuntimeError, match="changed during snapshot"):
        snapshot_folder(ChangingAPI(), "folder-id")


def test_source_adapter_observation_records_safe_success_and_error(tmp_path, monkeypatch):
    ops = OpsStore(tmp_path / "connector-ops.db")
    monkeypatch.setattr(connector_observation_module, "get_ops", lambda: ops)
    context = {
        "workspace_id": "personal",
        "source_type": "google_drive_folder",
        "connector_id": "google-drive-v1",
    }

    with observe_connector_run("google_drive_connector", **context):
        pass
    secret = "secret-token-and-source-content"
    with (
        pytest.raises(ValueError, match=secret) as raised,
        observe_connector_run("google_drive_connector", **context),
    ):
        raise ValueError(secret)
    assert raised.value.__notes__[0].startswith("Recorded connector error: error:")

    with ops.connect() as db:
        telemetry = db.execute("SELECT status,context_json FROM telemetry ORDER BY id").fetchall()
        error = db.execute("SELECT message,context_json FROM errors").fetchone()
    assert [row[0] for row in telemetry] == ["SUCCESS", "ERROR"]
    persisted = " ".join(row[1] for row in telemetry) + " " + error[0] + " " + error[1]
    assert secret not in persisted
    assert error[0] == "source adapter run failed"
    assert all("source-adapter-observation-v1" in row[1] for row in telemetry)


def test_google_drive_connector_is_deterministic_replay_safe_and_tombstones():
    snapshots = [
        DriveFileSnapshot(
            file_id="file-a",
            name="Architecture.md",
            mime_type="text/markdown",
            modified_time="2026-09-05T00:00:00Z",
            web_view_link="https://drive.test/file-a",
            content="# Architecture",
            owner="google-drive:me",
            visibility="PRIVATE",
            acl=("google-drive:me",),
            source_checksum="md5-a",
        ),
        DriveFileSnapshot(
            file_id="file-b",
            name="Decision.md",
            mime_type="text/markdown",
            modified_time="2026-09-05T01:00:00Z",
            web_view_link="https://drive.test/file-b",
            content="Decision: preserve foundations.",
            owner="google-drive:me",
            visibility="PRIVATE",
            acl=("google-drive:me",),
        ),
    ]
    options = {
        "workspace_id": "personal",
        "folder_id": "folder-id",
        "connection_id": "google-drive:permission:owner-id",
        "connector_id": "google-drive-v1",
    }
    empty = {"version": "1", "files": {}}
    first, first_state = build_google_drive_manifest(snapshots, empty, **options)
    retry, _ = build_google_drive_manifest(list(reversed(snapshots)), empty, **options)
    assert first == retry
    assert [record.document_external_id for record in first.records] == ["file-a", "file-b"]
    assert all(record.acl == ["google-drive:me"] for record in first.records)
    assert first.records[0].document_source_uri == "https://drive.test/file-a"

    unchanged, unchanged_state = build_google_drive_manifest(snapshots, first_state, **options)
    assert unchanged.cursor == first.cursor
    assert unchanged.expected_previous_cursor == first.cursor
    assert unchanged.sync_run_id != first.sync_run_id
    assert unchanged_state == first_state

    removed, _ = build_google_drive_manifest(snapshots[:1], first_state, **options)
    assert [record.operation for record in removed.records] == ["UPSERT", "TOMBSTONE"]
    assert removed.records[1].document_external_id == "file-b"

    with pytest.raises(ValueError, match="different Google Drive folder"):
        build_google_drive_manifest(
            snapshots, first_state, **{**options, "folder_id": "other-folder"}
        )
    with pytest.raises(ValueError, match="duplicate file IDs"):
        build_google_drive_manifest([snapshots[0], snapshots[0]], empty, **options)


def test_notion_api_paginates_with_versioned_authorization_headers():
    first_id = "11111111-1111-1111-1111-111111111111"
    second_id = "22222222-2222-2222-2222-222222222222"
    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        cursor = request.url.params.get("start_cursor")
        if cursor is None:
            return httpx.Response(
                200,
                json={"results": [{"id": first_id}], "has_more": True, "next_cursor": "next"},
            )
        return httpx.Response(
            200,
            json={"results": [{"id": second_id}], "has_more": False, "next_cursor": None},
        )

    api = NotionAPI("secret", transport=httpx.MockTransport(handler))
    try:
        assert [item["id"] for item in api.block_children(first_id)] == [first_id, second_id]
    finally:
        api.close()
    assert len(requests) == 2
    assert all(request.headers["notion-version"] == NOTION_API_VERSION for request in requests)
    assert all(request.headers["authorization"] == "Bearer secret" for request in requests)
    assert requests[0].url.params["page_size"] == "100"
    assert requests[1].url.params["start_cursor"] == "next"


def test_notion_token_resolution_prefers_environment_and_accepts_owner_only_file(
    tmp_path, monkeypatch
):
    token_file = tmp_path / "notion_token"
    token_file.write_text("file-token\n", encoding="utf-8")
    token_file.chmod(0o600)
    monkeypatch.setenv("NOTION_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    assert notion_token_path() == token_file
    assert resolve_notion_token() == "file-token"

    monkeypatch.setenv("NOTION_TOKEN", " environment-token ")
    assert resolve_notion_token() == "environment-token"


def test_notion_token_file_fails_closed_for_missing_empty_or_unsafe_paths(tmp_path, monkeypatch):
    token_file = tmp_path / "notion_token"
    monkeypatch.setenv("NOTION_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="were not found"):
        resolve_notion_token()

    token_file.write_text("", encoding="utf-8")
    token_file.chmod(0o600)
    with pytest.raises(RuntimeError, match="is empty"):
        resolve_notion_token()

    token_file.write_text("secret", encoding="utf-8")
    token_file.chmod(0o644)
    with pytest.raises(RuntimeError, match="0600"):
        resolve_notion_token()

    token_file.chmod(0o600)
    link = tmp_path / "linked_token"
    link.symlink_to(token_file)
    monkeypatch.setenv("NOTION_TOKEN_FILE", str(link))
    with pytest.raises(RuntimeError, match="not a symlink"):
        resolve_notion_token()


def test_notion_api_queries_data_source_pages_with_post_cursors():
    data_source_id = "11111111-1111-1111-1111-111111111111"
    page_ids = [
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    ]
    bodies = []

    def handler(request: httpx.Request):
        body = __import__("json").loads(request.content)
        bodies.append(body)
        index = 0 if "start_cursor" not in body else 1
        return httpx.Response(
            200,
            json={
                "results": [{"object": "page", "id": page_ids[index]}],
                "has_more": index == 0,
                "next_cursor": "next" if index == 0 else None,
            },
        )

    api = NotionAPI("secret", transport=httpx.MockTransport(handler))
    try:
        assert [item["id"] for item in api.data_source_pages(data_source_id)] == page_ids
    finally:
        api.close()
    assert bodies == [
        {"page_size": 100, "result_type": "page"},
        {"page_size": 100, "result_type": "page", "start_cursor": "next"},
    ]


def test_notion_api_paginates_encoded_page_property_ids():
    page_id = "11111111-1111-1111-1111-111111111111"
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        cursor = request.url.params.get("start_cursor")
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [
                    {
                        "object": "property_item",
                        "type": "relation",
                        "relation": {"id": "22222222-2222-2222-2222-222222222222"},
                    }
                ],
                "has_more": cursor is None,
                "next_cursor": "next" if cursor is None else None,
            },
        )

    api = NotionAPI("secret", transport=httpx.MockTransport(handler))
    try:
        assert len(api.page_property_items(page_id, "abc%3Adef")) == 2
    finally:
        api.close()
    assert len(seen) == 2
    assert all("abc%3Adef" in str(request.url) for request in seen)
    assert seen[1].url.params["start_cursor"] == "next"


def test_notion_page_tree_and_manifest_are_deterministic_and_acl_bound():
    root_id = "11111111-1111-1111-1111-111111111111"
    child_id = "22222222-2222-2222-2222-222222222222"
    toggle_id = "33333333-3333-3333-3333-333333333333"
    connection_id = "44444444-4444-4444-4444-444444444444"

    class FakeNotionAPI:
        def page(self, page_id):
            title = "Root" if page_id == root_id else "Child"
            return {
                "id": page_id,
                "last_edited_time": "2026-09-05T06:00:00.000Z",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": title}],
                    }
                },
            }

        def block_children(self, block_id):
            if block_id == root_id:
                return [
                    {
                        "id": child_id,
                        "type": "child_page",
                        "has_children": True,
                        "child_page": {"title": "Child"},
                    },
                    {
                        "id": toggle_id,
                        "type": "toggle",
                        "has_children": True,
                        "toggle": {"rich_text": [{"plain_text": "Details"}]},
                    },
                ]
            if block_id == toggle_id:
                return [
                    {
                        "id": "55555555-5555-5555-5555-555555555555",
                        "type": "paragraph",
                        "has_children": False,
                        "paragraph": {"rich_text": [{"plain_text": "Nested evidence"}]},
                    }
                ]
            if block_id == child_id:
                return [
                    {
                        "id": "66666666-6666-6666-6666-666666666666",
                        "type": "unsupported_future_block",
                        "has_children": False,
                        "unsupported_future_block": {},
                    }
                ]
            raise AssertionError(block_id)

    snapshots = snapshot_page_tree(FakeNotionAPI(), root_id)
    assert [snapshot.page_id for snapshot in snapshots] == [root_id, child_id]
    assert "Nested evidence" in snapshots[0].content
    assert "Unsupported Notion block" in snapshots[1].content

    empty_state = {"version": "1", "pages": {}}
    options = {
        "workspace_id": "personal",
        "root_page_id": root_id,
        "connection_id": connection_id,
        "connector_id": "notion-api-personal-v1",
    }
    first, first_state = build_notion_manifest(snapshots, empty_state, **options)
    repeated, _ = build_notion_manifest(snapshots, empty_state, **options)
    assert first.cursor == repeated.cursor
    assert first.sync_run_id == repeated.sync_run_id
    principal = f"notion:connection:{connection_id}"
    assert all(record.owner == principal and record.acl == [principal] for record in first.records)

    unchanged, unchanged_state = build_notion_manifest(snapshots, first_state, **options)
    unchanged_retry, _ = build_notion_manifest(snapshots, first_state, **options)
    assert unchanged.cursor == first.cursor
    assert unchanged.expected_previous_cursor == first.cursor
    assert unchanged.sync_run_id != first.sync_run_id
    assert unchanged.sync_run_id == unchanged_retry.sync_run_id
    assert unchanged_state == first_state

    second, _ = build_notion_manifest(snapshots[:1], first_state, **options)
    assert [record.operation for record in second.records] == ["UPSERT", "TOMBSTONE"]
    assert second.expected_previous_cursor == first.cursor
    assert normalize_notion_id(root_id.replace("-", "")) == root_id


def test_notion_page_tree_includes_child_data_source_rows_and_properties():
    root_id = "11111111-1111-1111-1111-111111111111"
    database_id = "22222222-2222-2222-2222-222222222222"
    data_source_id = "33333333-3333-3333-3333-333333333333"
    row_id = "44444444-4444-4444-4444-444444444444"

    class FakeDataSourceAPI:
        def page(self, page_id):
            title = "Root" if page_id == root_id else "Task"
            properties = {
                "Name": {"type": "title", "title": [{"plain_text": title}]},
            }
            if page_id == row_id:
                properties.update(
                    {
                        "Done": {"type": "checkbox", "checkbox": True},
                        "Status": {"type": "status", "status": {"name": "Doing"}},
                    }
                )
            return {
                "id": page_id,
                "last_edited_time": "2026-09-05T06:00:00Z",
                "properties": properties,
            }

        def block_children(self, block_id):
            if block_id == root_id:
                return [
                    {
                        "id": database_id,
                        "type": "child_database",
                        "has_children": True,
                        "child_database": {"title": "Tasks"},
                    }
                ]
            if block_id == row_id:
                return []
            raise AssertionError(block_id)

        def database(self, requested_id):
            assert requested_id == database_id
            return {"id": database_id, "data_sources": [{"id": data_source_id, "name": "Tasks"}]}

        def data_source_pages(self, requested_id):
            assert requested_id == data_source_id
            return [{"object": "page", "id": row_id}]

    snapshots = snapshot_page_tree(FakeDataSourceAPI(), root_id)
    assert [snapshot.page_id for snapshot in snapshots] == [root_id, row_id]
    row = next(snapshot for snapshot in snapshots if snapshot.page_id == row_id)
    assert "## Properties" in row.content
    assert "- Done: True" in row.content
    assert "- Status: Doing" in row.content


def test_notion_page_tree_completes_paginated_reference_properties():
    page_id = "11111111-1111-1111-1111-111111111111"
    related_ids = [
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    ]

    class FakePropertyAPI:
        def page(self, requested_id):
            assert requested_id == page_id
            return {
                "id": page_id,
                "last_edited_time": "2026-09-05T06:00:00Z",
                "properties": {
                    "Name": {
                        "id": "title",
                        "type": "title",
                        "title": [{"plain_text": "Truncated"}],
                    },
                    "Related": {
                        "id": "relation",
                        "type": "relation",
                        "relation": [{"id": related_ids[0]}],
                        "has_more": True,
                    },
                },
            }

        def page_property_items(self, requested_page_id, property_id):
            assert requested_page_id == page_id
            if property_id == "title":
                return [
                    {"type": "title", "title": {"plain_text": "Complete "}},
                    {"type": "title", "title": {"plain_text": "Title"}},
                ]
            assert property_id == "relation"
            return [
                {"type": "relation", "relation": {"id": related_id}} for related_id in related_ids
            ]

        def block_children(self, requested_id):
            assert requested_id == page_id
            return []

    snapshots = snapshot_page_tree(FakePropertyAPI(), page_id)
    assert len(snapshots) == 1
    assert snapshots[0].title == "Complete Title"
    assert all(related_id in snapshots[0].content for related_id in related_ids)
    assert "additional references not loaded" not in snapshots[0].content


def test_notion_connector_rejects_invalid_identity_and_state_rebinding():
    with pytest.raises(ValueError, match="Notion IDs"):
        normalize_notion_id("not-a-page")
    snapshot = NotionPageSnapshot(
        page_id="11111111-1111-1111-1111-111111111111",
        title="Page",
        last_edited_time="2026-09-05T06:00:00Z",
        content="# Page",
    )
    with pytest.raises(ValueError, match="different Notion connection"):
        build_notion_manifest(
            [snapshot],
            {
                "version": "1",
                "pages": {},
                "connection_id": "22222222-2222-2222-2222-222222222222",
            },
            workspace_id="personal",
            root_page_id=snapshot.page_id,
            connection_id="33333333-3333-3333-3333-333333333333",
            connector_id="notion-api-personal-v1",
        )


def test_action_contract_requires_explicit_governed_capability_name():
    action = ActionCreate(
        action_type="NOTION_CREATE_PAGE",
        target="notion:database:123",
        requested_by="agent:researcher",
        parameters={"title": "Draft only"},
        idempotency_key="request-123",
    )
    assert action.approval_required is True
    assert action.policy_version == "action-policy-v1"

    with pytest.raises(ValidationError, match="require an explicit approval"):
        ActionCreate(
            action_type="NOTION_CREATE_PAGE",
            target="notion:database:123",
            requested_by="agent:researcher",
            approval_required=False,
            idempotency_key="request-without-approval",
        )
    assert action.review_principals == ["local-user"]
    assert action.execution_principals == ["local-connector"]

    with pytest.raises(ValidationError, match="idempotency_key"):
        ActionCreate(
            action_type="NOTION_CREATE_PAGE",
            target="notion:database:123",
            requested_by="agent:researcher",
        )

    with pytest.raises(ValidationError):
        ActionCreate(
            action_type="notion.create",
            target="x",
            requested_by="agent",
            idempotency_key="invalid-type",
        )
    with pytest.raises(ValidationError):
        ActionCreate(
            action_type="NOTION_CREATE_PAGE",
            target="x",
            requested_by="agent",
            execution_principals=[],
            idempotency_key="empty-executors",
        )


def test_failed_action_execution_requires_structured_error_evidence():
    with pytest.raises(ValidationError, match="requires error evidence"):
        ActionExecutionCreate(
            claim_id="claim:1",
            external_idempotency_key="external:1",
            status="FAILED",
            executed_by="connector:notion",
            connector="notion-v1",
            external_api="notion.pages.create",
            authorization_ref="credential:local-notion",
            policy_version="action-policy-v1",
            idempotency_key="attempt-1",
        )

    execution = ActionExecutionCreate(
        claim_id="claim:1",
        external_idempotency_key="external:1",
        status="FAILED",
        executed_by="connector:notion",
        connector="notion-v1",
        external_api="notion.pages.create",
        authorization_ref="credential:local-notion",
        policy_version="action-policy-v1",
        idempotency_key="attempt-1",
        error={"type": "rate_limit", "retryable": True},
        access=AccessContext(workspace_id="personal", principals=["connector:notion"]),
    )
    assert execution.error["retryable"] is True


def test_action_execution_claim_has_bounded_lease_and_access_context():
    claim = ActionExecutionClaimCreate(
        executed_by="connector:notion",
        connector="notion-v1",
        authorization_ref="credential:local-notion",
        policy_version="action-policy-v1",
        idempotency_key="attempt-1",
        access=AccessContext(workspace_id="personal", principals=["connector:notion"]),
    )
    assert claim.lease_seconds == 300
    with pytest.raises(ValidationError):
        ActionExecutionClaimCreate(
            executed_by="connector:notion",
            connector="notion-v1",
            authorization_ref="credential:local-notion",
            policy_version="action-policy-v1",
            idempotency_key="attempt-1",
            lease_seconds=3600,
        )


def test_semantic_retrieval_requires_versioned_embedding_contract():
    with pytest.raises(ValidationError, match="requires an embedding"):
        RetrievalQuery(query="knowledge graph", mode="semantic")
    with pytest.raises(ValidationError, match="embedding_model"):
        RetrievalQuery(query="knowledge graph", mode="semantic", embedding=[0.1, 0.2])

    query = RetrievalQuery(
        query="knowledge graph",
        mode="hybrid",
        embedding=[0.1, 0.2],
        embedding_model="local-test-model",
        embedding_version="1",
    )
    assert query.mode == "hybrid"


def test_embedding_write_carries_explicit_adapter_access_context():
    embedding = EmbeddingUpsert(
        vector=[0.1, 0.2],
        model="local-model",
        model_version="1",
        created_by="adapter:embedding",
        access=AccessContext(
            workspace_id="customer-a", principals=["adapter:embedding", "user:alice"]
        ),
    )
    assert embedding.created_by in embedding.access.principals
    assert embedding.access.workspace_id == "customer-a"


def test_embedding_fingerprint_binds_vector_model_and_version():
    first = embedding_fingerprint([0.1, 0.2], "local-model", "1")
    assert first == embedding_fingerprint([0.1, 0.2], "local-model", "1")
    assert first != embedding_fingerprint([0.1, 0.3], "local-model", "1")
    assert first != embedding_fingerprint([0.1, 0.2], "other-model", "1")
    assert first != embedding_fingerprint([0.1, 0.2], "local-model", "2")


def test_retrieval_evaluation_suite_requires_unique_cases_and_one_target_kind():
    request = RetrievalQuery(query="knowledge graph")
    case = RetrievalEvaluationCase(
        id="case-1",
        request=request,
        expected_document_ids=["document:2", "document:2"],
        excluded_document_ids=["document:3", "document:3"],
    )
    assert case.expected_document_ids == ["document:2"]
    assert case.excluded_document_ids == ["document:3"]

    with pytest.raises(ValidationError, match="exactly one"):
        RetrievalEvaluationCase(id="invalid", request=request)
    with pytest.raises(ValidationError, match="exactly one"):
        RetrievalEvaluationCase(
            id="invalid",
            request=request,
            expected_chunk_ids=["chunk:1"],
            expected_document_ids=["document:1"],
        )
    with pytest.raises(ValidationError, match="cannot also be excluded"):
        RetrievalEvaluationCase(
            id="invalid-overlap",
            request=request,
            expected_document_ids=["document:1"],
            excluded_document_ids=["document:1"],
        )
    with pytest.raises(ValidationError, match="unique"):
        RetrievalEvaluationSuite(suite_id="duplicates", cases=[case, case])


def test_retrieval_evaluation_runner_records_traces_and_measured_gate():
    class FakeOps:
        def __init__(self):
            self.rows = []

        def record_evaluation(self, *args, **kwargs):
            self.rows.append((args, kwargs))
            return len(self.rows)

    class FakeGraph:
        def __init__(self):
            self.ops = FakeOps()

        def retrieve(self, request):
            if request.query == "denied":
                return {"trace_id": "trace:denied", "results": []}
            if request.query == "chunks":
                return {
                    "trace_id": "trace:chunks",
                    "results": [
                        {"chunk_id": "chunk:1", "document_id": "document:1"},
                        {"chunk_id": "chunk:x", "document_id": "document:x"},
                    ],
                }
            return {
                "trace_id": "trace:documents",
                "results": [
                    {"chunk_id": "chunk:a", "document_id": "document:1"},
                    {"chunk_id": "chunk:b", "document_id": "document:1"},
                    {"chunk_id": "chunk:c", "document_id": "document:2"},
                ],
            }

    suite = RetrievalEvaluationSuite(
        suite_id="baseline-v1",
        minimum_mean_recall=0.8,
        cases=[
            RetrievalEvaluationCase(
                id="chunks",
                request=RetrievalQuery(query="chunks"),
                expected_chunk_ids=["chunk:1", "chunk:2"],
                excluded_document_ids=["document:x"],
            ),
            RetrievalEvaluationCase(
                id="documents",
                request=RetrievalQuery(query="documents"),
                expected_document_ids=["document:2"],
            ),
            RetrievalEvaluationCase(
                id="denied",
                request=RetrievalQuery(query="denied"),
                expected_no_results=True,
            ),
        ],
    )
    graph = FakeGraph()
    report = run_suite(graph, suite)
    assert report["suite_fingerprint"] == suite_fingerprint(suite)
    assert report["mean_recall_at_k"] == 0.75
    assert report["mean_reciprocal_rank"] == 0.75
    assert report["policy_case_count"] == 1
    assert report["policy_pass_rate"] == 1.0
    assert report["passed"] is False
    assert report["cases"][0]["excluded_result_ids"] == ["document:x"]
    assert [args[5] for args, _ in graph.ops.rows] == [
        "trace:chunks",
        "trace:documents",
        "trace:denied",
    ]
    expected_fingerprint = access_fingerprint("personal", ["local-user"])
    assert [kwargs for _, kwargs in graph.ops.rows] == [
        {"workspace_id": "personal", "access_fingerprint": expected_fingerprint},
        {"workspace_id": "personal", "access_fingerprint": expected_fingerprint},
        {"workspace_id": "personal", "access_fingerprint": expected_fingerprint},
    ]

    leaked = RetrievalEvaluationSuite(
        suite_id="policy-leak",
        cases=[
            RetrievalEvaluationCase(
                id="must-be-empty",
                request=RetrievalQuery(query="documents"),
                expected_no_results=True,
            )
        ],
    )
    leaked_report = run_suite(graph, leaked)
    assert leaked_report["mean_recall_at_k"] is None
    assert leaked_report["policy_pass_rate"] == 0.0
    assert leaked_report["passed"] is False


def test_empty_evaluation_exclusions_preserve_the_existing_suite_fingerprint():
    path = __import__("pathlib").Path("examples/personal-google-drive-retrieval-eval-v1.json")
    suite = RetrievalEvaluationSuite.model_validate_json(path.read_text())
    assert suite_fingerprint(suite) == (
        "4780846fa2e39a76d5d1b6226d4d29c4f6abd08037a757ad30e7308c15208061"
    )


def test_hybrid_fusion_ranks_each_retrieval_source_independently():
    keyword = [
        {"chunk_id": "shared", "score": 100.0},
        {"chunk_id": "keyword-only", "score": 90.0},
    ]
    semantic = [
        {"chunk_id": "semantic-only", "score": 0.99},
        {"chunk_id": "shared", "score": 0.80},
    ]
    fused = GraphStore.fuse_results(keyword, semantic, 3)
    assert fused[0]["chunk_id"] == "shared"
    assert fused[0]["keyword_score"] == 100.0
    assert fused[0]["semantic_score"] == 0.80


def test_ontology_accepts_valid_relation(ontology: Ontology):
    change = AssertionChange(
        subject=EntityRef(name="Project A", entity_type="Project"),
        predicate="USES",
        object=EntityRef(name="Neo4j", entity_type="Technology"),
        evidence_chunk_id="chunk:1",
    )
    ontology.validate(change)


def test_ontology_rejects_invalid_relation(ontology: Ontology):
    change = AssertionChange(
        subject=EntityRef(name="A document", entity_type="Document"),
        predicate="WORKS_FOR",
        object=EntityRef(name="ACME", entity_type="Organization"),
        evidence_chunk_id="chunk:1",
    )
    with pytest.raises(ValueError):
        ontology.validate(change)


def test_assertion_rejects_inverted_validity_window():
    with pytest.raises(ValidationError, match="valid_to must not be earlier"):
        AssertionChange(
            subject=EntityRef(name="Project A", entity_type="Project"),
            predicate="USES",
            object=EntityRef(name="Neo4j", entity_type="Technology"),
            evidence_chunk_id="chunk:1",
            valid_from=datetime(2026, 2, 1, tzinfo=UTC),
            valid_to=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_decision_proposal_deduplicates_evidence_and_validates_time():
    proposal = DecisionProposalCreate(
        title="Use Neo4j",
        statement="Neo4j remains the system of context.",
        decided_at=datetime(2026, 9, 2, tzinfo=UTC),
        evidence_chunk_ids=["chunk:2", "chunk:1", "chunk:2"],
        participants=["person:b", "person:a", "person:b"],
        proposed_by="local-user",
    )
    assert proposal.evidence_chunk_ids == ["chunk:1", "chunk:2"]
    assert proposal.participants == ["person:a", "person:b"]
    assert proposal.decided_at_precision == "INSTANT"
    assert proposal.decided_on is None

    day_precision = DecisionProposalCreate(
        title="Use artifact-specific authority",
        statement="Notion and Drive retain artifact-specific authority.",
        decided_on="2026-09-02",
        evidence_chunk_ids=["chunk:1"],
        proposed_by="local-user",
    )
    assert day_precision.decided_on.isoformat() == "2026-09-02"
    assert day_precision.decided_at.isoformat() == "2026-09-02T00:00:00+00:00"
    assert day_precision.decided_at_precision == "DAY"

    with pytest.raises(ValidationError, match="exactly one"):
        DecisionProposalCreate(
            title="Missing time",
            statement="No temporal evidence",
            evidence_chunk_ids=["chunk:1"],
            proposed_by="local-user",
        )
    with pytest.raises(ValidationError, match="day boundary"):
        DecisionProposalCreate(
            title="Conflicting time",
            statement="Two temporal values",
            decided_at=datetime(2026, 9, 2, 1, tzinfo=UTC),
            decided_on="2026-09-02",
            decided_at_precision="DAY",
            evidence_chunk_ids=["chunk:1"],
            proposed_by="local-user",
        )
    assert DecisionProposalCreate.model_validate_json(day_precision.model_dump_json()) == (
        day_precision
    )

    with pytest.raises(ValidationError, match="valid_to must not be earlier"):
        DecisionProposalCreate(
            title="Invalid",
            statement="Invalid temporal range",
            decided_at=datetime(2026, 9, 2, tzinfo=UTC),
            valid_from=datetime(2026, 9, 2, tzinfo=UTC),
            valid_to=datetime(2026, 9, 1, tzinfo=UTC),
            evidence_chunk_ids=["chunk:1"],
            proposed_by="local-user",
        )


def test_event_proposal_deduplicates_evidence_and_validates_time():
    proposal = EventProposalCreate(
        title="Production deployment",
        description="Release 1.2 reached production.",
        event_type="DEPLOYMENT_COMPLETED",
        occurred_at=datetime(2026, 9, 2, tzinfo=UTC),
        evidence_chunk_ids=["chunk:2", "chunk:1", "chunk:2"],
        participants=["person:b", "person:a", "person:b"],
        proposed_by="local-user",
    )
    assert proposal.evidence_chunk_ids == ["chunk:1", "chunk:2"]
    assert proposal.participants == ["person:a", "person:b"]

    with pytest.raises(ValidationError, match="ended_at must not be earlier"):
        EventProposalCreate(
            title="Invalid",
            description="Invalid temporal range",
            event_type="DEPLOYMENT_COMPLETED",
            occurred_at=datetime(2026, 9, 2, tzinfo=UTC),
            ended_at=datetime(2026, 9, 1, tzinfo=UTC),
            evidence_chunk_ids=["chunk:1"],
            proposed_by="local-user",
        )


def test_ops_trace_feedback_evaluation_and_error_are_linked(tmp_path):
    from time import perf_counter

    ops = OpsStore(tmp_path / "ops.db")
    fingerprint = access_fingerprint("personal", ["local-user"])
    trace_id = ops.retrieval_trace(
        "neo4j provenance",
        "keyword",
        perf_counter(),
        ["chunk:1"],
        limit=10,
        workspace_id="personal",
        access_fingerprint=fingerprint,
    )
    trace = ops.get_trace(trace_id)
    assert trace is not None
    assert trace["result_ids"] == ["chunk:1"]
    assert trace["contract_version"] == "retrieval-v1"
    assert ops.get_trace_for_access(trace_id, "personal", fingerprint) is not None
    assert ops.get_trace_for_access(trace_id, "other", fingerprint) is None
    assert ops.get_trace_for_access(trace_id, "personal", "access-context:wrong") is None

    feedback_id = ops.record_feedback(trace_id, 1, "Relevant evidence", "local-user")
    evaluation_id = ops.record_evaluation(
        "What store is used?",
        {"answer": "Neo4j"},
        {"answer": "Neo4j"},
        1.0,
        "manual-eval-v1",
        trace_id,
    )
    error_id = ops.error("test-operation", ValueError("measured failure"), trace_id=trace_id)
    assert feedback_id == 1
    assert evaluation_id == 1
    assert error_id.startswith("error:")

    with ops.connect() as db:
        feedback_access = db.execute(
            "SELECT workspace_id,access_fingerprint FROM feedback WHERE id=?", (feedback_id,)
        ).fetchone()
        evaluation_access = db.execute(
            "SELECT workspace_id,access_fingerprint FROM evaluations WHERE id=?", (evaluation_id,)
        ).fetchone()
    assert feedback_access == ("personal", fingerprint)
    assert evaluation_access == ("personal", fingerprint)

    with pytest.raises(KeyError):
        ops.record_feedback("trace:missing", -1, None, "local-user")
    with pytest.raises(ValueError, match="unlinked evaluation"):
        ops.record_evaluation("Question", {}, None, None, "manual-v1")
    with pytest.raises(ValueError, match="workspace does not match"):
        ops.record_evaluation(
            "Question",
            {},
            None,
            None,
            "manual-v1",
            trace_id,
            workspace_id="other",
            access_fingerprint=fingerprint,
        )
    with pytest.raises(ValueError, match="access does not match"):
        ops.record_evaluation(
            "Question",
            {},
            None,
            None,
            "manual-v1",
            trace_id,
            workspace_id="personal",
            access_fingerprint="access-context:wrong",
        )


def test_ops_backfills_operational_access_from_existing_trace(tmp_path):
    import json
    import sqlite3

    path = tmp_path / "legacy-ops.db"
    fingerprint = access_fingerprint("customer-a", ["user:alice"])
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE retrieval_traces (
                trace_id TEXT PRIMARY KEY, query TEXT NOT NULL, mode TEXT NOT NULL,
                result_count INTEGER NOT NULL, result_ids_json TEXT NOT NULL,
                duration_ms REAL NOT NULL, contract_version TEXT NOT NULL,
                context_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
                expected_json TEXT NOT NULL, actual_json TEXT, score REAL,
                trace_id TEXT, evaluator_version TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT, trace_id TEXT NOT NULL,
                rating INTEGER, comment TEXT, actor TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.execute(
            """
            INSERT INTO retrieval_traces(
                trace_id,query,mode,result_count,result_ids_json,duration_ms,
                contract_version,context_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "trace:legacy",
                "question",
                "keyword",
                0,
                "[]",
                1.0,
                "retrieval-v7",
                json.dumps({"workspace_id": "customer-a", "access_fingerprint": fingerprint}),
            ),
        )
        db.execute(
            """
            INSERT INTO evaluations(question,expected_json,trace_id,evaluator_version)
            VALUES('question','{}','trace:legacy','manual-v1')
            """
        )
        db.execute(
            """
            INSERT INTO feedback(trace_id,rating,actor)
            VALUES('trace:legacy',1,'user:alice')
            """
        )

    ops = OpsStore(path)
    with ops.connect() as db:
        row = db.execute(
            "SELECT workspace_id,access_fingerprint FROM evaluations WHERE id=1"
        ).fetchone()
        feedback_row = db.execute(
            "SELECT workspace_id,access_fingerprint FROM feedback WHERE id=1"
        ).fetchone()
    assert row == ("customer-a", fingerprint)
    assert feedback_row == ("customer-a", fingerprint)

    with ops.connect() as db:
        assert audit_evaluation_access(db)["status"] == "PASS"
        assert audit_feedback_access(db)["status"] == "PASS"
        db.execute(
            """
            INSERT INTO evaluations(question,expected_json,evaluator_version)
            VALUES('unattributed','{}','legacy-v1')
            """
        )
        failed = audit_evaluation_access(db)
        db.execute(
            """
            INSERT INTO feedback(trace_id,rating,actor)
            VALUES('trace:legacy',-1,'legacy-user')
            """
        )
        failed_feedback = audit_feedback_access(db)
    assert failed["status"] == "FAIL"
    assert failed["violations"] == 1
    assert failed["samples"] == [2]
    assert failed_feedback["status"] == "FAIL"
    assert failed_feedback["violations"] == 1
    assert failed_feedback["samples"] == [2]
