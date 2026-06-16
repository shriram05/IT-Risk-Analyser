from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.agent import run_agent_sse

router = APIRouter()


class AlertRequest(BaseModel):
    alert_text: str


@router.post("/analyze")
async def analyze_incident(request: AlertRequest):
    return StreamingResponse(
        run_agent_sse(request.alert_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
