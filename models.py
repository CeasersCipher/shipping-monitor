"""Data models for shipping rate monitor."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class Rate:
    """Represents a shipping rate quote."""
    carrier: str
    service: str
    package_name: str
    origin: str
    origin_country: str
    destination: str
    destination_country: str
    price: float
    currency: str
    delivery_days: Optional[int] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Rate":
        return cls(**data)

    def rate_key(self) -> str:
        """Unique key for this rate (excluding price and timestamp)."""
        return f"{self.carrier}|{self.service}|{self.package_name}|{self.origin}|{self.destination}"


@dataclass
class RateChange:
    """Represents a change in shipping rate."""
    rate: Rate
    old_price: float
    new_price: float
    change_amount: float
    change_percent: float
    detected_at: str

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()

    @property
    def is_increase(self) -> bool:
        return self.change_amount > 0

    def to_dict(self) -> dict:
        return {
            "rate": self.rate.to_dict(),
            "old_price": self.old_price,
            "new_price": self.new_price,
            "change_amount": self.change_amount,
            "change_percent": self.change_percent,
            "detected_at": self.detected_at,
        }


@dataclass
class ScrapeResult:
    """Result of a scraping run."""
    timestamp: str
    carrier: str
    success: bool
    rates: List[Rate]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "carrier": self.carrier,
            "success": self.success,
            "rates": [r.to_dict() for r in self.rates],
            "error": self.error,
        }
