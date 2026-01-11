import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from life.services.tracking import update_all_shipments

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def tracking_update_job():
    """Job to update tracking status for all shipments."""
    logger.info("Starting tracking update job")
    try:
        result = await update_all_shipments()
        logger.info(f"Tracking update complete: {result}")
    except Exception as e:
        logger.error(f"Tracking update failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        tracking_update_job,
        trigger=IntervalTrigger(hours=1),
        id="tracking_update",
        name="Update shipment tracking status",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shutdown")
