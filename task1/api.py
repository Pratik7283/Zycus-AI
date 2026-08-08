from __future__ import annotations

from fastapi import FastAPI

from .models import TriageRequest, TriageResponse
from .service import triage_ticket


app = FastAPI(title="Task 1 Ticket Triage Agent", version="0.1.0")


@app.post("/triage", response_model=TriageResponse)
def triage_endpoint(request: TriageRequest) -> TriageResponse:
    return triage_ticket(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("task1.api:app", host="127.0.0.1", port=8000, reload=False)

