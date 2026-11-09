"""Derivatives Analytics - Option pricing, Greeks, and volatility surfaces."""

import numpy as np
import scipy.stats as stats
import scipy.optimize as optimize
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime
from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    pass


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class OptionStyle(str, Enum):
    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"
    BERMUDAN = "BERMUDAN"
    ASIAN = "ASIAN"
    BARRIER = "BARRIER"
    LOOKBACK = "LOOKBACK"
    DIGITAL = "DIGITAL"


class ExerciseType(str, Enum):
    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"


@dataclass
class Option:
    """Option contract."""
    
    # Identity
    figi: str = ""
    underlying_figi: str = ""
    
    # Terms
    option_type: OptionType = OptionType.CALL
    style: OptionStyle = OptionStyle.EUROPEAN
    strike: Decimal = Decimal('100')
    expiration: date = field(default_factory=lambda: date.today() + timedelta(days=30))
    
    # Settlement
    settlement: str = "PHYSICAL"  # PHYSICAL, CASH
    contract_size: int = 100
    currency: str = "USD"
    exchange: str = ""
    
    # Underlying
    underlying_price: Decimal = Decimal('100')
    dividend_yield: Decimal = Decimal('0')
    
    # Market
    implied_vol: Optional[Decimal] = None
    
    def time_to_expiry(self, valuation_date: date = None) -> Decimal:
        """Time to expiration in years."""
        valuation_date = valuation_date or date.today()
        days = (self.expiration - valuation_date).days
        return Decimal(str(max(days, 0))) / Decimal('365.25')
    
    def is_expired(self, valuation_date: date = None) -> bool:
        valuation_date = valuation_date or date.today()
        return valuation_date >= self.expiration
    
    def intrinsic_value(self, spot: Decimal) -> Decimal:
        if self.option_type == OptionType.CALL:
            return max(spot - self.strike, Decimal('0'))
        else:
            return max(self.strike - spot, Decimal('0'))
    
    def moneyness(self, spot: Decimal) -> Decimal:
        return spot / self.strike if self.strike != 0 else Decimal('0')


@dataclass
class Greeks:
    """Option Greeks."""
    delta: Decimal = Decimal('0')
    gamma: Decimal = Decimal('0')
    vega: Decimal = Decimal('0')
    theta: Decimal = Decimal('0')
    rho: Decimal = Decimal('0')
    
    # Second order
    vanna: Decimal = Decimal('0')      # dDelta/dVol
    volga: Decimal = Decimal('0')      # dVega/dVol
    charm: Decimal = Decimal('0')      # dDelta/dTime
    speed: Decimal = Decimal('0')      # dGamma/dSpot
    color: Decimal = Decimal('0')      # dGamma/dTime
    
    def to_dict(self) -> Dict[str, float]:
        return {k: float(v) for k, v in self.__dict__.items()}


