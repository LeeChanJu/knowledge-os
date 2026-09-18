"""Owner-paired Telegram review UI over the existing local Governance service.

No Cypher, extraction, approval bypass, or external Action execution lives here.
Only callback IDs/digests and delivery state are retained, never a second knowledge store.
"""

import argparse
import asyncio
import fcntl
import getpass
import hashlib
import json
import logging
import os
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from knowledge_os import review_cli as review
from knowledge_os.config import get_settings

DEFAULT_CONFIG = Path.home() / ".config/knowledge-os/telegram-review.json"
TTL = 24 * 60 * 60


def save_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".telegram-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def private_json(path: Path) -> dict:
    if path.stat().st_mode & 0o077:
        raise ValueError("Telegram 설정 파일 권한은 600이어야 합니다.")
    return json.loads(path.read_text())


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Telegram:
    def __init__(self, token: str):
        self.client = httpx.AsyncClient(
            base_url=f"https://api.telegram.org/bot{token}/",
            timeout=40,
        )

    async def call(self, method: str, **params):
        try:
            response = await self.client.post(method, json=params)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                raise ValueError("Telegram API rejected request")
            return result["result"]
        except (httpx.HTTPError, ValueError, KeyError):
            # HTTP exception URLs contain the bot token. Never surface them.
            raise RuntimeError(f"Telegram {method} 요청 실패") from None

    async def document(self, chat_id: int, text: str):
        try:
            response = await self.client.post(
                "sendDocument",
                data={"chat_id": str(chat_id), "protect_content": "true"},
                files={"document": ("review.txt", text.encode(), "text/plain")},
            )
            response.raise_for_status()
            if not response.json().get("ok"):
                raise ValueError("Telegram API rejected document")
        except (httpx.HTTPError, ValueError):
            raise RuntimeError("Telegram 검토 자료 전송 실패") from None


class Service:
    async def pending(self):
        items = []
        for kind, command in (("proposal", "list"), ("action", "action-list")):
            rows = await review._execute(
                argparse.Namespace(
                    command=command,
                    status="PROPOSED",
                    type=None,
                    limit=100,
                )
            )
            for row in rows:
                item = row["proposal"] if kind == "proposal" else row
                items.append((kind, item["id"]))
        return items

    async def detail(self, kind: str, identifier: str):
        if kind == "proposal":
            result = await review._proposal(identifier, include_text=True)
            # Neo4j collect order is not an identity contract.
            for key in ("evidence", "evidence_bundle", "approvals"):
                if key in result:
                    result[key] = sorted(result[key], key=canonical)
            return result
        return await review._execute(
            argparse.Namespace(command="action-show", action_id=identifier)
        )

    async def decide(self, kind, identifier, decision, reason):
        return await review._execute(
            argparse.Namespace(
                command=decision if kind == "proposal" else f"action-{decision}",
                proposal_id=identifier,
                action_id=identifier,
                yes=True,
                reason=reason,
            )
        )


def summary(kind: str, detail: dict) -> str:
    record = detail[kind]
    if kind == "action":
        content = (
            f"외부 작업 검토: {record['action_type']}\n대상: {record['target']}\n"
            f"사유: {record.get('reason', '')}\n정책: {record.get('policy_version', '')}\n"
            f"매개변수: {canonical(record.get('parameters', {}))}\n"
            "승인은 실행 허가만 기록합니다. 실제 외부 작업은 별도 실행기가 수행합니다."
        )
    else:
        payload = detail.get("payload") or {}
        parts = []
        for change in payload.get("changes", []):
            obj = change.get("object")
            target = obj["name"] if obj else canonical(change.get("value"))
            parts.append(f"• {change['subject']['name']} → {change['predicate']} → {target}")
            if change.get("supersedes_assertion_id"):
                parts.append(f"  대체 대상: {change['supersedes_assertion_id']}")
        if not parts:
            parts = [str(payload.get("title", "")), str(payload.get("statement", ""))]
        content = "지식 변경 검토\n" + "\n".join(parts)
        content += f"\n사유: {record.get('reason', '')}"
    return content[:2600] + f"\n\nID: {record['id']}\n전체 내용·근거는 첨부 자료에서 확인하세요."


