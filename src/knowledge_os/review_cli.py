import argparse
import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote

import httpx

from knowledge_os.api import app
from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_graph


def _principals() -> list[str]:
    values = sorted(
        {item.strip() for item in get_settings().review_principals.split(",") if item.strip()}
    )
    if not values:
        raise ValueError("REVIEW_PRINCIPALS must contain at least one principal")
    return values


def _access() -> dict[str, Any]:
    return {
        "workspace_id": get_settings().review_workspace_id,
        "principals": _principals(),
    }


def _actor() -> str:
    settings = get_settings()
    principals = _principals()
    if settings.review_actor:
        if settings.review_actor not in principals:
            raise ValueError("REVIEW_ACTOR must be one of REVIEW_PRINCIPALS")
        return settings.review_actor
    if len(principals) != 1:
        raise ValueError("REVIEW_ACTOR is required when REVIEW_PRINCIPALS has multiple identities")
    return principals[0]


@asynccontextmanager
async def _service() -> AsyncIterator[None]:
    if get_settings().review_base_url:
        yield
        return
    try:
        async with app.router.lifespan_context(app):
            yield
    finally:
        get_graph.cache_clear()


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    settings = get_settings()
    if settings.review_base_url:
        transport = None
        base_url = settings.review_base_url.rstrip("/")
    else:
        transport = httpx.ASGITransport(app=app)
        base_url = "http://knowledge-os.local"
    async with httpx.AsyncClient(
        transport=transport,
        base_url=base_url,
        timeout=settings.review_timeout_seconds,
    ) as client:
        response = await client.request(method, path, **kwargs)
    if response.is_error:
        raise RuntimeError(f"Knowledge Service returned HTTP {response.status_code}")
    return response.json()


def _path_segment(value: str) -> str:
    return quote(value, safe=":")


def _access_params() -> list[tuple[str, str]]:
    access = _access()
    return [
        ("workspace_id", access["workspace_id"]),
        *(("principal", principal) for principal in access["principals"]),
    ]


async def _proposal(proposal_id: str, *, include_text: bool) -> dict[str, Any]:
    proposal = await _request(
        "GET", f"/v1/proposals/{_path_segment(proposal_id)}", params=_access_params()
    )
    if not include_text:
        return proposal
    chunk_ids = sorted(item["chunk_id"] for item in proposal["evidence"])
    evidence = await _request(
        "POST",
        "/v1/evidence/bundle",
        json={"chunk_ids": chunk_ids, "access": _access()},
    )
    return {**proposal, "evidence_bundle": evidence["evidence"]}


async def _execute(args: argparse.Namespace) -> Any:
    if args.command == "action-list":
        params = [("limit", str(args.limit)), *_access_params()]
        if args.status is not None:
            params.append(("status", args.status))
        if args.type is not None:
            params.append(("action_type", args.type))
        return await _request("GET", "/v1/actions", params=params)
    if args.command == "action-show":
        return await _request(
            "GET", f"/v1/actions/{_path_segment(args.action_id)}", params=_access_params()
        )
    if args.command in {"action-approve", "action-reject"}:
        if not args.yes:
            raise ValueError(
                "Action approval and rejection require --yes after reviewing target, "
                "parameters, policy, reviewer, and executor"
            )
        decision = args.command.removeprefix("action-")
        return await _request(
            "POST",
            f"/v1/actions/{_path_segment(args.action_id)}/{decision}",
            json={"reviewed_by": _actor(), "reason": args.reason, "access": _access()},
        )
    if args.command == "list":
        params = [("limit", str(args.limit)), *_access_params()]
        if args.status is not None:
            params.append(("status", args.status))
        if args.type is not None:
            params.append(("proposal_type", args.type))
        return await _request("GET", "/v1/proposals", params=params)
    if args.command == "show":
        return await _proposal(args.proposal_id, include_text=True)
    if not args.yes:
        raise ValueError("approval and rejection require --yes after reviewing the Evidence")
    return await _request(
        "POST",
        f"/v1/proposals/{_path_segment(args.proposal_id)}/{args.command}",
        json={"reviewed_by": _actor(), "reason": args.reason, "access": _access()},
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review governed Knowledge OS Proposals and Actions through service contracts"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="List authorized Proposals")
    listing.add_argument(
        "--status", choices=["PROPOSED", "APPROVED", "REJECTED"], default="PROPOSED"
    )
    listing.add_argument("--type", choices=["ASSERTION", "DECISION", "EVENT"])
    listing.add_argument("--limit", type=_bounded_limit, default=50, metavar="1..100")
    showing = commands.add_parser("show", help="Show a Proposal with exact Evidence text")
    showing.add_argument("proposal_id")
    for name in ("approve", "reject"):
        decision = commands.add_parser(name, help=f"{name.title()} a pending Proposal")
        decision.add_argument("proposal_id")
        decision.add_argument("--reason")
        decision.add_argument(
            "--yes",
            action="store_true",
            help="Confirm that the exact Evidence was reviewed",
        )
    action_listing = commands.add_parser("action-list", help="List authorized governed Actions")
    action_listing.add_argument(
        "--status", choices=["PROPOSED", "APPROVED", "REJECTED"], default="PROPOSED"
    )
    action_listing.add_argument("--type")
    action_listing.add_argument("--limit", type=_bounded_limit, default=50, metavar="1..100")
    action_showing = commands.add_parser(
        "action-show", help="Show an Action, policy, decisions, claims, and executions"
    )
    action_showing.add_argument("action_id")
    for name in ("approve", "reject"):
        decision = commands.add_parser(
            f"action-{name}", help=f"{name.title()} a pending governed Action"
        )
        decision.add_argument("action_id")
        decision.add_argument("--reason")
        decision.add_argument(
            "--yes",
            action="store_true",
            help="Confirm target, parameters, policy, reviewer, and executor were reviewed",
        )
    return parser


def _bounded_limit(value: str) -> int:
    limit = int(value)
    if not 1 <= limit <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return limit


async def _main_async(args: argparse.Namespace) -> Any:
    async with _service():
        return await _execute(args)


def main() -> None:
    args = _parser().parse_args()
    try:
        result = asyncio.run(_main_async(args))
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
