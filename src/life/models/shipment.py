from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class TrackingEvent(BaseModel):
    timestamp: datetime
    location: str | None = None
    description: str
    status: str


class Shipment(BaseModel):
    id: str = Field(default_factory=lambda: f"ship_{uuid4().hex[:8]}")
    carrier: Literal["usps", "ups", "fedex", "dhl", "amazon", "other"]
    tracking_number: str
    tracking_url: str | None = None
    description: str = ""
    status: Literal["pending", "in_transit", "out_for_delivery", "delivered", "exception", "unknown"] = "unknown"
    eta: datetime | None = None
    source_email_subject: str | None = None
    history: list[TrackingEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_archived: bool = False

    def tracking_link(self) -> str | None:
        """Get the tracking URL for this shipment."""
        if self.tracking_url:
            return self.tracking_url

        match self.carrier:
            case "ups":
                return f"https://www.ups.com/track?tracknum={self.tracking_number}"
            case "usps":
                return f"https://tools.usps.com/go/TrackConfirmAction?tLabels={self.tracking_number}"
            case "fedex":
                return f"https://www.fedex.com/fedextrack/?trknbr={self.tracking_number}"
            case _:
                return None
