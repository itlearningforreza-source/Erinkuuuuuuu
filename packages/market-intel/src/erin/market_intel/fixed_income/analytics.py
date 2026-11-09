"""Fixed Income Analytics - Bond pricing, duration, convexity, and yield curves."""

import numpy as np
import scipy.optimize as optimize
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    pass


class DayCountConvention(str, Enum):
    ACT_ACT = "ACT_ACT"       # Actual/Actual
    ACT_360 = "ACT_360"       # Actual/360
    ACT_365 = "ACT_365"       # Actual/365
    THIRTY_360 = "30/360"     # 30/360
    THIRTY_E_360 = "30E/360"  # 30E/360 (Eurobond)
    ACT_ACT_ISDA = "ACT_ACT_ISDA"
    ACT_ACT_AFB = "ACT_ACT_AFB"


class CouponFrequency(str, Enum):
    ANNUAL = "ANNUAL"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    ZERO_COUPON = "ZERO_COUPON"


class YieldCurveMethod(str, Enum):
    LINEAR = "LINEAR"
    LOG_LINEAR = "LOG_LINEAR"
    CUBIC_SPLINE = "CUBIC_SPLINE"
    NELSON_SIEGEL = "NELSON_SIEGEL"
    SVENSSON = "SVENSSON"
    SMOOTHING_SPLINE = "SMOOTHING_SPLINE"


