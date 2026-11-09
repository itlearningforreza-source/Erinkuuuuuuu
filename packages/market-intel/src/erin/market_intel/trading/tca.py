"""Transaction Cost Analysis - Slippage, market impact, and execution quality."""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from typing import TYPE_CHECKING
import scipy.stats as stats

if TYPE_CHECKING:
    from erin.market_intel.trading.backtest import Trade


class SlippageModel(str, Enum):
    FIXED_BPS = "FIXED_BPS"
    VOLUME_WEIGHTED = "VOLUME_WEIGHTED"
    SQUARE_ROOT = "SQUARE_ROOT"      # Almgren-Chriss square root model
    ALMGREN_CHRISS = "ALMGREN_CHRISS"
    MARKET_IMPACT = "MARKET_IMPACT"


@dataclass
class TCAConfig:
    """TCA configuration."""
    commission_bps: Decimal = Decimal('5')
    slippage_model: SlippageModel = SlippageModel.FIXED_BPS
    fixed_slippage_bps: Decimal = Decimal('2')
    
    # Market impact parameters
    participation_rate: Decimal = Decimal('0.10')  # 10% of volume
    volatility_window: int = 20
    adv_window: int = 20  # Average daily volume window
    
    # Almgren-Chriss parameters
    permanent_impact_factor: Decimal = Decimal('0.5')
    temporary_impact_factor: Decimal = Decimal('1.0')
    risk_aversion: Decimal = Decimal('1e-6')
    
    # Benchmark prices
    use_vwap: bool = True
    use_arrival: bool = True
    use_twap: bool = False


@dataclass
class ExecutionMetrics:
    """Execution quality metrics for a single trade."""
    
    # Trade details
    symbol: str
    side: str
    quantity: Decimal
    arrival_price: Decimal
    execution_price: Decimal
    vwap_price: Optional[Decimal] = None
    twap_price: Optional[Decimal] = None
    
    # Costs
    commission: Decimal = Decimal('0')
    spread_cost: Decimal = Decimal('0')
    market_impact: Decimal = Decimal('0')
    timing_cost: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    
    # Metrics
    slippage_bps: Decimal = Decimal('0')
    implementation_shortfall_bps: Decimal = Decimal('0')
    
    # Volume metrics
    participation_rate: Decimal = Decimal('0')
    volume_adv: Decimal = Decimal('0')
    
    # Timing
    order_time: datetime = field(default_factory=datetime.utcnow)
    completion_time: Optional[datetime] = None
    duration_seconds: int = 0
    
    def calculate_metrics(self, arrival_price: Decimal, vwap: Decimal = None):
        """Calculate all execution metrics."""
        # Convert to Decimal if passed as float
        if not isinstance(arrival_price, Decimal):
            arrival_price = Decimal(str(arrival_price))
        if vwap is not None and not isinstance(vwap, Decimal):
            vwap = Decimal(str(vwap))
        
        if self.arrival_price == 0:
            return
        
        # Implementation Shortfall (IS)
        if self.side == 'BUY':
            is_bps = (self.execution_price - self.arrival_price) / self.arrival_price * Decimal('10000')
        else:
            is_bps = (self.arrival_price - self.execution_price) / self.arrival_price * Decimal('10000')
        
        self.implementation_shortfall_bps = is_bps
        
        # Slippage vs arrival
        if self.side == 'BUY':
            slippage = (self.execution_price - self.arrival_price) / self.arrival_price * Decimal('10000')
        else:
            slippage = (self.arrival_price - self.execution_price) / self.arrival_price * Decimal('10000')
        
        self.slippage_bps = slippage
        
        # VWAP slippage
        if vwap:
            if self.side == 'BUY':
                vwap_slip = (self.execution_price - vwap) / vwap * Decimal('10000')
            else:
                vwap_slip = (vwap - self.execution_price) / vwap * Decimal('10000')
            self.timing_cost = vwap_slip - self.slippage_bps


