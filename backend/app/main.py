from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.ingest import router as ingest_router
from app.api.routers.dea import router as dea_router
from app.api.routers.scripts import router as scripts_router
from app.api.routers.inventory import router as inventory_router
from app.api.routers.adherence import router as adherence_router
from app.api.routers.benchmarking import router as benchmarking_router
from app.api.routers.ai import router as ai_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="ScriptHound API", version="1.0.0", description="PawPrint Intelligence Veterinary Pharmacy Analytics")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(ingest_router, prefix="/api/v1/ingest", tags=["ingest"])
app.include_router(dea_router, prefix="/api/dea", tags=["dea"])
app.include_router(scripts_router, prefix="/api/scripts", tags=["scripts"])
app.include_router(inventory_router, prefix="/api/inventory", tags=["inventory"])
app.include_router(adherence_router, prefix="/api/adherence", tags=["adherence"])
app.include_router(benchmarking_router, prefix="/api/benchmarking", tags=["benchmarking"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ScriptHound", "brand": "PawPrint Intelligence"}
