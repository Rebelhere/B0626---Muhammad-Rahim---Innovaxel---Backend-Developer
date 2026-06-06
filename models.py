"""Data models for the Event Registration System."""
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    total_seats: int = 0
    event_date: str = ""  # ISO format: YYYY-MM-DD
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Event":
        return Event(**data)


@dataclass
class Registration:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_name: str = ""
    event_id: str = ""
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    cancelled: bool = False
    cancelled_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Registration":
        return Registration(**data)
