from datetime import UTC, date, datetime, time
from enum import StrEnum
from math import isfinite
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_utc(value: AwareDatetime) -> datetime:
    return value.astimezone(UTC)


CanonicalDatetime = Annotated[AwareDatetime, AfterValidator(normalize_utc)]


class Status(StrEnum):
    PROPOSED = "PROPOSED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class AccessContext(BaseModel):
    workspace_id: str = Field(default="personal", min_length=1)
    principals: list[str] = Field(default_factory=lambda: ["local-user"])

    @model_validator(mode="after")
    def normalize_principals(self):
        self.principals = sorted(set(self.principals))
        return self


class TextIngestionRequest(BaseModel):
    connector_id: str = Field(default="local-ingestion", min_length=1)
    source_type: str = "file"
    source_external_id: str
    source_uri: str | None = None
    document_source_uri: str | None = None
    source_version: str | None = Field(default=None, min_length=1)
    source_updated_at: CanonicalDatetime | None = None
    expected_current_version_id: str | None = Field(default=None, min_length=1)
    sync_cursor: str | None = None
    sync_run_id: str | None = None
    document_external_id: str
    title: str
    content: str = Field(min_length=1)
    workspace_id: str = "personal"
    owner: str | None = "local-user"
    visibility: str = Field(default="PRIVATE", pattern=r"^(PRIVATE|SHARED|PUBLIC)$")
    acl: list[str] = Field(default_factory=list)
    parser_version: str = "plain-text-v1"
    chunker_version: str = "paragraph-v1"
    chunk_size: int = Field(default=1200, ge=200, le=8000)

    @model_validator(mode="after")
    def normalize_acl(self):
        self.acl = sorted(set(self.acl))
        return self


class DocumentTombstoneRequest(BaseModel):
    connector_id: str = Field(default="local-ingestion", min_length=1)
    workspace_id: str = "personal"
    source_type: str = "file"
    source_external_id: str = Field(min_length=1)
    document_external_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    expected_current_version_id: str | None = Field(default=None, min_length=1)
    # Effective source deletion time; an absent inventory item has no known instant.
    deleted_at: CanonicalDatetime | None = None
    sync_cursor: str | None = None
    sync_run_id: str | None = None
    reason: str | None = None
    recorded_by: str = Field(default="source-connector", min_length=1)


class SyncCheckpointCommit(BaseModel):
    connector_id: str = Field(default="local-ingestion", min_length=1)
    workspace_id: str = "personal"
    source_type: str = Field(min_length=1)
    source_external_id: str = Field(min_length=1)
    sync_run_id: str = Field(min_length=1)
    cursor: str = Field(min_length=1)
    expected_previous_cursor: str | None = None
    allow_empty_run: bool = False
    completed_at: CanonicalDatetime = Field(default_factory=utc_now)
    committed_by: str = Field(default="source-connector", min_length=1)
    stats: dict[str, int] = Field(default_factory=dict)
    manifest_hash: str | None = Field(default=None, min_length=1)
    manifest_version: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def nonnegative_stats(self):
        if any(value < 0 for value in self.stats.values()):
            raise ValueError("sync checkpoint stats must be nonnegative")
        return self


class ManifestUpsertRecord(BaseModel):
    operation: Literal["UPSERT"]
    document_external_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    source_updated_at: CanonicalDatetime | None = None
    title: str = Field(min_length=1)
    document_source_uri: str | None = None
    content: str = Field(min_length=1)
    owner: str | None = "local-user"
    visibility: str = Field(default="PRIVATE", pattern=r"^(PRIVATE|SHARED|PUBLIC)$")
    acl: list[str] = Field(default_factory=list)
    parser_version: str = "plain-text-v1"
    chunker_version: str = "paragraph-v1"
    chunk_size: int = Field(default=1200, ge=200, le=8000)

    @model_validator(mode="after")
    def normalize_acl(self):
        self.acl = sorted(set(self.acl))
        return self


class ManifestTombstoneRecord(BaseModel):
    operation: Literal["TOMBSTONE"]
    document_external_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    # Never manufacture remote deletion time from the manifest builder's clock.
    deleted_at: CanonicalDatetime | None = None
    reason: str | None = None


ManifestRecord = Annotated[
    ManifestUpsertRecord | ManifestTombstoneRecord,
    Field(discriminator="operation"),
]


