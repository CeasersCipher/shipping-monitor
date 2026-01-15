"""DHL Express shipping rate scraper."""
from typing import List, Optional

from scrapers.base import BaseScraper
from config import Package, Route
from models import Rate


class DHLScraper(BaseScraper):
    """Scraper for DHL Express shipping rates."""

    carrier_name = "DHL Express"
    base_url = "https://www.dhl.com"

    def get_rate(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """Get DHL rates for a package on a route."""
        # DHL is primarily international, less competitive for US domestic
        # Using estimated rates based on DHL Express pricing

        if route.destination_country == route.origin_country == "US":
            return self._get_domestic_rates(package, route)
        else:
            return self._get_international_rates(package, route)

    def _get_domestic_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated domestic DHL rates."""
        # DHL domestic US is limited - mainly express services

        base_rates = {
            "DHL Express Domestic": {
                "base": 35.00,
                "per_lb": 2.50,
                "delivery_days": 2
            },
            "DHL Express 12:00": {
                "base": 55.00,
                "per_lb": 4.00,
                "delivery_days": 1
            },
        }

        rates = []
        for service, pricing in base_rates.items():
            dim_weight = (package.length * package.width * package.height) / 139
            billable_weight = max(package.weight, dim_weight)

            price = pricing["base"] + (billable_weight * pricing["per_lb"])
            price *= 1.18  # Fuel surcharge

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2),
                delivery_days=pricing["delivery_days"]
            ))

        return rates

    def _get_international_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated international DHL rates."""
        # DHL is very competitive for international

        base_rates = {
            "DHL Express Worldwide": {
                "base": 70.00,
                "per_lb": 6.50,
                "delivery_days": 3
            },
            "DHL Express 9:00": {
                "base": 120.00,
                "per_lb": 10.00,
                "delivery_days": 2
            },
            "DHL Express 12:00": {
                "base": 100.00,
                "per_lb": 8.50,
                "delivery_days": 2
            },
            "DHL Economy Select": {
                "base": 50.00,
                "per_lb": 4.50,
                "delivery_days": 6
            },
        }

        rates = []
        for service, pricing in base_rates.items():
            dim_weight = (package.length * package.width * package.height) / 139
            billable_weight = max(package.weight, dim_weight)

            price = pricing["base"] + (billable_weight * pricing["per_lb"])

            # DHL fuel and international surcharges
            price *= 1.20

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2),
                delivery_days=pricing["delivery_days"]
            ))

        return rates
