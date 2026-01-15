"""Configuration for shipping rate monitor."""
from dataclasses import dataclass
from typing import List
import os

# Base directory for data storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "rates")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Scraping interval in seconds (1 hour)
SCRAPE_INTERVAL_SECONDS = 3600

# Request settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


@dataclass
class Package:
    """Represents a package with dimensions and weight."""
    name: str
    length: float  # inches
    width: float   # inches
    height: float  # inches
    weight: float  # pounds

    @property
    def dimensions_str(self) -> str:
        return f"{self.length}x{self.width}x{self.height}"


@dataclass
class Route:
    """Represents a shipping route."""
    name: str
    origin_zip: str
    origin_country: str
    destination_zip: str
    destination_country: str


# Standard packages to track
PACKAGES: List[Package] = [
    Package(name="Small", length=6, width=4, height=2, weight=1),
    Package(name="Medium", length=12, width=8, height=6, weight=5),
    Package(name="Large", length=18, width=12, height=10, weight=15),
]

# Routes to track
ROUTES: List[Route] = [
    Route(
        name="US Domestic (NY to LA)",
        origin_zip="10001",
        origin_country="US",
        destination_zip="90001",
        destination_country="US"
    ),
    Route(
        name="US to UK",
        origin_zip="10001",
        origin_country="US",
        destination_zip="SW1A 1AA",
        destination_country="GB"
    ),
]

# Carriers to scrape (Phase 1)
ACTIVE_CARRIERS = [
    "usps",
    "ups",
    "fedex",
    "dhl",
]