class SyncManifest(BaseModel):
    manifest_version: Literal["1", "2"] = "2"
    workspace_id: str = "personal"
    source_type: str = Field(min_length=1)
    source_external_id: str = Field(min_length=1)
    source_uri: str | None = None
    sync_run_id: str = Field(min_length=1)
    cursor: str = Field(min_length=1)
    expected_previous_cursor: str | None = None
    connector_id: str = Field(min_length=1)
    records: list[ManifestRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_document_records(self):
        document_ids = [record.document_external_id for record in self.records]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("manifest records must have unique document_external_id values")
        self.records.sort(key=lambda record: record.document_external_id)
        return self


class IngestionResult(BaseModel):
    source_id: str
    document_id: str
    document_version_id: str
    content_hash: str
    processing_fingerprint: str
    chunks_created: int
    unchanged: bool


class EvidenceBundleRequest(BaseModel):
    chunk_ids: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1, max_length=100)
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def normalize_chunk_ids(self):
        self.chunk_ids = sorted(set(self.chunk_ids))
        return self


class EntityRef(BaseModel):
    name: str = Field(min_length=1)
    entity_type: str
    aliases: list[str] = Field(default_factory=list)


class AssertionChange(BaseModel):
    subject: EntityRef
    predicate: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    object: EntityRef | None = None
    value: str | int | float | bool | None = None
    evidence_chunk_id: str
    confidence: float = Field(default=0.8, ge=0, le=1)
    observed_at: CanonicalDatetime | None = None
    valid_from: CanonicalDatetime | None = None
    valid_to: CanonicalDatetime | None = None
    supersedes_assertion_id: str | None = None
    extractor_version: str = "manual-v1"

    @model_validator(mode="after")
    def object_or_value(self):
        if (self.object is None) == (self.value is None):
            raise ValueError("exactly one of object or value is required")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be earlier than valid_from")
        return self


class ProposalCreate(BaseModel):
    changes: list[AssertionChange] = Field(min_length=1)
    workspace_id: str = "personal"
    created_by: str = "local-user"
    reason: str | None = None
    ontology_version: str = "1.0.0"
    access: AccessContext = Field(default_factory=AccessContext)


class ProposalDecision(BaseModel):
    reviewed_by: str = Field(default="local-user", min_length=1)
    reason: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)


class DecisionProposalCreate(BaseModel):
    workspace_id: str = "personal"
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    decided_at: CanonicalDatetime | None = None
    decided_on: date | None = None
    decided_at_precision: Literal["INSTANT", "DAY"] | None = None
    valid_from: CanonicalDatetime | None = None
    valid_to: CanonicalDatetime | None = None
    evidence_chunk_ids: list[str] = Field(min_length=1)
    participants: list[str] = Field(default_factory=list)
    proposed_by: str = Field(min_length=1)
    reason: str | None = None
    ontology_version: str = "1.0.0"
    supersedes_decision_id: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def normalize_and_validate(self):
        if self.decided_at is None and self.decided_on is None:
            raise ValueError("exactly one of decided_at or decided_on is required")
        expected_precision = "DAY" if self.decided_on is not None else "INSTANT"
        if self.decided_at_precision not in (None, expected_precision):
            raise ValueError("decided_at_precision conflicts with the supplied temporal value")
        self.decided_at_precision = expected_precision
        if self.decided_on is not None:
            day_boundary = datetime.combine(self.decided_on, time.min, tzinfo=UTC)
            if self.decided_at is not None and self.decided_at != day_boundary:
                raise ValueError("decided_at conflicts with the decided_on day boundary")
            self.decided_at = day_boundary
        self.evidence_chunk_ids = sorted(set(self.evidence_chunk_ids))
        self.participants = sorted(set(self.participants))
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be earlier than valid_from")
        return self


class EventProposalCreate(BaseModel):
    workspace_id: str = "personal"
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    event_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    occurred_at: CanonicalDatetime
    ended_at: CanonicalDatetime | None = None
    evidence_chunk_ids: list[str] = Field(min_length=1)
    participants: list[str] = Field(default_factory=list)
    proposed_by: str = Field(min_length=1)
    reason: str | None = None
    ontology_version: str = "1.0.0"
    supersedes_event_id: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def normalize_and_validate(self):
        self.evidence_chunk_ids = sorted(set(self.evidence_chunk_ids))
        self.participants = sorted(set(self.participants))
        if self.ended_at and self.ended_at < self.occurred_at:
            raise ValueError("ended_at must not be earlier than occurred_at")
        return self


class ActionCreate(BaseModel):
    action_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    target: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = Field(min_length=1)
    workspace_id: str = "personal"
    reason: str | None = None
    policy_version: str = "action-policy-v1"
    approval_required: bool = True
    review_principals: list[str] = Field(default_factory=lambda: ["local-user"], min_length=1)
    execution_principals: list[str] = Field(
        default_factory=lambda: ["local-connector"], min_length=1
    )
    idempotency_key: str = Field(min_length=1, max_length=200)
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def normalize_capability_principals(self):
        if not self.approval_required:
            raise ValueError("external actions require an explicit approval")
        self.review_principals = sorted(set(self.review_principals))
        self.execution_principals = sorted(set(self.execution_principals))
        return self


