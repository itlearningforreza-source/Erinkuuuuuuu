"""Financial Statements Service - GAAP/IFRS financial statement storage and retrieval."""

import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Any
from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    from erin.data_infra.storage.sqlite import SQLiteStorage

logger = logging.getLogger(__name__)


class FinancialStatementType(str):
    """Financial statement types."""
    INCOME_STATEMENT = "INCOME_STATEMENT"
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW = "CASH_FLOW"
    STATEMENT_OF_EQUITY = "STATEMENT_OF_EQUITY"
    COMPREHENSIVE_INCOME = "COMPREHENSIVE_INCOME"


class PeriodType(str):
    """Period types."""
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    TTM = "TTM"  # Trailing twelve months


class GAAPType(str):
    """GAAP standards."""
    US_GAAP = "US_GAAP"
    IFRS = "IFRS"


class FinancialStatementsService:
    """Service for managing financial statements."""

    def __init__(self, storage: 'SQLiteStorage'):
        self.storage = storage

    async def create_financial_statement(
        self,
        company_id: str,
        statement_type: str,
        period_type: str,
        period_end: date,
        filing_date: date,
        gaap: str,
        currency: str,
        line_items: Dict[str, Any],
        source: str,
        source_accession: str = None,
        is_restated: bool = False,
        restatement_reason: str = None
    ) -> str:
        """Create a financial statement record."""
        import uuid
        
        statement_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Validate statement type
        valid_types = ["INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW", 
                      "STATEMENT_OF_EQUITY", "COMPREHENSIVE_INCOME"]
        if statement_type not in valid_types:
            raise ValueError(f"Invalid statement type: {statement_type}")
        
        # Validate period type
        valid_periods = ["ANNUAL", "QUARTERLY", "SEMI_ANNUAL", "TTM"]
        if period_type not in valid_periods:
            raise ValueError(f"Invalid period type: {period_type}")
        
        # Validate GAAP
        valid_gaap = ["US_GAAP", "IFRS"]
        if gaap not in valid_gaap:
            raise ValueError(f"Invalid GAAP: {gaap}")
        
        statement_data = {
            "id": statement_id,
            "company_id": company_id,
            "statement_type": statement_type,
            "period_type": period_type,
            "period_end": period_end.isoformat(),
            "filing_date": filing_date.isoformat(),
            "gaap": gaap,
            "currency": currency,
            "line_items": json.dumps(line_items),
            "source": source,
            "source_accession": source_accession,
            "is_restated": 1 if is_restated else 0,
            "restatement_reason": restatement_reason,
            "created_at": now.isoformat()
        }
        
        # Store in SQLite (would need a method to insert financial statements)
        # For now, return the statement_id
        return statement_id

    async def get_financial_statement(self, statement_id: str) -> Optional[Dict]:
        """Get financial statement by ID."""
        # Would query from storage
        pass

    async def get_company_financials(
        self,
        company_id: str,
        statement_type: str = None,
        period_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get financial statements for a company."""
        return self.storage.get_company_financials(
            company_id=company_id,
            statement_type=statement_type,
            period_type=period_type,
            limit=limit
        )

    async def get_latest_financials(
        self,
        company_id: str,
        statement_type: str = "INCOME_STATEMENT",
        period_type: str = "ANNUAL"
    ) -> Optional[Dict]:
        """Get the latest financial statement for a company."""
        financials = await self.get_company_financials(
            company_id=company_id,
            statement_type=statement_type,
            period_type=period_type,
            limit=1
        )
        return financials[0] if financials else None

    async def get_income_statement(
        self,
        company_id: str,
        period_type: str = "ANNUAL",
        limit: int = 5
    ) -> List[Dict]:
        """Get income statements for a company."""
        return await self.get_company_financials(
            company_id=company_id,
            statement_type="INCOME_STATEMENT",
            period_type=period_type,
            limit=limit
        )

    async def get_balance_sheet(
        self,
        company_id: str,
        period_type: str = "ANNUAL",
        limit: int = 5
    ) -> List[Dict]:
        """Get balance sheets for a company."""
        return await self.get_company_financials(
            company_id=company_id,
            statement_type="BALANCE_SHEET",
            period_type=period_type,
            limit=limit
        )

    async def get_cash_flow(
        self,
        company_id: str,
        period_type: str = "ANNUAL",
        limit: int = 5
    ) -> List[Dict]:
        """Get cash flow statements for a company."""
        return await self.get_company_financials(
            company_id=company_id,
            statement_type="CASH_FLOW",
            period_type=period_type,
            limit=limit
        )

    async def parse_xbrl_to_line_items(
        self,
        xbrl_facts: List[Dict],
        statement_type: str
    ) -> Dict[str, Decimal]:
        """Parse XBRL facts into standardized line items."""
        # Standard GAAP concept mappings
        concept_mapping = {
            "INCOME_STATEMENT": {
                "Revenue": ["RevenueFromContractWithCustomer", "Revenues", "SalesRevenueNet"],
                "CostOfRevenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfSales"],
                "GrossProfit": ["GrossProfit"],
                "OperatingExpenses": ["OperatingExpenses"],
                "ResearchAndDevelopment": ["ResearchAndDevelopmentExpense"],
                "SellingGeneralAndAdministrative": ["SellingGeneralAndAdministrativeExpense"],
                "OperatingIncome": ["OperatingIncomeLoss"],
                "InterestExpense": ["InterestExpense"],
                "OtherIncomeExpense": ["OtherNonoperatingIncomeExpense"],
                "IncomeBeforeTax": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxes"],
                "IncomeTaxExpense": ["IncomeTaxExpenseBenefit"],
                "NetIncome": ["NetIncomeLoss"],
                "EarningsPerShareBasic": ["EarningsPerShareBasic"],
                "EarningsPerShareDiluted": ["EarningsPerShareDiluted"],
            },
            "BALANCE_SHEET": {
                "CashAndCashEquivalents": ["CashAndCashEquivalentsAtCarryingValue"],
                "ShortTermInvestments": ["ShortTermInvestments"],
                "AccountsReceivable": ["AccountsReceivableNetCurrent"],
                "Inventory": ["InventoryNet"],
                "CurrentAssets": ["AssetsCurrent"],
                "PropertyPlantEquipment": ["PropertyPlantAndEquipmentNet"],
                "TotalAssets": ["Assets"],
                "AccountsPayable": ["AccountsPayableCurrent"],
                "ShortTermDebt": ["ShortTermBorrowings"],
                "CurrentLiabilities": ["LiabilitiesCurrent"],
                "LongTermDebt": ["LongTermDebt"],
                "TotalLiabilities": ["Liabilities"],
                "TotalEquity": ["StockholdersEquity"],
            },
            "CASH_FLOW": {
                "OperatingCashFlow": ["NetCashProvidedByUsedInOperatingActivities"],
                "InvestingCashFlow": ["NetCashProvidedByUsedInInvestingActivities"],
                "FinancingCashFlow": ["NetCashProvidedByUsedInFinancingActivities"],
                "FreeCashFlow": ["FreeCashFlow"],
                "CapitalExpenditures": ["PaymentsToAcquirePropertyPlantAndEquipment"],
                "DepreciationAndAmortization": ["DepreciationDepletionAndAmortization"],
            }
        }
        
        mapping = concept_mapping.get(statement_type, {})
        line_items = {}
        
        for concept, possible_names in mapping.items():
            for fact in xbrl_facts:
                if fact["concept"] in possible_names and fact["value"] is not None:
                    line_items[concept] = fact["value"]
                    break
        
        return line_items