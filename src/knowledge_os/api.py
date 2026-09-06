from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_contracts, get_graph, get_ontology, get_ops, get_prompts
from knowledge_os.doctor import run_doctor
from knowledge_os.graph import GraphStore
from knowledge_os.ids import access_fingerprint
from knowledge_os.models import (
    AccessContext,
    ActionCreate,
    ActionDecision,
    ActionExecutionClaimCreate,
    ActionExecutionCreate,
    CanonicalDatetime,
    DecisionProposalCreate,
    DocumentTombstoneRequest,
    EmbeddingUpsert,
    EvaluationCreate,
    EventProposalCreate,
    EvidenceBundleRequest,
    FeedbackCreate,
    IngestionResult,
    ProposalCreate,
    ProposalDecision,
    RetrievalQuery,
    SyncCheckpointCommit,
    SyncManifest,
    TextIngestionRequest,
)
from knowledge_os.ontology import Ontology


@asynccontextmanager
async def lifespan(app: FastAPI):
    graph = get_graph()
    graph.verify()
    graph.migrate(get_settings().migrations_path)
    yield
    graph.close()


app = FastAPI(title="Knowledge OS", version="0.1.0", lifespan=lifespan)
GraphDep = Annotated[GraphStore, Depends(get_graph)]
OntologyDep = Annotated[Ontology, Depends(get_ontology)]


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "UNMATCHED")


@app.middleware("http")
async def observe_http_adapter(request: Request, call_next):
    started = perf_counter()
    request_id = f"request:{uuid4()}"
    ops = get_ops()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001 - adapter boundary records unexpected failures
        route = _route_template(request)
        error_id = ops.error(
            "http_adapter",
            exc,
            safe_message="unhandled HTTP adapter failure",
            request_id=request_id,
            method=request.method,
            route=route,
            adapter_contract="http-v1",
        )
        ops.telemetry(
            "http_adapter",
            "ERROR",
            started,
            request_id=request_id,
            method=request.method,
            route=route,
            error_id=error_id,
            adapter_contract="http-v1",
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "internal server error",
                "error_id": error_id,
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
    route = _route_template(request)
    if response.status_code in {401, 403}:
        status = "DENIED"
    elif response.status_code == 404:
        status = "NOT_FOUND"
    elif response.status_code == 409:
        status = "CONFLICT"
    elif response.status_code >= 500:
        status = "SERVER_ERROR"
    elif response.status_code >= 400:
        status = "CLIENT_ERROR"
    else:
        status = "SUCCESS"
    ops.telemetry(
        "http_adapter",
        status,
        started,
        request_id=request_id,
        method=request.method,
        route=route,
        status_code=response.status_code,
        adapter_contract="http-v1",
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health(graph: GraphDep):
    graph.verify()
    return {"status": "ok"}


@app.get("/health/readiness")
def readiness(graph: GraphDep):
    report = run_doctor(graph)
    if report["status"] != "ok":
        raise HTTPException(503, detail=report)
    return report


@app.get("/v1/contracts")
def contracts():
    return get_contracts().as_dict()


@app.get("/v1/prompts")
def prompts():
    return get_prompts().metadata()


@app.get("/v1/prompts/{name}")
def prompt(name: str):
    try:
        return get_prompts().prompt(name)
    except KeyError as exc:
        raise HTTPException(404, "prompt not found") from exc


@app.get("/v1/ontology")
def ontology(ontology: OntologyDep):
    return ontology.as_dict()


@app.post("/v1/ingestion/text", response_model=IngestionResult)
def ingest_text(request: TextIngestionRequest, graph: GraphDep):
    try:
        return graph.ingest_text(request)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/evidence/bundle")
def evidence_bundle(request: EvidenceBundleRequest, graph: GraphDep):
    result = graph.evidence_bundle(request)
    if result is None:
        raise HTTPException(404, "evidence bundle unavailable")
    return {"evidence": result}


@app.post("/v1/ingestion/tombstone")
def tombstone_document(request: DocumentTombstoneRequest, graph: GraphDep):
    try:
        return graph.tombstone_document(request)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "source document not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/ingestion/checkpoints", status_code=201)
def commit_sync_checkpoint(request: SyncCheckpointCommit, graph: GraphDep):
    try:
        return graph.commit_sync_checkpoint(request)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "source not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/ingestion/manifests", status_code=201)
def ingest_manifest(request: SyncManifest, graph: GraphDep):
    try:
        return graph.ingest_manifest(request)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "manifest references an unknown source document") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/v1/sources")
