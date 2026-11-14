"""ERIN Market Intelligence - API Entry Point."""

from erin.market_intel.api.main import app

# Re-export the app for uvicorn
__all__ = ["app"]