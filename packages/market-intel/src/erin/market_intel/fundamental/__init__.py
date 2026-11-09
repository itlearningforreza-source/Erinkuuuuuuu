"""ERIN Market Intelligence - Fundamental Research Module."""

from erin.market_intel.fundamental.company_service import CompanyService
from erin.market_intel.fundamental.financial_statements_service import (
    FinancialStatementsService,
    FinancialStatementType,
    PeriodType,
    GAAPType
)
from erin.market_intel.fundamental.ratio_engine import (
    RatioEngine,
    RatioType,
    PeerComparison
)
from erin.market_intel.fundamental.peer_group import (
    PeerGroupService,
    PeerGroup,
    level_length
)
from erin.market_intel.fundamental.notebook_service import NotebookService

__all__ = [
    "CompanyService",
    "FinancialStatementsService",
    "FinancialStatementType",
    "PeriodType",
    "GAAPType",
    "RatioEngine",
    "RatioType",
    "PeerComparison",
    "PeerGroupService",
    "PeerGroup",
    "level_length",
    "NotebookService",
]