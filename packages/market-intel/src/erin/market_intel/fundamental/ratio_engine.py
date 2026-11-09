"""Financial Ratio Engine - Comprehensive financial ratio calculations."""

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING
from enum import Enum
import math

if TYPE_CHECKING:
    from erin.market_intel.fundamental.financial_statements_service import FinancialStatementsService

logger = logging.getLogger(__name__)


class RatioType(str, Enum):
    PROFITABILITY = "PROFITABILITY"
    LIQUIDITY = "LIQUIDITY"
    SOLVENCY = "SOLVENCY"
    EFFICIENCY = "EFFICIENCY"
    VALUATION = "VALUATION"
    GROWTH = "GROWTH"


class RatioEngine:
    """Comprehensive financial ratio calculation engine."""
    
    def __init__(self, financial_service: 'FinancialStatementsService'):
        self.financial_service = financial_service
        self._ratio_cache = {}
    
    async def calculate_all_ratios(
        self,
        company_id: str,
        period_end: date = None
    ) -> List[Dict[str, Any]]:
        """Calculate all financial ratios for a company."""
        ratios = []
        
        # Get latest financial statements
        income_stmt = await self.financial_service.get_latest_financials(
            company_id, "INCOME_STATEMENT", "ANNUAL"
        )
        balance_sheet = await self.financial_service.get_latest_financials(
            company_id, "BALANCE_SHEET", "ANNUAL"
        )
        cash_flow = await self.financial_service.get_latest_financials(
            company_id, "CASH_FLOW", "ANNUAL"
        )
        
        if not income_stmt or not balance_sheet:
            logger.warning(f"Insufficient financial data for {company_id}")
            return []
        
        # Parse line items
        is_items = income_stmt.get("line_items", {})
        bs_items = balance_sheet.get("line_items", {})
        cf_items = cash_flow.get("line_items", {}) if cash_flow else {}
        
        period_end = period_end or date.fromisoformat(income_stmt["period_end"])
        
        # Profitability Ratios
        ratios.extend(await self._calculate_profitability_ratios(
            company_id, period_end, is_items, bs_items
        ))
        
        # Liquidity Ratios
        ratios.extend(await self._calculate_liquidity_ratios(
            company_id, period_end, bs_items
        ))
        
        # Solvency Ratios
        ratios.extend(await self._calculate_solvency_ratios(
            company_id, period_end, bs_items, is_items
        ))
        
        # Efficiency Ratios
        ratios.extend(await self._calculate_efficiency_ratios(
            company_id, period_end, is_items, bs_items
        ))
        
        # Valuation Ratios (need market data)
        ratios.extend(await self._calculate_valuation_ratios(
            company_id, period_end, is_items, bs_items
        ))
        
        # Growth Ratios (need historical data)
        ratios.extend(await self._calculate_growth_ratios(
            company_id, period_end, is_items, bs_items
        ))
        
        return ratios
    
    async def _calculate_profitability_ratios(
        self,
        company_id: str,
        period_end: date,
        is_items: Dict[str, Any],
        bs_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate profitability ratios."""
        ratios = []
        
        revenue = is_items.get("Revenue")
        gross_profit = is_items.get("GrossProfit")
        operating_income = is_items.get("OperatingIncome")
        net_income = is_items.get("NetIncome")
        total_assets = bs_items.get("TotalAssets")
        total_equity = bs_items.get("TotalEquity")
        
        # Gross Margin
        if revenue and gross_profit:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "PROFITABILITY",
                "ratio_name": "GrossMargin",
                "value": float(gross_profit / revenue),
                "inputs": {"GrossProfit": float(gross_profit), "Revenue": float(revenue)},
                "methodology_version": "1.0"
            })
        
        # Operating Margin
        if revenue and operating_income:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "PROFITABILITY",
                "ratio_name": "OperatingMargin",
                "value": float(operating_income / revenue),
                "inputs": {"OperatingIncome": float(operating_income), "Revenue": float(revenue)},
                "methodology_version": "1.0"
            })
        
        # Net Profit Margin
        if revenue and net_income:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "PROFITABILITY",
                "ratio_name": "NetProfitMargin",
                "value": float(net_income / revenue),
                "inputs": {"NetIncome": float(net_income), "Revenue": float(revenue)},
                "methodology_version": "1.0"
            })
        
        # Return on Assets (ROA)
        if net_income and total_assets:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "PROFITABILITY",
                "ratio_name": "ReturnOnAssets",
                "value": float(net_income / total_assets),
                "inputs": {"NetIncome": float(net_income), "TotalAssets": float(total_assets)},
                "methodology_version": "1.0"
            })
        
        # Return on Equity (ROE)
        if net_income and total_equity:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "PROFITABILITY",
                "ratio_name": "ReturnOnEquity",
                "value": float(net_income / total_equity),
                "inputs": {"NetIncome": float(net_income), "TotalEquity": float(total_equity)},
                "methodology_version": "1.0"
            })
        
        # Return on Invested Capital (ROIC) - simplified
        if operating_income and total_assets and bs_items.get("CurrentLiabilities"):
            invested_capital = total_assets - bs_items.get("CurrentLiabilities", 0)
            if invested_capital:
                ratios.append({
                    "company_id": company_id,
                    "period_end": period_end.isoformat(),
                    "ratio_type": "PROFITABILITY",
                    "ratio_name": "ReturnOnInvestedCapital",
                    "value": float(operating_income * Decimal("0.75") / invested_capital),  # NOPAT approx
                    "inputs": {
                        "OperatingIncome": float(operating_income),
                        "InvestedCapital": float(invested_capital)
                    },
                    "methodology_version": "1.0"
                })
        
        return ratios
    
    async def _calculate_liquidity_ratios(
        self,
        company_id: str,
        period_end: date,
        bs_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate liquidity ratios."""
        ratios = []
        
        current_assets = bs_items.get("CurrentAssets")
        current_liabilities = bs_items.get("CurrentLiabilities")
        cash = bs_items.get("CashAndCashEquivalents")
        short_term_investments = bs_items.get("ShortTermInvestments")
        accounts_receivable = bs_items.get("AccountsReceivable")
        inventory = bs_items.get("Inventory")
        
        # Current Ratio
        if current_assets and current_liabilities and current_liabilities != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "LIQUIDITY",
                "ratio_name": "CurrentRatio",
                "value": float(current_assets / current_liabilities),
                "inputs": {
                    "CurrentAssets": float(current_assets),
                    "CurrentLiabilities": float(current_liabilities)
                },
                "methodology_version": "1.0"
            })
        
        # Quick Ratio (Acid Test)
        if current_assets and inventory and current_liabilities and current_liabilities != 0:
            quick_assets = current_assets - inventory
            if cash and short_term_investments:
                quick_assets = cash + short_term_investments + (accounts_receivable or 0)
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "LIQUIDITY",
                "ratio_name": "QuickRatio",
                "value": float(quick_assets / current_liabilities),
                "inputs": {
                    "QuickAssets": float(quick_assets),
                    "CurrentLiabilities": float(current_liabilities)
                },
                "methodology_version": "1.0"
            })
        
        # Cash Ratio
        if cash and current_liabilities and current_liabilities != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "LIQUIDITY",
                "ratio_name": "CashRatio",
                "value": float(cash / current_liabilities),
                "inputs": {
                    "CashAndCashEquivalents": float(cash),
                    "CurrentLiabilities": float(current_liabilities)
                },
                "methodology_version": "1.0"
            })
        
        return ratios
    
    async def _calculate_solvency_ratios(
        self,
        company_id: str,
        period_end: date,
        bs_items: Dict[str, Any],
        is_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate solvency/leverage ratios."""
        ratios = []
        
        total_assets = bs_items.get("TotalAssets")
        total_liabilities = bs_items.get("TotalLiabilities")
        total_equity = bs_items.get("TotalEquity")
        long_term_debt = bs_items.get("LongTermDebt")
        short_term_debt = bs_items.get("ShortTermDebt")
        operating_income = is_items.get("OperatingIncome")
        interest_expense = is_items.get("InterestExpense")
        
        total_debt = (long_term_debt or 0) + (short_term_debt or 0)
        
        # Debt to Equity
        if total_debt and total_equity and total_equity != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "SOLVENCY",
                "ratio_name": "DebtToEquity",
                "value": float(total_debt / total_equity),
                "inputs": {
                    "TotalDebt": float(total_debt),
                    "TotalEquity": float(total_equity)
                },
                "methodology_version": "1.0"
            })
        
        # Debt to Assets
        if total_debt and total_assets and total_assets != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "SOLVENCY",
                "ratio_name": "DebtToAssets",
                "value": float(total_debt / total_assets),
                "inputs": {
                    "TotalDebt": float(total_debt),
                    "TotalAssets": float(total_assets)
                },
                "methodology_version": "1.0"
            })
        
        # Equity Ratio
        if total_equity and total_assets and total_assets != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "SOLVENCY",
                "ratio_name": "EquityRatio",
                "value": float(total_equity / total_assets),
                "inputs": {
                    "TotalEquity": float(total_equity),
                    "TotalAssets": float(total_assets)
                },
                "methodology_version": "1.0"
            })
        
        # Interest Coverage Ratio
        if operating_income and interest_expense and interest_expense != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "SOLVENCY",
                "ratio_name": "InterestCoverage",
                "value": float(operating_income / interest_expense),
                "inputs": {
                    "OperatingIncome": float(operating_income),
                    "InterestExpense": float(interest_expense)
                },
                "methodology_version": "1.0"
            })
        
        # Debt to EBITDA (approximate)
        if total_debt and operating_income:
            # Simplified: EBITDA ≈ Operating Income + D&A
            ebitda_approx = operating_income * Decimal("1.2")  # rough estimate
            if ebitda_approx != 0:
                ratios.append({
                    "company_id": company_id,
                    "period_end": period_end.isoformat(),
                    "ratio_type": "SOLVENCY",
                    "ratio_name": "DebtToEBITDA",
                    "value": float(total_debt / ebitda_approx),
                    "inputs": {
                        "TotalDebt": float(total_debt),
                        "EBITDA_approx": float(ebitda_approx)
                    },
                    "methodology_version": "1.0"
                })
        
        return ratios
    
    async def _calculate_efficiency_ratios(
        self,
        company_id: str,
        period_end: date,
        is_items: Dict[str, Any],
        bs_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate efficiency/activity ratios."""
        ratios = []
        
        revenue = is_items.get("Revenue")
        cost_of_revenue = is_items.get("CostOfRevenue")
        total_assets = bs_items.get("TotalAssets")
        accounts_receivable = bs_items.get("AccountsReceivable")
        inventory = bs_items.get("Inventory")
        accounts_payable = bs_items.get("AccountsPayable")
        
        # Asset Turnover
        if revenue and total_assets and total_assets != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "AssetTurnover",
                "value": float(revenue / total_assets),
                "inputs": {
                    "Revenue": float(revenue),
                    "TotalAssets": float(total_assets)
                },
                "methodology_version": "1.0"
            })
        
        # Receivables Turnover
        if revenue and accounts_receivable and accounts_receivable != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "ReceivablesTurnover",
                "value": float(revenue / accounts_receivable),
                "inputs": {
                    "Revenue": float(revenue),
                    "AccountsReceivable": float(accounts_receivable)
                },
                "methodology_version": "1.0"
            })
        
        # Days Sales Outstanding (DSO)
        if revenue and accounts_receivable and revenue != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "DaysSalesOutstanding",
                "value": float(accounts_receivable / revenue * 365),
                "inputs": {
                    "AccountsReceivable": float(accounts_receivable),
                    "Revenue": float(revenue)
                },
                "methodology_version": "1.0"
            })
        
        # Inventory Turnover
        if cost_of_revenue and inventory and inventory != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "InventoryTurnover",
                "value": float(cost_of_revenue / inventory),
                "inputs": {
                    "CostOfRevenue": float(cost_of_revenue),
                    "Inventory": float(inventory)
                },
                "methodology_version": "1.0"
            })
        
        # Days Inventory Outstanding (DIO)
        if cost_of_revenue and inventory and cost_of_revenue != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "DaysInventoryOutstanding",
                "value": float(inventory / cost_of_revenue * 365),
                "inputs": {
                    "Inventory": float(inventory),
                    "CostOfRevenue": float(cost_of_revenue)
                },
                "methodology_version": "1.0"
            })
        
        # Payables Turnover
        if cost_of_revenue and accounts_payable and accounts_payable != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "PayablesTurnover",
                "value": float(cost_of_revenue / accounts_payable),
                "inputs": {
                    "CostOfRevenue": float(cost_of_revenue),
                    "AccountsPayable": float(accounts_payable)
                },
                "methodology_version": "1.0"
            })
        
        # Days Payable Outstanding (DPO)
        if cost_of_revenue and accounts_payable and cost_of_revenue != 0:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "DaysPayableOutstanding",
                "value": float(accounts_payable / cost_of_revenue * 365),
                "inputs": {
                    "AccountsPayable": float(accounts_payable),
                    "CostOfRevenue": float(cost_of_revenue)
                },
                "methodology_version": "1.0"
            })
        
        # Cash Conversion Cycle
        dso = None
        dio = None
        dpo = None
        for r in ratios:
            if r["ratio_name"] == "DaysSalesOutstanding":
                dso = r["value"]
            elif r["ratio_name"] == "DaysInventoryOutstanding":
                dio = r["value"]
            elif r["ratio_name"] == "DaysPayableOutstanding":
                dpo = r["value"]
        
        if dso is not None and dio is not None and dpo is not None:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "EFFICIENCY",
                "ratio_name": "CashConversionCycle",
                "value": dso + dio - dpo,
                "inputs": {
                    "DSO": dso,
                    "DIO": dio,
                    "DPO": dpo
                },
                "methodology_version": "1.0"
            })
        
        return ratios
    
    async def _calculate_valuation_ratios(
        self,
        company_id: str,
        period_end: date,
        is_items: Dict[str, Any],
        bs_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate valuation ratios (need market data)."""
        ratios = []
        
        # These would need market cap/share price from market data service
        # For now, return empty - will be populated when market data is available
        net_income = is_items.get("NetIncome")
        total_equity = bs_items.get("TotalEquity")
        
        # Book Value Per Share (would need shares outstanding)
        if total_equity:
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "VALUATION",
                "ratio_name": "BookValuePerShare",
                "value": None,  # Need shares outstanding
                "inputs": {"TotalEquity": float(total_equity)},
                "methodology_version": "1.0"
            })
        
        # Earnings Per Share (from income statement if available)
        if is_items.get("EarningsPerShareDiluted"):
            ratios.append({
                "company_id": company_id,
                "period_end": period_end.isoformat(),
                "ratio_type": "VALUATION",
                "ratio_name": "EarningsPerShare",
                "value": float(is_items["EarningsPerShareDiluted"]),
                "inputs": {"EPS": float(is_items["EarningsPerShareDiluted"])},
                "methodology_version": "1.0"
            })
        
        return ratios
    
    async def _calculate_growth_ratios(
        self,
        company_id: str,
        period_end: date,
        is_items: Dict[str, Any],
        bs_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate growth ratios (need historical data)."""
        ratios = []
        
        # Would need prior period data for growth calculations
        # For now, return placeholders
        
        return ratios
    
    def calculate_dupont_analysis(
        self,
        net_income: Decimal,
        revenue: Decimal,
        total_assets: Decimal,
        total_equity: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate DuPont Analysis decomposition of ROE."""
        if not all([net_income, revenue, total_assets, total_equity]):
            return {}
        
        profit_margin = net_income / revenue
        asset_turnover = revenue / total_assets
        equity_multiplier = total_assets / total_equity
        roe = profit_margin * asset_turnover * equity_multiplier
        
        return {
            "ROE": roe,
            "ProfitMargin": profit_margin,
            "AssetTurnover": asset_turnover,
            "EquityMultiplier": equity_multiplier,
            "ROA": profit_margin * asset_turnover
        }
    
    def calculate_altman_z_score(
        self,
        working_capital: Decimal,
        total_assets: Decimal,
        retained_earnings: Decimal,
        ebit: Decimal,
        market_value_equity: Decimal,
        total_liabilities: Decimal,
        sales: Decimal
    ) -> Decimal:
        """Calculate Altman Z-Score for bankruptcy prediction."""
        if total_assets == 0:
            return Decimal("0")
        
        x1 = working_capital / total_assets
        x2 = retained_earnings / total_assets
        x3 = ebit / total_assets
        x4 = market_value_equity / total_liabilities if total_liabilities else Decimal("0")
        x5 = sales / total_assets
        
        z_score = (Decimal("1.2") * x1 + 
                  Decimal("1.4") * x2 + 
                  Decimal("3.3") * x3 + 
                  Decimal("0.6") * x4 + 
                  Decimal("1.0") * x5)
        
        return z_score
    
    def calculate_piotroski_f_score(
        self,
        net_income: Decimal,
        operating_cash_flow: Decimal,
        total_assets: Decimal,
        prior_total_assets: Decimal,
        long_term_debt: Decimal,
        prior_long_term_debt: Decimal,
        current_ratio: Decimal,
        prior_current_ratio: Decimal,
        shares_outstanding: Decimal,
        prior_shares_outstanding: Decimal,
        gross_margin: Decimal,
        prior_gross_margin: Decimal,
        asset_turnover: Decimal,
        prior_asset_turnover: Decimal
    ) -> int:
        """Calculate Piotroski F-Score (0-9)."""
        score = 0
        
        # Profitability
        if net_income > 0:
            score += 1
        if operating_cash_flow > 0:
            score += 1
        if net_income / total_assets > 0:  # ROA positive
            score += 1
        if operating_cash_flow > net_income:  # Quality of earnings
            score += 1
        
        # Leverage/Liquidity
        if long_term_debt < prior_long_term_debt:  # Decrease in leverage
            score += 1
        if current_ratio > prior_current_ratio:  # Increase in liquidity
            score += 1
        if shares_outstanding <= prior_shares_outstanding:  # No dilution
            score += 1
        
        # Operating Efficiency
        if gross_margin > prior_gross_margin:
            score += 1
        if asset_turnover > prior_asset_turnover:
            score += 1
        
        return score


class PeerComparison:
    """Peer group comparison for ratio analysis."""
    
    def __init__(self, ratio_engine: RatioEngine):
        self.ratio_engine = ratio_engine
    
    async def compare_with_peers(
        self,
        company_id: str,
        peer_ids: List[str],
        ratios: List[str] = None
    ) -> Dict[str, Any]:
        """Compare company ratios with peer group."""
        # Get company ratios
        company_ratios = await self.ratio_engine.calculate_all_ratios(company_id)
        
        # Get peer ratios
        peer_ratios = {}
        for peer_id in peer_ids:
            peer_ratios[peer_id] = await self.ratio_engine.calculate_all_ratios(peer_id)
        
        # Compare
        comparison = {}
        target_ratios = ratios or [r["ratio_name"] for r in company_ratios]
        
        for ratio_name in target_ratios:
            company_value = None
            for r in company_ratios:
                if r["ratio_name"] == ratio_name:
                    company_value = r["value"]
                    break
            
            if company_value is None:
                continue
            
            peer_values = []
            for peer_id, ratios in peer_ratios.items():
                for r in ratios:
                    if r["ratio_name"] == ratio_name and r["value"] is not None:
                        peer_values.append(r["value"])
            
            if peer_values:
                peer_values.sort()
                n = len(peer_values)
                comparison[ratio_name] = {
                    "company_value": company_value,
                    "peer_count": n,
                    "peer_median": peer_values[n // 2] if n % 2 == 1 else (peer_values[n//2 - 1] + peer_values[n//2]) / 2,
                    "peer_mean": sum(peer_values) / n,
                    "peer_min": min(peer_values),
                    "peer_max": max(peer_values),
                    "percentile": self._calculate_percentile(company_value, peer_values)
                }
        
        return comparison
    
    def _calculate_percentile(self, value: float, sorted_values: List[float]) -> float:
        """Calculate percentile rank of value in sorted list."""
        import bisect
        rank = bisect.bisect_left(sorted_values, value)
        return (rank / len(sorted_values)) * 100 if sorted_values else 0