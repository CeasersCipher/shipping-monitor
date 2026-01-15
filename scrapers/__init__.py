"""Shipping rate scrapers."""
import os
from scrapers.base import BaseScraper
from scrapers.usps import USPSScraper
from scrapers.ups import UPSScraper
from scrapers.fedex import FedExScraper
from scrapers.dhl import DHLScraper

# Check for API keys (env vars or Streamlit secrets)
def _get_secret(key: str) -> str:
    """Get secret from env var or Streamlit secrets."""
    # First check environment variable
    val = os.environ.get(key, "")
    if val:
        return val
    # Then check Streamlit secrets (for cloud deployment)
    try:
        import streamlit as st
        return st.secrets.get(key, "")
    except:
        return ""

EASYPOST_API_KEY = _get_secret("EASYPOST_API_KEY")
SHIPPO_API_KEY = _get_secret("SHIPPO_API_KEY")

SCRAPERS = {
    "usps": USPSScraper,
    "ups": UPSScraper,
    "fedex": FedExScraper,
    "dhl": DHLScraper,
}


def get_scraper(carrier: str) -> BaseScraper:
    """Get a scraper instance for the given carrier."""
    scraper_class = SCRAPERS.get(carrier.lower())
    if scraper_class is None:
        raise ValueError(f"Unknown carrier: {carrier}")
    return scraper_class()


def get_all_scrapers():
    """Get instances of all available scrapers."""
    return [scraper_class() for scraper_class in SCRAPERS.values()]


def use_live_rates() -> bool:
    """Check if any live rate API is configured."""
    return bool(EASYPOST_API_KEY or SHIPPO_API_KEY)


def use_easypost() -> bool:
    """Check if EasyPost API is configured."""
    return bool(EASYPOST_API_KEY)


def use_shippo() -> bool:
    """Check if Shippo API is configured."""
    return bool(SHIPPO_API_KEY)


def get_live_rate_provider() -> str:
    """Get which live rate provider is active."""
    if EASYPOST_API_KEY:
        return "EasyPost"
    if SHIPPO_API_KEY:
        return "Shippo"
    return None


def get_live_scraper():
    """Get the configured live rate scraper (EasyPost or Shippo)."""
    if EASYPOST_API_KEY:
        from scrapers.easypost_scraper import EasyPostScraper
        return EasyPostScraper(EASYPOST_API_KEY)
    if SHIPPO_API_KEY:
        from scrapers.shippo_scraper import ShippoScraper
        return ShippoScraper(SHIPPO_API_KEY)
    return None


def get_easypost_scraper():
    """Get EasyPost scraper if configured."""
    if use_easypost():
        from scrapers.easypost_scraper import EasyPostScraper
        return EasyPostScraper(EASYPOST_API_KEY)
    return None


def get_shippo_scraper():
    """Get Shippo scraper if configured."""
    if use_shippo():
        from scrapers.shippo_scraper import ShippoScraper
        return ShippoScraper(SHIPPO_API_KEY)
    return None