class BlackScholesMerton:
    """Black-Scholes-Merton option pricing model."""
    
    @staticmethod
    def d1(
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal
    ) -> Decimal:
        """Calculate d1 parameter."""
        S_f = float(S)
        K_f = float(K)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        
        if T_f <= 0 or sigma_f <= 0:
            return 0.0
        
        d1_val = (math.log(S_f / K_f) + (r_f - q_f + 0.5 * sigma_f**2) * T_f) / (sigma_f * math.sqrt(T_f))
        return Decimal(str(d1_val))
    
    @staticmethod
    def d2(d1: Decimal, sigma: Decimal, T: Decimal) -> Decimal:
        """Calculate d2 parameter."""
        return d1 - sigma * Decimal(str(math.sqrt(float(T))))
    
    @staticmethod
    def price(
        option_type: OptionType,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal
    ) -> Decimal:
        """Black-Scholes option price."""
        S_f = float(S)
        K_f = float(K)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        
        if T_f <= 0:
            # At expiration
            if option_type == OptionType.CALL:
                return max(Decimal(str(S_f - K_f)), Decimal('0'))
            else:
                return max(Decimal(str(K_f - S_f)), Decimal('0'))
        
        if sigma_f <= 0:
            # Zero volatility
            forward = S_f * math.exp((r_f - q_f) * T_f)
            if option_type == OptionType.CALL:
                return max(Decimal(str(forward - K_f)) * Decimal(str(math.exp(-r_f * T_f))), Decimal('0'))
            else:
                return max(Decimal(str(K_f - forward)) * Decimal(str(math.exp(-r_f * T_f))), Decimal('0'))
        
        d1_val = (math.log(S_f / K_f) + (r_f - q_f + 0.5 * sigma_f**2) * T_f) / (sigma_f * math.sqrt(T_f))
        d2_val = d1_val - sigma_f * math.sqrt(T_f)
        
        if option_type == OptionType.CALL:
            price = S_f * math.exp(-q_f * T_f) * stats.norm.cdf(d1_val) - K_f * math.exp(-r_f * T_f) * stats.norm.cdf(d2_val)
        else:
            price = K_f * math.exp(-r_f * T_f) * stats.norm.cdf(-d2_val) - S_f * math.exp(-q_f * T_f) * stats.norm.cdf(-d1_val)
        
        return Decimal(str(max(price, 0)))
    
    @staticmethod
    def greeks(
        option_type: OptionType,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal
    ) -> Greeks:
        """Calculate all Greeks."""
        S_f = float(S)
        K_f = float(K)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        
        if T_f <= 0 or sigma_f <= 0:
            # At expiration or zero vol
            intrinsic = max(S_f - K_f, 0) if option_type == OptionType.CALL else max(K_f - S_f, 0)
            delta = 1.0 if (option_type == OptionType.CALL and S_f > K_f) or (option_type == OptionType.PUT and S_f < K_f) else 0.0
            return Greeks(
                delta=Decimal(str(delta)),
                gamma=Decimal('0'),
                vega=Decimal('0'),
                theta=Decimal('0'),
                rho=Decimal('0')
            )
        
        d1_val = (math.log(S_f / K_f) + (r_f - q_f + 0.5 * sigma_f**2) * T_f) / (sigma_f * math.sqrt(T_f))
        d2_val = d1_val - sigma_f * math.sqrt(T_f)
        
        pdf_d1 = stats.norm.pdf(d1_val)
        cdf_d1 = stats.norm.cdf(d1_val)
        cdf_d2 = stats.norm.cdf(d2_val)
        cdf_neg_d1 = stats.norm.cdf(-d1_val)
        cdf_neg_d2 = stats.norm.cdf(-d2_val)
        
        sqrt_T = math.sqrt(T_f)
        exp_qT = math.exp(-q_f * T_f)
        exp_rT = math.exp(-r_f * T_f)
        
        # Delta
        if option_type == OptionType.CALL:
            delta = exp_qT * cdf_d1
        else:
            delta = exp_qT * (cdf_d1 - 1)
        
        # Gamma
        gamma = exp_qT * pdf_d1 / (S_f * sigma_f * sqrt_T)
        
        # Vega (per 1% vol change)
        vega = S_f * exp_qT * pdf_d1 * sqrt_T / 100
        
        # Theta (per day)
        if option_type == OptionType.CALL:
            theta = (-S_f * sigma_f * exp_qT * pdf_d1 / (2 * sqrt_T) 
                    - r_f * K_f * exp_rT * cdf_d2 
                    + q_f * S_f * exp_qT * cdf_d1) / 365
        else:
            theta = (-S_f * sigma_f * exp_qT * pdf_d1 / (2 * sqrt_T) 
                    + r_f * K_f * exp_rT * cdf_neg_d2 
                    - q_f * S_f * exp_qT * cdf_neg_d1) / 365
        
        # Rho (per 1% rate change)
        if option_type == OptionType.CALL:
            rho = K_f * T_f * exp_rT * cdf_d2 / 100
        else:
            rho = -K_f * T_f * exp_rT * cdf_neg_d2 / 100
        
        # Second order Greeks
        # Vanna = dDelta/dVol = dVega/dSpot
        vanna = -exp_qT * pdf_d1 * d2_val / sigma_f / 100
        
        # Volga = dVega/dVol
        volga = S_f * exp_qT * pdf_d1 * sqrt_T * d1_val * d2_val / sigma_f / 10000
        
        # Charm = dDelta/dTime
        if option_type == OptionType.CALL:
            charm = q_f * exp_qT * cdf_d1 - exp_qT * pdf_d1 * (2 * r_f - 2 * q_f + sigma_f**2) / (2 * sigma_f * sqrt_T)
        else:
            charm = -q_f * exp_qT * cdf_neg_d1 - exp_qT * pdf_d1 * (2 * r_f - 2 * q_f + sigma_f**2) / (2 * sigma_f * sqrt_T)
        charm = charm / 365
        
        return Greeks(
            delta=Decimal(str(delta)),
            gamma=Decimal(str(gamma)),
            vega=Decimal(str(vega)),
            theta=Decimal(str(theta)),
            rho=Decimal(str(rho)),
            vanna=Decimal(str(vanna)),
            volga=Decimal(str(volga)),
            charm=Decimal(str(charm))
        )
    
    @staticmethod
    def implied_vol(
        option_type: OptionType,
        market_price: Decimal,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal,
        initial_guess: Decimal = Decimal('0.2')
    ) -> Decimal:
        """Calculate implied volatility using Brent's method."""
        from scipy.optimize import brentq
        
        def price_diff(sigma):
            price = BlackScholesMerton.price(option_type, S, K, T, r, q, Decimal(str(sigma)))
            return float(price - market_price)
        
        try:
            iv = brentq(price_diff, 0.001, 5.0)
            return Decimal(str(iv))
        except ValueError:
            return Decimal('0')


