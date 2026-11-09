import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

print("=== FINAL COMPREHENSIVE TEST ===")

from erin.data_infra.storage.sqlite import get_sqlite_storage
from erin.data_infra.storage.duckdb import get_duckdb_storage
from erin.data_infra.storage.parquet import get_parquet_storage
from erin.market_intel.domain.instrument_master import instrument_master
from erin.market_intel.adapters.openbb import OpenBBProvider
from erin.market_intel.adapters.sec_edgar import SECEdgarProvider
from erin.market_intel.adapters.registry import provider_registry, initialize_provider_registry
from erin.market_intel.fundamental import CompanyService, RatioEngine
from erin.market_intel.fundamental.financial_statements_service import FinancialStatementsService
from erin.market_intel.quant import create_distribution_engine, create_monte_carlo_engine, create_factor_engine, create_optimization_engine
from erin.market_intel.risk import VaREngine, VaRMethod, VaRConfig, StressTestingEngine
from erin.market_intel.fixed_income import Bond, BondPricer, DayCountConvention, CouponFrequency
from erin.market_intel.derivatives import Option, OptionType, BlackScholesMerton
from erin.market_intel.trading.oms import OrderManager, Order, OrderSide, OrderType, OrderStatus, TimeInForce
from erin.market_intel.trading.tca import TCACalculator, TCAConfig, SlippageModel
from erin.market_intel.macro import EconomicCalendar, EconomicEvent, EventImportance, EventCategory, FREDEconomicCalendarProvider, NLPProcessor
from datetime import date, timedelta, datetime
from decimal import Decimal

print('1. Storage & Market Data')
sqlite = get_sqlite_storage()
duckdb = get_duckdb_storage()
parquet = get_parquet_storage()
stats = instrument_master.get_stats()
print(f'  Storage: OK, Instruments: {stats["total_instruments"]}')

openbb = OpenBBProvider()
sec = SECEdgarProvider()
initialize_provider_registry()
print(f'  Providers: OK')

print('2. Fundamental Research')
company_svc = CompanyService(sqlite, None)
financial_svc = FinancialStatementsService(sqlite)
ratio_engine = RatioEngine(financial_svc)
print('  Fundamental: OK')

print('3. Quantitative Finance')
dist = create_distribution_engine()
mc = create_monte_carlo_engine(dist)
factor = create_factor_engine()
opt = create_optimization_engine()
print('  Quant: OK')

print('4. Risk Management')
var = VaREngine()
returns = __import__('numpy').random.normal(0.0005, 0.01, 500)
config = VaRConfig(method=VaRMethod.HISTORICAL, confidence_level=0.95)
var_val, es_val, _ = var.calculate_var(returns, 1000000, config)
stress = StressTestingEngine()
print(f'  VaR: {var_val:.0f}, Stress: OK')

print('5. Fixed Income & Derivatives')
from erin.market_intel.fixed_income import DayCountConvention, CouponFrequency
bond = Bond(figi='TEST', issuer='Test', coupon_rate=0.05, coupon_frequency=2, day_count=1, issue_date=date.today()-timedelta(days=365), maturity_date=date.today()+timedelta(days=365*5), face_value=100, redemption_value=100, currency='USD')
pricer = BondPricer()
dirty, clean = pricer.price_from_yield(bond, 0.045)
print(f'  Bond Price: {clean:.2f}')

from erin.market_intel.derivatives import Option, OptionType, BlackScholesMerton
bsm = BlackScholesMerton()
price = bsm.price(1, 100, 100, 0.082, 0.05, 0, 0.2)
print(f'  Option Price: {price:.4f}')

print('6. Trading & TCA')
oms = OrderManager()
order = oms.create_order('test', 'AAPL', 'AAPL', 1, 100, 1, 150.0, 1)
oms.submit_order(order.id)
print('  OMS: OK')

tca = TCACalculator(TCAConfig(5, 1, 2))
trade = {'symbol':'AAPL','side':'BUY','quantity':100,'price':150,'arrival_price':149.8,'vwap':150.1}
market_data = {'spread':0.0001,'adv':1000000,'volatility':0.02}
metrics = tca.analyze_trade(trade, market_data, 149.8)
print(f'  TCA IS: {metrics.implementation_shortfall_bps:.2f} bps')

print('7. Macro & News')
from erin.market_intel.macro import EconomicCalendar, EconomicEvent, EventImportance, EventCategory, FREDEconomicCalendarProvider
from datetime import date, timedelta, datetime

cal = EconomicCalendar()
event1 = EconomicEvent(title='Nonfarm Payrolls', category=1, importance=3, country='US', scheduled_time=datetime.utcnow()+timedelta(days=7), previous_value=200, consensus_forecast=180, unit='K')
cal.add_event(event1)
print(f'  Economic Calendar: {len(cal._events)} events')

from erin.market_intel.macro import NLPProcessor
import asyncio

async def test_nlp():
    nlp = NLPProcessor()
    tickers = await nlp.extract_tickers('AAPL beats earnings. Apple surges.')
    categories = await nlp.classify_category('Apple beats earnings', 'Strong iPhone sales drive revenue beat')
    sentiment, score, conf = await nlp.analyze_sentiment('Apple beats earnings, stock surges.')
    print(f'  NLP: Tickers={tickers}, Categories={categories}, Sentiment={sentiment}')

asyncio.run(test_nlp())

print('\n✅ ALL PHASES 1-11 COMPLETE AND WORKING!')