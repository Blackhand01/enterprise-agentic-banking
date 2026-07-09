"""FastAPI entrypoint for the Part A prototype."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from .part_a_banking_demo_application import PartABankingDemoApplication
except ImportError:  # Allows running from src/backend during quick prototyping.
    from part_a_banking_demo_application import PartABankingDemoApplication


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "src" / "bank_data"
FRONTEND_DIR = ROOT_DIR / "src" / "frontend"

app = FastAPI(title="Prototipo TCS Agentic Bank")
service = PartABankingDemoApplication(DATA_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class TransferRequest(BaseModel):
    amount: float = Field(gt=0)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ScenarioRequest(BaseModel):
    scenario: str = Field(min_length=1)


class FinancialRulesRequest(BaseModel):
    autonomous_transfer_limit_eur: float | None = Field(default=None, gt=0)
    minimum_cash_buffer_eur: float | None = Field(default=None, ge=0)
    surplus_investment_ratio: float | None = Field(default=None, gt=0, le=1)
    transfer_rounding_increment_eur: float | None = Field(default=None, gt=0)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/state")
def state() -> dict:
    return service.dashboard_state()


@app.post("/api/preview-transfer")
def preview_transfer(request: TransferRequest) -> dict:
    proposal = service.build_liquidity_proposal(request.amount)
    return {"proposal": proposal}


@app.post("/api/submit-transfer")
def submit_transfer(request: TransferRequest) -> dict:
    return service.submit_transfer(request.amount)


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    return service.chat(request.message)


@app.post("/api/simulate-event")
def simulate_event(request: ScenarioRequest) -> dict:
    return service.simulate_event(request.scenario)


@app.post("/api/financial-rules")
def update_financial_rules(request: FinancialRulesRequest) -> dict:
    updated = service.update_financial_rules(**request.model_dump(exclude_none=True))
    return {"status": "OK", "financial_rules": updated, "state": service.dashboard_state()}


@app.post("/api/reset-audit")
def reset_audit() -> dict:
    service.reset_audit()
    return {"status": "OK"}


@app.post("/api/reset-data")
def reset_data() -> dict:
    service.reset_data()
    service.reset_audit()
    return {"status": "OK"}