class BinomialTree:
    """Binomial tree option pricing (Cox-Ross-Rubinstein)."""
    
    @staticmethod
    def price(
        option_type: OptionType,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal,
        steps: int = 100,
        american: bool = False
    ) -> Tuple[Decimal, Greeks]:
        """Price option using binomial tree."""
        S_f = float(S)
        K_f = float(K)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        
        dt = T_f / steps
        u = math.exp(sigma_f * math.sqrt(dt))
        d = 1 / u
        p = (math.exp((r_f - q_f) * dt) - d) / (u - d)
        disc = math.exp(-r_f * dt)
        
        # Initialize asset prices at maturity
        asset_prices = [S_f * (u ** (steps - i)) * (d ** i) for i in range(steps + 1)]
        
        # Initialize option values at maturity
        if option_type == OptionType.CALL:
            option_values = [max(price - K_f, 0) for price in asset_prices]
        else:
            option_values = [max(K_f - price, 0) for price in asset_prices]
        
        # Backward induction
        for step in range(steps - 1, -1, -1):
            for i in range(step + 1):
                option_values[i] = disc * (p * option_values[i] + (1 - p) * option_values[i + 1])
                
                if american:
                    # Check early exercise
                    spot = S_f * (u ** (step - i)) * (d ** i)
                    if option_type == OptionType.CALL:
                        exercise = max(spot - K_f, 0)
                    else:
                        exercise = max(K_f - spot, 0)
                    option_values[i] = max(option_values[i], exercise)
        
        price = Decimal(str(option_values[0]))
        
        # Calculate Greeks using finite differences
        # Simplified - would need more precise calculation
        greeks = Greeks(
            delta=Decimal('0'),
            gamma=Decimal('0'),
            vega=Decimal('0'),
            theta=Decimal('0'),
            rho=Decimal('0')
        )
        
        return price, greeks
    
    @staticmethod
    def implied_vol(
        option_type: OptionType,
        market_price: Decimal,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal,
        american: bool = False,
        steps: int = 100
    ) -> Decimal:
        """Implied volatility using binomial tree."""
        from scipy.optimize import brentq
        
        def price_diff(sigma):
            price, _ = BinomialTree.price(option_type, S, K, T, r, q, Decimal(str(sigma)), steps, american)
            return float(price - market_price)
        
        try:
            iv = brentq(price_diff, 0.001, 5.0)
            return Decimal(str(iv))
        except ValueError:
            return Decimal('0')


