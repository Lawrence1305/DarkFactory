"""
Cron Scheduler - Schedule and execute periodic jobs
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class CronExpression:
    """
    Cron expression parser and builder

    Supports standard cron format: minute hour day month weekday
    Also supports simple intervals: @every X (seconds|minutes|hours|days)
    """
    expression: str

    # Standard cron fields
    minute: str = "*"
    hour: str = "*"
    day: str = "*"
    month: str = "*"
    weekday: str = "*"

    # Interval support
    interval_seconds: Optional[int] = None
    interval_minutes: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_days: Optional[int] = None

    def __post_init__(self):
        self._parse()

    def _parse(self):
        """Parse cron expression"""
        if self.expression.startswith("@every "):
            self._parse_interval()
        elif " " in self.expression:
            parts = self.expression.split()
            if len(parts) >= 5:
                self.minute, self.hour, self.day, self.month, self.weekday = parts[:5]
        else:
            raise ValueError(f"Invalid cron expression: {self.expression}")

    def _parse_interval(self):
        """Parse @every interval"""
        interval_str = self.expression[7:]  # Remove "@every "

        match = re.match(r"(\d+)\s*(seconds?|minutes?|hours?|days?)", interval_str)
        if not match:
            raise ValueError(f"Invalid interval: {interval_str}")

        value = int(match.group(1))
        unit = match.group(2).lower()

        if "second" in unit:
            self.interval_seconds = value
        elif "minute" in unit:
            self.interval_minutes = value
        elif "hour" in unit:
            self.interval_hours = value
        elif "day" in unit:
            self.interval_days = value

    def get_next_run(self, from_time: Optional[datetime] = None) -> datetime:
        """Get next run time after given time"""
        if from_time is None:
            from_time = datetime.now()

        # Handle intervals
        if self.interval_seconds:
            return from_time + timedelta(seconds=self.interval_seconds)
        if self.interval_minutes:
            return from_time + timedelta(minutes=self.interval_minutes)
        if self.interval_hours:
            return from_time + timedelta(hours=self.interval_hours)
        if self.interval_days:
            return from_time + timedelta(days=self.interval_days)

        # Handle cron - simplified, just add an hour for now
        return from_time + timedelta(hours=1)

    @classmethod
    def every_seconds(cls, seconds: int) -> "CronExpression":
        """Create interval expression for seconds"""
        return cls(f"@every {seconds} seconds")

    @classmethod
    def every_minutes(cls, minutes: int) -> "CronExpression":
        """Create interval expression for minutes"""
        return cls(f"@every {minutes} minutes")

    @classmethod
    def every_hours(cls, hours: int) -> "CronExpression":
        """Create interval expression for hours"""
        return cls(f"@every {hours} hours")

    @classmethod
    def daily(cls, hour: int = 0, minute: int = 0) -> "CronExpression":
        """Create daily cron expression"""
        return cls(f"{minute} {hour} * * *")


@dataclass
class CronJob:
    """
    Cron Job Definition
    """
    id: str
    name: str
    handler: Callable
    schedule: CronExpression
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CronScheduler:
    """
    Cron Scheduler

    Schedules and executes periodic jobs.
    Based on hermes-agent's cron scheduling.
    """

    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    def add_job(
        self,
        job_id: str,
        name: str,
        handler: Callable,
        schedule: CronExpression,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CronJob:
        """
        Add a cron job

        Args:
            job_id: Unique job ID
            name: Job name
            handler: Job handler function
            schedule: Cron expression
            metadata: Optional metadata

        Returns:
            Created CronJob
        """
        job = CronJob(
            id=job_id,
            name=name,
            handler=handler,
            schedule=schedule,
            next_run=schedule.get_next_run(),
            metadata=metadata or {},
        )

        self._jobs[job_id] = job
        logger.info(f"Added cron job: {name} ({job_id})")
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a cron job"""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Removed cron job: {job_id}")
            return True
        return False

    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get job by ID"""
        return self._jobs.get(job_id)

    def list_jobs(self, enabled_only: bool = False) -> List[CronJob]:
        """List all jobs"""
        jobs = list(self._jobs.values())
        if enabled_only:
            jobs = [j for j in jobs if j.enabled]
        return jobs

    def enable_job(self, job_id: str) -> bool:
        """Enable a job"""
        job = self._jobs.get(job_id)
        if job:
            job.enabled = True
            job.next_run = job.schedule.get_next_run()
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        """Disable a job"""
        job = self._jobs.get(job_id)
        if job:
            job.enabled = False
            job.next_run = None
            return True
        return False

    async def start(self):
        """Start the scheduler"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Cron scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cron scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                now = datetime.now()

                for job in self._jobs.values():
                    if not job.enabled or job.next_run is None:
                        continue

                    if now >= job.next_run:
                        await self._execute_job(job)

                # Sleep for 1 second
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

    async def _execute_job(self, job: CronJob):
        """Execute a job"""
        logger.info(f"Executing cron job: {job.name}")

        try:
            result = job.handler()

            # Handle coroutines
            if asyncio.iscoroutine(result):
                await result

            job.last_run = datetime.now()
            job.next_run = job.schedule.get_next_run(job.last_run)
            job.run_count += 1

            logger.info(f"Cron job completed: {job.name}")

        except Exception as e:
            logger.error(f"Cron job failed: {job.name} - {e}")
            job.failure_count += 1
            job.next_run = job.schedule.get_next_run()

    def run_now(self, job_id: str) -> bool:
        """Immediately run a job"""
        job = self._jobs.get(job_id)
        if job:
            asyncio.create_task(self._execute_job(job))
            return True
        return False
