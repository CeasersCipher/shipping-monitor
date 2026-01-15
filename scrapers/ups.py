"""UPS shipping rate scraper."""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
import json

from scrapers.base import BaseScraper
from config import Package, Route
from models import Rate


class UPSScraper(BaseScraper):
    """Scraper for UPS shipping rates."""

    carrier_name = "UPS"
    base_url = "https://www.ups.com"

    def get_rate(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """Get UPS rates for a package on a route."""
        # UPS website is heavily JavaScript-based, so we use estimated rates
        # based on their published rate sheets

        if route.destination_country == route.origin_country:
            return self._get_domestic_rates(package, route)
        else:
            return self._get_international_rates(package, route)

    def _get_domestic_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated domestic UPS rates."""
        # Based on UPS 2024 rate sheets for US domestic
        # Zone 8 pricing (coast to coast like NY to LA)

        base_rates = {
            "UPS Ground": {
                "base": 12.50,
                "per_lb": 0.75,
                "delivery_days": 5
            },
            "UPS 3 Day Select": {
                "base": 18.00,
                "per_lb": 1.20,
                "delivery_days": 3
            },
            "UPS 2nd Day Air": {
                "base": 28.00,
                "per_lb": 2.00,
                "delivery_days": 2
            },
            "UPS Next Day Air Saver": {
                "base": 45.00,
                "per_lb": 3.50,
                "delivery_days": 1
            },
            "UPS Next Day Air": {
                "base": 55.00,
                "per_lb": 4.00,
                "delivery_days": 1
            },
        }

        rates = []
        for service, pricing in base_rates.items():
            # Calculate billable weight (actual vs dimensional)
            dim_weight = (package.length * package.width * package.height) / 139
            billable_weight = max(package.weight, dim_weight)

            price = pricing["base"] + (billable_weight * pricing["per_lb"])

            # Add fuel surcharge (typical ~15%)
            price *= 1.15

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2),
                delivery_days=pricing["delivery_days"]
            ))

        return rates

    def _get_international_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated international UPS rates."""
        # Based on UPS international rates to Western Europe

        base_rates = {
            "UPS Worldwide Express": {
                "base": 85.00,
                "per_lb": 8.00,
                "delivery_days": 2
            },
            "UPS Worldwide Expedited": {
                "base": 65.00,
                "per_lb": 6.00,
                "delivery_days": 4
            },
            "UPS Worldwide Saver": {
                "base": 75.00,
                "per_lb": 7.00,
                "delivery_days": 3
            },
            "UPS Standard (International)": {
                "base": 45.00,
                "per_lb": 4.00,
                "delivery_days": 7
            },
        }

        rates = []
        for service, pricing in base_rates.items():
            dim_weight = (package.length * package.width * package.height) / 139
            billable_weight = max(package.weight, dim_weight)

            price = pricing["base"] + (billable_weight * pricing["per_lb"])

            # Add fuel surcharge and international fees
            price *= 1.20

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2),
                delivery_days=pricing["delivery_days"]
            ))

        return rates
