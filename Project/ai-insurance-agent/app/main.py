# app/main.py
from fastapi import FastAPI

from app.routers import ingestion

# Create FastAPI instance with KEYWORD arguments only (no positional args)
app = FastAPI(
    title="AI Insurance Payment Collection Agent",
    description="Compliance-first Voice AI for overdue premium collection",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Include the ingestion router
app.include_router(ingestion.router)

# Simple health check endpoint
@app.get("/")
def health_check():
    return {"status": "healthy", "message": "Data Ingestion & Calling Engine ready"}