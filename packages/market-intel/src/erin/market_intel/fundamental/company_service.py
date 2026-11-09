"""Company Profile Service - CRUD for company profiles with SEC EDGAR integration."""

import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.data_infra.storage.sqlite import SQLiteStorage
    from erin.market_intel.adapters.sec_edgar import SECEdgarProvider

logger = logging.getLogger(__name__)


class CompanyService:
    """Service for managing company profiles with SEC EDGAR integration."""

    def __init__(self, storage: 'SQLiteStorage', sec_provider: 'SECEdgarProvider'):
        self.storage = storage
        self.sec = sec_provider

    async def create_company(
        self,
        cik: str,
        name: str,
        tickers: List[str],
        primary_exchange: str,
        currency: str = "USD",
        sector: str = None,
        industry: str = None,
        gics_code: str = None,
        headquarters: Dict = None,
        description: str = None
    ) -> str:
        """Create a new company profile."""
        company_id = cik.zfill(10)
        now = datetime.utcnow()
        
        # Upsert in SQLite storage
        company_data = {
            "id": company_id,
            "cik": cik,
            "name": name,
            "tickers": tickers,
            "primary_exchange": primary_exchange,
            "currency": currency,
            "sector": sector,
            "industry": industry,
            "gics_code": gics_code,
            "headquarters": headquarters or {},
            "description": description,
            "is_active": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        self.storage.create_company(company_data)
        return company_id

    async def get_company(self, company_id: str) -> Optional[Dict]:
        """Get company profile by CIK."""
        return self.storage.get_company(company_id)

    async def get_company_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Get company by ticker symbol."""
        companies = self.storage.search_companies(query=ticker)
        if companies:
            return companies[0]
        return None

    async def search_companies(
        self,
        query: str = "",
        sector: str = "",
        limit: int = 50
    ) -> List[Dict]:
        """Search companies."""
        return self.storage.search_companies(query=query, sector=sector, limit=limit)

    async def sync_from_sec(self, cik: str) -> Optional[Dict]:
        """Sync company data from SEC EDGAR."""
        try:
            sec_data = await self.sec.get_instrument(cik)
            if not sec_data:
                return None
            
            company_id = sec_data["cik"]
            existing = self.storage.get_company(company_id)
            
            company_data = {
                "id": company_id,
                "cik": sec_data["cik"],
                "name": sec_data["name"],
                "tickers": sec_data.get("tickers", []),
                "primary_exchange": sec_data.get("exchanges", [""])[0] if sec_data.get("exchanges") else "",
                "currency": "USD",
                "sector": None,  # Would need GICS mapping
                "industry": None,
                "gics_code": None,
                "headquarters": {
                    "state": sec_data.get("state"),
                    "city": sec_data.get("city")
                },
                "description": None,
                "is_active": 1,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if existing:
                # Update existing
                self.storage.update_company(company_id, company_data)
            else:
                # Create new
                self.storage.create_company(company_data)
            
            return company_data
        except Exception as e:
            logger.error(f"SEC sync failed for {cik}: {e}")
            return None

    async def get_company_filings(
        self,
        cik: str,
        form_types: List[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get company filings from SEC EDGAR."""
        return await self.sec.get_company_filings(cik, form_types, limit)

    async def get_company_financials(
        self,
        cik: str,
        concepts: List[str] = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict]:
        """Get company financial data from SEC XBRL filings."""
        return await self.sec.get_company_financials(cik, concepts, start_date, end_date)

    async def get_company_info(self, cik: str) -> Optional[Dict]:
        """Get comprehensive company info including filings and financials."""
        company = await self.get_company(cik)
        if not company:
            # Try to sync from SEC
            company = await self.sync_from_sec(cik)
        
        if company:
            # Get recent filings
            filings = await self.get_company_filings(cik, ["10-K", "10-Q"], limit=20)
            company["filings"] = filings
            
            # Get key financial concepts
            financials = await self.get_company_financials(
                cik,
                concepts=["Revenue", "NetIncome", "TotalAssets", "TotalLiabilities", 
                         "StockholdersEquity", "OperatingIncome", "CashAndCashEquivalents"]
            )
            company["financials"] = financials
        
        return company