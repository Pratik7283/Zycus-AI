from __future__ import annotations

from fastapi import FastAPI

from .models import AccountBriefRequest, AccountBriefResponse
from .service import generate_account_brief


app = FastAPI(title="Task 2 Account Health Summariser", version="0.1.0")


@app.post("/account-brief", response_model=AccountBriefResponse)
def account_brief_endpoint(request: AccountBriefRequest) -> AccountBriefResponse:
    return generate_account_brief(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