@dataclass
class OrderTCA:
    """TCA for a complete order (may have multiple fills)."""
    
    order_id: str
    symbol: str
    side: str
    total_quantity: Decimal
    fills: List[Dict] = field(default_factory=list)
    
    # Aggregate metrics
    vwap_price: Optional[Decimal] = None
    twap_price: Optional[Decimal] = None
    arrival_price: Optional[Decimal] = None
    
    total_commission: Decimal = Decimal('0')
    total_slippage: Decimal = Decimal('0')
    total_market_impact: Decimal = Decimal('0')
    implementation_shortfall: Decimal = Decimal('0')
    
    def add_fill(self, fill: Dict):
        self.fills.append(fill)
    
    def calculate_vwap(self):
        """Calculate volume-weighted average price."""
        if not self.fills:
            return
        
        total_qty = Decimal('0')
        total_notional = Decimal('0')
        
        for fill in self.fills:
            qty = Decimal(str(fill['quantity']))
            price = Decimal(str(fill['price']))
            total_qty += qty
            total_notional += qty * price
        
        if total_qty > 0:
            self.vwap_price = total_notional / total_qty
    
    def calculate_twap(self):
        """Calculate time-weighted average price."""
        if not self.fills:
            return
        
        prices = [Decimal(str(f['price'])) for f in self.fills]
        self.twap_price = sum(prices) / len(prices)
    
    def aggregate_metrics(self):
        """Aggregate fill-level metrics."""
        if not self.fills:
            return
        
        self.total_commission = sum(Decimal(str(f.get('commission', 0))) for f in self.fills)
        
        # Calculate VWAP slippage
        self.calculate_vwap()
        self.calculate_twap()
        
        # Aggregate slippage
        total_slippage = sum(Decimal(str(f.get('slippage', 0))) for f in self.fills)
        self.total_slippage = total_slippage


class MarketImpactModel:
    """Market impact models for TCA."""
    
    @staticmethod
    def fixed_bps(quantity: Decimal, price: Decimal, bps: Decimal) -> Decimal:
        """Fixed basis points slippage."""
        notional = quantity * price
        return notional * (bps / Decimal('10000'))
    
    @staticmethod
    def square_root_model(
        quantity: Decimal,
        price: Decimal,
        adv: Decimal,
        volatility: Decimal,
        participation: Decimal = Decimal('0.1')
    ) -> Decimal:
        """Square root market impact model (Almgren-Chriss approximation).
        
        Impact = sigma * sqrt(Q/ADV) * price
        """
        if adv <= 0:
            return Decimal('0')
        
        qty = float(quantity)
        adv_f = float(adv)
        vol = float(volatility)
        part = float(participation)
        
        # Square root impact
        impact_bps = vol * math.sqrt(qty / adv_f) * 10000 * math.sqrt(part)
        
        notional = float(quantity) * float(price)
        return Decimal(str(notional * impact_bps / 10000))
    
    @staticmethod
    def almgren_chriss(
        quantity: Decimal,
        price: Decimal,
        adv: Decimal,
        volatility: Decimal,
        sigma: Decimal,        # Daily volatility
        eta: Decimal,          # Temporary impact coefficient
        gamma: Decimal,        # Permanent impact coefficient
        risk_aversion: Decimal = Decimal('1e-6'),
        time_horizon: int = 1  # Days
    ) -> Tuple[Decimal, Decimal]:
        """Almgren-Chriss optimal execution.
        
        Returns: (temporary_impact, permanent_impact)
        """
        qty = float(quantity)
        adv_f = float(adv)
        vol = float(volatility)
        sigma_f = float(sigma)
        eta_f = float(eta)
        gamma_f = float(gamma)
        lambda_f = float(risk_aversion)
        T = float(time_horizon)
        
        if adv_f <= 0 or sigma_f <= 0:
            return Decimal('0'), Decimal('0')
        
        # Optimal trading rate
        kappa = math.sqrt(gamma_f * sigma_f**2 / eta_f)
        
        # Temporary impact cost
        temp_impact = eta_f * qty**2 / (2 * T) * (1 + 1 / (kappa * T))
        
        # Permanent impact cost
        perm_impact = gamma_f * qty**2 / (2 * T)
        
        total_impact = temp_impact + perm_impact
        notional = float(quantity) * float(adv)  # Approximate
        
        return (
            Decimal(str(temp_impact / notional * 10000)),
            Decimal(str(perm_impact / notional * 10000))
        )
    
    @staticmethod
    def linear_slippage(
        quantity: Decimal,
        price: Decimal,
        spread: Decimal,
        participation: Decimal = Decimal('0.1')
    ) -> Decimal:
        """Linear slippage model: half spread + participation impact."""
        notional = quantity * price
        spread_cost = notional * (spread / price) / Decimal('2')
        participation_cost = notional * participation * Decimal('0.0001')
        return spread_cost + participation_cost


