"""JSON file storage manager with change detection."""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from config import DATA_DIR
from models import Rate, RateChange


class StorageManager:
    """Manages JSON file storage for shipping rates."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, date: datetime = None) -> Path:
        """Get the file path for a specific date."""
        if date is None:
            date = datetime.now()
        filename = date.strftime("%Y-%m-%d") + ".json"
        return self.data_dir / filename

    def _load_file(self, filepath: Path) -> Dict:
        """Load data from a JSON file."""
        if not filepath.exists():
            return {"entries": []}
        with open(filepath, "r") as f:
            return json.load(f)

    def _save_file(self, filepath: Path, data: Dict):
        """Save data to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def get_latest_rates(self) -> Dict[str, Rate]:
        """Get the most recent rates for each rate key."""
        latest_rates = {}

        # Check today and yesterday's files
        for days_ago in range(7):
            date = datetime.now() - timedelta(days=days_ago)
            filepath = self._get_file_path(date)
            if filepath.exists():
                data = self._load_file(filepath)
                for entry in reversed(data.get("entries", [])):
                    for rate_data in entry.get("rates", []):
                        rate = Rate.from_dict(rate_data)
                        key = rate.rate_key()
                        if key not in latest_rates:
                            latest_rates[key] = rate
                if latest_rates:
                    break  # Found data, stop looking

        return latest_rates

    def save_rates(self, rates: List[Rate]) -> Tuple[List[Rate], List[RateChange]]:
        """
        Save rates, detecting changes from previous rates.
        Returns (new_rates, changes).
        """
        if not rates:
            return [], []

        # Get latest known rates
        latest_rates = self.get_latest_rates()

        # Detect changes
        new_rates = []
        changes = []

        for rate in rates:
            key = rate.rate_key()

            if key in latest_rates:
                old_rate = latest_rates[key]
                if abs(old_rate.price - rate.price) > 0.01:  # Price changed
                    change_amount = rate.price - old_rate.price
                    change_percent = (change_amount / old_rate.price * 100) if old_rate.price > 0 else 0
                    changes.append(RateChange(
                        rate=rate,
                        old_price=old_rate.price,
                        new_price=rate.price,
                        change_amount=change_amount,
                        change_percent=change_percent,
                        detected_at=datetime.now().isoformat()
                    ))
                    new_rates.append(rate)
            else:
                # New rate we haven't seen before
                new_rates.append(rate)

        # Save to file if we have new data
        if new_rates:
            filepath = self._get_file_path()
            data = self._load_file(filepath)

            entry = {
                "timestamp": datetime.now().isoformat(),
                "rates": [r.to_dict() for r in new_rates]
            }
            data["entries"].append(entry)

            self._save_file(filepath, data)

            # Also save changes to a separate file
            if changes:
                self._save_changes(changes)

        return new_rates, changes

    def _save_changes(self, changes: List[RateChange]):
        """Save rate changes to a separate file."""
        changes_file = self.data_dir / "changes.json"

        if changes_file.exists():
            with open(changes_file, "r") as f:
                data = json.load(f)
        else:
            data = {"changes": []}

        for change in changes:
            data["changes"].append(change.to_dict())

        # Keep only last 1000 changes
        data["changes"] = data["changes"][-1000:]

        with open(changes_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_all_changes(self, limit: int = 100) -> List[RateChange]:
        """Get recent rate changes."""
        changes_file = self.data_dir / "changes.json"

        if not changes_file.exists():
            return []

        with open(changes_file, "r") as f:
            data = json.load(f)

        changes = []
        for change_data in data.get("changes", [])[-limit:]:
            rate = Rate.from_dict(change_data["rate"])
            changes.append(RateChange(
                rate=rate,
                old_price=change_data["old_price"],
                new_price=change_data["new_price"],
                change_amount=change_data["change_amount"],
                change_percent=change_data["change_percent"],
                detected_at=change_data["detected_at"]
            ))

        return list(reversed(changes))  # Most recent first

    def get_historical_rates(self, days: int = 30) -> List[Dict]:
        """Get all rate entries from the last N days."""
        all_entries = []

        for days_ago in range(days):
            date = datetime.now() - timedelta(days=days_ago)
            filepath = self._get_file_path(date)
            if filepath.exists():
                data = self._load_file(filepath)
                all_entries.extend(data.get("entries", []))

        return sorted(all_entries, key=lambda x: x["timestamp"])

    def get_rate_history(self, carrier: str, service: str, package: str, days: int = 30) -> List[Tuple[datetime, float]]:
        """Get price history for a specific rate."""
        history = []

        for entry in self.get_historical_rates(days):
            for rate_data in entry.get("rates", []):
                if (rate_data["carrier"] == carrier and
                    rate_data["service"] == service and
                    rate_data["package_name"] == package):
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    history.append((timestamp, rate_data["price"]))

        return sorted(history, key=lambda x: x[0])

    def get_scrape_status(self) -> Dict:
        """Get the last scrape timestamp and stats."""
        latest = self.get_latest_rates()

        if not latest:
            return {
                "last_scrape": None,
                "total_rates": 0,
                "carriers": []
            }

        # Find most recent timestamp
        timestamps = [r.timestamp for r in latest.values() if r.timestamp]
        last_scrape = max(timestamps) if timestamps else None

        carriers = list(set(r.carrier for r in latest.values()))

        return {
            "last_scrape": last_scrape,
            "total_rates": len(latest),
            "carriers": carriers
        }
