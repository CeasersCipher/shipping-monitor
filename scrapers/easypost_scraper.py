"""EasyPost API-based scraper for real shipping rates."""
import os
from typing import List, Optional
from datetime import datetime
import logging

import easypost

from config import Package, Route, PACKAGES, ROUTES
from models import Rate, ScrapeResult

logger = logging.getLogger(__name__)

# Get API key from environment or use test key
EASYPOST_API_KEY = os.environ.get("EASYPOST_API_KEY", "")


class EasyPostScraper:
    """Scraper that uses EasyPost API for real carrier rates."""

    carrier_name = "EasyPost"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or EASYPOST_API_KEY
        if self.api_key:
            self.client = easypost.EasyPostClient(self.api_key)
        else:
            self.client = None
            logger.warning("No EasyPost API key configured")

    def get_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get rates from all carriers via EasyPost."""
        if not self.client:
            logger.error("EasyPost client not initialized - no API key")
            return []

        try:
            # Create shipment to get rates
            shipment = self.client.shipment.create(
                from_address={
                    "street1": "123 Main St",
                    "city": "New York",
                    "state": "NY",
                    "zip": route.origin_zip,
                    "country": route.origin_country,
                },
                to_address={
                    "street1": "456 Oak Ave",
                    "city": "Los Angeles" if route.destination_country == "US" else "London",
                    "state": "CA" if route.destination_country == "US" else "",
                    "zip": route.destination_zip,
                    "country": route.destination_country,
                },
                parcel={
                    "length": package.length,
                    "width": package.width,
                    "height": package.height,
                    "weight": package.weight * 16,  # Convert lbs to oz
                },
            )

            rates = []
            for rate in shipment.rates:
                # Map EasyPost carrier names to our standard names
                carrier = self._normalize_carrier(rate.carrier)

                rates.append(Rate(
                    carrier=carrier,
                    service=rate.service,
                    package_name=package.name,
                    origin=route.origin_zip,
                    origin_country=route.origin_country,
                    destination=route.destination_zip,
                    destination_country=route.destination_country,
                    price=float(rate.rate),
                    currency=rate.currency,
                    delivery_days=rate.delivery_days,
                ))

            return rates

        except easypost.errors.api.ApiError as e:
            logger.error(f"EasyPost API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting EasyPost rates: {e}")
            return []

    def _normalize_carrier(self, carrier: str) -> str:
        """Normalize carrier names."""
        carrier_map = {
            "USPS": "USPS",
            "UPS": "UPS",
            "FedEx": "FedEx",
            "FedExSmartPost": "FedEx",
            "DHL": "DHL Express",
            "DHLExpress": "DHL Express",
            "DHLGlobalMail": "DHL",
            "CanadaPost": "Canada Post",
            "RoyalMail": "Royal Mail",
        }
        return carrier_map.get(carrier, carrier)

    def scrape_all(self) -> ScrapeResult:
        """Scrape rates for all packages and routes."""
        timestamp = datetime.now().isoformat()
        all_rates = []
        errors = []

        for package in PACKAGES:
            for route in ROUTES:
                try:
                    rates = self.get_rates(package, route)
                    if rates:
                        all_rates.extend(rates)
                        logger.info(f"Got {len(rates)} rates for {package.name} on {route.name}")
                except Exception as e:
                    error_msg = f"Error getting rates for {package.name} on {route.name}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        return ScrapeResult(
            timestamp=timestamp,
            carrier="EasyPost",
            success=len(all_rates) > 0,
            rates=all_rates,
            error="; ".join(errors) if errors else None
        )


def get_easypost_scraper() -> Optional[EasyPostScraper]:
    """Get an EasyPost scraper if API key is configured."""
    if EASYPOST_API_KEY:
        return EasyPostScraper(EASYPOST_API_KEY)
    return None
