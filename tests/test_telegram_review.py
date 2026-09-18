import asyncio
import copy

import httpx
import pytest

from knowledge_os.telegram_review import Reviewer, Telegram, private_json, save_private

CONFIG = {
    "user_id": 123,
    "chat_id": 123,
    "bot_id": 99,
    "workspace": "personal",
    "principals": ["human:owner"],
    "actor": "human:owner",
}


class FakeTelegram:
    def __init__(self):
        self.calls = []
        self.documents = []
        self.fail_send = False
        self.fail_document = False

    async def call(self, method, **params):
        self.calls.append((method, params))
        if self.fail_send and method == "sendMessage":
            raise RuntimeError("delivery failed")
        return {"message_id": len(self.calls)}

    async def document(self, chat_id, text):
        if self.fail_document:
            raise RuntimeError("evidence delivery failed")
        self.documents.append((chat_id, text))


class FakeService:
    def __init__(self, kind="proposal"):
        self.kind = kind
        record = {"id": f"{kind}:fixture", "status": "PROPOSED", "reason": "Evidence checked"}
        if kind == "action":
            record.update(
                action_type="NOTION_CREATE_PAGE",
                target="notion:fixture",
                parameters={"body": "Exact body"},
                policy_version="v1",
            )
        self.value = {
            kind: record,
            "payload": {
                "changes": [
                    {"subject": {"name": "A"}, "predicate": "USES", "object": {"name": "B"}},
                ]
            },
            "evidence_bundle": [{"text": "A uses B", "chunk_id": "chunk:1"}],
        }
        self.decisions = []

    async def pending(self):
        return [(self.kind, self.value[self.kind]["id"])]

    async def detail(self, kind, identifier):
        return copy.deepcopy(self.value)

    async def decide(self, kind, identifier, decision, reason):
        self.decisions.append((kind, identifier, decision, reason))
        self.value[kind]["status"] = "APPROVED" if decision == "approve" else "REJECTED"
        return {"status": self.value[kind]["status"]}


def callback(worker, token, command, **overrides):
    q = {
        "id": "callback:1",
        "data": f"{command}:{token}",
        "from": {"id": 123, "is_bot": False},
        "message": {
            "message_id": worker.state["cards"][token]["message_id"],
            "chat": {"id": 123, "type": "private"},
        },
    }
    q.update(overrides)
    return {"callback_query": q}


async def prepared(tmp_path, kind="proposal"):
    tg, service = FakeTelegram(), FakeService(kind)
    worker = Reviewer(CONFIG, tmp_path / "state.json", tg, service)
    await worker.refresh()
    token = next(iter(worker.state["cards"]))
    return worker, token, tg, service