class ActionDecision(BaseModel):
    reviewed_by: str = Field(min_length=1)
    reason: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)


class ActionExecutionClaimCreate(BaseModel):
    executed_by: str = Field(min_length=1)
    connector: str = Field(min_length=1)
    authorization_ref: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=200)
    lease_seconds: int = Field(default=300, ge=30, le=900)
    access: AccessContext = Field(default_factory=AccessContext)


class ActionExecutionCreate(BaseModel):
    claim_id: str = Field(min_length=1)
    external_idempotency_key: str = Field(min_length=1)
    status: str = Field(pattern=r"^(SUCCEEDED|FAILED)$")
    executed_by: str = Field(min_length=1)
    connector: str = Field(min_length=1)
    external_api: str = Field(min_length=1)
    authorization_ref: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=200)
    external_request_id: str | None = None
    executed_at: CanonicalDatetime = Field(default_factory=utc_now)
    result: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    rollback_ref: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def failure_requires_error(self):
        if self.status == "FAILED" and not self.error:
            raise ValueError("failed execution requires error evidence")
        return self


class FeedbackCreate(BaseModel):
    trace_id: str = Field(min_length=1)
    rating: int | None = Field(default=None, ge=-1, le=1)
    comment: str | None = Field(default=None, min_length=1, max_length=4000)
    actor: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def validate_content_and_actor(self):
        if self.rating is None and not self.comment:
            raise ValueError("rating or comment is required")
        if self.actor is None:
            if len(self.access.principals) != 1:
                raise ValueError("actor is required when access has multiple principals")
            self.actor = self.access.principals[0]
        elif self.actor not in self.access.principals:
            raise ValueError("actor must be one of access principals")
        return self


class EvaluationCreate(BaseModel):
    question: str = Field(min_length=1)
    expected: Any
    actual: Any | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    evaluator_version: str = Field(min_length=1)
    trace_id: str | None = None
    access: AccessContext = Field(default_factory=AccessContext)


class EmbeddingUpsert(BaseModel):
    vector: list[float] = Field(min_length=1)
    model: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    created_by: str = Field(min_length=1)
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def finite_vector(self):
        if not all(isfinite(value) for value in self.vector):
            raise ValueError("embedding vector values must be finite")
        return self


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1)
    mode: str = Field(default="keyword", pattern=r"^(keyword|semantic|hybrid)$")
    embedding: list[float] | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
    access: AccessContext = Field(default_factory=AccessContext)

    @model_validator(mode="after")
    def semantic_modes_require_embedding(self):
        if self.mode in {"semantic", "hybrid"} and self.embedding is None:
            raise ValueError(f"{self.mode} retrieval requires an embedding")
        if self.embedding is not None and (not self.embedding_model or not self.embedding_version):
            raise ValueError("embedding_model and embedding_version are required with an embedding")
        if self.embedding is not None and not all(isfinite(value) for value in self.embedding):
            raise ValueError("query embedding values must be finite")
        return self


class RetrievalEvaluationCase(BaseModel):
    id: str = Field(min_length=1)
    question: str | None = None
    request: RetrievalQuery
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_document_ids: list[str] = Field(default_factory=list)
    expected_no_results: bool = False
    excluded_document_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_expected_ids(self):
        self.expected_chunk_ids = sorted(set(self.expected_chunk_ids))
        self.expected_document_ids = sorted(set(self.expected_document_ids))
        self.excluded_document_ids = sorted(set(self.excluded_document_ids))
        expectation_count = sum(
            [
                bool(self.expected_chunk_ids),
                bool(self.expected_document_ids),
                self.expected_no_results,
            ]
        )
        if expectation_count != 1:
            raise ValueError("exactly one retrieval result expectation is required")
        overlap = set(self.expected_document_ids).intersection(self.excluded_document_ids)
        if overlap:
            raise ValueError("expected documents cannot also be excluded")
        return self


class RetrievalEvaluationSuite(BaseModel):
    suite_version: Literal["1"] = "1"
    suite_id: str = Field(min_length=1)
    evaluator_version: str = Field(default="retrieval-eval-v1", min_length=1)
    minimum_mean_recall: float = Field(default=0.8, ge=0, le=1)
    cases: list[RetrievalEvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_case_ids(self):
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation case ids must be unique")
        return self


class ActionContract(BaseModel):
    action_type: str
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_by: str
    requested_at: CanonicalDatetime = Field(default_factory=utc_now)
    status: str = "PROPOSED"
    approval_required: bool = True
    approved_by: str | None = None
    execution_ref: str | None = None
    result: dict[str, Any] | None = None
    rollback_ref: str | None = None
