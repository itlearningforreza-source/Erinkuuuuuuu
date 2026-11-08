from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from erin.api.core.config import settings
from erin.api.core.database import init_db
from erin.api.routers import auth, market_data, instruments, watchlists, companies, valuation, portfolios, risk, fixed_income, derivatives, workspace, ai, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="ERIN API",
    description="Enterprise Research, Investment & Intelligence Network API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(market_data.router, prefix="/api/v1/quotes", tags=["market-data"])
app.include_router(instruments.router, prefix="/api/v1/instruments", tags=["instruments"])
app.include_router(watchlists.router, prefix="/api/v1/watchlists", tags=["watchlists"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["companies"])
app.include_router(valuation.router, prefix="/api/v1/valuation", tags=["valuation"])
app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["portfolios"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
app.include_router(fixed_income.router, prefix="/api/v1/fixed-income", tags=["fixed-income"])
app.include_router(derivatives.router, prefix="/api/v1/derivatives", tags=["derivatives"])
app.include_router(workspace.router, prefix="/api/v1/workspace", tags=["workspace"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

if __name__ == "__main__":
    uvicorn.run(
        "erin.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )