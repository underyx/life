from fastapi import APIRouter
from pydantic import BaseModel

from life.services.email_parser import parse_shipping_email
from life.storage import database
from life.models.shipment import Shipment

router = APIRouter()


class EmailPayload(BaseModel):
    subject: str
    body: str
    from_address: str | None = None


@router.post("/email/shipping")
async def receive_shipping_email(payload: EmailPayload):
    """Receive shipping email from n8n and extract tracking info."""
    shipments = parse_shipping_email(payload.subject, payload.body)

    created = []
    for shipment in shipments:
        # Check for duplicates by tracking number
        existing = database.load_all("shipments", Shipment)
        if any(s.tracking_number == shipment.tracking_number for s in existing):
            continue

        database.save("shipments", shipment)
        created.append(shipment.id)

    return {"created": created, "total_found": len(shipments)}
