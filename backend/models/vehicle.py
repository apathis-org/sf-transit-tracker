"""
Vehicle data models for SF Transit Tracker
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Vehicle:
    """Vehicle data structure"""
    id: str
    type: str
    route: str
    lat: float
    lng: float
    heading: float = 0.0
    speed: float = 0.0
    agency: str = ''
    destination: str = ''
    last_update: str = ''

    def to_dict(self):
        return asdict(self)