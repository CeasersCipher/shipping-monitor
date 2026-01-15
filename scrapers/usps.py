"""USPS shipping rate scraper."""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
import json

from scrapers.base import BaseScraper
from config import Package, Route
from models import Rate


class USPSScraper(BaseScraper):
    """Scraper for USPS shipping rates using their public calculator."""

    carrier_name = "USPS"
    base_url = "https://postcalc.usps.com"

    def get_rate(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """Get USPS rates for a package on a route."""
        rates = []

        # USPS only handles US domestic and US-origin international
        if route.origin_country != "US":
            return None

        if route.destination_country == "US":
            return self._get_domestic_rates(package, route)
        else:
            return self._get_international_rates(package, route)

    def _get_domestic_rates(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """Get domestic USPS rates."""
        # Use the USPS postage calculator API endpoint
        url = f"{self.base_url}/Calculator/GetMailServices"

        params = {
            "client_ip": "127.0.0.1",
            "countrycode": "US",
            "dpb": "0",
            "dz": route.destination_zip,
            "filteraliases": "true",
            "girth": "0",
            "height": str(package.height),
            "length": str(package.length),
            "maildate": "",
            "mailtime": "",
            "mailtimeoffset": "",
            "mailtype": "Package",
            "oz": route.origin_zip,
            "pricetype": "RETAIL",
            "rect": "true",
            "weight": str(package.weight),
            "width": str(package.width),
        }

        response = self._make_request(
            url,
            method="GET",
            headers={"Accept": "application/json"}
        )

        if not response:
            return self._get_estimated_domestic_rates(package, route)

        try:
            data = response.json()
            rates = []

            for service in data.get("MailServices", []):
                service_name = service.get("ServiceName", "")
                price = service.get("TotalPrice", 0)

                if price and price > 0:
                    delivery_desc = service.get("DeliveryTimeLine", "")
                    delivery_days = self._parse_delivery_days(delivery_desc)

                    rates.append(self._create_rate(
                        service=service_name,
                        package=package,
                        route=route,
                        price=price,
                        delivery_days=delivery_days
                    ))

            return rates if rates else self._get_estimated_domestic_rates(package, route)

        except (json.JSONDecodeError, KeyError):
            return self._get_estimated_domestic_rates(package, route)

    def _get_international_rates(self, package: Package, route: Route) -> Optional[List[Rate]]:
        """Get international USPS rates."""
        # For international, we use estimated rates based on typical pricing
        return self._get_estimated_international_rates(package, route)

    def _get_estimated_domestic_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated domestic rates based on typical USPS pricing."""
        # Estimated rates based on 2024 USPS pricing
        base_rates = {
            "Priority Mail": {"base": 8.70, "per_lb": 1.50},
            "Priority Mail Express": {"base": 28.75, "per_lb": 2.00},
            "USPS Ground Advantage": {"base": 5.50, "per_lb": 0.80},
            "Media Mail": {"base": 3.65, "per_lb": 0.65},
        }

        rates = []
        for service, pricing in base_rates.items():
            price = pricing["base"] + (package.weight * pricing["per_lb"])
            # Adjust for package size
            volume = package.length * package.width * package.height
            if volume > 500:
                price *= 1.2
            if volume > 1000:
                price *= 1.3

            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2)
            ))

        return rates

    def _get_estimated_international_rates(self, package: Package, route: Route) -> List[Rate]:
        """Get estimated international rates."""
        base_rates = {
            "Priority Mail International": {"base": 45.00, "per_lb": 5.00},
            "Priority Mail Express International": {"base": 65.00, "per_lb": 7.00},
            "First-Class Package International": {"base": 15.00, "per_lb": 3.00},
        }

        rates = []
        for service, pricing in base_rates.items():
            if service == "First-Class Package International" and package.weight > 4:
                continue  # First class limited to 4 lbs

            price = pricing["base"] + (package.weight * pricing["per_lb"])
            rates.append(self._create_rate(
                service=service,
                package=package,
                route=route,
                price=round(price, 2)
            ))

        return rates

    def _parse_delivery_days(self, delivery_desc: str) -> Optional[int]:
        """Parse delivery days from description."""
        if not delivery_desc:
            return None

        match = re.search(r"(\d+)", delivery_desc)
        if match:
            return int(match.group(1))
        return None
