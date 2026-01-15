"""FedEx shipping rate scraper."""
from typing import List, Optional

from scrapers.base import BaseScraper
from config import Package, Route
from models import Rate


class FedExScraper(BaseScraper):
    """Scraper for FedEx shipping rates."""

    carrier_name = "FedEx"
    base_url = "https://www.fedex.com"

    def get_rate(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """Get FedEx rates for a package on a route."""
        # FedEx website requires JavaScript/authentication
        # Using estimated rates based on published rate sheets

        if route.destination_country == route.origin_country:
            return self._get_domestic_rates(package, route)
        else:
            return self._get_international_rates(package, route)

    def _get_domestic_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated domestic FedEx rates."""
        # Based on FedEx 2024 rate sheets
        # Zone 8 pricing (coast to coast)

        base_rates = {
            "FedEx Ground": {
                "base": 11.80,
                "per_lb": 0.70,
                "delivery_days": 5
            },
            "FedEx Home Delivery": {
                "base": 12.50,
                "per_lb": 0.75,
                "delivery_days": 5
            },
            "FedEx Express Saver": {
                "base": 22.00,
                "per_lb": 1.80,
                "delivery_days": 3
            },
            "FedEx 2Day": {
                "base": 30.00,
                "per_lb": 2.20,
                "delivery_days": 2
            },
            "FedEx 2Day AM": {
                "base": 35.00,
                "per_lb": 2.50,
                "delivery_days": 2
            },
            "FedEx Priority Overnight": {
                "base": 52.00,
                "per_lb": 3.80,
                "delivery_days": 1
            },
            "FedEx Standard Overnight": {
                "base": 48.00,
                "per_lb": 3.50,
                "delivery_days": 1
            },
        }

        rates = []
        for service, pricing in base_rates.items():
            # Calculate dimensional weight
            dim_weight = (package.length * package.width * package.height) / 139
            billable_weight = max(package.weight, dim_weight)

            price = pricing["base"] + (billable_weight * pricing["per_lb"])

            # Add fuel surcharge (typical ~16%)
            price *= 1.16

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2),
                delivery_days=pricing["delivery_days"]
            ))

        return rates

    def _get_international_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated international FedEx rates."""

        base_rates = {
            "FedEx International Priority": {
                "base": 80.00,
                "per_lb": 7.50,
                "delivery_days": 2
            },
            "FedEx International Economy": {
                "base": 55.00,
                "per_lb": 5.00,
                "delivery_days": 5
            },
            "FedEx International First": {
                "base": 95.00,
                "per_lb": 9.00,
                "delivery_days": 1
            },
            "FedEx International Ground": {
                "base": 40.00,
                "per_lb": 3.50,
                "delivery_days": 7
            },
        }

        rates = []
        for service, pricing in base_rates.items():
            dim_weight = (package.length * package.width * package.height) / 139
            billable_weight = max(package.weight, dim_weight)

            price = pricing["base"] + (billable_weight * pricing["per_lb"])

            # Add international fees and fuel surcharge
            price *= 1.22

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2),
                delivery_days=pricing["delivery_days"]
            ))

        return rates
