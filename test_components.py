import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

from erin.data_infra.storage.sqlite import get_sqlite_storage
from erin.data_infra.storage.duckdb import get_duckdb_storage
from erin.data_infra.storage.parquet import get_parquet_storage
from erin.market_intel.domain.instrument_master import instrument_master
from erin.market_intel.adapters.openbb import OpenBBProvider

sqlite = get_sqlite_storage()
print('✅ SQLite storage initialized')

duckdb = get_duckdb_storage()
print('✅ DuckDB storage initialized')

parquet = get_parquet_storage()
print('✅ Parquet storage initialized')

stats = instrument_master.get_stats()
print(f'Instrument Master: {stats["total_instruments"]} instruments')

from erin.market_intel.adapters.openbb import OpenBBProvider
openbb = OpenBBProvider()
print('✅ Provider adapters working')

print('✅ All core components working!')