def list_sources(
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return graph.sources(
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        limit,
    )


@app.get("/v1/sources/{source_id}")
def get_source(
    source_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    result = graph.source(
        source_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
    )
    if result is None:
        raise HTTPException(404, "source not found")
    return result


@app.get("/v1/documents")
def list_documents(
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    source_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    return graph.documents(
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        source_id,
        limit,
    )


@app.get("/v1/documents/{document_id}")
def get_document(
    document_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    include_chunks: bool = Query(default=False),
):
    result = graph.document(
        document_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        include_chunks,
    )
    if result is None:
        raise HTTPException(404, "document not found")
    return result


@app.post("/v1/proposals", status_code=201)
def create_proposal(request: ProposalCreate, graph: GraphDep):
    try:
        return graph.create_proposal(request)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@app.get("/v1/proposals")
def list_proposals(
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    status: Annotated[str | None, Query(pattern=r"^(PROPOSED|APPROVED|REJECTED)$")] = "PROPOSED",
    proposal_type: Annotated[str | None, Query(pattern=r"^(ASSERTION|DECISION|EVENT)$")] = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    return graph.proposals(
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        status,
        proposal_type,
        limit,
    )


@app.get("/v1/proposals/{proposal_id}")
def get_proposal(
    proposal_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    result = graph.proposal(
        proposal_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
    )
    if result is None:
        raise HTTPException(404, "proposal not found")
    return result


@app.post("/v1/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    decision: ProposalDecision,
    graph: GraphDep,
    ontology: OntologyDep,
):
    try:
        return graph.approve_proposal(
            proposal_id,
            decision.reviewed_by,
            decision.reason,
            ontology,
            decision.access,
        )
    except KeyError as exc:
        raise HTTPException(404, "proposal not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    decision: ProposalDecision,
    graph: GraphDep,
):
    try:
        return graph.reject_proposal(
            proposal_id,
            decision.reviewed_by,
            decision.reason,
            decision.access,
        )
    except KeyError as exc:
        raise HTTPException(404, "proposal not found or no longer pending") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/decisions/proposals", status_code=201)
def create_decision_proposal(request: DecisionProposalCreate, graph: GraphDep):
    try:
        return graph.create_decision_proposal(request)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@app.get("/v1/decisions/{decision_id}")
def get_decision(
    decision_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    as_of: Annotated[CanonicalDatetime | None, Query()] = None,
):
    result = graph.decision(
        decision_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        as_of,
    )
    if result is None:
        raise HTTPException(404, "decision not found")
    return result


@app.post("/v1/events/proposals", status_code=201)
def create_event_proposal(request: EventProposalCreate, graph: GraphDep):
    try:
        return graph.create_event_proposal(request)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@app.get("/v1/events/{event_id}")
def get_event(
    event_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    as_of: Annotated[CanonicalDatetime | None, Query()] = None,
):
    result = graph.event(
        event_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        as_of,
    )
    if result is None:
        raise HTTPException(404, "event not found")
    return result


@app.get("/v1/search")
def search(
    graph: GraphDep,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    return graph.search_traced(
        q,
        limit,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
    )


@app.post("/v1/retrieval/query")
def retrieve(request: RetrievalQuery, graph: GraphDep):
    try:
        return graph.retrieve(request)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/v1/retrieval/capabilities")
def retrieval_capabilities(
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    return graph.retrieval_capabilities(
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        )
    )


@app.put("/v1/chunks/{chunk_id}/embedding")
def upsert_chunk_embedding(chunk_id: str, request: EmbeddingUpsert, graph: GraphDep):
    try:
        return graph.upsert_chunk_embedding(chunk_id, request)
    except KeyError as exc:
        raise HTTPException(404, "chunk not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/v1/traces/{trace_id}")
def get_trace(
    trace_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    access = AccessContext(
        workspace_id=workspace_id,
        principals=principal if principal is not None else ["local-user"],
    )
    result = graph.ops.get_trace_for_access(
        trace_id,
        access.workspace_id,
        access_fingerprint(access.workspace_id, access.principals),
    )
    if result is None:
        raise HTTPException(404, "trace not found")
    return result


@app.post("/v1/feedback", status_code=201)
def create_feedback(request: FeedbackCreate, graph: GraphDep):
    try:
        if (
            graph.ops.get_trace_for_access(
                request.trace_id,
                request.access.workspace_id,
                access_fingerprint(request.access.workspace_id, request.access.principals),
            )
            is None
        ):
            raise KeyError(request.trace_id)
        feedback_id = graph.ops.record_feedback(
            request.trace_id, request.rating, request.comment, request.actor
        )
    except KeyError as exc:
        raise HTTPException(404, "retrieval trace not found") from exc
    return {"id": feedback_id, "trace_id": request.trace_id}


@app.post("/v1/evaluations", status_code=201)
def create_evaluation(request: EvaluationCreate, graph: GraphDep):
    try:
        if (
            request.trace_id
            and graph.ops.get_trace_for_access(
                request.trace_id,
                request.access.workspace_id,
                access_fingerprint(request.access.workspace_id, request.access.principals),
            )
            is None
        ):
            raise KeyError(request.trace_id)
        evaluation_id = graph.ops.record_evaluation(
            request.question,
            request.expected,
            request.actual,
            request.score,
            request.evaluator_version,
            request.trace_id,
            workspace_id=request.access.workspace_id,
            access_fingerprint=access_fingerprint(
                request.access.workspace_id, request.access.principals
            ),
        )
    except KeyError as exc:
        raise HTTPException(404, "retrieval trace not found") from exc
    return {"id": evaluation_id, "trace_id": request.trace_id}


@app.get("/v1/entities/search")
def search_entities(
    graph: GraphDep,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    as_of: Annotated[CanonicalDatetime | None, Query()] = None,
):
    return graph.search_entities(
        q,
        limit,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        as_of,
    )


@app.get("/v1/assertions/{assertion_id}")
def get_assertion(
    assertion_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    as_of: Annotated[CanonicalDatetime | None, Query()] = None,
):
    result = graph.assertion(
        assertion_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        as_of,
    )
    if result is None:
        raise HTTPException(404, "assertion not found")
    return result


@app.get("/v1/entities/{entity_id}")
def get_entity(
    entity_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    as_of: Annotated[CanonicalDatetime | None, Query()] = None,
):
    result = graph.entity(
        entity_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        as_of,
    )
    if result is None:
        raise HTTPException(404, "entity not found")
    return result


@app.get("/v1/entities/{entity_id}/neighbors")
def get_neighbors(
    entity_id: str,
    graph: GraphDep,
    limit: int = Query(default=50, ge=1, le=200),
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
    as_of: Annotated[CanonicalDatetime | None, Query()] = None,
):
    return graph.neighbors(
        entity_id,
        limit,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        as_of,
    )


@app.post("/v1/actions", status_code=201)
def create_action(request: ActionCreate, graph: GraphDep):
    try:
        return graph.create_action(request)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@app.get("/v1/actions")
def list_actions(
    graph: GraphDep,
    status: Annotated[str | None, Query(pattern=r"^(PROPOSED|APPROVED|REJECTED)$")] = None,
    action_type: Annotated[str | None, Query(pattern=r"^[A-Z][A-Z0-9_]*$")] = None,
    limit: int = Query(default=50, ge=1, le=100),
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    return graph.actions(
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
        status=status,
        action_type=action_type,
        limit=limit,
    )


@app.get("/v1/actions/{action_id}")
def get_action(
    action_id: str,
    graph: GraphDep,
    workspace_id: str = Query(default="personal", min_length=1),
    principal: Annotated[list[str] | None, Query()] = None,
):
    result = graph.action(
        action_id,
        AccessContext(
            workspace_id=workspace_id,
            principals=principal if principal is not None else ["local-user"],
        ),
    )
    if result is None:
        raise HTTPException(404, "action not found")
    return result


@app.post("/v1/actions/{action_id}/approve")
def approve_action(action_id: str, decision: ActionDecision, graph: GraphDep):
    try:
        return graph.decide_action(
            action_id,
            "APPROVED",
            decision.reviewed_by,
            decision.reason,
            decision.access,
        )
    except KeyError as exc:
        raise HTTPException(404, "action not found or no longer pending") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/actions/{action_id}/reject")
def reject_action(action_id: str, decision: ActionDecision, graph: GraphDep):
    try:
        return graph.decide_action(
            action_id,
            "REJECTED",
            decision.reviewed_by,
            decision.reason,
            decision.access,
        )
    except KeyError as exc:
        raise HTTPException(404, "action not found or no longer pending") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/actions/{action_id}/executions", status_code=201)
def record_action_execution(action_id: str, execution: ActionExecutionCreate, graph: GraphDep):
    try:
        return graph.record_action_execution(action_id, execution)
    except KeyError as exc:
        raise HTTPException(404, "action not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/actions/{action_id}/execution-claims", status_code=201)
def claim_action_execution(action_id: str, claim: ActionExecutionClaimCreate, graph: GraphDep):
    try:
        return graph.claim_action_execution(action_id, claim)
    except KeyError as exc:
        raise HTTPException(404, "action not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
