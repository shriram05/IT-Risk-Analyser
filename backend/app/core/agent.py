import json
import asyncio
import httpx
from typing import AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.tools.graph_tools import (
    get_affected_services,
    trace_dependencies,
    get_server_info,
    get_team_ownership,
)
from app.tools.vector_tools import get_similar_past_incidents
from app.core.config import settings

TOOLS = [
    get_affected_services,
    trace_dependencies,
    get_server_info,
    get_team_ownership,
    get_similar_past_incidents,
]

SYSTEM_PROMPT = """You are an expert IT incident root cause analysis (RCA) agent with deep knowledge of distributed systems and microservices architecture.

You have access to two data sources:
1. **Infrastructure Graph (Neo4j)** — real-time graph of services, servers, databases, teams, and their relationships
2. **Incident Knowledge Base (ChromaDB)** — semantic search over hundreds of past incident reports with root causes and resolutions

When given an alert, follow this strategy:
1. Extract keywords and find affected services in the graph
2. Trace dependency chains upstream (what does the failing service depend on?) and downstream (what services will be impacted?)
3. Get server/infrastructure details for affected services
4. Find team ownership for escalation
5. Search for similar past incidents and their proven resolutions
6. Synthesize all findings into a comprehensive RCA report

Write your final RCA report in this exact markdown structure:
## Incident Summary
## Affected Services
## Dependency Analysis & Root Cause
## Infrastructure Details
## Similar Past Incidents
## Root Cause Conclusion
## Immediate Actions
## Long-term Recommendations
## Escalation Contacts

Be specific, technical, and actionable. Reference exact service names, server names, and team contacts from the graph data."""


def _build_llm():
    return ChatOpenAI(
        model="gemini-2.5-flash",
        api_key=settings.GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        http_client=httpx.Client(verify=False),
        temperature=0,
    )


async def run_agent_sse(alert_text: str) -> AsyncGenerator[str, None]:
    llm = _build_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    tool_map = {t.name: t for t in TOOLS}

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"Analyze this IT incident and generate a root cause analysis:\n\n{alert_text}"
        ),
    ]

    MAX_ITERATIONS = 12

    for _ in range(MAX_ITERATIONS):
        response = await asyncio.to_thread(llm_with_tools.invoke, messages)
        messages.append(response)

        if not response.tool_calls:
            yield f"data: {json.dumps({'type': 'report', 'content': response.content})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'input': tool_args})}\n\n"

            try:
                result = await asyncio.to_thread(tool_map[tool_name].invoke, tool_args)
            except Exception as e:
                result = {"error": str(e)}

            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'output': result})}\n\n"

            messages.append(
                ToolMessage(content=json.dumps(result), tool_call_id=tool_id)
            )