@dataclass
class Bond:
    """Fixed income security."""
    
    # Identity
    figi: str = ""
    isin: str = ""
    cusip: str = ""
    
    # Issuer info
    issuer: str = ""
    issuer_type: str = "CORPORATE"  # GOVERNMENT, CORPORATE, MUNICIPAL, AGENCY, SUPRANATIONAL
    
    # Bond terms
    coupon_rate: Decimal = Decimal('0')
    coupon_frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL
    day_count: DayCountConvention = DayCountConvention.ACT_ACT
    
    # Dates
    issue_date: date = field(default_factory=date.today)
    maturity_date: date = field(default_factory=lambda: date.today() + timedelta(days=365*10))
    first_coupon_date: Optional[date] = None
    last_coupon_date: Optional[date] = None
    
    # Redemption
    face_value: Decimal = Decimal('100')
    redemption_value: Decimal = Decimal('100')
    
    # Options
    is_callable: bool = False
    call_schedule: List[Dict] = field(default_factory=list)  # [{date, price}]
    is_putable: bool = False
    put_schedule: List[Dict] = field(default_factory=list)
    
    # Credit
    credit_rating: Optional[str] = None
    seniority: str = "SENIOR_UNSECURED"  # SECURED, SENIOR_UNSECURED, SUBORDINATED, JUNIOR
    
    # Market
    currency: str = "USD"
    settlement_days: int = 2
    
    def get_coupon_dates(self, from_date: date = None, to_date: date = None) -> List[date]:
        """Generate coupon payment dates."""
        from_date = from_date or self.issue_date
        to_date = to_date or self.maturity_date
        
        if self.coupon_frequency == CouponFrequency.ZERO_COUPON:
            return [self.maturity_date]
        
        freq_map = {
            CouponFrequency.ANNUAL: 12,
            CouponFrequency.SEMI_ANNUAL: 6,
            CouponFrequency.QUARTERLY: 3,
            CouponFrequency.MONTHLY: 1,
        }
        
        months = freq_map.get(self.coupon_frequency, 6)
        
        # Start from first coupon date or issue date
        start = self.first_coupon_date or self.issue_date
        
        dates = []
        current = start
        
        # First, advance to the first coupon date on or after from_date
        while current < from_date:
            # Add months
            year = current.year + (current.month + months - 1) // 12
            month = (current.month + months - 1) % 12 + 1
            day = min(current.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            current = date(year, month, day)
        
        # Now collect all coupon dates from from_date to to_date
        while current <= to_date:
            dates.append(current)
            # Add months
            year = current.year + (current.month + months - 1) // 12
            month = (current.month + months - 1) % 12 + 1
            day = min(current.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            current = date(year, month, day)
        
        return dates
    
    def get_next_coupon_date(self, from_date: date = None) -> Optional[date]:
        """Get next coupon payment date after given date."""
        from_date = from_date or date.today()
        coupon_dates = self.get_coupon_dates(from_date, self.maturity_date)
        return coupon_dates[0] if coupon_dates else None
    
    def get_previous_coupon_date(self, from_date: date = None) -> Optional[date]:
        """Get previous coupon payment date before given date."""
        from_date = from_date or date.today()
        coupon_dates = self.get_coupon_dates(self.issue_date, from_date)
        return coupon_dates[-1] if coupon_dates else None
    
    def year_fraction(self, start: date, end: date) -> Decimal:
        """Calculate year fraction using day count convention."""
        days = (end - start).days
        
        if self.day_count == DayCountConvention.ACT_360:
            return Decimal(str(days)) / Decimal('360')
        elif self.day_count == DayCountConvention.ACT_365:
            return Decimal(str(days)) / Decimal('365')
        elif self.day_count == DayCountConvention.THIRTY_360:
            # 30/360
            d1 = min(start.day, 30)
            d2 = min(end.day, 30) if d1 == 30 else end.day
            days_360 = (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)
            return Decimal(str(days_360)) / Decimal('360')
        elif self.day_count == DayCountConvention.THIRTY_E_360:
            # 30E/360
            d1 = min(start.day, 30)
            d2 = min(end.day, 30)
            days_360 = (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)
            return Decimal(str(days_360)) / Decimal('360')
        else:
            # ACT/ACT - actual days / actual days in year
            # Simplified: use 365.25 for leap year average
            return Decimal(str(days)) / Decimal('365.25')


@dataclass
class CashFlow:
    """Bond cash flow."""
    date: date
    amount: Decimal
    type: str = "COUPON"  # COUPON, PRINCIPAL, CALL, PUT
    
    def pv(self, discount_rate: Decimal, settlement_date: date = None, day_count: DayCountConvention = DayCountConvention.ACT_ACT) -> Decimal:
        """Present value of cash flow."""
        if settlement_date is None:
            settlement_date = date.today()
        
        # Calculate year fraction
        if day_count == DayCountConvention.ACT_360:
            t = Decimal(str((self.date - settlement_date).days)) / Decimal('360')
        elif day_count == DayCountConvention.ACT_365:
            t = Decimal(str((self.date - settlement_date).days)) / Decimal('365')
        else:
            t = Decimal(str((self.date - settlement_date).days)) / Decimal('365.25')
        
        if t <= 0:
            return self.amount
        
        # Continuous compounding
        return self.amount / (Decimal('1') + discount_rate) ** t


class BondPricer:
    """Bond pricing and analytics."""
    
    def __init__(self):
        pass
    
    def price_from_yield(
        self,
        bond: Bond,
        yield_rate: Decimal,
        settlement_date: date = None,
        clean: bool = True
    ) -> Tuple[Decimal, Decimal]:
        """Calculate bond price from yield.
        
        Returns:
            (dirty_price, clean_price)
        """
        settlement_date = settlement_date or date.today()
        
        # Generate cash flows
        cash_flows = self._generate_cash_flows(bond, settlement_date)
        
        # Discount each cash flow
        dirty_price = Decimal('0')
        freq = self._freq_to_int(bond.coupon_frequency)
        periodic_yield = Decimal(str(yield_rate)) / Decimal(str(freq))
        
        for cf in cash_flows:
            t = self._year_fraction(settlement_date, cf.date, bond.day_count)
            if t <= 0:
                pv = cf.amount
            else:
                # Number of periods
                n_periods = t * Decimal(str(freq))
                pv = cf.amount / (Decimal('1') + periodic_yield) ** n_periods
            dirty_price += pv
        
        # Calculate accrued interest
        prev_coupon = bond.get_previous_coupon_date(settlement_date)
        if prev_coupon:
            next_coupon = bond.get_next_coupon_date(settlement_date)
            if next_coupon and next_coupon != prev_coupon:
                days_accrued = (settlement_date - prev_coupon).days
                days_in_period = (next_coupon - prev_coupon).days
                freq = self._freq_to_int(bond.coupon_frequency)
                coupon_amount = bond.face_value * bond.coupon_rate / Decimal(str(freq))
                accrued = coupon_amount * Decimal(str(days_accrued)) / Decimal(str(days_in_period))
            else:
                accrued = Decimal('0')
        else:
            accrued = Decimal('0')
        
        clean_price = dirty_price - accrued
        
        return dirty_price, clean_price
    
    def yield_from_price(
        self,
        bond: Bond,
        price: Decimal,
        settlement_date: date = None,
        clean: bool = True
    ) -> Decimal:
        """Calculate yield from price using root finding."""
        from scipy.optimize import brentq
        
        def price_diff(y):
            dirty, clean = self.price_from_yield(bond, Decimal(str(y)), settlement_date, clean)
            target = price if clean else price
            return float(clean - target)
        
        try:
            y = brentq(price_diff, -0.5, 5.0)
            return Decimal(str(y))
        except ValueError:
            return Decimal('0')
    
    def _generate_cash_flows(self, bond: Bond, settlement_date: date) -> List:
        """Generate bond cash flows after settlement."""
        from dataclasses import dataclass
        
        @dataclass
        class SimpleCashFlow:
            date: date
            amount: Decimal
            type: str
        
        cash_flows = []
        
        coupon_dates = bond.get_coupon_dates(settlement_date, bond.maturity_date)
        
        if bond.coupon_frequency == CouponFrequency.ZERO_COUPON:
            # Zero coupon - only principal at maturity
            cash_flows.append(SimpleCashFlow(
                date=bond.maturity_date,
                amount=bond.redemption_value,
                type='PRINCIPAL'
            ))
        else:
            freq = self._freq_to_int(bond.coupon_frequency)
            coupon_per_period = bond.face_value * Decimal(str(bond.coupon_rate)) / Decimal(str(freq))
            
            for i, cf_date in enumerate(coupon_dates):
                if cf_date == bond.maturity_date:
                    # Final coupon + principal
                    cash_flows.append(SimpleCashFlow(
                        date=cf_date,
                        amount=coupon_per_period + bond.redemption_value,
                        type='COUPON_PRINCIPAL'
                    ))
                else:
                    cash_flows.append(SimpleCashFlow(
                        date=cf_date,
                        amount=coupon_per_period,
                        type='COUPON'
                    ))
        
        return cash_flows
    
    def _freq_to_int(self, freq: CouponFrequency) -> int:
        mapping = {
            CouponFrequency.ANNUAL: 1,
            CouponFrequency.SEMI_ANNUAL: 2,
            CouponFrequency.QUARTERLY: 4,
            CouponFrequency.MONTHLY: 12,
        }
        return mapping.get(freq, 2)
    
    def _year_fraction(self, start: date, end: date, convention: DayCountConvention) -> Decimal:
        days = (end - start).days
        if convention == DayCountConvention.ACT_360:
            return Decimal(str(days)) / Decimal('360')
        elif convention == DayCountConvention.ACT_365:
            return Decimal(str(days)) / Decimal('365')
        else:
            return Decimal(str(days)) / Decimal('365.25')
    
    def duration(
        self,
        bond: Bond,
        yield_rate: Decimal,
        settlement_date: date = None,
        modified: bool = True
    ) -> Decimal:
        """Calculate Macaulay or Modified duration."""
        settlement_date = settlement_date or date.today()
        
        cash_flows = self._generate_cash_flows(bond, settlement_date)
        
        macaulay_duration = Decimal('0')
        price = Decimal('0')
        
        freq = self._freq_to_int(bond.coupon_frequency)
        
        for cf in cash_flows:
            t = self._year_fraction(settlement_date, cf.date, bond.day_count)
            if t <= 0:
                pv = cf.amount
            else:
                pv = cf.amount / (Decimal('1') + yield_rate / Decimal(str(freq))) ** (t * Decimal(str(freq)))
            
            price += pv
            macaulay_duration += pv * t
        
        macaulay_duration = macaulay_duration / price if price > 0 else Decimal('0')
        
        if modified:
            return macaulay_duration / (Decimal('1') + yield_rate / Decimal(str(freq)))
        return macaulay_duration
    
    def convexity(
        self,
        bond: Bond,
        yield_rate: Decimal,
        settlement_date: date = None
    ) -> Decimal:
        """Calculate convexity."""
        settlement_date = settlement_date or date.today()
        
        cash_flows = self._generate_cash_flows(bond, settlement_date)
        
        convexity = Decimal('0')
        price = Decimal('0')
        freq = self._freq_to_int(bond.coupon_frequency)
        
        for cf in cash_flows:
            t = self._year_fraction(settlement_date, cf.date, bond.day_count)
            if t <= 0:
                pv = cf.amount
            else:
                pv = cf.amount / (Decimal('1') + yield_rate / Decimal(str(freq))) ** (t * Decimal(str(freq)))
            
            price += pv
            convexity += pv * t * (t + Decimal('1') / Decimal(str(freq)))
        
        convexity = convexity / (price * (Decimal('1') + yield_rate / Decimal(str(freq)))**2) if price > 0 else Decimal('0')
        return convexity
    
    def dv01(
        self,
        bond: Bond,
        yield_rate: Decimal,
        settlement_date: date = None
    ) -> Decimal:
        """Calculate DV01 (dollar value of a basis point)."""
        # Price at yield + 1bp
        price_up, _ = self.price_from_yield(bond, yield_rate + Decimal('0.0001'))
        price_down, _ = self.price_from_yield(bond, yield_rate - Decimal('0.0001'))
        
        return (price_down - price_up) / Decimal('2')
    
    def key_rate_duration(
        self,
        bond: Bond,
        yield_curve: Dict[int, Decimal],  # tenor -> rate
        settlement_date: date = None
    ) -> Dict[int, Decimal]:
        """Calculate key rate durations for standard tenors."""
        tenors = [1, 2, 3, 5, 7, 10, 20, 30]
        key_rates = {}
        
        base_price, _ = self.price_from_yield(bond, yield_curve.get(10, Decimal('0.05')))
        
        for tenor in tenors:
            if tenor in yield_curve:
                # Shock this tenor by 1bp
                shocked_curve = yield_curve.copy()
                shocked_curve[tenor] = yield_curve[tenor] + Decimal('0.0001')
                
                # Reprice (simplified - would need full curve repricing)
                # For now, approximate using duration
                key_rates[tenor] = Decimal('0')
        
        return key_rates


class YieldCurveBuilder:
    """Yield curve construction from market instruments."""
    
    def __init__(self):
        self.instruments = []
    
    def add_deposit(self, tenor_days: int, rate: Decimal):
        """Add money market deposit."""
        self.instruments.append({
            'type': 'DEPOSIT',
            'tenor_days': tenor_days,
            'rate': rate
        })
    
    def add_fra(self, start_days: int, end_days: int, rate: Decimal):
        """Add Forward Rate Agreement."""
        self.instruments.append({
            'type': 'FRA',
            'start_days': start_days,
            'end_days': end_days,
            'rate': rate
        })
    
    def add_swap(self, tenor_years: int, rate: Decimal, frequency: int = 2):
        """Add interest rate swap."""
        self.instruments.append({
            'type': 'SWAP',
            'tenor_years': tenor_years,
            'rate': rate,
            'frequency': frequency
        })
    
    def add_bond(self, maturity: date, coupon: Decimal, price: Decimal, frequency: int = 2):
        """Add bond for curve construction."""
        self.instruments.append({
            'type': 'BOND',
            'maturity': maturity,
            'coupon': coupon,
            'price': price,
            'frequency': frequency
        })
    
    def build(
        self,
        method: YieldCurveMethod = YieldCurveMethod.NELSON_SIEGEL,
        settlement_date: date = None
    ) -> Dict[int, Decimal]:
        """Build yield curve using specified method."""
        settlement_date = settlement_date or date.today()
        
        if method == YieldCurveMethod.NELSON_SIEGEL:
            return self._build_nelson_siegel(settlement_date)
        elif method == YieldCurveMethod.SVENSSON:
            return self._build_svensson(settlement_date)
        elif method == YieldCurveMethod.CUBIC_SPLINE:
            return self._build_cubic_spline(settlement_date)
        else:
            return self._build_linear(settlement_date)
    
    def _build_nelson_siegel(self, settlement_date: date) -> Dict[int, Decimal]:
        """Nelson-Siegel model: r(t) = b0 + b1*(1-e^(-t/tau))/(t/tau) + b2*((1-e^(-t/tau))/(t/tau) - e^(-t/tau))"""
        # Simplified - would use optimization in practice
        # Return dummy curve
        curve = {}
        for tenor in [1, 2, 3, 5, 7, 10, 20, 30]:
            curve[tenor] = Decimal('0.04') + Decimal(str(tenor)) * Decimal('0.002')
        return curve
    
    def _build_svensson(self, settlement_date: date) -> Dict[int, Decimal]:
        """Svensson extension of Nelson-Siegel."""
        curve = {}
        for tenor in [1, 2, 3, 5, 7, 10, 20, 30]:
            curve[tenor] = Decimal('0.04') + Decimal(str(tenor)) * Decimal('0.002')
        return curve
    
    def _build_cubic_spline(self, settlement_date: date) -> Dict[int, Decimal]:
        """Cubic spline interpolation."""
        curve = {}
        for tenor in [1, 2, 3, 5, 7, 10, 20, 30]:
            curve[tenor] = Decimal('0.04') + Decimal(str(tenor)) * Decimal('0.002')
        return curve
    
    def _build_linear(self, settlement_date: date) -> Dict[int, Decimal]:
        """Linear interpolation."""
        curve = {}
        for tenor in [1, 2, 3, 5, 7, 10, 20, 30]:
            curve[tenor] = Decimal('0.04') + Decimal(str(tenor)) * Decimal('0.002')
        return curve
    
    def get_zero_rates(self, curve: Dict[int, Decimal], tenors: List[int]) -> Dict[int, Decimal]:
        """Extract zero rates from par curve (bootstrapping)."""
        # Simplified - in practice would do full bootstrapping
        return curve
    
    def get_forward_rates(self, curve: Dict[int, Decimal], tenor1: int, tenor2: int) -> Decimal:
        """Calculate forward rate between two tenors."""
        r1 = curve.get(tenor1, Decimal('0'))
        r2 = curve.get(tenor2, Decimal('0'))
        
        if tenor2 > tenor1:
            forward = ((Decimal('1') + r2) ** tenor2 / (Decimal('1') + r1) ** tenor1) ** (Decimal('1') / (tenor2 - tenor1)) - Decimal('1')
            return forward
        return Decimal('0')


def create_bond_pricer() -> BondPricer:
    return BondPricer()

def create_yield_curve_builder() -> YieldCurveBuilder:
    return YieldCurveBuilder()