"""Valuation Engine - DCF, DDM, WACC, and other valuation models."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, getcontext
from typing import Optional, List, Dict, Any, Optional
from enum import Enum
from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from erin.market_intel.domain.interfaces import CurrencyCode

logger = logging.getLogger(__name__)

# Set precision for financial calculations
getcontext().prec = 28


class ValuationMethod(str, Enum):
    DCF_FCFF = "DCF_FCFF"          # Discounted Cash Flow - Free Cash Flow to Firm
    DCF_FCFE = "DCF_FCFE"          # Discounted Cash Flow - Free Cash Flow to Equity
    DDM_GORDON = "DDM_GORDON"      # Dividend Discount Model - Gordon Growth
    DDM_H_MODEL = "DDM_H_MODEL"    # Dividend Discount Model - H-Model
    DDM_TWO_STAGE = "DDM_TWO_STAGE" # Dividend Discount Model - Two Stage
    WACC = "WACC"                  # Weighted Average Cost of Capital
    COMPS = "COMPS"                # Comparable Company Analysis
    PRECEDENT = "PRECEDENT"        # Precedent Transactions
    SOTP = "SOTP"                  # Sum of the Parts


@dataclass
class DCFInputs:
    """Inputs for DCF valuation."""
    # Revenue projections
    revenue_year_0: Decimal
    revenue_growth_years: List[Decimal]  # e.g., [0.12, 0.10, 0.08, 0.06, 0.04]
    terminal_growth: Decimal
    
    # Margin assumptions
    ebitda_margin: Decimal
    depreciation_pct_revenue: Decimal
    capex_pct_revenue: Decimal
    nwc_pct_revenue: Decimal
    tax_rate: Decimal
    
    # Capital structure
    wacc: Decimal
    net_debt: Decimal
    cash: Decimal
    shares_outstanding: Decimal
    
    # Terminal value method
    terminal_method: str = "gordon"  # "gordon" or "exit_multiple"
    exit_multiple: Optional[Decimal] = None  # EV/EBITDA multiple


@dataclass
class DCFOutputs:
    """DCF valuation outputs."""
    enterprise_value: Decimal
    equity_value: Decimal
    value_per_share: Decimal
    
    # Components
    pv_explicit_fcf: Decimal
    pv_terminal_value: Decimal
    terminal_value: Decimal
    
    # Key metrics
    wacc: Decimal
    terminal_growth: Decimal
    terminal_year_fcf: Decimal
    
    # Breakdown
    fcf_projections: List[Dict[str, Decimal]] = field(default_factory=list)
    pv_fcf_breakdown: List[Decimal] = field(default_factory=list)


class DCFEngine:
    """Discounted Cash Flow valuation engine."""
    
    @staticmethod
    def calculate_fcff(
        revenue: Decimal,
        ebitda_margin: Decimal,
        depreciation_pct: Decimal,
        capex_pct: Decimal,
        nwc_pct: Decimal,
        tax_rate: Decimal
    ) -> Decimal:
        """Calculate Free Cash Flow to Firm."""
        ebitda = revenue * ebitda_margin
        depreciation = revenue * depreciation_pct
        ebit = ebitda - depreciation
        taxes = ebit * tax_rate
        nopat = ebit - taxes
        capex = revenue * capex_pct
        nwc_change = revenue * nwc_pct
        
        fcff = nopat + depreciation - capex - nwc_change
        return max(fcff, Decimal('0'))  # FCFF shouldn't be negative in steady state
    
    @staticmethod
    def calculate_wacc(
        risk_free_rate: Decimal,
        equity_risk_premium: Decimal,
        beta: Decimal,
        cost_of_debt: Decimal,
        tax_rate: Decimal,
        debt_to_equity: Decimal,
        equity_weight: Optional[Decimal] = None,
        debt_weight: Optional[Decimal] = None
    ) -> Decimal:
        """Calculate WACC using CAPM."""
        if equity_weight is None:
            equity_weight = Decimal('1') / (Decimal('1') + debt_to_equity)
        if debt_weight is None:
            debt_weight = debt_to_equity / (Decimal('1') + debt_to_equity)
        
        cost_of_equity = risk_free_rate + beta * equity_risk_premium
        after_tax_cost_of_debt = cost_of_debt * (Decimal('1') - tax_rate)
        
        wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
        return wacc
    
    @staticmethod
    def calculate_terminal_value_gordon(
        terminal_fcf: Decimal,
        wacc: Decimal,
        terminal_growth: Decimal
    ) -> Decimal:
        """Calculate terminal value using Gordon Growth Model."""
        if wacc <= terminal_growth:
            raise ValueError("WACC must be greater than terminal growth rate")
        return terminal_fcf * (Decimal('1') + terminal_growth) / (wacc - terminal_growth)
    
    @staticmethod
    def calculate_terminal_value_exit_multiple(
        terminal_ebitda: Decimal,
        exit_multiple: Decimal
    ) -> Decimal:
        """Calculate terminal value using exit multiple."""
        return terminal_ebitda * exit_multiple
    
    def run_dcf(self, inputs: DCFInputs) -> DCFOutputs:
        """Run full DCF valuation."""
        # Project FCFF for explicit forecast period
        fcf_projections = []
        pv_fcf_list = []
        
        revenue = inputs.revenue_year_0
        discount_factor = Decimal('1')
        
        for i, growth in enumerate(inputs.revenue_growth_years):
            year = i + 1
            revenue *= (Decimal('1') + growth)
            
            fcf = self.calculate_fcff(
                revenue=revenue,
                ebitda_margin=inputs.ebitda_margin,
                depreciation_pct=inputs.depreciation_pct_revenue,
                capex_pct=inputs.capex_pct_revenue,
                nwc_pct=inputs.nwc_pct_revenue,
                tax_rate=inputs.tax_rate
            )
            
            # Discount factor
            discount_factor = Decimal('1') / ((Decimal('1') + inputs.wacc) ** year)
            pv_fcf = fcf * discount_factor
            
            fcf_projections.append({
                "year": year,
                "revenue": revenue,
                "fcf": fcf,
                "discount_factor": discount_factor,
                "pv_fcf": pv_fcf
            })
            pv_fcf_list.append(pv_fcf)
        
        # Terminal value
        terminal_fcf = fcf_projections[-1]["fcf"] * (Decimal('1') + inputs.terminal_growth)
        
        if inputs.terminal_method == "gordon":
            terminal_value = self.calculate_terminal_value_gordon(
                terminal_fcf, inputs.wacc, inputs.terminal_growth
            )
        else:
            # Need EBITDA for exit multiple
            terminal_ebitda = inputs.revenue_growth_years[-1] * inputs.ebitda_margin * revenue
            terminal_value = self.calculate_terminal_value_exit_multiple(
                terminal_ebitda, inputs.exit_multiple
            )
        
        # PV of terminal value
        n_years = len(inputs.revenue_growth_years)
        pv_terminal = terminal_value / ((Decimal('1') + inputs.wacc) ** n_years)
        
        # Enterprise value
        pv_explicit_fcf = sum(pv_fcf_list)
        enterprise_value = pv_explicit_fcf + pv_terminal
        
        # Equity value
        equity_value = enterprise_value - inputs.net_debt + inputs.cash
        value_per_share = equity_value / inputs.shares_outstanding if inputs.shares_outstanding > 0 else Decimal('0')
        
        return DCFOutputs(
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            value_per_share=value_per_share,
            pv_explicit_fcf=pv_explicit_fcf,
            pv_terminal_value=pv_terminal,
            terminal_value=terminal_value,
            wacc=inputs.wacc,
            terminal_growth=inputs.terminal_growth,
            terminal_year_fcf=terminal_fcf,
            fcf_projections=fcf_projections,
            pv_fcf_breakdown=pv_fcf_list
        )


@dataclass
class WACCInputs:
    """Inputs for WACC calculation."""
    risk_free_rate: Decimal
    equity_risk_premium: Decimal
    beta: Decimal
    cost_of_debt: Decimal
    tax_rate: Decimal
    debt_to_equity: Decimal
    equity_weight: Optional[Decimal] = None
    debt_weight: Optional[Decimal] = None


class WACCCalculator:
    """WACC Calculator with multiple methods."""
    
    @staticmethod
    def calculate_capm_wacc(inputs: WACCInputs) -> Decimal:
        """Calculate WACC using CAPM."""
        cost_of_equity = inputs.risk_free_rate + inputs.beta * inputs.equity_risk_premium
        after_tax_cost_of_debt = inputs.cost_of_debt * (Decimal('1') - inputs.tax_rate)
        
        if inputs.equity_weight is not None and inputs.debt_weight is not None:
            equity_weight = inputs.equity_weight
            debt_weight = inputs.debt_weight
        else:
            total = Decimal('1') + inputs.debt_to_equity
            equity_weight = Decimal('1') / total
            debt_weight = inputs.debt_to_equity / total
        
        wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
        return wacc
    
    @staticmethod
    def calculate_build_up_wacc(
        risk_free_rate: Decimal,
        equity_risk_premium: Decimal,
        size_premium: Decimal,
        company_specific_premium: Decimal,
        cost_of_debt: Decimal,
        tax_rate: Decimal,
        debt_to_equity: Decimal
    ) -> Decimal:
        """Calculate WACC using Build-up method."""
        cost_of_equity = (
            risk_free_rate + 
            equity_risk_premium + 
            size_premium + 
            company_specific_premium
        )
        
        after_tax_cost_of_debt = cost_of_debt * (Decimal('1') - tax_rate)
        total = Decimal('1') + debt_to_equity
        equity_weight = Decimal('1') / total
        debt_weight = debt_to_equity / total
        
        wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
        return wacc
    
    @staticmethod
    def calculate_cost_of_equity(
        risk_free_rate: Decimal,
        beta: Decimal,
        equity_risk_premium: Decimal,
        size_premium: Decimal = Decimal('0'),
        company_specific_premium: Decimal = Decimal('0')
    ) -> Decimal:
        """Calculate cost of equity using CAPM + build-up."""
        return risk_free_rate + beta * equity_risk_premium + size_premium + company_specific_premium


@dataclass
class DDMInputs:
    """Inputs for Dividend Discount Model."""
    current_dividend: Decimal
    dividend_growth_rate: Decimal
    required_return: Decimal
    # For H-model
    short_term_growth: Optional[Decimal] = None
    long_term_growth: Optional[Decimal] = None
    transition_years: Optional[int] = None


class DDMEngine:
    """Dividend Discount Model engine."""
    
    @staticmethod
    def gordon_growth(ddm: DDMInputs) -> Decimal:
        """Gordon Growth Model: P = D1 / (r - g)"""
        d1 = ddm.current_dividend * (Decimal('1') + ddm.dividend_growth_rate)
        if ddm.required_return <= ddm.dividend_growth_rate:
            raise ValueError("Required return must exceed growth rate")
        return d1 / (ddm.required_return - ddm.dividend_growth_rate)
    
    @staticmethod
    def h_model(ddm: DDMInputs) -> Decimal:
        """H-Model for transitioning growth rates."""
        if not all([ddm.short_term_growth, ddm.long_term_growth, ddm.transition_years]):
            raise ValueError("H-model requires short_term_growth, long_term_growth, and transition_years")
        
        if ddm.required_return <= ddm.long_term_growth:
            raise ValueError("Required return must exceed long-term growth rate")
        
        # H-model formula
        # P = D0 * (1 + g_L) / (r - g_L) + D0 * H * (g_S - g_L) / (r - g_L)
        d0 = ddm.current_dividend
        g_s = ddm.short_term_growth
        g_l = ddm.long_term_growth
        r = ddm.required_return
        h = Decimal(str(ddm.transition_years)) / Decimal('2')
        
        term1 = d0 * (Decimal('1') + g_l) / (r - g_l)
        term2 = d0 * Decimal(str(h)) * (g_s - g_l) / (r - g_l)
        
        return term1 + term2
    
    @staticmethod
    def two_stage_ddm(
        current_dividend: Decimal,
        high_growth_rate: Decimal,
        high_growth_years: int,
        stable_growth_rate: Decimal,
        required_return: Decimal
    ) -> Decimal:
        """Two-stage DDM: high growth then stable growth."""
        if required_return <= stable_growth_rate:
            raise ValueError("Required return must exceed stable growth rate")
        
        # Stage 1: High growth
        pv_dividends = Decimal('0')
        dividend = current_dividend
        
        for year in range(1, high_growth_years + 1):
            dividend *= (Decimal('1') + high_growth_rate)
            pv = dividend / (Decimal('1') + required_return) ** year
            pv_dividends += pv
        
        # Stage 2: Stable growth (terminal value)
        terminal_dividend = dividend * (Decimal('1') + stable_growth_rate)
        terminal_value = terminal_dividend / (required_return - stable_growth_rate)
        pv_terminal = terminal_value / (Decimal('1') + required_return) ** high_growth_years
        
        return pv_dividends + pv_terminal


class ComparableAnalysis:
    """Comparable Company Analysis (Comps)."""
    
    @staticmethod
    def calculate_multiples(
        peers: List[Dict[str, Any]],
        metric: str = "EV_EBITDA"
    ) -> Dict[str, Decimal]:
        """Calculate valuation multiples for peer group."""
        multiples = []
        
        for peer in peers:
            if metric in peer and peer[metric] is not None:
                multiples.append(Decimal(str(peer[metric])))
        
        if not multiples:
            return {}
        
        multiples.sort()
        n = len(multiples)
        
        return {
            "min": min(multiples),
            "max": max(multiples),
            "median": multiples[n // 2] if n % 2 == 1 else (multiples[n//2 - 1] + multiples[n//2]) / Decimal('2'),
            "mean": sum(multiples) / Decimal(str(len(multiples))),
            "count": Decimal(str(len(multiples)))
        }
    
    @staticmethod
    def apply_multiple(
        subject_metric: Decimal,
        peer_multiple: Decimal
    ) -> Decimal:
        """Apply peer multiple to subject company metric."""
        return subject_metric * peer_multiple


class PrecedentTransactions:
    """Precedent Transaction Analysis."""
    
    @staticmethod
    def analyze_transactions(
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Decimal]:
        """Analyze precedent transaction multiples."""
        multiples = {
            "EV_EBITDA": [],
            "EV_REVENUE": [],
            "P_E": []
        }
        
        for tx in transactions:
            for key in multiples:
                if key in tx and tx[key] is not None:
                    multiples[key].append(Decimal(str(tx[key])))
        
        result = {}
        for key, values in multiples.items():
            if values:
                values.sort()
                n = len(values)
                multiples[key] = {
                    "min": min(values),
                    "max": max(values),
                    "median": values[n // 2] if n % 2 == 1 else (values[n//2 - 1] + values[n//2]) / Decimal('2'),
                    "mean": sum(values) / Decimal(str(len(values))),
                    "count": len(values)
                }
        
        return multiples


class SumOfTheParts:
    """Sum-of-the-Parts Valuation."""
    
    @staticmethod
    def calculate(
        divisions: List[Dict[str, Any]],
        corporate_overhead: Decimal = Decimal('0'),
        tax_rate: Decimal = Decimal('0')
    ) -> Decimal:
        """Calculate SOTP valuation."""
        total_value = Decimal('0')
        
        for division in divisions:
            value = division.get('value', Decimal('0'))
            ownership = division.get('ownership_pct', Decimal('1'))
            total_value += value * ownership
        
        # Subtract corporate overhead (after tax)
        after_tax_overhead = corporate_overhead * (Decimal('1') - tax_rate)
        
        return total_value - after_tax_overhead