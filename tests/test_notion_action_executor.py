import asyncio
import json
from typing import Any

import httpx
import pytest

from knowledge_os.notion_action_executor import (
    ARCHIVE_ACTION_TYPE,
    ARCHIVE_POLICY_VERSION,
    CREATE_ACTION_TYPE,
    CREATE_POLICY_VERSION,
    EXECUTOR,
    ROOT_PAGE_ID,
    ROOT_TARGET,
    AmbiguousNotionOutcome,
    NotionWriteAPI,
    execute_action,
    validate_action,
)

CREATED_PAGE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def action_detail(
    *,
    action_type: str = CREATE_ACTION_TYPE,
    target: str = ROOT_TARGET,
    policy_version: str = CREATE_POLICY_VERSION,
    parameters: dict[str, Any] | None = None,
    execution_status: str = "NOT_EXECUTED",
    executions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "action": {
            "action_type": action_type,
            "target": target,
            "policy_version": policy_version,
            "parameters": parameters if parameters is not None else {"title": "Governed page"},
            "status": "APPROVED",
            "execution_status": execution_status,
            "execution_principals": [EXECUTOR],
        },
        "executions": executions or [],
    }


class FakeService:
    def __init__(
        self,
        detail: dict[str, Any],
        *,
        creation_detail: dict[str, Any] | None = None,
        claim_unchanged: bool = False,
    ) -> None:
        self.detail = detail
        self.creation_detail = creation_detail
        self.claim_unchanged = claim_unchanged
        self.claim_calls = 0
        self.records: list[dict[str, Any]] = []

    async def get_action(self, action_id: str) -> dict[str, Any]:
        if action_id == "action:create":
            assert self.creation_detail is not None
            return self.creation_detail
        return self.detail

    async def claim(self, action_id: str, policy_version: str) -> dict[str, Any]:
        self.claim_calls += 1
        return {
            "id": "claim:1",
            "external_idempotency_key": "external:1",
            "unchanged": self.claim_unchanged,
        }

    async def record(
        self,
        action_id: str,
        claim: dict[str, Any],
        policy_version: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        record = {"action_id": action_id, "policy_version": policy_version, **kwargs}
        self.records.append(record)
        return record


def notion_api(handler) -> NotionWriteAPI:
    return NotionWriteAPI("secret", transport=httpx.MockTransport(handler))


def test_create_policy_is_exact_and_bounded():
    valid = validate_action(action_detail(parameters={"title": "Page", "body": "one\ntwo"}))
    assert valid.target_page_id == ROOT_PAGE_ID

    invalid_cases = [
        action_detail(target=f"notion:page:{CREATED_PAGE_ID}"),
        action_detail(policy_version="action-policy-v1"),
        action_detail(parameters={"title": " Page"}),
        action_detail(parameters={"title": "Page", "extra": True}),
        action_detail(parameters={"title": "Page\nTwo"}),
        action_detail(parameters={"title": "Page", "body": "\x00"}),
        action_detail(parameters={"title": "Page", "body": "\n" * 101}),
    ]
    for detail in invalid_cases:
        with pytest.raises((ValueError, PermissionError)):
            validate_action(detail)


def test_write_api_uses_one_bounded_create_request_and_current_trash_field():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"x-request-id": "notion-request-1"},
            json={"object": "page", "id": CREATED_PAGE_ID, "url": "https://notion.so/page"},
        )

    api = notion_api(handler)
    try:
        created = api.create_page(parent_page_id=ROOT_PAGE_ID, title="Page", body="one\ntwo")
        archived = api.archive_page(CREATED_PAGE_ID)
    finally:
        api.close()

    assert created.page_id == CREATED_PAGE_ID
    assert archived.page_id == CREATED_PAGE_ID
    create_body = json.loads(requests[0].content)
    assert requests[0].method == "POST"
    assert create_body["parent"] == {"type": "page_id", "page_id": ROOT_PAGE_ID}
    assert len(create_body["children"]) == 2
    assert requests[1].method == "PATCH"
    assert json.loads(requests[1].content) == {"in_trash": True}
    assert "archived" not in requests[1].content.decode()


def test_create_execution_records_external_identity_once():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"x-request-id": "notion-request-1"},
            json={"object": "page", "id": CREATED_PAGE_ID, "url": "https://notion.so/page"},
        )

    service = FakeService(action_detail(parameters={"title": "Page", "body": "Body"}))
    api = notion_api(handler)
    try:
        result = asyncio.run(execute_action("action:new", service, api))
    finally:
        api.close()

    assert calls == 1
    assert result["status"] == "SUCCEEDED"
    assert result["result"]["page_id"] == CREATED_PAGE_ID
    assert result["external_request_id"] == "notion-request-1"
    assert result["rollback_ref"] == ARCHIVE_ACTION_TYPE


def test_existing_claim_never_repeats_external_call():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    service = FakeService(action_detail(), claim_unchanged=True)
    api = notion_api(handler)
    try:
        with pytest.raises(RuntimeError, match="reconciliation"):
            asyncio.run(execute_action("action:new", service, api))
    finally:
        api.close()
    assert calls == 0
    assert service.records == []


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("timeout")),
        lambda request: httpx.Response(503, headers={"x-request-id": "server-1"}),
        lambda request: httpx.Response(200, content=b"not-json"),
    ],
)
def test_ambiguous_create_is_failed_without_retry(handler):
    calls = 0

    def counted(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return handler(request)

    service = FakeService(action_detail())
    api = notion_api(counted)
    try:
        result = asyncio.run(execute_action("action:new", service, api))
    finally:
        api.close()
    assert calls == 1
    assert result["status"] == "FAILED"
    assert result["error"]["type"] == "ambiguous_external_outcome"
    assert result["error"]["retryable"] is False


def test_archive_requires_and_uses_successful_creation_evidence():
    creation = action_detail(
        execution_status="SUCCEEDED",
        executions=[
            {
                "status": "SUCCEEDED",
                "payload": {"result": {"page_id": CREATED_PAGE_ID}},
            }
        ],
    )
    archive = action_detail(
        action_type=ARCHIVE_ACTION_TYPE,
        target=f"notion:page:{CREATED_PAGE_ID}",
        policy_version=ARCHIVE_POLICY_VERSION,
        parameters={"creation_action_id": "action:create"},
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"object": "page", "id": CREATED_PAGE_ID})

    service = FakeService(archive, creation_detail=creation)
    api = notion_api(handler)
    try:
        result = asyncio.run(execute_action("action:archive", service, api))
    finally:
        api.close()

    assert len(requests) == 1
    assert requests[0].method == "PATCH"
    assert result["status"] == "SUCCEEDED"
    assert result["result"]["creation_action_id"] == "action:create"
    assert result["result"]["in_trash"] is True


def test_archive_rejects_page_not_proven_by_creation():
    creation = action_detail(
        execution_status="SUCCEEDED",
        executions=[
            {"status": "SUCCEEDED", "payload": {"result": {"page_id": ROOT_PAGE_ID}}}
        ],
    )
    archive = action_detail(
        action_type=ARCHIVE_ACTION_TYPE,
        target=f"notion:page:{CREATED_PAGE_ID}",
        policy_version=ARCHIVE_POLICY_VERSION,
        parameters={"creation_action_id": "action:create"},
    )
    with pytest.raises(ValueError, match="does not match"):
        validate_action(archive, creation_detail=creation)


def test_ambiguous_exception_type_is_not_a_retry_signal():
    assert issubclass(AmbiguousNotionOutcome, RuntimeError)
