"""Background scheduler for periodic rate scraping."""
import logging
from datetime import datetime
from typing import Callable, Optional, List
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import SCRAPE_INTERVAL_SECONDS, ACTIVE_CARRIERS
from scrapers import get_scraper, use_live_rates, get_live_scraper, get_live_rate_provider
from storage import StorageManager
from models import Rate, RateChange, ScrapeResult

logger = logging.getLogger(__name__)


class RateScrapeScheduler:
    """Manages scheduled scraping of shipping rates."""

    def __init__(
        self,
        storage: StorageManager = None,
        interval_seconds: int = SCRAPE_INTERVAL_SECONDS,
        on_complete: Callable[[List[ScrapeResult]], None] = None,
        on_change: Callable[[List[RateChange]], None] = None,
    ):
        self.storage = storage or StorageManager()
        self.interval_seconds = interval_seconds
        self.on_complete = on_complete
        self.on_change = on_change

        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_results: List[ScrapeResult] = []
        self.last_changes: List[RateChange] = []
        self._lock = threading.Lock()

    def _scrape_job(self):
        """The job that runs on schedule to scrape all carriers."""
        logger.info("Starting scheduled scrape job...")

        results = []
        all_rates = []
        all_changes = []

        # Use live rate API if configured (EasyPost or Shippo)
        if use_live_rates():
            provider = get_live_rate_provider()
            logger.info(f"Using {provider} API for live rates...")
            try:
                scraper = get_live_scraper()
                result = scraper.scrape_all()
                results.append(result)

                if result.success:
                    all_rates.extend(result.rates)
                    logger.info(f"Got {len(result.rates)} live rates from {provider}")
                else:
                    logger.warning(f"{provider} scrape failed: {result.error}")

            except Exception as e:
                logger.error(f"Error with {provider}: {e}")
                results.append(ScrapeResult(
                    timestamp=datetime.now().isoformat(),
                    carrier=provider,
                    success=False,
                    rates=[],
                    error=str(e)
                ))
        else:
            # Fall back to individual scrapers (estimated rates)
            logger.info("Using estimated rates (no live API key configured)")
            for carrier_id in ACTIVE_CARRIERS:
                try:
                    logger.info(f"Scraping {carrier_id}...")
                    scraper = get_scraper(carrier_id)
                    result = scraper.scrape_all()
                    results.append(result)

                    if result.success:
                        all_rates.extend(result.rates)
                        logger.info(f"Got {len(result.rates)} rates from {carrier_id}")
                    else:
                        logger.warning(f"Failed to scrape {carrier_id}: {result.error}")

                except Exception as e:
                    logger.error(f"Error scraping {carrier_id}: {e}")
                    results.append(ScrapeResult(
                        timestamp=datetime.now().isoformat(),
                        carrier=carrier_id,
                        success=False,
                        rates=[],
                        error=str(e)
                    ))

        # Save rates and detect changes
        if all_rates:
            new_rates, changes = self.storage.save_rates(all_rates)
            all_changes = changes
            logger.info(f"Saved {len(new_rates)} new/changed rates, {len(changes)} price changes detected")

        # Update state
        with self._lock:
            self.last_run = datetime.now()
            self.last_results = results
            self.last_changes = all_changes

        # Callbacks
        if self.on_complete:
            self.on_complete(results)

        if all_changes and self.on_change:
            self.on_change(all_changes)

        logger.info("Scrape job completed")

    def start(self, run_immediately: bool = True):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # Add the job
        self.scheduler.add_job(
            self._scrape_job,
            trigger=IntervalTrigger(seconds=self.interval_seconds),
            id="rate_scrape_job",
            name="Shipping Rate Scraper",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started, running every {self.interval_seconds} seconds")

        # Optionally run immediately
        if run_immediately:
            logger.info("Running initial scrape...")
            threading.Thread(target=self._scrape_job, daemon=True).start()

    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return

        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Scheduler stopped")

    def run_now(self):
        """Trigger an immediate scrape."""
        logger.info("Manual scrape triggered")
        threading.Thread(target=self._scrape_job, daemon=True).start()

    def get_status(self) -> dict:
        """Get current scheduler status."""
        with self._lock:
            next_run = None
            if self.is_running:
                job = self.scheduler.get_job("rate_scrape_job")
                if job:
                    next_run = job.next_run_time

            return {
                "is_running": self.is_running,
                "last_run": self.last_run.isoformat() if self.last_run else None,
                "next_run": next_run.isoformat() if next_run else None,
                "interval_seconds": self.interval_seconds,
                "last_results": [r.to_dict() for r in self.last_results],
                "recent_changes": [c.to_dict() for c in self.last_changes[-10:]],
            }


# Singleton scheduler instance for use with Streamlit
_scheduler_instance: Optional[RateScrapeScheduler] = None


def get_scheduler() -> RateScrapeScheduler:
    """Get or create the singleton scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RateScrapeScheduler()
    return _scheduler_instance


def init_scheduler(
    storage: StorageManager = None,
    interval_seconds: int = SCRAPE_INTERVAL_SECONDS,
    run_immediately: bool = True
) -> RateScrapeScheduler:
    """Initialize and start the scheduler."""
    global _scheduler_instance

    if _scheduler_instance is not None and _scheduler_instance.is_running:
        return _scheduler_instance

    _scheduler_instance = RateScrapeScheduler(
        storage=storage,
        interval_seconds=interval_seconds
    )
    _scheduler_instance.start(run_immediately=run_immediately)

    return _scheduler_instance
