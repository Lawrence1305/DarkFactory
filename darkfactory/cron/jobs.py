"""
Jobs - Decorator-based job registration
"""

from typing import Callable, Dict, Any, Optional
from functools import wraps

from .scheduler import CronScheduler, CronExpression, CronJob


class JobRegistry:
    """
    Job Registry

    Global registry for cron jobs with decorator support.
    """

    def __init__(self):
        self._scheduler = CronScheduler()

    @property
    def scheduler(self) -> CronScheduler:
        """Get the underlying scheduler"""
        return self._scheduler

    def register(
        self,
        job_id: str,
        name: str,
        schedule: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator to register a job

        Usage:
            @job_registry.register("my-job", "My Job", "@every 5 minutes")
            async def my_job():
                ...
        """
        def decorator(func: Callable):
            cron_expr = CronExpression(schedule)
            self._scheduler.add_job(
                job_id=job_id,
                name=name,
                handler=func,
                schedule=cron_expr,
                metadata=metadata,
            )

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator


# Global registry
_global_registry: Optional[JobRegistry] = None


def get_registry() -> JobRegistry:
    """Get global job registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = JobRegistry()
    return _global_registry


# Convenience decorator
def job(schedule: str, name: Optional[str] = None, job_id: Optional[str] = None):
    """
    Decorator to register a function as a cron job

    Usage:
        @job("@every 5 minutes", name="My Job")
        async def my_job():
            ...

        @job("daily 10:00", name="Morning Task")
        def morning_task():
            ...
    """
    def decorator(func: Callable):
        registry = get_registry()

        # Generate job_id from function name if not provided
        jid = job_id or func.__name__.replace("_", "-")

        # Use function name as name if not provided
        jname = name or func.__name__.replace("-", " ").title()

        cron_expr = CronExpression(schedule)
        registry.scheduler.add_job(
            job_id=jid,
            name=jname,
            handler=func,
            schedule=cron_expr,
        )

        return func

    return decorator


# Predefined job schedules
class Schedules:
    """Common schedule presets"""

    @staticmethod
    def every_minute() -> str:
        return "@every 1 minute"

    @staticmethod
    def every_5_minutes() -> str:
        return "@every 5 minutes"

    @staticmethod
    def every_15_minutes() -> str:
        return "@every 15 minutes"

    @staticmethod
    def every_hour() -> str:
        return "@every 1 hour"

    @staticmethod
    def every_6_hours() -> str:
        return "@every 6 hours"

    @staticmethod
    def daily(hour: int = 0, minute: int = 0) -> str:
        return CronExpression.daily(hour, minute).expression

    @staticmethod
    def weekly(day: int = 0, hour: int = 0, minute: int = 0) -> str:
        """Weekly schedule (day: 0=Sunday, 6=Saturday)"""
        return f"{minute} {hour} * * {day}"
