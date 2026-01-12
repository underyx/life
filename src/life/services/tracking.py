import logging
from datetime import datetime, timezone

import httpx

from life.config import settings
from life.models.shipment import Shipment, TrackingEvent

logger = logging.getLogger(__name__)

SHIP24_API_URL = "https://api.ship24.com/public/v1"


async def fetch_tracking_status(shipment: Shipment) -> Shipment | None:
    """Fetch latest tracking status for a shipment using Ship24 API."""
    if not settings.ship24_api_key:
        logger.warning("No Ship24 API key configured")
        return None

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.ship24_api_key}",
                "Content-Type": "application/json",
            }

            # First, ensure tracker exists
            await client.post(
                f"{SHIP24_API_URL}/trackers",
                json={"trackingNumber": shipment.tracking_number},
                headers=headers,
                timeout=30.0,
            )

            # Get tracking results
            response = await client.get(
                f"{SHIP24_API_URL}/trackers/search/{shipment.tracking_number}/results",
                headers=headers,
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Ship24 API error: {response.status_code}")
                return None

            data = response.json()
            trackings = data.get("data", {}).get("trackings", [])

            if not trackings:
                return None

            tracking = trackings[0]
            ship = tracking.get("shipment", {})
            events = tracking.get("events", [])

            # Update status based on statusMilestone
            milestone = ship.get("statusMilestone", "").lower()
            if milestone == "delivered":
                shipment.status = "delivered"
            elif milestone == "out_for_delivery":
                shipment.status = "out_for_delivery"
            elif milestone == "in_transit":
                shipment.status = "in_transit"
            elif milestone == "info_received":
                shipment.status = "pending"
            elif milestone == "exception" or milestone == "failed_attempt":
                shipment.status = "exception"
            else:
                shipment.status = "unknown"

            # Update ETA
            delivery = ship.get("delivery", {})
            eta_str = delivery.get("estimatedDeliveryDate")
            if eta_str:
                try:
                    shipment.eta = datetime.fromisoformat(eta_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            # Update carrier from Ship24's detection
            courier_code = None
            if events:
                courier_code = events[0].get("courierCode", "")

            if courier_code:
                carrier_map = {
                    "us-post": "usps",
                    "ups": "ups",
                    "fedex": "fedex",
                    "dhl": "dhl",
                }
                shipment.carrier = carrier_map.get(courier_code, shipment.carrier)

            # Set tracking URL
            shipment.tracking_url = _get_tracking_url(shipment.carrier, shipment.tracking_number)

            # Update description with service type
            service = delivery.get("service")
            if service and not shipment.description:
                shipment.description = service

            # Convert events to history
            new_history = []
            for event in events:
                event_time = event.get("datetime")
                if event_time:
                    try:
                        timestamp = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                    except ValueError:
                        timestamp = datetime.now(timezone.utc)
                else:
                    timestamp = datetime.now(timezone.utc)

                location = event.get("location") or ""
                status_text = event.get("status", "")
                description = f"{status_text} - {location}".strip(" -")

                new_history.append(
                    TrackingEvent(
                        timestamp=timestamp,
                        description=description,
                        location=location,
                        status=event.get("statusMilestone") or shipment.status,
                    )
                )

            if new_history:
                shipment.history = new_history

            return shipment

    except Exception as e:
        logger.exception(f"Error fetching tracking: {e}")
        return None


def _get_tracking_url(carrier: str, tracking_number: str) -> str:
    """Get carrier tracking URL."""
    urls = {
        "usps": f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}",
        "ups": f"https://www.ups.com/track?tracknum={tracking_number}",
        "fedex": f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}",
        "dhl": f"https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}",
    }
    return urls.get(carrier, f"https://www.ship24.com/tracking/{tracking_number}")


async def update_all_shipments() -> dict:
    """Update tracking status for all active shipments."""
    from life.storage import database

    all_shipments = database.load_all("shipments", Shipment)
    updated = 0
    failed = 0

    for shipment in all_shipments:
        # Skip delivered or archived
        if shipment.status == "delivered" or shipment.is_archived:
            continue

        result = await fetch_tracking_status(shipment)
        if result:
            database.save("shipments", result)
            updated += 1
            logger.info(f"Updated {shipment.tracking_number}: {result.status}")
        else:
            failed += 1

    return {"updated": updated, "failed": failed}