@pytest.mark.parametrize("kind", ["proposal", "action"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_exact_review_then_one_decision_survives_restart(tmp_path, kind, decision):
    async def scenario():
        worker, token, tg, service = await prepared(tmp_path, kind)
        assert '"A uses B"' in tg.documents[0][1]
        buttons = tg.calls[-1][1]["reply_markup"]["inline_keyboard"][0]
        assert [b["text"] for b in buttons] == ["승인", "반려"]
        update = callback(worker, token, decision)
        await worker.handle(update)
        restarted = Reviewer(CONFIG, worker.path, tg, service)
        await restarted.handle(update)
        assert len(service.decisions) == 1
        assert service.decisions[0][2] == decision
        assert "user=123" in service.decisions[0][3]
        assert "review_sha256=" in service.decisions[0][3]

    asyncio.run(scenario())


@pytest.mark.parametrize("attack", ["user", "group", "message", "expired", "undelivered"])
def test_untrusted_or_undelivered_callback_never_mutates(tmp_path, attack):
    async def scenario():
        worker, token, _tg, service = await prepared(tmp_path)
        if attack == "undelivered":
            worker.state["cards"][token]["ready"] = False
        update = callback(worker, token, "approve")
        query = update["callback_query"]
        if attack == "user":
            query["from"]["id"] = 456
        elif attack == "group":
            query["message"]["chat"]["type"] = "group"
        elif attack == "message":
            query["message"]["message_id"] += 100
        elif attack == "expired":
            worker.state["cards"][token]["expires"] = 0
        await worker.handle(update)
        assert service.decisions == []

    asyncio.run(scenario())


def test_changed_evidence_requires_new_review(tmp_path):
    async def scenario():
        worker, token, _tg, service = await prepared(tmp_path)
        service.value["evidence_bundle"][0]["text"] = "Changed content"
        await worker.handle(callback(worker, token, "approve"))
        assert service.decisions == []
        assert worker.state["cards"][token]["done"]

    asyncio.run(scenario())


def test_failed_notification_can_be_retried(tmp_path):
    async def scenario():
        tg, service = FakeTelegram(), FakeService()
        worker = Reviewer(CONFIG, tmp_path / "state.json", tg, service)
        tg.fail_send = True
        with pytest.raises(RuntimeError):
            await worker.refresh()
        tg.fail_send = False
        await worker.refresh()
        assert any(c.get("message_id") for c in worker.state["cards"].values())

    asyncio.run(scenario())


def test_delivery_failure_after_commit_never_repeats_decision(tmp_path):
    async def scenario():
        worker, token, tg, service = await prepared(tmp_path)
        update = callback(worker, token, "approve")
        tg.fail_send = True
        with pytest.raises(RuntimeError):
            await worker.handle(update)
        tg.fail_send = False
        await Reviewer(CONFIG, worker.path, tg, service).handle(update)
        assert len(service.decisions) == 1

    asyncio.run(scenario())


def test_evidence_failure_never_exposes_decision_buttons(tmp_path):
    async def scenario():
        tg, service = FakeTelegram(), FakeService()
        tg.fail_document = True
        worker = Reviewer(CONFIG, tmp_path / "state.json", tg, service)
        with pytest.raises(RuntimeError, match="evidence delivery"):
            await worker.refresh()
        assert not any(method == "sendMessage" for method, _ in tg.calls)
        assert all(not card["ready"] for card in worker.state["cards"].values())
        tg.fail_document = False
        await worker.refresh()
        assert any(card["ready"] for card in worker.state["cards"].values())
        assert service.decisions == []

    asyncio.run(scenario())


def test_existing_two_step_card_is_upgraded_without_new_decision(tmp_path):
    async def scenario():
        worker, token, tg, service = await prepared(tmp_path)
        card = worker.state["cards"][token]
        old_message = card["message_id"]
        card.pop("ui_version", None)
        card["ready"] = False
        worker.save()
        await worker.refresh()
        assert card["message_id"] == old_message
        assert card["ready"] and card["ui_version"] == 2
        assert tg.calls[-1][0] == "editMessageText"
        assert service.decisions == []
        await worker.handle(callback(worker, token, "approve"))
        assert len(service.decisions) == 1

    asyncio.run(scenario())


def test_private_state_and_account_binding(tmp_path):
    path = tmp_path / "secret.json"
    save_private(path, {"secret": "test"})
    assert path.stat().st_mode & 0o077 == 0
    assert private_json(path)["secret"] == "test"
    path.chmod(0o644)
    with pytest.raises(ValueError):
        private_json(path)
    worker = Reviewer(CONFIG, tmp_path / "state.json", FakeTelegram(), FakeService())
    worker.save()
    with pytest.raises(ValueError):
        Reviewer({**CONFIG, "user_id": 999}, worker.path, FakeTelegram(), FakeService())


def test_telegram_http_failure_does_not_expose_token():
    async def scenario():
        tg = Telegram("123:secret-token")
        await tg.client.aclose()
        tg.client = httpx.AsyncClient(
            base_url="https://api.telegram.org/bot123:secret-token/",
            transport=httpx.MockTransport(lambda request: httpx.Response(401)),
        )
        try:
            with pytest.raises(RuntimeError) as error:
                await tg.call("getMe")
            assert "secret-token" not in str(error.value)
            assert error.value.__suppress_context__
        finally:
            await tg.client.aclose()

    asyncio.run(scenario())


def test_pairing_requires_secret_and_private_owner_chat(tmp_path, monkeypatch):
    import argparse
    from types import SimpleNamespace

    import knowledge_os.telegram_review as module

    class PairingTelegram(FakeTelegram):
        def __init__(self, token):
            super().__init__()
            self.client = SimpleNamespace(aclose=self.close)

        async def close(self):
            pass

        async def call(self, method, **params):
            if method == "getMe":
                return {"id": 99, "username": "fixture_bot"}
            if method == "getWebhookInfo":
                return {"url": ""}
            if method == "getUpdates":
                return [
                    {
                        "update_id": 1,
                        "message": {
                            "text": "/start wrong",
                            "from": {"id": 9},
                            "chat": {"id": 9, "type": "private"},
                        },
                    },
                    {
                        "update_id": 2,
                        "message": {
                            "text": "/start fixture-code",
                            "from": {"id": 9},
                            "chat": {"id": -9, "type": "group"},
                        },
                    },
                    {
                        "update_id": 3,
                        "message": {
                            "text": "/start fixture-code",
                            "from": {"id": 123},
                            "chat": {"id": 123, "type": "private"},
                        },
                    },
                ]
            return await super().call(method, **params)

    monkeypatch.setattr(module, "Telegram", PairingTelegram)
    monkeypatch.setattr(module.getpass, "getpass", lambda _: "99:fixture-token")
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda _: "fixture-code")
    path = tmp_path / "config.json"
    asyncio.run(
        module.setup(
            path,
            argparse.Namespace(principals="human:owner", actor="human:owner", workspace="personal"),
        )
    )
    assert private_json(path)["user_id"] == 123
