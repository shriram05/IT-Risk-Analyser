from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import incidents, graph

app = FastAPI(
    title="GraphRAG RCA API",
    description="IT Incident Root Cause Analysis using Neo4j GraphRAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router, prefix="/api", tags=["incidents"])
app.include_router(graph.router, prefix="/api", tags=["graph"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "graphrag-rca"}
