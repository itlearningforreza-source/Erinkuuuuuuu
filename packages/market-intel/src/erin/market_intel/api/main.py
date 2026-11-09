"""ERIN Market Intelligence - Main FastAPI Application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from erin.core.config import get_settings
from erin.core.logging import setup_logging
from erin.core.exceptions import (
    ERINException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
)
from erin.market_intel.api.routers.market_data import router as market_data
from erin.market_intel.api.routers.instruments import router as instruments
from erin.market_intel.api.routers.watchlists import router as watchlists
from erin.market_intel.api.routers.charts import router as charts
from erin.market_intel.api.routers.portfolios import router as portfolios
from erin.market_intel.api.routers.orders import router as orders
from erin.market_intel.api.routers.risk import router as risk
from erin.market_intel.api.routers.analytics import router as analytics
from erin.market_intel.api.routers.news import router as news
from erin.market_intel.api.routers.fundamentals import router as fundamentals

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting ERIN Market Intelligence API")
    # Initialize services
    yield
    logger.info("Shutting down ERIN Market Intelligence API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="ERIN Market Intelligence",
        description="Institutional-grade financial operating system API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Trusted host middleware
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Exception handlers
    app.add_exception_handler(ERINException, erin_exception_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(RateLimitError, rate_limit_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Include routers
    app.include_router(market_data.router, prefix="/api/v1/market-data", tags=["Market Data"])
    app.include_router(instruments.router, prefix="/api/v1/instruments", tags=["Instruments"])
    app.include_router(watchlists.router, prefix="/api/v1/watchlists", tags=["Watchlists"])
    app.include_router(charts.router, prefix="/api/v1/charts", tags=["Charts"])
    app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["Portfolios"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(news.router, prefix="/api/v1/news", tags=["News"])
    app.include_router(fundamentals.router, prefix="/api/v1/fundamentals", tags=["Fundamentals"])
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "erin-market-intel"}
    
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        return {"status": "ready", "service": "erin-market-intel"}
    
    return app


# Exception handlers
async def erin_exception_handler(request: Request, exc: ERINException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "FORBIDDEN",
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def rate_limit_error_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal server error occurred",
            }
        }
    )


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "erin.market_intel.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )