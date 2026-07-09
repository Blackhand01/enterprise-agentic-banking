"""Smoke checks for the Part A prototype."""

import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from src.backend.agentic_system.agent import BankingAgent
from src.backend.agentic_system.semantic_transaction_retriever import SemanticTransactionRetriever
from src.backend.application.customer_chat_service import _assistant_unavailable_message
from src.backend.main import app, service


class FakeAgent:
    def __init__(self) -> None:
        self.history = []

    def chat(self, user_input: str) -> str:
        self.history.append(
            {
                "role": "tool",
                "content": '{"status":"OK","category":"sport","count":2,"transactions":[]}',
            }
        )
        return "Risposta agentica di test tramite tool calling."


class FakeNoToolAgent:
    def __init__(self) -> None:
        self.history = [
            {
                "role": "tool",
                "content": '{"status":"OK","category":"sport","count":1,"transactions":[]}',
            }
        ]

    def chat(self, user_input: str) -> str:
        self.history.append({"role": "assistant", "content": "Risposta senza tool."})
        return "Risposta senza tool."


class FakeEmbeddingModel:
    def encode(
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ):
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "proski" in lowered or "sci" in lowered:
                vectors.append([1.0, 0.0])
            elif "trail" in lowered or "trekking" in lowered:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.0, 0.0])
        return vectors


def main() -> None:
    client = TestClient(app)
    service.reset_data()

    try:
        assert client.get("/").status_code == 200

        state = client.get("/api/state")
        assert state.status_code == 200
        payload = state.json()
        assert payload["user"]["first_name"] == "Stefano"
        assert payload["proposal"]["route"] == "APPROVAL_REQUIRED"
        assert payload["proposal"]["action_type"] == "TRANSFER"
        assert payload["proposal"]["amount"] == 500.0
        assert payload["proposal"]["financial_rules"]["surplus_investment_ratio"] == 0.25
        assert payload["proposal"]["financial_rules"]["minimum_cash_buffer_eur"] == 750.0
        assert payload["proposal"]["financial_rules"]["autonomous_transfer_limit_eur"] == 500.0
        assert "user_goal" in payload
        assert payload["user_goal"]["target_months"] == 18
        assert payload["emergency_goal_projection"]["target_balance"] == 10000.0
        assert payload["emergency_goal_projection"]["target_label"]
        assert payload["emergency_goal_projection"]["historical_eta_label"]
        assert payload["emergency_goal_projection"]["agent_timeline_label"]
        assert payload["emergency_goal_projection"]["is_behind_plan"] is True
        assert payload["emergency_goal_projection"]["monthly_savings_gap"] > 0
        assert "servono" in payload["emergency_goal_projection"]["status_summary"]
        assert len(payload["monthly_snapshots"]) == 12
        assert payload["cashflow_forecast"]["horizon_days"] == 30
        assert len(payload["agent_inbox"]) >= 1
        assert len(payload["proposal"]["evidence"]) >= 6
        evidence_groups = {item["group"] for item in payload["proposal"]["evidence"]}
        assert "Contesto bancario fornito all'agente" in evidence_groups
        assert "Decisione Safety and Approval" in evidence_groups
        assert len(payload["policies"]["stale"]) == 1
        initial_checking = next(
            account for account in payload["accounts"] if account["name"] == "Checking"
        )
        initial_emergency = next(
            account for account in payload["accounts"] if account["name"] == "Emergency_Fund"
        )

        preview = client.post("/api/preview-transfer", json={"amount": 750}).json()
        assert preview["proposal"]["route"] == "STEP_UP_REQUIRED"

        updated_rules = client.post(
            "/api/financial-rules",
            json={"autonomous_transfer_limit_eur": 800},
        ).json()
        assert updated_rules["status"] == "OK"
        assert updated_rules["financial_rules"]["autonomous_transfer_limit_eur"] == 800.0
        assert (
            updated_rules["state"]["proposal"]["financial_rules"][
                "autonomous_transfer_limit_eur"
            ]
            == 800.0
        )
        assert updated_rules["state"]["user"]["risk_thresholds"][
            "autonomous_transfer_limit_eur"
        ] == 800.0
        assert updated_rules["state"]["proposal"]["amount"] == 700.0
        dynamic_preview = client.post("/api/preview-transfer", json={"amount": 750}).json()
        assert dynamic_preview["proposal"]["route"] == "APPROVAL_REQUIRED"

        service.reset_data()
        payload = client.get("/api/state").json()
        initial_checking = next(
            account for account in payload["accounts"] if account["name"] == "Checking"
        )
        initial_emergency = next(
            account for account in payload["accounts"] if account["name"] == "Emergency_Fund"
        )

        default_executed = client.post("/api/submit-transfer", json={"amount": 500}).json()
        assert default_executed["tool_result"]["status"] == "EXECUTED"
        executed_state = client.get("/api/state").json()
        assert executed_state["proposal"]["already_executed"] is True
        assert executed_state["proposal"]["route"] == "ALREADY_EXECUTED"
        assert executed_state["emergency_goal_projection"]["agent_action_amount"] == 0.0
        assert executed_state["cashflow_forecast"]["proposed_action_amount"] == 0.0
        assert (
            executed_state["emergency_goal_projection"]["required_monthly_after_agent_action"]
            == executed_state["emergency_goal_projection"]["required_monthly_savings"]
        )

        service.reset_data()
        payload = client.get("/api/state").json()
        initial_checking = next(
            account for account in payload["accounts"] if account["name"] == "Checking"
        )
        initial_emergency = next(
            account for account in payload["accounts"] if account["name"] == "Emergency_Fund"
        )

        original_model_cache = SemanticTransactionRetriever._model_cache
        try:
            SemanticTransactionRetriever._model_cache = {
                "sentence-transformers/all-MiniLM-L6-v2": FakeEmbeddingModel()
            }
            ski_transactions = json.loads(
                service.tool_executor.execute(
                    "fetch_transactions",
                    {"category": "sport", "search_query": "sci"},
                )
            )
            assert ski_transactions["status"] == "OK"
            assert ski_transactions["count"] == 1
            assert ski_transactions["unfiltered_count"] >= ski_transactions["count"]
            assert ski_transactions["transactions"][0]["merchant"] == "ProSki Shop"
            assert ski_transactions["transactions"][0]["semantic_score"] == 1.0

            trekking_transactions = json.loads(
                service.tool_executor.execute(
                    "fetch_transactions",
                    {"category": "sport", "search_query": "trekking"},
                )
            )
            assert trekking_transactions["status"] == "OK"
            assert trekking_transactions["transactions"][0]["merchant"] == "Trail Running Store"

            sea_transactions = json.loads(
                service.tool_executor.execute(
                    "fetch_transactions",
                    {"category": "sport", "search_query": "mare"},
                )
            )
            assert sea_transactions["status"] == "NO_DATA"
            assert sea_transactions["count"] == 0
        finally:
            SemanticTransactionRetriever._model_cache = original_model_cache

        balance_summary = json.loads(service.tool_executor.execute("get_balance_summary", {}))
        assert balance_summary["status"] == "OK"
        assert balance_summary["total_balance"] == 7250.0
        assert len(balance_summary["accounts"]) == 2

        customer_context = json.loads(service.tool_executor.execute("get_customer_context", {}))
        assert customer_context["status"] == "OK"
        assert customer_context["balance_summary"]["total_balance"] == 7250.0

        guardrail_agent = BankingAgent(
            groq_client=object(),
            policy_db_path=service.policy_path,
            db_path=service.db_path,
            ledger_seed_path=service.ledger_path,
        )
        system_prompt = guardrail_agent._system_prompt()  # noqa: SLF001
        assert "Non offrire calcoli manuali di rischio" in system_prompt
        assert "Non ho accesso ai dati relativi a [argomento]" in system_prompt
        guardrail_agent._append_message(  # noqa: SLF001
            {
                "role": "tool",
                "name": "get_balance_summary",
                "content": json.dumps(balance_summary),
            }
        )
        safe_text = guardrail_agent._customer_safe_text(  # noqa: SLF001
            "Posso usare <function=get_total_balance/> per calcolarlo."
        )
        assert "7.250,00 EUR" in safe_text
        assert "<function" not in safe_text
        assert "get_total_balance" not in safe_text

        executed = client.post("/api/submit-transfer", json={"amount": 300}).json()
        assert executed["tool_result"]["status"] == "EXECUTED"
        updated = client.get("/api/state").json()
        checking = next(account for account in updated["accounts"] if account["name"] == "Checking")
        emergency = next(
            account for account in updated["accounts"] if account["name"] == "Emergency_Fund"
        )
        assert checking["available_balance"] == initial_checking["available_balance"] - 300.0
        assert emergency["balance"] == initial_emergency["balance"] + 300.0
        assert updated["transactions"][0]["transfer_id"] == executed["trace_id"]
        assert updated["transactions"][1]["transfer_id"] == executed["trace_id"]
        assert updated["customer_activity"][0]["title"] == "Trasferimento al fondo emergenze"
        assert updated["customer_activity"][0]["amount"] == -300.0
        assert updated["proposal"]["action_type"] in {"TRANSFER", "REVIEW_CASHFLOW"}

        duplicate = client.post("/api/submit-transfer", json={"amount": 300}).json()
        assert duplicate["tool_result"]["status"] == "DUPLICATE"
        unchanged = client.get("/api/state").json()
        unchanged_checking = next(
            account for account in unchanged["accounts"] if account["name"] == "Checking"
        )
        unchanged_emergency = next(
            account for account in unchanged["accounts"] if account["name"] == "Emergency_Fund"
        )
        assert unchanged_checking["available_balance"] == checking["available_balance"]
        assert unchanged_emergency["balance"] == emergency["balance"]

        blocked = client.post("/api/submit-transfer", json={"amount": 750}).json()
        assert blocked["tool_result"]["status"] == "BLOCKED"

        service.reset_data()
        sandbox = client.post(
            "/api/sandbox/inject-state",
            json={
                "checking_balance": 7450.0,
                "emergency_balance": 3000.0,
                "upcoming_expenses": 760.0,
            },
        ).json()
        assert sandbox["status"] == "SANDBOX_STATE_INJECTED"
        sandbox_checking = next(
            account for account in sandbox["state"]["accounts"] if account["name"] == "Checking"
        )
        sandbox_emergency = next(
            account
            for account in sandbox["state"]["accounts"]
            if account["name"] == "Emergency_Fund"
        )
        assert sandbox_checking["available_balance"] == 7450.0
        assert sandbox_emergency["balance"] == 3000.0
        assert sandbox["state"]["cashflow_forecast"]["known_expenses_total"] == 760.0
        assert sandbox["state"]["scheduled_transactions"][0]["amount"] == -760.0
        assert sandbox["state"]["proposal"]["action_type"] == "TRANSFER"
        assert sandbox["state"]["proposal"]["amount"] == 500.0
        assert sandbox["state"]["last_event"] is None

        low_liquidity = client.post(
            "/api/sandbox/inject-state",
            json={
                "checking_balance": 650.0,
                "emergency_balance": 3000.0,
                "upcoming_expenses": 760.0,
            },
        ).json()
        low_checking = next(
            account
            for account in low_liquidity["state"]["accounts"]
            if account["name"] == "Checking"
        )
        assert low_checking["available_balance"] == 650.0
        assert low_liquidity["state"]["proposal"]["action_type"] == "REVIEW_CASHFLOW"
        assert low_liquidity["state"]["proposal"]["route"] == "REVIEW_REQUIRED"

        service.reset_data()
        with service.repository.connection_provider.connect() as connection:
            connection.execute(
                "UPDATE monthly_snapshots SET savings_transfer_eur = ?",
                (450.0,),
            )
        on_track_state = client.get("/api/state").json()
        assert on_track_state["emergency_goal_projection"]["is_behind_plan"] is False
        assert on_track_state["proposal"]["action_type"] == "MAINTAIN_PACE"
        assert on_track_state["proposal"]["route"] == "INFO"
        assert on_track_state["proposal"]["required_next_step"] == "NO_ACTION"
        assert on_track_state["proposal"]["amount"] == 0.0
        assert (
            on_track_state["proposal"]["recommended_action"]
            == "Sei perfettamente allineato al tuo piano di risparmio. Non sono necessari trasferimenti extra questo mese."
        )

        service.reset_data()
        for index in range(3):
            service.repository.record_external_expense(
                trace_id=f"trc_test_expense_{index}",
                operation_id=f"test_expense_{index}",
                account_name="Checking",
                merchant=f"Spesa test {index}",
                amount=1200.0,
                category="imprevisti",
                display_name=f"Spesa imprevista test {index}",
            )
        degraded_state = client.get("/api/state").json()
        assert degraded_state["proposal"]["action_type"] == "REVIEW_CASHFLOW"
        assert degraded_state["proposal"]["route"] == "REVIEW_REQUIRED"
        assert degraded_state["proposal"]["required_next_step"] == "CUSTOMER_REVIEW"
        blocked_cashflow = client.post("/api/submit-transfer", json={"amount": 300}).json()
        assert blocked_cashflow["tool_result"]["status"] == "BLOCKED"
        assert blocked_cashflow["tool_result"]["reason"] == "ACTION_NOT_EXECUTABLE"

        service.reset_data()

        service._banking_agent = FakeAgent()  # noqa: SLF001
        chat = client.post("/api/chat", json={"message": "sport"}).json()
        assert chat["tool_result"]["status"] == "OK"

        service._banking_agent = FakeNoToolAgent()  # noqa: SLF001
        no_tool_chat = client.post("/api/chat", json={"message": "mare"}).json()
        assert no_tool_chat["tool_result"]["status"] == "NO_TOOL_CALL"
        assert "limite di utilizzo del provider LLM" in _assistant_unavailable_message(
            "openai LLM API call failed: Error code: 429 - rate_limit_exceeded"
        )
        assert "chiave LLM configurata non e valida" in _assistant_unavailable_message(
            "openai LLM API call failed: Error code: 401 - invalid_api_key"
        )

        client.post("/api/reset-audit")
        print("smoke checks passed")
    finally:
        service.reset_data()
        client.post("/api/reset-audit")


if __name__ == "__main__":
    main()
