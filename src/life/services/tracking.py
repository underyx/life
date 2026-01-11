import re
from datetime import datetime, timezone

import httpx
from selectolax.parser import HTMLParser

from life.models.shipment import Shipment, TrackingEvent


async def fetch_tracking_status(shipment: Shipment) -> Shipment | None:
    """Fetch latest tracking status for a shipment. Returns updated shipment or None if failed."""
    match shipment.carrier:
        case "ups":
            return await _fetch_ups(shipment)
        case "usps":
            return await _fetch_usps(shipment)
        case "fedex":
            return await _fetch_fedex(shipment)
        case _:
            return None


async def _fetch_ups(shipment: Shipment) -> Shipment | None:
    """Fetch UPS tracking status."""
    url = f"https://www.ups.com/track?tracknum={shipment.tracking_number}"

    try:
        async with httpx.AsyncClient() as client:
            # UPS requires specific headers
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                },
                follow_redirects=True,
                timeout=30.0,
            )

            if response.status_code != 200:
                return None

            # UPS uses a lot of JavaScript, so basic HTML parsing may not work well
            # For now, just update the tracking URL and return
            shipment.tracking_url = url
            return shipment

    except Exception:
        return None


async def _fetch_usps(shipment: Shipment) -> Shipment | None:
    """Fetch USPS tracking status."""
    url = f"https://tools.usps.com/go/TrackConfirmAction?tLabels={shipment.tracking_number}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                },
                follow_redirects=True,
                timeout=30.0,
            )

            if response.status_code != 200:
                return None

            tree = HTMLParser(response.text)

            # Try to find status
            status_elem = tree.css_first(".delivery-status-header, .tb-status")
            if status_elem:
                status_text = status_elem.text().strip().lower()
                if "delivered" in status_text:
                    shipment.status = "delivered"
                elif "out for delivery" in status_text:
                    shipment.status = "out_for_delivery"
                elif "in transit" in status_text or "on its way" in status_text:
                    shipment.status = "in_transit"
                elif "accepted" in status_text or "picked up" in status_text:
                    shipment.status = "pending"

            # Try to find expected delivery date
            eta_elem = tree.css_first(".expected-delivery, .tb-expected-delivery-date")
            if eta_elem:
                eta_text = eta_elem.text().strip()
                # Try to parse date - this is fragile but worth trying
                date_match = re.search(
                    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}",
                    eta_text,
                )
                if date_match:
                    try:
                        shipment.eta = datetime.strptime(
                            date_match.group(0).replace(",", ""), "%B %d %Y"
                        ).replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

            shipment.tracking_url = url
            return shipment

    except Exception:
        return None


async def _fetch_fedex(shipment: Shipment) -> Shipment | None:
    """Fetch FedEx tracking status."""
    url = f"https://www.fedex.com/fedextrack/?trknbr={shipment.tracking_number}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                },
                follow_redirects=True,
                timeout=30.0,
            )

            if response.status_code != 200:
                return None

            # FedEx is heavily JavaScript-based, so basic parsing won't work well
            # Just update the URL for now
            shipment.tracking_url = url
            return shipment

    except Exception:
        return None


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
            # Add history event if status changed
            if result.status != shipment.status:
                result.history.append(
                    TrackingEvent(
                        timestamp=datetime.now(timezone.utc),
                        description=f"Status changed to {result.status}",
                        status=result.status,
                    )
                )
            database.save("shipments", result)
            updated += 1
        else:
            failed += 1

    return {"updated": updated, "failed": failed}