class TCACalculator:
    """Main TCA calculator."""
    
    def __init__(self, config: TCAConfig):
        self.config = config
    
    def analyze_trade(
        self,
        trade: Dict,
        market_data: Dict,
        arrival_price: Optional[Decimal] = None
    ) -> ExecutionMetrics:
        """Analyze a single trade."""
        
        # Convert arrival_price to Decimal if provided
        if arrival_price is not None and not isinstance(arrival_price, Decimal):
            arrival_price = Decimal(str(arrival_price))
        
        metrics = ExecutionMetrics(
            symbol=trade['symbol'],
            side=trade['side'],
            quantity=Decimal(str(trade['quantity'])),
            arrival_price=arrival_price or Decimal(str(trade.get('arrival_price', trade['price']))),
            execution_price=Decimal(str(trade['price'])),
            vwap_price=Decimal(str(trade['vwap'])) if trade.get('vwap') else None,
        )
        
        # Calculate commission
        notional = metrics.quantity * metrics.execution_price
        metrics.commission = max(
            notional * (self.config.commission_bps / Decimal('10000')),
            Decimal('1.00')
        )
        
        # Calculate market impact
        metrics.market_impact = self._estimate_market_impact(trade, market_data)
        
        # Calculate spread cost
        spread = Decimal(str(market_data.get('spread', 0)))
        metrics.spread_cost = metrics.quantity * metrics.execution_price * spread
        
        # Total cost
        metrics.total_cost = metrics.commission + metrics.spread_cost + metrics.market_impact
        
        # Calculate metrics
        if arrival_price:
            metrics.calculate_metrics(arrival_price, metrics.vwap_price)
        
        return metrics
    
    def _estimate_market_impact(self, trade: Dict, market_data: Dict) -> Decimal:
        """Estimate market impact using configured model."""
        
        qty = Decimal(str(trade['quantity']))
        price = Decimal(str(trade['price']))
        adv = Decimal(str(market_data.get('adv', 1000000)))
        volatility = Decimal(str(market_data.get('volatility', 0.02)))
        spread = Decimal(str(market_data.get('spread', 0.0001)))
        
        if self.config.slippage_model == SlippageModel.FIXED_BPS:
            return MarketImpactModel.fixed_bps(qty, price, self.config.fixed_slippage_bps)
        
        elif self.config.slippage_model == SlippageModel.SQUARE_ROOT:
            return MarketImpactModel.square_root_model(
                qty, price, adv, volatility, self.config.participation_rate
            )
        
        elif self.config.slippage_model == SlippageModel.ALMGREN_CHRISS:
            temp, perm = MarketImpactModel.almgren_chriss(
                qty, price, adv, volatility,
                Decimal(str(math.sqrt(252))),  # Annualized to daily
                self.config.temporary_impact_factor,
                self.config.permanent_impact_factor,
                self.config.risk_aversion
            )
            return temp + perm
        
        elif self.config.slippage_model == SlippageModel.MARKET_IMPACT:
            return MarketImpactModel.linear_slippage(
                qty, price, spread, self.config.participation_rate
            )
        
        return Decimal('0')
    
    def analyze_order(self, order_fills: List[Dict], market_data: Dict) -> OrderTCA:
        """Analyze complete order with multiple fills."""
        
        tca = OrderTCA(
            order_id=order_fills[0].get('order_id', ''),
            symbol=order_fills[0]['symbol'],
            side=order_fills[0]['side'],
            total_quantity=sum(Decimal(str(f['quantity'])) for f in order_fills)
        )
        
        for fill in order_fills:
            tca.add_fill(fill)
        
        tca.calculate_vwap()
        tca.calculate_twap()
        tca.aggregate_metrics()
        
        # Calculate arrival price (first fill or market open)
        if tca.fills:
            tca.arrival_price = Decimal(str(tca.fills[0].get('arrival_price', tca.fills[0]['price'])))
        
        # Calculate implementation shortfall
        if tca.arrival_price and tca.vwap_price:
            if tca.side == 'BUY':
                is_bps = (tca.vwap_price - tca.arrival_price) / tca.arrival_price * Decimal('10000')
            else:
                is_bps = (tca.arrival_price - tca.vwap_price) / tca.arrival_price * Decimal('10000')
            tca.implementation_shortfall = is_bps
        
        return tca
    
    def portfolio_tca(self, trades: List[Dict], market_data: Dict) -> Dict:
        """Portfolio-level TCA analysis."""
        
        results = {
            'by_symbol': {},
            'by_side': {'BUY': [], 'SELL': []},
            'total': {
                'commission': Decimal('0'),
                'slippage': Decimal('0'),
                'market_impact': Decimal('0'),
                'spread_cost': Decimal('0'),
                'total_cost': Decimal('0'),
                'implementation_shortfall_bps': Decimal('0'),
            }
        }
        
        all_metrics = []
        
        for trade in trades:
            # Get market data for this trade
            symbol_md = market_data.get(trade['symbol'], {})
            metrics = self.analyze_trade(trade, symbol_md)
            all_metrics.append(metrics)
            
            # Aggregate by symbol
            sym = trade['symbol']
            if sym not in results['by_symbol']:
                results['by_symbol'][sym] = {
                    'commission': Decimal('0'),
                    'slippage': Decimal('0'),
                    'market_impact': Decimal('0'),
                    'count': 0,
                    'total_quantity': Decimal('0'),
                }
            
            results['by_symbol'][sym]['commission'] += metrics.commission
            results['by_symbol'][sym]['slippage'] += metrics.slippage_bps
            results['by_symbol'][sym]['market_impact'] += metrics.market_impact
            results['by_symbol'][sym]['count'] += 1
            results['by_symbol'][sym]['total_quantity'] += metrics.quantity
            
            # By side
            results['by_side'][trade['side']].append(metrics)
            
            # Total
            results['total']['commission'] += metrics.commission
            results['total']['slippage'] += metrics.slippage_bps
            results['total']['market_impact'] += metrics.market_impact
            results['total']['spread_cost'] += metrics.spread_cost
            results['total']['total_cost'] += metrics.total_cost
        
        # Average implementation shortfall
        if all_metrics:
            results['total']['implementation_shortfall_bps'] = sum(
                m.implementation_shortfall_bps for m in all_metrics
            ) / len(all_metrics)
        
        return results