class MonteCarloPricer:
    """Monte Carlo option pricing for exotic options."""
    
    @staticmethod
    def asian_option(
        option_type: OptionType,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal,
        average_type: str = 'arithmetic',  # 'arithmetic' or 'geometric'
        n_paths: int = 50000,
        n_steps: int = 252
    ) -> Tuple[Decimal, Greeks]:
        """Price Asian option using Monte Carlo."""
        S_f = float(S)
        K_f = float(K)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        
        dt = T_f / n_steps
        drift = (r_f - q_f - 0.5 * sigma_f**2) * dt
        vol_sqrt_dt = sigma_f * math.sqrt(dt)
        
        payoffs = []
        
        for _ in range(n_paths):
            spot = S_f
            prices = []
            
            for _ in range(n_steps):
                z = np.random.randn()
                spot *= math.exp(drift + vol_sqrt_dt * z)
                prices.append(spot)
            
            if average_type == 'arithmetic':
                avg = np.mean(prices)
            else:
                avg = np.exp(np.mean(np.log(prices)))
            
            if option_type == OptionType.CALL:
                payoff = max(avg - K_f, 0)
            else:
                payoff = max(K_f - avg, 0)
            
            payoffs.append(payoff)
        
        price = np.mean(payoffs) * math.exp(-r_f * T_f)
        return Decimal(str(price)), Greeks()
    
    @staticmethod
    def barrier_option(
        option_type: OptionType,
        S: Decimal, K: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal,
        barrier: Decimal,
        barrier_type: str,  # 'up-and-out', 'down-and-out', 'up-and-in', 'down-and-in'
        n_paths: int = 50000,
        n_steps: int = 252
    ) -> Tuple[Decimal, Greeks]:
        """Price barrier option using Monte Carlo."""
        S_f = float(S)
        K_f = float(K)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        H_f = float(barrier)
        
        dt = T_f / n_steps
        drift = (r_f - q_f - 0.5 * sigma_f**2) * dt
        vol_sqrt_dt = sigma_f * math.sqrt(dt)
        
        payoffs = []
        
        for _ in range(n_paths):
            spot = S_f
            barrier_hit = False
            
            for _ in range(n_steps):
                z = np.random.randn()
                spot *= math.exp(drift + vol_sqrt_dt * z)
                
                if barrier_type.startswith('up'):
                    if spot >= H_f:
                        barrier_hit = True
                else:
                    if spot <= H_f:
                        barrier_hit = True
            
            if option_type == OptionType.CALL:
                payoff = max(spot - K_f, 0)
            else:
                payoff = max(K_f - spot, 0)
            
            # Apply barrier condition
            if 'out' in barrier_type:
                payoff = payoff if not barrier_hit else 0
            else:  # 'in'
                payoff = payoff if barrier_hit else 0
            
            payoffs.append(payoff)
        
        price = np.mean(payoffs) * math.exp(-r_f * T_f)
        return Decimal(str(price)), Greeks()
    
    @staticmethod
    def lookback_option(
        option_type: OptionType,
        S: Decimal, T: Decimal,
        r: Decimal, q: Decimal, sigma: Decimal,
        fixed_strike: bool = True,
        K: Decimal = None,
        n_paths: int = 50000,
        n_steps: int = 252
    ) -> Tuple[Decimal, Greeks]:
        """Price lookback option (floating or fixed strike)."""
        S_f = float(S)
        T_f = float(T)
        r_f = float(r)
        q_f = float(q)
        sigma_f = float(sigma)
        
        dt = T_f / n_steps
        drift = (r_f - q_f - 0.5 * sigma_f**2) * dt
        vol_sqrt_dt = sigma_f * math.sqrt(dt)
        
        payoffs = []
        
        for _ in range(n_paths):
            spot = S_f
            min_spot = S_f
            max_spot = S_f
            
            for _ in range(n_steps):
                z = np.random.randn()
                spot *= math.exp(drift + vol_sqrt_dt * z)
                min_spot = min(min_spot, spot)
                max_spot = max(max_spot, spot)
            
            if fixed_strike and K is not None:
                K_f = float(K)
                if option_type == OptionType.CALL:
                    payoff = max(max_spot - K_f, 0)
                else:
                    payoff = max(K_f - min_spot, 0)
            else:
                # Floating strike
                if option_type == OptionType.CALL:
                    payoff = max(spot - min_spot, 0)
                else:
                    payoff = max(max_spot - spot, 0)
            
            payoffs.append(payoff)
        
        price = np.mean(payoffs) * math.exp(-r_f * T_f)
        return Decimal(str(price)), Greeks()


