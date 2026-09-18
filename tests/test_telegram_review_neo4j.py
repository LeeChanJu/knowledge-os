"""Real isolated DB + real ASGI Governance; Telegram transport alone is simulated."""

import asyncio

import pytest
from test_telegram_review import CONFIG, FakeTelegram, callback
from test_v01_neo4j_regressions import graph, query, seed_proposal  # noqa: F401

from knowledge_os import api
from knowledge_os.config import get_settings
from knowledge_os.dependencies import get_graph
from knowledge_os.models import ActionCreate
from knowledge_os.telegram_review import Reviewer, Service


@pytest.mark.parametrize("kind", ["proposal", "action"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_telegram_real_governance_only_once(graph, tmp_path, monkeypatch, kind, decision):  # noqa: F811
    monkeypatch.setenv("REVIEW_PRINCIPALS", "local-user")
    monkeypatch.setenv("REVIEW_ACTOR", "local-user")
    monkeypatch.delenv("REVIEW_BASE_URL", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(api, "get_ops", lambda: graph.ops)
    api.app.dependency_overrides[get_graph] = lambda: graph
    if kind == "proposal":
        identifier = seed_proposal(graph)
    else:
        identifier = graph.create_action(
            ActionCreate(
                action_type="NOTION_CREATE_PAGE",
                target="notion:fixture",
                requested_by="local-user",
                idempotency_key="telegram-fixture",
                review_principals=["local-user"],
                execution_principals=["connector:fixture"],
            )
        )["id"]

    async def scenario():
        worker = Reviewer(
            {**CONFIG, "principals": ["local-user"], "actor": "local-user"},
            tmp_path / "telegram.json",
            FakeTelegram(),
            Service(),
        )
        await worker.refresh()
        token = next(iter(worker.state["cards"]))
        assert worker.state["cards"][token]["ready"]
        assert worker.tg.documents
        update = callback(worker, token, decision)
        await worker.handle(update)
        await worker.handle(update)
        record = (await Service().detail(kind, identifier))[kind]
        assert record["status"] == ("APPROVED" if decision == "approve" else "REJECTED")
        assert query(graph, "MATCH (a:Approval) RETURN count(a) AS n")[0]["n"] == 1
        if kind == "proposal":
            count = query(graph, "MATCH (a:Assertion) RETURN count(a) AS n")[0]["n"]
            assert count == (1 if decision == "approve" else 0)
        else:
            assert record["execution_status"] == "NOT_EXECUTED"
            assert query(graph, "MATCH (e:ActionExecution) RETURN count(e) AS n")[0]["n"] == 0

    try:
        asyncio.run(scenario())
    finally:
        api.app.dependency_overrides.clear()
        get_settings.cache_clear()