class Reviewer:
    def __init__(self, config: dict, state_path: Path, telegram, service, clock=time.time):
        self.config, self.path, self.tg, self.service, self.clock = (
            config,
            state_path,
            telegram,
            service,
            clock,
        )
        self.state = (
            private_json(state_path)
            if state_path.exists()
            else {
                "offset": 0,
                "cards": {},
            }
        )
        binding = digest(
            {
                k: config[k]
                for k in (
                    "user_id",
                    "chat_id",
                    "bot_id",
                    "workspace",
                    "principals",
                    "actor",
                )
            }
        )
        if self.state.get("binding", binding) != binding:
            raise ValueError("승인 계정이 바뀌었습니다. 새 상태 파일로 시작하세요.")
        self.state["binding"] = binding

    def save(self):
        save_private(self.path, self.state)

    async def message(self, text, keyboard=None):
        params = {
            "chat_id": self.config["chat_id"],
            "text": text,
            "protect_content": True,
            "link_preview_options": {"is_disabled": True},
        }
        if keyboard is not None:
            params["reply_markup"] = {"inline_keyboard": keyboard}
        return await self.tg.call("sendMessage", **params)

    async def answer(self, query, text):
        await self.tg.call("answerCallbackQuery", callback_query_id=query["id"], text=text)

    async def present(self, token, card, detail, *, update_existing=False):
        # Evidence delivery must succeed BEFORE decision buttons become available.
        await self.tg.document(
            self.config["chat_id"], json.dumps(detail, ensure_ascii=False, indent=2)
        )
        text = summary(card["kind"], detail)
        keyboard = [
            [
                {"text": "승인", "callback_data": f"approve:{token}"},
                {"text": "반려", "callback_data": f"reject:{token}"},
            ]
        ]
        if update_existing:
            await self.tg.call(
                "editMessageText",
                chat_id=self.config["chat_id"],
                message_id=card["message_id"],
                text=text,
                reply_markup={"inline_keyboard": keyboard},
                link_preview_options={"is_disabled": True},
            )
        else:
            sent = await self.message(text, keyboard)
            card["message_id"] = sent["message_id"]
        card.update(ready=True, digest=digest(detail), ui_version=2)
        self.save()

    async def refresh(self):
        for kind, identifier in await self.service.pending():
            live = [
                (token, c)
                for token, c in self.state["cards"].items()
                if c["kind"] == kind
                and c["id"] == identifier
                and c["expires"] > self.clock()
                and not c.get("done")
                and c.get("message_id")
            ]
            if live and all(c.get("ui_version") == 2 for _, c in live):
                continue
            try:
                detail = await self.service.detail(kind, identifier)
            except (RuntimeError, ValueError):
                print("검토 항목 조회 실패: 근거 접근 권한을 확인하세요.", flush=True)
                continue
            if detail[kind]["status"] != "PROPOSED":
                continue
            if live:
                # Upgrade pending legacy cards without creating another review decision.
                for token, card in live:
                    if card.get("ui_version") != 2:
                        await self.present(token, card, detail, update_existing=True)
                continue
            token = secrets.token_hex(12)
            card = {
                "kind": kind,
                "id": identifier,
                "expires": self.clock() + TTL,
                "ready": False,
                "digest": digest(detail),
            }
            self.state["cards"][token] = card
            self.save()
            await self.present(token, card, detail)

    async def handle(self, update):
        query = update.get("callback_query")
        if not query:
            message = update.get("message", {})
            if self.authorized(message.get("from", {}), message.get("chat", {})) and message.get(
                "text", ""
            ).split(" ")[0] in ("/start", "/pending"):
                await self.message(
                    "연결되었습니다. 승인 대기 항목을 확인합니다. 알림이 없으면 대기 항목이 없습니다."
                )
                await self.refresh()
            return
        message = query.get("message", {})
        if not self.authorized(query.get("from", {}), message.get("chat", {})):
            await self.answer(query, "승인 권한이 없는 계정입니다.")
            return
        command, _, token = query.get("data", "").partition(":")
        card = self.state["cards"].get(token)
        if (
            command not in {"view", "approve", "reject"}
            or not card
            or card.get("message_id") != message.get("message_id")
            or card.get("done")
            or card["expires"] <= self.clock()
        ):
            await self.answer(query, "만료되었거나 이미 처리된 버튼입니다. 최신 알림을 사용하세요.")
            return
        await self.answer(query, "확인 중입니다.")
        detail = await self.service.detail(card["kind"], card["id"])
        if detail[card["kind"]]["status"] != "PROPOSED":
            card["done"] = True
            self.save()
            await self.message(f"이미 처리된 항목입니다: {detail[card['kind']]['status']}")
            return
        if command == "view":
            # Backwards compatibility for a previously delivered two-step card.
            await self.present(token, card, detail, update_existing=True)
            return
        if not card["ready"] or card["digest"] != digest(detail):
            card["done"] = True
            self.save()
            await self.message(
                "검토 이후 내용 또는 근거가 바뀌었습니다. 새 알림에서 다시 검토하세요."
            )
            return
        reason = (
            f"Telegram explicit {command}; user={self.config['user_id']}; "
            f"chat={self.config['chat_id']}; message={message['message_id']}; "
            f"review_sha256={card['digest']}"
        )
        result = await self.service.decide(card["kind"], card["id"], command, reason)
        card["done"] = True
        self.save()
        # If notification fails, never resend the governance mutation on retry.
        await self.message(f"처리 완료: {result['status']}\n{card['id']}")
        await self.tg.call(
            "editMessageReplyMarkup",
            chat_id=self.config["chat_id"],
            message_id=message["message_id"],
            reply_markup={"inline_keyboard": []},
        )

    def authorized(self, user, chat):
        return (
            user.get("id") == self.config["user_id"]
            and not user.get("is_bot", False)
            and chat.get("id") == self.config["chat_id"]
            and chat.get("type") == "private"
        )