class VolatilitySurface:
    """Volatility surface construction and interpolation."""
    
    def __init__(self):
        self.market_data: Dict[Tuple[float, float], float] = {}  # (strike, expiry) -> iv
    
    def add_quote(self, strike: float, expiry_days: float, iv: float):
        """Add market implied volatility quote."""
        self.market_data[(strike, expiry_days)] = iv
    
    def build_svi(self, expiry_days: float) -> Dict:
        """Build SVI parameterization for a given expiry.
        
        SVI: w(k) = a + b*(rho*(k-m) + sqrt((k-m)^2 + sigma^2))
        where k = log(K/F), w = sigma^2 * T
        """
        # Filter data for this expiry
        expiry_data = [(k, v) for (k, t), v in self.market_data.items() if abs(t - expiry_days) < 1]
        
        if len(expiry_data) < 5:
            return {}
        
        strikes = np.array([k for k, _ in expiry_data])
        ivs = np.array([v for _, v in expiry_data])
        log_moneyness = np.log(strikes / np.median(strikes))
        variances = ivs**2 * (expiry_days / 365.25)
        
        # Fit SVI parameters (simplified)
        from scipy.optimize import minimize
        
        def svi(params, k):
            a, b, rho, m, sigma = params
            return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))
        
        def objective(params):
            pred = svi(params, log_moneyness)
            return np.sum((pred - variances)**2)
        
        # Initial guess
        init = [np.mean(variances), 0.1, 0, 0, 0.1]
        bounds = [(0, None), (0, None), (-1, 1), (None, None), (0, None)]
        
        result = minimize(objective, init, bounds=bounds, method='L-BFGS-B')
        
        if result.success:
            a, b, rho, m, sigma = result.x
            return {
                'a': float(a), 'b': float(b), 'rho': float(rho),
                'm': float(m), 'sigma': float(sigma),
                'expiry_days': expiry_days
            }
        return {}
    
    def interpolate(self, strike: float, expiry_days: float) -> float:
        """Interpolate implied volatility."""
        # Simple bilinear interpolation
        expiries = sorted(set(t for _, t in self.market_data.keys()))
        strikes = sorted(set(k for k, _ in self.market_data.keys()))
        
        if not expiries or not strikes:
            return 0.2
        
        # Find surrounding expiries
        exp_low = max([e for e in expiries if e <= expiry_days], default=min(expiries))
        exp_high = min([e for e in expiries if e >= expiry_days], default=max(expiries))
        
        # Find surrounding strikes
        str_low = max([s for s in strikes if s <= strike], default=min(strikes))
        str_high = min([s for s in strikes if s >= strike], default=max(strikes))
        
        # Get four corner values
        def get_iv(k, e):
            return self.market_data.get((k, e), 0.2)
        
        v11 = get_iv(str_low, exp_low)
        v12 = get_iv(str_high, exp_low)
        v21 = get_iv(str_low, exp_high)
        v22 = get_iv(str_high, exp_high)
        
        # Bilinear interpolation
        if str_high == str_low:
            w_k = 0
        else:
            w_k = (strike - str_low) / (str_high - str_low)
        
        if exp_high == exp_low:
            w_t = 0
        else:
            w_t = (expiry_days - exp_low) / (exp_high - exp_low)
        
        v_low = v11 * (1 - w_k) + v12 * w_k
        v_high = v21 * (1 - w_k) + v22 * w_k
        
        return v_low * (1 - w_t) + v_high * w_t
    
    def get_vol_smile(self, expiry_days: float, strikes: List[float]) -> List[float]:
        """Get volatility smile for given expiry."""
        return [self.interpolate(k, expiry_days) for k in strikes]


def create_bsm_pricer() -> BlackScholesMerton:
    return BlackScholesMerton()

def create_binomial_pricer() -> BinomialTree:
    return BinomialTree()

def create_mc_pricer() -> MonteCarloPricer:
    return MonteCarloPricer()

def create_vol_surface() -> VolatilitySurface:
    return VolatilitySurface()