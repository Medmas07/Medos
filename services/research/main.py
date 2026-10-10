"""D2 MOCKED Research Service composition root."""

from fastapi import FastAPI

from adapters.inbound.http.research_jobs import router

app = FastAPI(
    title="Research Service (MOCKED D2)",
    version="0.1.0",
    description=(
        "D2 deterministic distributed research execution. "
        "No hospital database, sandbox, or production execution is used."
    ),
)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "research", "mocked": True}