async def setup(path: Path, args):
    if path.exists():
        raise ValueError("이미 설정되어 있습니다. 기존 설정을 검토한 후 별도 경로를 사용하세요.")
    token = getpass.getpass("BotFather 토큰 (화면에 표시되지 않음): ").strip()
    if not token or ":" not in token:
        raise ValueError("유효한 BotFather 토큰을 입력하세요.")
    tg = Telegram(token)
    try:
        bot = await tg.call("getMe")
        webhook = await tg.call("getWebhookInfo")
        if webhook.get("url"):
            raise ValueError("이미 webhook이 연결된 봇입니다. 승인 전용 봇을 사용하세요.")
        code = secrets.token_urlsafe(24)
        print(
            f"본인 텔레그램에서 다음 링크를 열고 시작을 누르세요:\n"
            f"https://t.me/{bot['username']}?start={code}",
            flush=True,
        )
        deadline, offset = time.time() + 600, 0
        while time.time() < deadline:
            updates = await tg.call(
                "getUpdates",
                offset=offset,
                timeout=25,
                allowed_updates=["message", "callback_query"],
            )
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                user, chat = message.get("from", {}), message.get("chat", {})
                if (
                    message.get("text") == f"/start {code}"
                    and chat.get("type") == "private"
                    and user.get("id") == chat.get("id")
                    and not user.get("is_bot")
                ):
                    principals = sorted(set(args.principals.split(",")))
                    if args.actor not in principals:
                        raise ValueError("actor는 principals에 포함되어야 합니다.")
                    config = {
                        "token": token,
                        "user_id": user["id"],
                        "chat_id": chat["id"],
                        "bot_id": bot["id"],
                        "bot_username": bot["username"],
                        "workspace": args.workspace,
                        "principals": principals,
                        "actor": args.actor,
                    }
                    save_private(path, config)
                    await tg.call(
                        "sendMessage",
                        chat_id=chat["id"],
                        text="Knowledge OS 승인 계정 연결 완료. 로컬 승인 프로그램을 실행하면 알림을 받습니다.",
                    )
                    print(f"연결 완료: @{bot['username']} / 설정: {path}")
                    return
        raise ValueError("연결 시간이 지났습니다. setup을 다시 실행하세요.")
    finally:
        await tg.client.aclose()


async def run(path: Path):
    config = private_json(path)
    if (
        type(config["user_id"]) is not int
        or config["user_id"] <= 0
        or config["chat_id"] != config["user_id"]
    ):
        raise ValueError("본인의 개인 채팅 연결이 필요합니다.")
    os.environ.update(
        REVIEW_WORKSPACE_ID=config["workspace"],
        REVIEW_PRINCIPALS=",".join(config["principals"]),
        REVIEW_ACTOR=config["actor"],
    )
    get_settings.cache_clear()
    if get_settings().review_base_url:
        raise ValueError("Telegram 승인은 로컬 서비스만 지원합니다. REVIEW_BASE_URL을 해제하세요.")
    review._actor()
    tg = Telegram(config["token"])
    try:
        bot = await tg.call("getMe")
        if bot["id"] != config["bot_id"]:
            raise ValueError("연결된 봇과 토큰이 일치하지 않습니다.")
        if (await tg.call("getWebhookInfo")).get("url"):
            raise ValueError("봇에 webhook이 설정되어 있습니다.")
        state_path = path.with_suffix(".state.json")
        with path.with_suffix(".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("승인 프로그램이 이미 실행 중입니다.") from None
            worker = Reviewer(config, state_path, tg, Service())
            async with review._service():
                print("Telegram 승인 수신 중. 종료: Ctrl+C", flush=True)
                while True:
                    try:
                        await worker.refresh()
                        updates = await tg.call(
                            "getUpdates",
                            offset=worker.state["offset"],
                            timeout=25,
                            allowed_updates=["message", "callback_query"],
                        )
                        for update in updates:
                            try:
                                await worker.handle(update)
                            except (RuntimeError, ValueError):
                                # No raw provider exceptions or source data in console logs.
                                print(
                                    "항목 처리 실패: 최신 상태·권한 확인 후 다시 시도하세요.",
                                    flush=True,
                                )
                            worker.state["offset"] = update["update_id"] + 1
                            worker.save()
                    except (RuntimeError, ValueError, httpx.HTTPError):
                        print("연결 일시 실패. 10초 후 재시도합니다.", flush=True)
                        await asyncio.sleep(10)
    finally:
        await tg.client.aclose()


def main():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Telegram Knowledge OS approval adapter")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest="command", required=True)
    setup_parser = commands.add_parser("setup")
    setup_parser.add_argument("--workspace", default="personal")
    setup_parser.add_argument("--principals", required=True)
    setup_parser.add_argument("--actor", required=True)
    commands.add_parser("run")
    args = parser.parse_args()
    try:
        asyncio.run(setup(args.config, args) if args.command == "setup" else run(args.config))
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from None
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
