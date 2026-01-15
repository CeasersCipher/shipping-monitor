"""Shipping rate scrapers."""
import os
from scrapers.base import BaseScraper
from scrapers.usps import USPSScraper
from scrapers.ups import UPSScraper
from scrapers.fedex import FedExScraper
from scrapers.dhl import DHLScraper

SCRAPERS = {
    "usps": USPSScraper,
    "ups": UPSScraper,
    "fedex": FedExScraper,
    "dhl": DHLScraper,
}


def get_api_key(key: str) -> str:
    """Get API key from env var or Streamlit secrets (lazy loaded)."""
    # First check environment variable
    val = os.environ.get(key, "")
    if val:
        return val
    # Then check Streamlit secrets (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return ""


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
    return bool(get_api_key("EASYPOST_API_KEY") or get_api_key("SHIPPO_API_KEY"))


def use_easypost() -> bool:
    """Check if EasyPost API is configured."""
    return bool(get_api_key("EASYPOST_API_KEY"))


def use_shippo() -> bool:
    """Check if Shippo API is configured."""
    return bool(get_api_key("SHIPPO_API_KEY"))


def get_live_rate_provider() -> str:
    """Get which live rate provider is active."""
    if get_api_key("EASYPOST_API_KEY"):
        return "EasyPost"
    if get_api_key("SHIPPO_API_KEY"):
        return "Shippo"
    return None


def get_live_scraper():
    """Get the configured live rate scraper (EasyPost or Shippo)."""
    easypost_key = get_api_key("EASYPOST_API_KEY")
    if easypost_key:
        from scrapers.easypost_scraper import EasyPostScraper
        return EasyPostScraper(easypost_key)

    shippo_key = get_api_key("SHIPPO_API_KEY")
    if shippo_key:
        from scrapers.shippo_scraper import ShippoScraper
        return ShippoScraper(shippo_key)
    return None


def get_easypost_scraper():
    """Get EasyPost scraper if configured."""
    key = get_api_key("EASYPOST_API_KEY")
    if key:
        from scrapers.easypost_scraper import EasyPostScraper
        return EasyPostScraper(key)
    return None


def get_shippo_scraper():
    """Get Shippo scraper if configured."""
    key = get_api_key("SHIPPO_API_KEY")
    if key:
        from scrapers.shippo_scraper import ShippoScraper
        return ShippoScraper(key)
    return None
