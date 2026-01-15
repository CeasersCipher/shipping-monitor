"""Base scraper class for shipping carriers."""
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import logging

import requests
from requests.exceptions import RequestException

from config import (
    USER_AGENTS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    Package,
    Route,
    PACKAGES,
    ROUTES,
)
from models import Rate, ScrapeResult

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for shipping rate scrapers."""

    carrier_name: str = "Unknown"
    base_url: str = ""

    def __init__(self):
        self.session = requests.Session()
        self._update_headers()

    def _update_headers(self):
        """Update session headers with a random user agent."""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: dict = None,
        json_data: dict = None,
        headers: dict = None,
    ) -> Optional[requests.Response]:
        """Make an HTTP request with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                self._update_headers()  # Rotate user agent

                if headers:
                    self.session.headers.update(headers)

                if method.upper() == "GET":
                    response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                elif method.upper() == "POST":
                    response = self.session.post(
                        url,
                        data=data,
                        json=json_data,
                        timeout=REQUEST_TIMEOUT
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response

            except RequestException as e:
                logger.warning(
                    f"{self.carrier_name} request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        return None

    @abstractmethod
    def get_rate(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """
        Get shipping rates for a package on a route.
        Must be implemented by each carrier scraper.
        Returns a list of Rate objects for different services.
        """
        pass

    def scrape_all(self) -> ScrapeResult:
        """Scrape rates for all packages and routes."""
        timestamp = datetime.now().isoformat()
        all_rates = []
        errors = []

        for package in PACKAGES:
            for route in ROUTES:
                try:
                    rates = self.get_rate(package, route)
                    if rates:
                        all_rates.extend(rates)
                except Exception as e:
                    error_msg = f"Error scraping {package.name} on {route.name}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

                # Rate limiting between requests
                time.sleep(random.uniform(1, 3))

        return ScrapeResult(
            timestamp=timestamp,
            carrier=self.carrier_name,
            success=len(all_rates) > 0,
            rates=all_rates,
            error="; ".join(errors) if errors else None
        )

    def _create_rate(
        self,
        service: str,
        package: Package,
        route: Route,
        price: float,
        currency: str = "USD",
        delivery_days: int = None,
    ) -> Rate:
        """Helper to create a Rate object."""
        return Rate(
            carrier=self.carrier_name,
            service=service,
            package_name=package.name,
            origin=route.origin_zip,
            origin_country=route.origin_country,
            destination=route.destination_zip,
            destination_country=route.destination_country,
            price=price,
            currency=currency,
            delivery_days=delivery_days,
        )
