"""Shippo API-based scraper for real shipping rates."""
import os
from typing import List, Optional
from datetime import datetime
import logging

import shippo

from config import Package, Route, PACKAGES, ROUTES
from models import Rate, ScrapeResult

logger = logging.getLogger(__name__)

# Get API key from environment
SHIPPO_API_KEY = os.environ.get("SHIPPO_API_KEY", "")


class ShippoScraper:
    """Scraper that uses Shippo API for real carrier rates."""

    carrier_name = "Shippo"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or SHIPPO_API_KEY
        if self.api_key:
            self.client = shippo.Shippo(api_key_header=self.api_key)
        else:
            self.client = None
            logger.warning("No Shippo API key configured")

    def get_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get rates from all carriers via Shippo."""
        if not self.client:
            logger.error("Shippo client not initialized - no API key")
            return []

        try:
            # Create address objects
            address_from = {
                "street1": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip": route.origin_zip,
                "country": route.origin_country,
            }

            if route.destination_country == "US":
                address_to = {
                    "street1": "456 Oak Ave",
                    "city": "Los Angeles",
                    "state": "CA",
                    "zip": route.destination_zip,
                    "country": route.destination_country,
                }
            else:
                address_to = {
                    "street1": "10 Downing St",
                    "city": "London",
                    "zip": route.destination_zip,
                    "country": route.destination_country,
                }

            # Create parcel
            parcel = {
                "length": str(package.length),
                "width": str(package.width),
                "height": str(package.height),
                "distance_unit": "in",
                "weight": str(package.weight),
                "mass_unit": "lb",
            }

            # Create shipment to get rates
            shipment = self.client.shipments.create(
                address_from=address_from,
                address_to=address_to,
                parcels=[parcel],
                async_=False,
            )

            rates = []
            for rate in shipment.rates:
                carrier = self._normalize_carrier(rate.provider)

                rates.append(Rate(
                    carrier=carrier,
                    service=rate.servicelevel.name if rate.servicelevel else rate.servicelevel_token,
                    package_name=package.name,
                    origin=route.origin_zip,
                    origin_country=route.origin_country,
                    destination=route.destination_zip,
                    destination_country=route.destination_country,
                    price=float(rate.amount),
                    currency=rate.currency,
                    delivery_days=rate.estimated_days,
                ))

            return rates

        except Exception as e:
            logger.error(f"Error getting Shippo rates: {e}")
            return []

    def _normalize_carrier(self, carrier: str) -> str:
        """Normalize carrier names."""
        carrier_map = {
            "usps": "USPS",
            "ups": "UPS",
            "fedex": "FedEx",
            "dhl_express": "DHL Express",
            "dhl_ecommerce": "DHL",
            "canada_post": "Canada Post",
            "royal_mail": "Royal Mail",
            "australia_post": "Australia Post",
        }
        return carrier_map.get(carrier.lower(), carrier)

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
            carrier="Shippo",
            success=len(all_rates) > 0,
            rates=all_rates,
            error="; ".join(errors) if errors else None
        )


def get_shippo_scraper() -> Optional[ShippoScraper]:
    """Get a Shippo scraper if API key is configured."""
    if SHIPPO_API_KEY:
        return ShippoScraper(SHIPPO_API_KEY)
    return None
