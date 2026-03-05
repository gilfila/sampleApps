from apscheduler.schedulers.background import BackgroundScheduler
import logging
import atexit

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def sync_workers_job(app):
    """Background job to sync workers from Workday. No-op when Workday not configured."""
    with app.app_context():
        try:
            from app.services.workday_config import is_workday_configured, get_workday_config
            if not is_workday_configured():
                logger.debug("Workday not configured; skipping scheduled worker sync")
                return
            from app.services.workday_sync import WorkdaySync
            sync_interval = get_workday_config().get("sync_interval") or 3600
            workday_sync = WorkdaySync(get_workday_config())
            logger.info("Starting worker sync from Workday")
            workday_sync.sync_workers()
            logger.info("Worker sync completed successfully")
        except Exception as e:
            logger.error("Error in worker sync job: %s", e)


def start_scheduler(app):
    """Start the background scheduler. Workday sync runs only when configured (in-app or env)."""
    with app.app_context():
        from app.services.workday_config import get_workday_config, is_workday_configured
        config = get_workday_config()
        interval = config.get("sync_interval") or 3600
        if is_workday_configured():
            scheduler.add_job(
                func=sync_workers_job,
                trigger="interval",
                seconds=interval,
                id="worker_sync",
                name="Sync workers from Workday",
                replace_existing=True,
                args=[app],
            )
            logger.info("Workday worker sync scheduled every %s seconds", interval)
        else:
            logger.info("Workday not configured; scheduled worker sync disabled")
    scheduler.start()
    logger.info("Background scheduler started")
    # Run initial sync on startup only when configured (non-blocking)
    try:
        sync_workers_job(app)
    except Exception as e:
        logger.debug("Initial worker sync: %s", e)
    atexit.register(lambda: scheduler.shutdown())


def stop_scheduler():
    """Stop the background scheduler"""
    scheduler.shutdown()
    logger.info("Background scheduler stopped")
