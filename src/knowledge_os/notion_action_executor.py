import argparse
import asyncio
import json
import unicodedata
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from knowledge_os.api import app
from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_graph
from knowledge_os.notion_connector import NOTION_API_VERSION, normalize_id, resolve_notion_token

CREATE_ACTION_TYPE = "NOTION_CREATE_PAGE"
ARCHIVE_ACTION_TYPE = "NOTION_ARCHIVE_PAGE"
CREATE_POLICY_VERSION = "notion-create-page-policy-v1"
ARCHIVE_POLICY_VERSION = "notion-archive-page-policy-v1"
ROOT_PAGE_ID = "3d2c3262-9b85-801f-a806-f5fec123ec68"
ROOT_TARGET = f"notion:page:{ROOT_PAGE_ID}"
EXECUTOR = "connector:notion"
CONNECTOR = "notion-governed-actions-v1"
AUTHORIZATION_REF = "credential:local-notion"


class AmbiguousNotionOutcome(RuntimeError):
    """The request may have reached Notion; automatic retry is unsafe."""


class NotionRejected(RuntimeError):
    def __init__(self, status_code: int, request_id: str) -> None:
        super().__init__(f"Notion API returned HTTP {status_code} (request_id={request_id})")
        self.status_code = status_code
        self.request_id = request_id


@dataclass(frozen=True)
class ExternalResult:
    page_id: str
    url: str | None
    request_id: str | None


@dataclass(frozen=True)
class ValidatedAction:
    action_type: str
    target_page_id: str
    policy_version: str
    title: str | None = None
    body: str | None = None
    creation_action_id: str | None = None


class ActionService(Protocol):
    async def get_action(self, action_id: str) -> dict[str, Any]: ...

    async def claim(self, action_id: str, policy_version: str) -> dict[str, Any]: ...

    async def record(
        self,
        action_id: str,
        claim: dict[str, Any],
        policy_version: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        external_request_id: str | None = None,
        rollback_ref: str | None = None,
    ) -> dict[str, Any]: ...


def _has_disallowed_control(value: str, *, allow_body_whitespace: bool) -> bool:
    for character in value:
        if allow_body_whitespace and character in {"\n", "\t"}:
            continue
        if unicodedata.category(character).startswith("C"):
            return True
    return False


def _page_id_from_target(target: str) -> str:
    prefix = "notion:page:"
    if not target.startswith(prefix):
        raise ValueError("Notion Action target must use notion:page:<uuid>")
    return normalize_id(target.removeprefix(prefix))


def _action_record(detail: dict[str, Any], *, allow_succeeded: bool = False) -> dict[str, Any]:
    action = detail.get("action")
    if not isinstance(action, dict):
        raise TypeError("Knowledge Service returned an invalid Action detail")
    if action.get("status") != "APPROVED":
        raise ValueError("Action must be approved before policy validation")
    if not allow_succeeded and action.get("execution_status") == "SUCCEEDED":
        raise ValueError("Action already succeeded")
    if EXECUTOR not in action.get("execution_principals", []):
        raise PermissionError("Action does not authorize connector:notion")
    return action


def validate_action(
    detail: dict[str, Any], *, creation_detail: dict[str, Any] | None = None
) -> ValidatedAction:
    action = _action_record(detail)
    action_type = action.get("action_type")
    parameters = action.get("parameters")
    if not isinstance(parameters, dict):
        raise TypeError("Action parameters must be an object")

    if action_type == CREATE_ACTION_TYPE:
        if action.get("policy_version") != CREATE_POLICY_VERSION:
            raise ValueError("creation Action policy version is not active")
        if action.get("target") != ROOT_TARGET:
            raise ValueError("creation Action target is outside the approved root")
        if set(parameters) - {"title", "body"} or "title" not in parameters:
            raise ValueError("creation parameters must contain only title and optional body")
        title = parameters["title"]
        body = parameters.get("body", "")
        if not isinstance(title, str) or not 1 <= len(title) <= 200 or title != title.strip():
            raise ValueError("title must be trimmed plain text between 1 and 200 code points")
        if _has_disallowed_control(title, allow_body_whitespace=False):
            raise ValueError("title contains a disallowed control character")
        if not isinstance(body, str) or len(body) > 10_000:
            raise ValueError("body must be plain text of at most 10000 code points")
        if _has_disallowed_control(body, allow_body_whitespace=True):
            raise ValueError("body contains a disallowed control character")
        _paragraph_children(body)
        return ValidatedAction(
            action_type=action_type,
            target_page_id=ROOT_PAGE_ID,
            policy_version=CREATE_POLICY_VERSION,
            title=title,
            body=body,
        )

    if action_type == ARCHIVE_ACTION_TYPE:
        if action.get("policy_version") != ARCHIVE_POLICY_VERSION:
            raise ValueError("archive Action policy version is not active")
        if set(parameters) != {"creation_action_id"}:
            raise ValueError("archive parameters must contain only creation_action_id")
        creation_action_id = parameters["creation_action_id"]
        if not isinstance(creation_action_id, str) or not creation_action_id:
            raise ValueError("creation_action_id is required")
        if creation_detail is None:
            raise ValueError("archive Action requires its creation Action evidence")
        created_action = _action_record(creation_detail, allow_succeeded=True)
        if created_action.get("action_type") != CREATE_ACTION_TYPE:
            raise ValueError("referenced Action is not a page creation")
        matching_results = []
        for execution in creation_detail.get("executions", []):
            payload = execution.get("payload", {})
            result = payload.get("result", {})
            if execution.get("status") == "SUCCEEDED" and isinstance(result, dict):
                matching_results.append(result)
        if len(matching_results) != 1:
            raise ValueError("creation Action must have exactly one successful execution")
        created_page_id = normalize_id(str(matching_results[0].get("page_id", "")))
        target_page_id = _page_id_from_target(str(action.get("target", "")))
        if target_page_id != created_page_id:
            raise ValueError("archive target does not match the created page evidence")
        return ValidatedAction(
            action_type=action_type,
            target_page_id=target_page_id,
            policy_version=ARCHIVE_POLICY_VERSION,
            creation_action_id=creation_action_id,
        )

    raise ValueError(f"unsupported Notion Action type: {action_type}")


def _paragraph_children(body: str) -> list[dict[str, Any]]:
    if not body:
        return []
    segments: list[str] = []
    for line in body.splitlines() or [body]:
        if not line:
            segments.append("")
            continue
        segments.extend(line[offset : offset + 2_000] for offset in range(0, len(line), 2_000))
    if len(segments) > 100:
        raise ValueError("body expands beyond the approved 100 paragraph limit")
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": segment}}]
                if segment
                else []
            },
        }
        for segment in segments
    ]


class NotionWriteAPI:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.notion.com/v1",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            },
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _write(self, method: str, path: str, body: dict[str, Any]) -> tuple[dict[str, Any], str]:
        try:
            response = self._client.request(method, path, json=body)
        except httpx.TransportError as exc:
            raise AmbiguousNotionOutcome("Notion transport outcome is ambiguous") from exc
        request_id = response.headers.get("x-request-id", "unavailable")
        if response.status_code >= 500:
            raise AmbiguousNotionOutcome(
                f"Notion server outcome is ambiguous (request_id={request_id})"
            )
        if response.is_error:
            raise NotionRejected(response.status_code, request_id)
        try:
            payload = response.json()
        except ValueError as exc:
            raise AmbiguousNotionOutcome(
                f"Notion success response was malformed (request_id={request_id})"
            ) from exc
        return payload, request_id

    def create_page(self, *, parent_page_id: str, title: str, body: str) -> ExternalResult:
        payload, request_id = self._write(
            "POST",
            "/pages",
            {
                "parent": {"type": "page_id", "page_id": normalize_id(parent_page_id)},
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"type": "text", "text": {"content": title}}],
                    }
                },
                "children": _paragraph_children(body),
            },
        )
        if payload.get("object") != "page" or not payload.get("id"):
            raise AmbiguousNotionOutcome(
                f"Notion success response omitted page identity (request_id={request_id})"
            )
        return ExternalResult(normalize_id(payload["id"]), payload.get("url"), request_id)

    def archive_page(self, page_id: str) -> ExternalResult:
        payload, request_id = self._write(
            "PATCH", f"/pages/{normalize_id(page_id)}", {"in_trash": True}
        )
        if payload.get("object") != "page" or not payload.get("id"):
            raise AmbiguousNotionOutcome(
                f"Notion success response omitted page identity (request_id={request_id})"
            )
        return ExternalResult(normalize_id(payload["id"]), payload.get("url"), request_id)


class KnowledgeServiceClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self.client.request(method, path, **kwargs)
        if response.is_error:
            raise RuntimeError(f"Knowledge Service returned HTTP {response.status_code}")
        return response.json()

    async def get_action(self, action_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/actions/{quote(action_id, safe=':')}",
            params=[("workspace_id", "personal"), ("principal", EXECUTOR)],
        )

    async def claim(self, action_id: str, policy_version: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/actions/{quote(action_id, safe=':')}/execution-claims",
            json={
                "executed_by": EXECUTOR,
                "connector": CONNECTOR,
                "authorization_ref": AUTHORIZATION_REF,
                "policy_version": policy_version,
                "idempotency_key": "notion-execution-v1",
                "access": {"workspace_id": "personal", "principals": [EXECUTOR]},
            },
        )

    async def record(
        self,
        action_id: str,
        claim: dict[str, Any],
        policy_version: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        external_request_id: str | None = None,
        rollback_ref: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/actions/{quote(action_id, safe=':')}/executions",
            json={
                "claim_id": claim["id"],
                "external_idempotency_key": claim["external_idempotency_key"],
                "status": status,
                "executed_by": EXECUTOR,
                "connector": CONNECTOR,
                "external_api": "notion.pages.create"
                if policy_version == CREATE_POLICY_VERSION
                else "notion.pages.update",
                "authorization_ref": AUTHORIZATION_REF,
                "policy_version": policy_version,
                "idempotency_key": "notion-execution-v1",
                "external_request_id": external_request_id,
                "result": result or {},
                "error": error,
                "rollback_ref": rollback_ref,
                "access": {"workspace_id": "personal", "principals": [EXECUTOR]},
            },
        )


async def execute_action(
    action_id: str, service: ActionService, notion: NotionWriteAPI
) -> dict[str, Any]:
    detail = await service.get_action(action_id)
    action = _action_record(detail)
    creation_detail = None
    if action.get("action_type") == ARCHIVE_ACTION_TYPE:
        creation_action_id = action.get("parameters", {}).get("creation_action_id")
        if isinstance(creation_action_id, str) and creation_action_id:
            creation_detail = await service.get_action(creation_action_id)
    validated = validate_action(detail, creation_detail=creation_detail)
    claim = await service.claim(action_id, validated.policy_version)
    if claim.get("unchanged"):
        raise RuntimeError(
            "existing execution claim requires reconciliation; external call was not repeated"
        )
    try:
        if validated.action_type == CREATE_ACTION_TYPE:
            external = notion.create_page(
                parent_page_id=validated.target_page_id,
                title=validated.title or "",
                body=validated.body or "",
            )
            result = {"page_id": external.page_id, "url": external.url}
            rollback_ref = ARCHIVE_ACTION_TYPE
        else:
            external = notion.archive_page(validated.target_page_id)
            result = {
                "page_id": external.page_id,
                "url": external.url,
                "in_trash": True,
                "creation_action_id": validated.creation_action_id,
            }
            rollback_ref = None
    except AmbiguousNotionOutcome as exc:
        return await service.record(
            action_id,
            claim,
            validated.policy_version,
            status="FAILED",
            error={"type": "ambiguous_external_outcome", "retryable": False, "message": str(exc)},
        )
    except NotionRejected as exc:
        return await service.record(
            action_id,
            claim,
            validated.policy_version,
            status="FAILED",
            error={
                "type": "notion_rejected",
                "status_code": exc.status_code,
                "request_id": exc.request_id,
                "retryable": False,
            },
            external_request_id=exc.request_id,
        )
    return await service.record(
        action_id,
        claim,
        validated.policy_version,
        status="SUCCEEDED",
        result=result,
        external_request_id=external.request_id,
        rollback_ref=rollback_ref,
    )


@asynccontextmanager
async def _service_client() -> AsyncIterator[KnowledgeServiceClient]:
    settings = get_settings()
    if settings.action_executor_base_url:
        async with httpx.AsyncClient(
            base_url=settings.action_executor_base_url.rstrip("/"),
            timeout=settings.action_executor_timeout_seconds,
        ) as client:
            yield KnowledgeServiceClient(client)
        return
    try:
        async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://knowledge-os.local",
            timeout=settings.action_executor_timeout_seconds,
        ) as client:
            yield KnowledgeServiceClient(client)
    finally:
        get_graph.cache_clear()


async def _main_async(action_id: str) -> dict[str, Any]:
    notion = NotionWriteAPI(resolve_notion_token())
    try:
        async with _service_client() as service:
            return await execute_action(action_id, service, notion)
    finally:
        notion.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute one approved governed Notion Action")
    parser.add_argument("action_id")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm execution of the already approved Action after reviewing its policy",
    )
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("execution requires --yes after reviewing the approved Action")
    try:
        result = asyncio.run(_main_async(args.action_id))
    except (PermissionError, RuntimeError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
