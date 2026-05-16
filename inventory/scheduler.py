from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)


def start_scheduler():
    from .etl_pipeline import run_all_pipelines

    scheduler = BackgroundScheduler()

    # Run all ETL pipelines every night at midnight
    scheduler.add_job(
        run_all_pipelines,
        trigger=CronTrigger(hour=0, minute=0),
        id='nightly_etl',
        name='Nightly ETL Pipeline',
        replace_existing=True,
    )

    scheduler.start()
    logger.info('APScheduler started — nightly ETL scheduled at 00:00.')
