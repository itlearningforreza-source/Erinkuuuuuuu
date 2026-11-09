"""Data Ingestion Pipeline - Scheduled, incremental, idempotent data ingestion."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, AsyncIterator
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.market_intel.domain.interfaces import (
        MarketDataProvider,
        ProviderId,
        InstrumentId,
        Quote,
        Bar,
    )

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobPriority(int, Enum):
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class IngestionJob:
    """Represents a data ingestion job."""
    id: str
    provider: str
    dataset: str
    params: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    watermark: Optional[str] = None  # For incremental loads
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Retry policy
    max_retries: int = 3
    retry_count: int = 0
    last_error: Optional[str] = None


class IngestionPipeline:
    """Orchestrates data ingestion from providers with scheduling and monitoring."""
    
    def __init__(
        self,
        provider_registry,
        storage_backend,
        max_concurrent_jobs: int = 2,
        default_retry_count: int = 3
    ):
        self.provider_registry = provider_registry
        self.storage = storage_backend
        self.max_concurrent_jobs = max_concurrent_jobs
        self.default_retry_count = default_retry_count
        
        self._jobs: Dict[str, IngestionJob] = {}
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._job_counter = 0
    
    async def start(self):
        """Start the ingestion pipeline scheduler."""
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Ingestion pipeline started")
    
    async def stop(self):
        """Stop the ingestion pipeline gracefully."""
        self._running = False
        
        # Cancel running jobs
        for task in self._running_jobs.values():
            task.cancel()
        
        # Wait for running jobs to complete
        if self._running_jobs:
            await asyncio.gather(*self._running_jobs.values(), return_exceptions=True)
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Ingestion pipeline stopped")
    
    async def submit_job(
        self,
        provider: str,
        dataset: str,
        params: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        watermark: Optional[str] = None
    ) -> str:
        """Submit a new ingestion job."""
        job_id = f"job_{int(datetime.utcnow().timestamp())}_{id(self)}"
        
        job = IngestionJob(
            id=job_id,
            provider=provider,
            dataset=dataset,
            params=params,
            priority=priority,
            watermark=watermark,
            max_retries=3
        )
        
        self._jobs[job_id] = job
        logger.info(f"Submitted ingestion job: {job_id} (provider={provider}, dataset={dataset})")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[IngestionJob]:
        """Get job status by ID."""
        return self._jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.status == JobStatus.RUNNING:
            task = self._running_jobs.get(job.id)
            if task:
                task.cancel()
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        return True
    
    async def _scheduler_loop(self):
        """Main scheduler loop - processes pending jobs."""
        while True:
            try:
                await self._process_pending_jobs()
                await asyncio.sleep(5)  # Check every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)
    
    async def _process_pending_jobs(self):
        """Process pending jobs up to concurrency limit."""
        # Get pending jobs sorted by priority
        pending = [
            job for job in self._jobs.values()
            if job.status == JobStatus.PENDING
        ]
        
        pending.sort(key=lambda j: (-j.priority, j.created_at))
        
        for job in pending:
            if len(self._running_jobs) >= self.max_concurrent_jobs:
                break
            
            # Start job
            task = asyncio.create_task(self._execute_job(job))
            self._running_jobs[job.id] = task
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Add completion callback
            task.add_done_callback(lambda t, jid=job.id: self._job_done(jid, t))
    
    def _job_done(self, job_id: str, task: asyncio.Task):
        """Callback when job completes."""
        self._running_jobs.pop(job_id, None)
        
        job = self._jobs.get(job_id)
        if job:
            if task.cancelled():
                job.status = JobStatus.CANCELLED
            elif task.exception():
                job.status = JobStatus.FAILED
                job.error_message = str(task.exception())
            else:
                job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
    
    async def _execute_job(self, job: IngestionJob):
        """Execute a single ingestion job with retries."""
        provider = self.provider_registry.get(job.provider)
        if not provider:
            job.status = JobStatus.FAILED
            job.error_message = f"Provider not found: {job.provider}"
            return
        
        attempt = 0
        while attempt <= job.max_retries:
            try:
                job.retry_count = attempt
                await self._run_ingestion(job, provider)
                job.status = JobStatus.COMPLETED
                return
            except Exception as e:
                attempt += 1
                job.last_error = str(e)
                logger.warning(f"Job {job.id} attempt {attempt} failed: {e}")
                
                if attempt <= job.max_retries:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        job.status = JobStatus.FAILED
        job.error_message = f"Failed after {job.max_retries} retries: {job.last_error}"
    
    async def _run_ingestion(self, job: IngestionJob, provider):
        """Execute the actual data ingestion."""
        dataset = job.dataset
        params = job.params
        
        # Route to appropriate ingestion method based on dataset
        if dataset == "quotes":
            await self._ingest_quotes(job, provider)
        elif dataset == "historical":
            await self._ingest_historical(job, provider)
        elif dataset == "fundamentals":
            await self._ingest_fundamentals(job, provider)
        elif dataset == "options":
            await self._ingest_options(job, provider)
        elif dataset == "news":
            await self._ingest_news(job, provider)
        elif dataset == "macro":
            await self._ingest_macro(job, provider)
        else:
            raise ValueError(f"Unknown dataset: {dataset}")
    
    async def _ingest_quotes(self, job: IngestionJob, provider):
        """Ingest real-time quotes."""
        symbols = job.params.get("symbols", [])
        if not symbols:
            raise ValueError("No symbols provided for quotes ingestion")
        
        quotes = await provider.get_quotes(symbols)
        
        # Store quotes in storage
        for symbol, quote in quotes.items():
            await self.storage.store_quote(quote)
            job.records_processed += 1
        
        job.records_processed = len(quotes)
    
    async def _ingest_historical(self, job: IngestionJob, provider):
        """Ingest historical price data."""
        symbols = job.params.get("symbols", [])
        start = job.params.get("start")
        end = job.params.get("end")
        frequency = job.params.get("frequency", "1d")
        adjustment = job.params.get("adjustment", "none")
        
        for symbol in symbols:
            try:
                bars = await provider.get_history(symbol, start, end)
                
                # Store in DuckDB/Parquet
                for bar in bars:
                    await self.storage.store_bar(bar)
                    job.records_processed += 1
                    
            except Exception as e:
                logger.error(f"Failed to ingest historical for {symbol}: {e}")
                job.records_failed += 1
    
    async def _ingest_fundamentals(self, job: IngestionJob, provider):
        """Ingest fundamental data."""
        # Implementation depends on provider capabilities
        pass
    
    async def _ingest_options(self, job: IngestionJob, provider):
        """Ingest options data."""
        pass
    
    async def _ingest_news(self, job: IngestionJob, provider):
        """Ingest news articles."""
        pass
    
    async def _ingest_macro(self, job: IngestionJob, provider):
        """Ingest macroeconomic data."""
        pass
    
    def get_job_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        status_counts = {}
        for job in self._jobs.values():
            status_counts[job.status.value] = status_counts.get(job.status.value, 0) + 1
        
        return {
            "total_jobs": len(self._jobs),
            "running_jobs": len(self._running_jobs),
            "by_status": status_counts,
            "max_concurrent": self.max_concurrent_jobs,
        }


# Watermark management for incremental loads
class WatermarkManager:
    """Manages watermarks for incremental data loads."""
    
    def __init__(self, storage):
        self.storage = storage
    
    async def get_watermark(self, provider: str, dataset: str, key: str) -> Optional[str]:
        """Get the last processed watermark."""
        key = f"watermark:{provider}:{dataset}:{key}"
        return await self.storage.get(key)
    
    async def set_watermark(self, provider: str, dataset: str, key: str, value: str):
        """Set a new watermark."""
        key = f"watermark:{provider}:{dataset}:{key}"
        await self.storage.set(key, value)
    
    async def advance_watermark(
        self,
        provider: str,
        dataset: str,
        key: str,
        new_value: str,
        compare_func: Callable[[str, str], bool] = lambda new, old: new > old
    ) -> bool:
        """Advance watermark if new value is greater."""
        current = await self.get_watermark(provider, dataset, key)
        
        if current is None or compare_func(new_value, current):
            await self.set_watermark(provider, dataset, key, new_value)
            return True
        return False