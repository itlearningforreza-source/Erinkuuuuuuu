"""SEC EDGAR Adapter - Company filings (10-K, 10-Q, 8-K) parsing and XBRL extraction."""

import asyncio
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncIterator
from typing import TYPE_CHECKING
import aiohttp
import zipfile
import io
import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from erin.market_intel.domain.interfaces import InstrumentId

logger = logging.getLogger(__name__)


class SECEdgarProvider:
    """SEC EDGAR adapter for company filings (10-K, 10-Q, 8-K) parsing and XBRL extraction."""

    def __init__(self, user_agent: str = "ERIN/2.0 (contact@erin.local)", timeout: int = 30):
        self._user_agent = user_agent
        self._timeout = timeout
        self._session = None
        self._base_url = "https://data.sec.gov"
        self._rate_limit = 10  # requests per second (SEC limit)
        self._last_request = 0

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": "ERIN/2.0 (contact@erin.local)"}
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), headers=headers)
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.SEC_EDGAR

    @property
    def name(self) -> str:
        return "SEC EDGAR"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return []

    @property
    def rate_limit(self):
        return {"requests_per_second": 10}

    async def _rate_limit(self):
        """Enforce SEC rate limit (10 req/sec)."""
        import time
        now = time.time()
        elapsed = time.time() - self._last_request
        if elapsed < 0.1:  # 10 req/sec = 0.1s between requests
            await asyncio.sleep(0.1 - elapsed)
        self._last_request = time.time()

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": "ERIN/2.0 (contact@erin.local)"}
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), headers=headers)
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def provider_id(self):
        from erin.market_intel.domain.interfaces import ProviderId
        return ProviderId.SEC_EDGAR

    @property
    def name(self) -> str:
        return "SEC EDGAR"

    @property
    def supported_asset_classes(self):
        from erin.market_intel.domain.interfaces import AssetClass
        return [AssetClass.EQUITY]

    @property
    def supported_frequencies(self):
        from erin.market_intel.domain.interfaces import DataFrequency
        return []

    @property
    def rate_limit(self):
        return {"requests_per_second": 10}

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.sec.gov/robots.txt") as resp:
                    return resp.status == 200
        except Exception as e:
            logger.warning(f"SEC EDGAR health check failed: {e}")
            return False

    async def search_instruments(
        self,
        query: str,
        asset_class: Optional[Any] = None,
        exchange: Optional[str] = None,
        limit: int = 50
    ):
        """Search instruments via SEC company tickers."""
        try:
            await self._rate_limit()
            async with aiohttp.ClientSession() as session:
                url = f"{self._base_url}/files/company_tickers.json"
                async with session.get(url) as resp:
                    data = await resp.json()
                
                instruments = []
                for item in data.values():
                    ticker = item.get("ticker", "")
                    if query.upper() in ticker.upper() or query.upper() in item.get("title", "").upper():
                        from erin.market_intel.domain.interfaces import InstrumentId
                        instruments.append(InstrumentId(
                            figi=f"SEC_{item.get('cik_str', '')}",
                            composite_ticker=ticker,
                            provider_symbol=item.get('cik_str', '')
                        ))
                        if len(instruments) >= limit:
                            break
                return instruments
        except Exception as e:
            logger.error(f"SEC search failed: {e}")
            return []

    async def get_instrument(self, instrument_id):
        """Get company info from SEC."""
        try:
            cik = instrument_id.provider_symbol or instrument_id.composite_ticker
            # Pad CIK to 10 digits
            cik = str(cik).zfill(10)
            
            await self._rate_limit()
            async with aiohttp.ClientSession() as session:
                url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return None
                    data = await resp.json()
                    
                    return {
                        "cik": data.get("cik"),
                        "name": data.get("name"),
                        "tickers": data.get("tickers", []),
                        "exchanges": data.get("exchanges", []),
                        "sic": data.get("sic"),
                        "sic_description": data.get("sicDescription"),
                        "entity_type": data.get("entityType"),
                        "state": data.get("state"),
                        "city": data.get("city"),
                        "website": data.get("website"),
                        "filings_recent": data.get("filings", {}).get("recent", {})
                    }
        except Exception as e:
            logger.error(f"SEC get_instrument failed: {e}")
            return None

    async def get_company_filings(
        self,
        cik: str,
        form_types: List[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get company filings from SEC EDGAR."""
        try:
            await self._rate_limit()
            cik = str(cik).zfill(10)
            
            async with aiohttp.ClientSession() as session:
                url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return []
                    data = await resp.json()
                    
                    filings = data.get("filings", {}).get("recent", {})
                    
                    results = []
                    forms = filings.get("form", [])
                    dates = filings.get("filingDate", [])
                    accession_numbers = filings.get("accessionNumber", [])
                    primary_docs = filings.get("primaryDocument", [])
                    
                    form_types = form_types or ["10-K", "10-Q", "8-K", "10-K/A", "10-Q/A"]
                    
                    for i, form in enumerate(forms):
                        if form in form_types:
                            results.append({
                                "form": form,
                                "filing_date": dates[i] if i < len(dates) else None,
                                "accession_number": accession_numbers[i] if i < len(accession_numbers) else None,
                                "primary_document": primary_docs[i] if i < len(primary_docs) else None,
                                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_numbers[i].replace('-', '')}/{primary_docs[i] if i < len(primary_docs) else ''}"
                            })
                            if len(results) >= limit:
                                break
                    
                    return results
        except Exception as e:
            logger.error(f"SEC get_filings failed: {e}")
            return []

    async def get_filing_content(self, cik: str, accession_number: str, primary_document: str) -> Optional[str]:
        """Get full filing content (HTML/XML)."""
        try:
            cik = str(cik).zfill(10)
            accession_clean = accession_number.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_document}"
            
            await self._rate_limit()
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception as e:
            logger.error(f"SEC get_filing_content failed: {e}")
        return None

    async def parse_xbrl_filing(self, content: str) -> Dict:
        """Parse XBRL filing for financial data."""
        try:
            # Parse XBRL/XML
            root = ET.fromstring(content)
            
            # Define namespaces
            ns = {
                'xbrli': 'http://www.xbrl.org/2003/instance',
                'xbrldi': 'http://xbrl.org/2006/xbrldi',
                'link': 'http://www.xbrl.org/2003/linkbase',
                'xlink': 'http://www.w3.org/1999/xlink',
                'us-gaap': 'http://fasb.org/us-gaap/2023',
                'dei': 'http://xbrl.sec.gov/dei/2023',
            }
            
            # Extract key financial facts
            facts = {}
            
            # Find all contexts
            contexts = {}
            for context in root.findall('.//xbrli:context', ns):
                context_id = context.get('id')
                period = context.find('xbrli:period', ns)
                if period is not None:
                    start_date = period.find('xbrli:startDate', ns)
                    end_date = period.find('xbrli:endDate', ns)
                    instant = period.find('xbrli:instant', ns)
                    if end_date is not None:
                        contexts[context_id] = {
                            'start_date': start_date.text if start_date is not None else None,
                            'end_date': end_date.text if end_date is not None else None,
                            'instant': instant.text if instant is not None else None
                        }
            
            # Extract facts
            for elem in root.iter():
                if elem.tag.startswith('{'):
                    # Extract namespace and local name
                    tag = elem.tag
                    if '}' in tag:
                        ns_uri, local_name = tag[1:].split('}', 1)
                        
                        # Get context
                        context_ref = elem.get('contextRef')
                        if context_ref in contexts:
                            ctx = contexts[context_ref]
                            
                            # Get unit
                            unit_ref = elem.get('unitRef')
                            
                            # Get value
                            value = elem.text
                            if value is not None:
                                try:
                                    value = Decimal(value)
                                except:
                                    pass
                                
                                key = f"{local_name}_{context_ref}"
                                facts[key] = {
                                    "concept": local_name,
                                    "namespace": ns_uri,
                                    "value": value,
                                    "context": ctx,
                                    "unit": unit_ref
                                }
            
            return {
                "facts": facts,
                "contexts": contexts
            }
        except Exception as e:
            logger.error(f"XBRL parsing failed: {e}")
            return {"facts": {}, "contexts": {}}

    async def get_company_financials(
        self,
        cik: str,
        concepts: List[str] = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict]:
        """Get company financial data from XBRL filings."""
        try:
            filings = await self.get_company_filings(cik, ["10-K", "10-Q"], limit=10)
            
            all_facts = {}
            for filing in filings:
                if filing.get("primary_document"):
                    content = await self.get_filing_content(
                        cik,
                        filing["accession_number"],
                        filing["primary_document"]
                    )
                    if content:
                        parsed = await self.parse_xbrl_filing(content)
                        # Merge facts
                        for key, fact in parsed.get("facts", {}).items():
                            if key not in all_facts:
                                all_facts[key] = fact
            
            # Filter by concepts if provided
            if concepts:
                filtered = {}
                for key, fact in all_facts.items():
                    for concept in concepts:
                        if concept.upper() in fact["concept"].upper():
                            filtered[key] = fact
                            break
                return list(filtered.values())
            
            return list(all_facts.values())
        except Exception as e:
            logger.error(f"SEC get_company_financials failed: {e}")
            return []

    # Abstract method implementations
    async def get_quotes(self, symbols, fields=None):
        return {}

    async def get_history(self, symbol, start, end, frequency=None, adjustment="none"):
        return []

    async def get_calendar(self, exchange: str, year: int):
        return {}

    def supports_real_time(self) -> bool:
        return False

    def requires_api_key(self) -> bool:
        return False