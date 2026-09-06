"""Phase 1: executable contracts, deliberately red until production is corrected.

No xfail markers: failures must remain visible in the release gate. Provider calls
are fake transports; persistent graph regressions live in the companion module.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from knowledge_os import models
from knowledge_os.evaluate import run_suite
from knowledge_os.file_connector import build_manifest as build_files
from knowledge_os.google_drive_connector import build_manifest as build_drive
from knowledge_os.graph import split_text
from knowledge_os.models import AssertionChange, RetrievalEvaluationSuite
from knowledge_os.notion_action_executor import (
    CREATE_ACTION_TYPE,
    CREATE_POLICY_VERSION,
    EXECUTOR,
    ROOT_TARGET,
    NotionWriteAPI,
    execute_action,
)
from knowledge_os.notion_connector import build_manifest as build_notion
from knowledge_os.ontology import Ontology
from knowledge_os.ops import OpsStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        instant = datetime(2026, 9, 1, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)

    # Patch the clock used by the existing utc_now factory, not the schema or
    # payload. Two explicit instants avoid timing-dependent sleeps/assertions.
    monkeypatch.setattr(models, "datetime", Clock)
    return Clock


@pytest.mark.parametrize("connector", ["filesystem", "google_drive", "notion"])
def test_f2_rebuilt_deletion_manifest_is_byte_identical(connector, tmp_path, clock):
    if connector == "filesystem":
        options = {
            "workspace_id": "regression",
            "source_external_id": "source",
            "connector_id": "files",
            "owner": "local-user",
            "visibility": "PRIVATE",
            "acl": [],
        }
        state = {
            "version": "1",
            "cursor": "previous",
            "files": {
                "deleted.txt": {"source_version": "v1"},
            },
        }

        def build():
            return build_files(tmp_path, state, **options)[0]
    elif connector == "google_drive":
        state = {
            "version": "1",
            "cursor": "previous",
            "files": {
                "deleted-file": {"source_version": "v1"},
            },
        }

        def build():
            return build_drive(
                [],
                state,
                workspace_id="regression",
                folder_id="folder",
                connection_id="connection",
                connector_id="drive",
            )[0]
    else:
        state = {
            "version": "1",
            "cursor": "previous",
            "pages": {
                "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee": {"source_version": "v1"},
            },
        }

        def build():
            return build_notion(
                [],
                state,
                workspace_id="regression",
                root_page_id="11111111-1111-4111-8111-111111111111",
                connection_id="22222222-2222-4222-8222-222222222222",
                connector_id="notion",
            )[0]

    first = build()
    clock.instant = datetime(2026, 9, 2, tzinfo=UTC)
    retry = build()
    assert first.records[0].operation == retry.records[0].operation == "TOMBSTONE"
    assert first.sync_run_id == retry.sync_run_id
    assert first.cursor == retry.cursor
    assert first.model_dump_json() == retry.model_dump_json(), (
        "Identical persisted checkpoint + provider inventory must reconstruct the exact manifest"
    )


@pytest.mark.parametrize("reviewer", ["agent:requester", "human:another-owner"])
def test_f4_wrong_policy_reviewer_never_reaches_claim_or_provider(reviewer):
    class Service:
        claims = 0

        async def get_action(self, action_id):
            return {
                "action": {
                    "action_type": CREATE_ACTION_TYPE,
                    "target": ROOT_TARGET,
                    "policy_version": CREATE_POLICY_VERSION,
                    "parameters": {"title": "Regression fixture"},
                    "status": "APPROVED",
                    "execution_status": "NOT_EXECUTED",
                    "review_principals": [reviewer],
                    "reviewed_by": reviewer,
                    "execution_principals": [EXECUTOR],
                },
                "decisions": [{"decision": "APPROVED", "reviewed_by": reviewer}],
                "executions": [],
            }

        async def claim(self, *args):
            self.claims += 1
            return {
                "id": "claim:fixture",
                "external_idempotency_key": "fixture",
                "unchanged": False,
            }

        async def record(self, *args, **kwargs):
            return kwargs

    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "object": "page",
                "id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            },
        )

    service = Service()
    api = NotionWriteAPI("fixture-not-a-token", transport=httpx.MockTransport(provider))
    try:
        try:
            asyncio.run(execute_action("action:fixture", service, api))
        except (ValueError, PermissionError):
            pass
    finally:
        api.close()
    assert (service.claims, len(calls)) == (0, 0), (
        "The exact policy reviewer human:owner must be checked before claiming or calling Notion"
    )


@pytest.mark.parametrize("value", ["text", 42, True])
def test_f5_scalar_assertions_reject_unregistered_predicate(value):
    change = AssertionChange(
        subject={"name": "Fixture", "entity_type": "Concept"},
        predicate="UNREGISTERED_PREDICATE",
        value=value,
        evidence_chunk_id="chunk:fixture",
    )
    with pytest.raises(ValueError, match="(?i)(predicate|relation)"):
        Ontology.load(ROOT / "config/ontology.yaml").validate(change)


@pytest.mark.parametrize(
    "text",
    ["x" * 10000, "가나다 " * 3000, "short\n\n" + "z" * 2401],
    ids=["long-ascii", "long-korean", "mixed-paragraphs"],
)
def test_f6_chunk_size_is_a_hard_bound_without_content_loss(text):
    chunks = split_text(text, 1200)
    assert chunks
    assert max(map(len, chunks)) <= 1200
    # Whitespace normalization is already part of paragraph-v1; evidence text
    # must not be truncated to achieve the size bound.
    assert "".join("".join(chunks).split()) == "".join(text.split())


def test_f7_denial_evaluation_checks_raw_results_before_exclusion(tmp_path):
    class Graph:
        ops = OpsStore(tmp_path / "ops.db")

        def retrieve(self, request):
            from time import perf_counter

            from knowledge_os.ids import access_fingerprint

            trace = self.ops.retrieval_trace(
                request.query,
                request.mode,
                perf_counter(),
                ["leaked-chunk"],
                workspace_id=request.access.workspace_id,
                access_fingerprint=access_fingerprint(
                    request.access.workspace_id,
                    request.access.principals,
                ),
            )
            return {
                "trace_id": trace,
                "results": [
                    {"document_id": "leaked-document", "chunk_id": "leaked-chunk"},
                ],
            }

    suite = RetrievalEvaluationSuite.model_validate(
        {
            "suite_id": "denial-regression",
            "cases": [
                {
                    "id": "deny",
                    "request": {"query": "fixture"},
                    "expected_no_results": True,
                    "excluded_document_ids": ["leaked-document"],
                }
            ],
        }
    )
    result = run_suite(Graph(), suite)
    assert result["passed"] is False
    assert result["policy_pass_rate"] == 0.0
