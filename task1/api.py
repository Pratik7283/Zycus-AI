from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .models import TriageRequest, TriageResponse
from .service import triage_ticket
from llm_client import get_llm_client


app = FastAPI(title="Task 1 Ticket Triage Agent", version="0.1.0")


@app.post("/triage", response_model=TriageResponse)
def triage_endpoint(request: TriageRequest) -> TriageResponse:
    return triage_ticket(request)


@app.post("/triage-stream")
def triage_stream_endpoint(request: TriageRequest):
    """Streaming endpoint for real-time response generation."""
    
    def generate_stream():
        try:
            llm_client = get_llm_client()
            subject = request.subject or ""
            body = request.body or ""
            text = (request.text or f"{subject} {body}").strip()
            
            # Stream the draft response generation
            from .service import DRAFT_RESPONSE_SYSTEM_PROMPT
            
            # First do classification (non-streaming for simplicity)
            classification_result = triage_ticket(request)
            
            # Send classification results as JSON
            import json
            yield f"data: {json.dumps({'type': 'classification', 'data': classification_result.model_dump()})}\n\n"
            
            # Now stream the response generation
            kb_match_text = classification_result.matched_kb_excerpt if classification_result.known_issue_match else "None"
            system_prompt = DRAFT_RESPONSE_SYSTEM_PROMPT.format(kb_excerpt=kb_match_text)
            user_prompt = f"Ticket subject: {subject}\nClassification: {classification_result.urgency_tier} {classification_result.issue_category} related to {classification_result.product_area}"
            
            yield f"data: {json.dumps({'type': 'stream_start', 'message': 'Generating response...'})}\n\n"
            
            for chunk in llm_client.call_llm_streaming(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=256,
                prompt_version="v1.0"
            ):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            yield f"data: {json.dumps({'type': 'stream_end', 'message': 'Response generation complete'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("task1.api:app", host="127.0.0.1", port=8000, reload=False)