class PerformanceAttribution:
    """Trade performance attribution."""
    
    @staticmethod
    def attribute(
        trades: List['Trade'],
        benchmark_returns: Dict[str, Decimal],
        factor_returns: Dict[str, Decimal] = None
    ) -> Dict:
        """Attribute trade performance to factors."""
        
        results = {
            'selection_effect': Decimal('0'),
            'allocation_effect': Decimal('0'),
            'interaction_effect': Decimal('0'),
            'total_active_return': Decimal('0'),
            'by_symbol': {},
        }
        
        for trade in trades:
            symbol = trade.symbol
            bench_return = benchmark_returns.get(symbol, Decimal('0'))
            
            # Trade return
            if trade.side == 'BUY':
                trade_return = -trade.slippage  # Negative cost
            else:
                trade_return = -trade.slippage  # Negative cost
            
            active_return = trade_return - bench_return
            
            if symbol not in results['by_symbol']:
                results['by_symbol'][symbol] = {
                    'trades': 0,
                    'active_return': Decimal('0'),
                    'benchmark_return': bench_return,
                }
            
            results['by_symbol'][symbol]['trades'] += 1
            results['by_symbol'][symbol]['active_return'] += active_return
        
        results['total_active_return'] = sum(
            s['active_return'] for s in results['by_symbol'].values()
        )
        
        return results


def create_tca_config(
    commission_bps: Decimal = Decimal('5'),
    slippage_model: SlippageModel = SlippageModel.FIXED_BPS,
    **kwargs
) -> TCAConfig:
    return TCAConfig(
        commission_bps=commission_bps,
        slippage_model=slippage_model,
        **kwargs
    )


def create_tca_calculator(config: TCAConfig) -> TCACalculator:
    return TCACalculator(config)


def create_market_impact_model() -> MarketImpactModel:
    return MarketImpactModel()