"""Ingestion Scheduler - Cron-like scheduler for recurring ingestion jobs."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.data_infra.ingestion.pipeline import IngestionPipeline, IngestionJob, JobPriority

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"


@dataclass
class Schedule:
    """Job schedule definition."""
    job_id: str
    schedule_type: ScheduleType
    cron_expression: Optional[str] = None  # For cron schedules
    interval_seconds: Optional[int] = None  # For interval schedules
    run_once_at: Optional[datetime] = None  # For one-time schedules
    timezone: str = "UTC"
    enabled: bool = True
    max_runs: Optional[int] = None
    run_count: int = 0
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    job_params: Dict[str, Any] = field(default_factory=dict)
    job_priority: int = 0


class Scheduler:
    """Cron-like scheduler for recurring ingestion jobs."""
    
    def __init__(self, pipeline: 'IngestionPipeline'):
        self.pipeline = pipeline
        self.schedules: Dict[str, Schedule] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._check_interval = 30  # Check every 30 seconds
    
    def add_schedule(
        self,
        schedule_id: str,
        provider: str,
        dataset: str,
        params: Dict[str, Any],
        cron: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_once_at: Optional[datetime] = None,
        priority: int = 0,
        timezone: str = "UTC",
        max_runs: Optional[int] = None,
        job_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a new schedule."""
        
        if cron:
            schedule_type = ScheduleType.CRON
            next_run = self._calculate_next_cron(cron, timezone)
        elif interval_seconds:
            schedule_type = ScheduleType.INTERVAL
            next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)
        elif run_once_at:
            schedule_type = ScheduleType.ONCE
            next_run = run_once_at
        else:
            raise ValueError("Must specify cron, interval_seconds, or run_once_at")
        
        schedule = Schedule(
            job_id=schedule_id,
            schedule_type=schedule_type,
            cron_expression=cron,
            interval_seconds=interval_seconds,
            run_once_at=run_once_at,
            timezone=timezone,
            enabled=True,
            max_runs=max_runs,
            job_params={
                "provider": provider,
                "dataset": dataset,
                "params": params,
                "priority": priority
            },
            next_run=next_run
        )
        
        self.schedules[schedule_id] = schedule
        logger.info(f"Added schedule {schedule_id}: {schedule_type.value} - next run: {next_run}")
        return schedule_id
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            return True
        return False
    
    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = True
            return True
        return False
    
    def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = False
            return True
        return False
    
    async def start(self):
        """Start the scheduler."""
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_schedules()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)
    
    async def _check_schedules(self):
        """Check all schedules and trigger due jobs."""
        now = datetime.utcnow()
        
        for schedule_id, schedule in self.schedules.items():
            if not schedule.enabled:
                continue
            
            if schedule.max_runs and schedule.run_count >= schedule.max_runs:
                self.disable_schedule(schedule_id)
                continue
            
            if schedule.next_run and now >= schedule.next_run:
                await self._trigger_schedule(schedule)
    
    async def _trigger_schedule(self, schedule: Schedule):
        """Trigger a scheduled job."""
        try:
            job_id = await self.pipeline.submit_job(
                provider=schedule.job_params["provider"],
                dataset=schedule.job_params["dataset"],
                params=schedule.job_params["params"],
                priority=schedule.job_params.get("priority", 0)
            )
            
            schedule.last_run = datetime.utcnow()
            schedule.run_count += 1
            
            # Calculate next run
            if schedule.schedule_type == ScheduleType.CRON:
                schedule.next_run = self._calculate_next_cron(
                    schedule.cron_expression, schedule.timezone
                )
            elif schedule.schedule_type == ScheduleType.INTERVAL:
                schedule.next_run = datetime.utcnow() + timedelta(seconds=schedule.interval_seconds)
            elif schedule.schedule_type == ScheduleType.ONCE:
                schedule.enabled = False
                schedule.next_run = None
            
            logger.info(f"Triggered scheduled job {schedule.job_id} from schedule {schedule}")
            
        except Exception as e:
            logger.error(f"Failed to trigger schedule {schedule}: {e}")
    
    def _calculate_next_cron(self, cron_expr: str, timezone: str) -> datetime:
        """Calculate next run time from cron expression."""
        # Simplified cron parsing - in production use croniter
        # For now, return next minute
        return datetime.utcnow() + timedelta(minutes=1)
    
    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get schedule by ID."""
        return self.schedules.get(schedule_id)
    
    def list_schedules(self) -> List[Schedule]:
        """List all schedules."""
        return list(self.schedules.values())
    
    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = True
            return True
        return False
    
    def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = False
            return True
        return False
    
    def get_schedule_status(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule status."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
        
        return {
            "schedule_id": schedule_id,
            "type": schedule.schedule_type.value,
            "enabled": schedule.enabled,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "last_run": schedule.last_run.isoformat() if schedule.last_run else None,
            "run_count": schedule.run_count,
            "max_runs": schedule.max_runs,
        }


# Factory function
def create_scheduler(pipeline: 'IngestionPipeline') -> Scheduler:
    """Create a scheduler for the ingestion pipeline."""
    return Scheduler(pipeline)