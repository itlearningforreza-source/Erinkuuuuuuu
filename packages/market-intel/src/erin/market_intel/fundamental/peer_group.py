"""Peer Group Identification - GICS-based and custom peer groups."""

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.data_infra.storage.sqlite import SQLiteStorage

logger = logging.getLogger(__name__)


@dataclass
class PeerGroup:
    """Peer group definition."""
    name: str
    description: str
    criteria: Dict[str, Any]  # e.g., {"gics_code": "45201010", "market_cap_min": 1e9}
    companies: List[str] = field(default_factory=list)  # CIKs
    created_at: date = field(default_factory=date.today)
    updated_at: date = field(default_factory=date.today)


class PeerGroupService:
    """Service for identifying and managing peer groups."""
    
    def __init__(self, storage: 'SQLiteStorage'):
        self.storage = storage
        self._gics_hierarchy = self._build_gics_hierarchy()
    
    def _build_gics_hierarchy(self) -> Dict[str, Dict]:
        """Build GICS hierarchy for peer identification."""
        return {
            # Energy
            "10": {"name": "Energy", "groups": {
                "1010": {"name": "Energy Equipment & Services", "industries": {
                    "101010": {"name": "Oil & Gas Drilling"},
                    "101020": {"name": "Oil & Gas Equipment & Services"},
                }},
                "1020": {"name": "Oil, Gas & Consumable Fuels", "industries": {
                    "102010": {"name": "Integrated Oil & Gas"},
                    "102020": {"name": "Oil & Gas Exploration & Production"},
                    "102030": {"name": "Oil & Gas Refining & Marketing"},
                    "102040": {"name": "Oil & Gas Storage & Transportation"},
                    "102050": {"name": "Coal & Consumable Fuels"},
                }},
            }},
            # Materials
            "15": {"name": "Materials", "groups": {
                "1510": {"name": "Materials", "industries": {
                    "151010": {"name": "Commodity Chemicals"},
                    "151020": {"name": "Diversified Chemicals"},
                    "151030": {"name": "Fertilizers & Agricultural Chemicals"},
                    "151040": {"name": "Industrial Gases"},
                    "151050": {"name": "Specialty Chemicals"},
                }},
            }},
            # Industrials
            "20": {"name": "Industrials", "groups": {
                "2010": {"name": "Capital Goods", "industries": {
                    "201010": {"name": "Aerospace & Defense"},
                    "201020": {"name": "Building Products"},
                    "201030": {"name": "Construction & Engineering"},
                    "201040": {"name": "Electrical Equipment"},
                    "201050": {"name": "Industrial Conglomerates"},
                    "201060": {"name": "Machinery"},
                    "201070": {"name": "Trading Companies & Distributors"},
                }},
            }},
            # Consumer Discretionary
            "25": {"name": "Consumer Discretionary", "groups": {
                "2510": {"name": "Automobiles & Components", "industries": {
                    "251010": {"name": "Automobile Manufacturers"},
                    "251020": {"name": "Automotive Parts & Equipment"},
                    "251030": {"name": "Tires & Rubber"},
                }},
                "2520": {"name": "Consumer Durables & Apparel", "industries": {
                    "252010": {"name": "Household Durables"},
                    "252020": {"name": "Leisure Products"},
                    "252030": {"name": "Textiles, Apparel & Luxury Goods"},
                }},
                "2530": {"name": "Consumer Services", "industries": {
                    "253010": {"name": "Hotels, Restaurants & Leisure"},
                    "253020": {"name": "Diversified Consumer Services"},
                    "253030": {"name": "Education Services"},
                }},
                "2540": {"name": "Retailing", "industries": {
                    "254010": {"name": "Internet & Direct Marketing Retail"},
                    "254020": {"name": "Multiline Retail"},
                    "254030": {"name": "Specialty Retail"},
                    "254040": {"name": "Food & Staples Retailing"},
                }},
            }},
            # Consumer Staples
            "30": {"name": "Consumer Staples", "groups": {
                "3010": {"name": "Food & Staples Retailing", "industries": {
                    "301010": {"name": "Food Distributors"},
                    "301020": {"name": "Food Retail"},
                }},
                "3020": {"name": "Food, Beverage & Tobacco", "industries": {
                    "302010": {"name": "Beverages"},
                    "302020": {"name": "Food Products"},
                    "302030": {"name": "Tobacco"},
                }},
                "3030": {"name": "Household & Personal Products", "industries": {
                    "303010": {"name": "Household Products"},
                    "303020": {"name": "Personal Products"},
                }},
            }},
            # Health Care
            "35": {"name": "Health Care", "groups": {
                "3510": {"name": "Health Care Equipment & Services", "industries": {
                    "351010": {"name": "Health Care Equipment"},
                    "351020": {"name": "Health Care Providers & Services"},
                    "351030": {"name": "Health Care Technology"},
                }},
                "3520": {"name": "Pharmaceuticals, Biotechnology & Life Sciences", "industries": {
                    "352010": {"name": "Biotechnology"},
                    "352020": {"name": "Pharmaceuticals"},
                    "352030": {"name": "Life Sciences Tools & Services"},
                }},
            }},
            # Financials
            "40": {"name": "Financials", "groups": {
                "4010": {"name": "Banks", "industries": {
                    "401010": {"name": "Diversified Banks"},
                    "401020": {"name": "Regional Banks"},
                }},
                "4020": {"name": "Diversified Financials", "industries": {
                    "402010": {"name": "Other Diversified Financial Services"},
                    "402020": {"name": "Multi-Sector Holdings"},
                    "402030": {"name": "Specialized Finance"},
                }},
                "4030": {"name": "Insurance", "industries": {
                    "403010": {"name": "Insurance Brokers"},
                    "403020": {"name": "Life & Health Insurance"},
                    "403030": {"name": "Multi-line Insurance"},
                    "403040": {"name": "Property & Casualty Insurance"},
                    "403050": {"name": "Reinsurance"},
                }},
            }},
            # Information Technology
            "45": {"name": "Information Technology", "groups": {
                "4510": {"name": "Software & Services", "industries": {
                    "451010": {"name": "Internet Software & Services"},
                    "451020": {"name": "IT Services"},
                    "451030": {"name": "Software"},
                }},
                "4520": {"name": "Technology Hardware & Equipment", "industries": {
                    "452010": {"name": "Communications Equipment"},
                    "452020": {"name": "Technology Hardware, Storage & Peripherals"},
                    "452030": {"name": "Electronic Equipment, Instruments & Components"},
                }},
                "4530": {"name": "Semiconductors & Semiconductor Equipment", "industries": {
                    "453010": {"name": "Semiconductor Equipment"},
                    "453020": {"name": "Semiconductors"},
                }},
            }},
            # Communication Services
            "50": {"name": "Communication Services", "groups": {
                "5010": {"name": "Telecommunication Services", "industries": {
                    "501010": {"name": "Alternative Carriers"},
                    "501020": {"name": "Integrated Telecommunication Services"},
                    "501030": {"name": "Wireless Telecommunication Services"},
                }},
                "5020": {"name": "Media & Entertainment", "industries": {
                    "502010": {"name": "Media"},
                    "502020": {"name": "Movies & Entertainment"},
                    "502030": {"name": "Interactive Media & Services"},
                }},
            }},
            # Utilities
            "55": {"name": "Utilities", "groups": {
                "5510": {"name": "Utilities", "industries": {
                    "551010": {"name": "Electric Utilities"},
                    "551020": {"name": "Gas Utilities"},
                    "551030": {"name": "Multi-Utilities"},
                    "551040": {"name": "Water Utilities"},
                    "551050": {"name": "Independent Power & Renewable Electricity Producers"},
                }},
            }},
            # Real Estate
            "60": {"name": "Real Estate", "groups": {
                "6010": {"name": "Real Estate", "industries": {
                    "601010": {"name": "Real Estate Management & Development"},
                    "601020": {"name": "REITs"},
                }},
            }},
        }
    
    def get_gics_info(self, gics_code: str) -> Optional[Dict]:
        """Get GICS hierarchy info for a code."""
        if not gics_code or len(gics_code) < 2:
            return None
        
        sector_code = gics_code[:2]
        sector = self._gics_hierarchy.get(sector_code)
        if not sector:
            return None
        
        result = {"sector": sector["name"]}
        
        if len(gics_code) >= 4:
            group_code = gics_code[:4]
            group = sector["groups"].get(group_code)
            if group:
                result["industry_group"] = group["name"]
        
        if len(gics_code) >= 6:
            industry_code = gics_code[:6]
            for group in sector["groups"].values():
                industry = group["industries"].get(industry_code)
                if industry:
                    result["industry"] = industry["name"]
                    break
        
        if len(gics_code) >= 8:
            result["sub_industry"] = gics_code  # Full 8-digit code
        
        return result
    
    async def find_peers_by_gics(
        self,
        gics_code: str,
        level: str = "industry",  # sector, industry_group, industry, sub_industry
        exclude_cik: str = None,
        limit: int = 50
    ) -> List[str]:
        """Find peers by GICS code at specified level."""
        companies = self.storage.search_companies(gics_code=gics_code[:level_length(level)], limit=limit * 2)
        
        peers = []
        for company in companies:
            cik = company.get("id")
            if cik != exclude_cik:
                peers.append(cik)
                if len(peers) >= limit:
                    break
        
        return peers
    
    async def find_peers_by_market_cap(
        self,
        target_market_cap: Decimal,
        range_pct: Decimal = Decimal("0.5"),  # ±50%
        exclude_cik: str = None,
        limit: int = 50
    ) -> List[str]:
        """Find peers by similar market cap."""
        # Would need market cap data - placeholder
        min_cap = target_market_cap * (Decimal("1") - range_pct)
        max_cap = target_market_cap * (Decimal("1") + range_pct)
        
        # Query companies in range
        companies = self.storage.search_companies(
            market_cap_min=min_cap,
            market_cap_max=max_cap,
            limit=limit * 2
        )
        
        peers = []
        for company in companies:
            cik = company.get("id")
            if cik != exclude_cik:
                peers.append(cik)
                if len(peers) >= limit:
                    break
        
        return peers
    
    async def find_peers_by_revenue(
        self,
        target_revenue: Decimal,
        range_pct: Decimal = Decimal("0.5"),
        exclude_cik: str = None,
        limit: int = 50
    ) -> List[str]:
        """Find peers by similar revenue."""
        # Placeholder - would query revenue data
        return []
    
    async def find_peers_composite(
        self,
        company_cik: str,
        weights: Dict[str, float] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Find peers using composite scoring (GICS + size + metrics)."""
        weights = weights or {
            "gics": 0.4,
            "market_cap": 0.3,
            "revenue": 0.2,
            "geography": 0.1
        }
        
        # Get target company
        target = self.storage.get_company(company_cik)
        if not target:
            return []
        
        # Get candidates from same industry
        gics_code = target.get("gics_code", "")
        candidates = await self.find_peers_by_gics(gics_code, level="industry", exclude_cik=company_cik, limit=100)
        
        # Score candidates
        scored = []
        for cik in candidates:
            candidate = self.storage.get_company(cik)
            if not candidate:
                continue
            
            score = 0
            
            # GICS similarity
            if candidate.get("gics_code", "").startswith(gics_code[:4]):
                score += weights.get("gics", 0.4)
            
            # Market cap similarity
            # Would need market cap data
            
            # Revenue similarity
            # Would need revenue data
            
            # Geography
            if candidate.get("headquarters", {}).get("country") == target.get("headquarters", {}).get("country"):
                score += weights.get("geography", 0.1)
            
            scored.append({
                "cik": cik,
                "name": candidate.get("name"),
                "score": score,
                "gics_code": candidate.get("gics_code")
            })
        
        # Sort by score
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]
    
    def create_peer_group(
        self,
        name: str,
        description: str,
        criteria: Dict[str, Any],
        companies: List[str]
    ) -> PeerGroup:
        """Create a custom peer group."""
        group = PeerGroup(
            name=name,
            description=description,
            criteria=criteria,
            companies=companies
        )
        return group
    
    def get_gics_sectors(self) -> List[Dict]:
        """Get all GICS sectors."""
        return [{"code": k, "name": v["name"]} for k, v in self._gics_hierarchy.items()]
    
    def get_gics_groups(self, sector_code: str) -> List[Dict]:
        """Get industry groups for a sector."""
        sector = self._gics_hierarchy.get(sector_code)
        if not sector:
            return []
        return [{"code": k, "name": v["name"]} for k, v in sector["groups"].items()]
    
    def get_gics_industries(self, group_code: str) -> List[Dict]:
        """Get industries for a group."""
        sector_code = group_code[:2]
        sector = self._gics_hierarchy.get(sector_code)
        if not sector:
            return []
        group = sector["groups"].get(group_code)
        if not group:
            return []
        return [{"code": k, "name": v["name"]} for k, v in group["industries"].items()]


def level_length(level: str) -> int:
    """Get GICS code length for hierarchy level."""
    return {
        "sector": 2,
        "industry_group": 4,
        "industry": 6,
        "sub_industry": 8
    }.get(level, 6)