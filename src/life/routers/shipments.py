from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from life.auth import verify_auth
from life.models.shipment import Shipment
from life.storage import database

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def list_shipments(request: Request, _: None = Depends(verify_auth)):
    """List all shipments."""
    all_shipments = database.load_all("shipments", Shipment)
    active = [s for s in all_shipments if not s.is_archived and s.status != "delivered"]
    delivered = [s for s in all_shipments if s.status == "delivered" and not s.is_archived]

    return templates.TemplateResponse(
        "shipments.html",
        {
            "request": request,
            "active_shipments": active,
            "delivered_shipments": delivered,
        },
    )


@router.post("/add")
async def add_shipment(
    tracking_number: str = Form(...),
    carrier: str = Form(...),
    description: str = Form(""),
    _: None = Depends(verify_auth),
):
    """Manually add a shipment."""
    shipment = Shipment(
        carrier=carrier,  # type: ignore
        tracking_number=tracking_number.strip(),
        description=description.strip(),
    )
    database.save("shipments", shipment)
    return RedirectResponse(url="/shipments", status_code=303)


@router.post("/{shipment_id}/archive")
async def archive_shipment(shipment_id: str, _: None = Depends(verify_auth)):
    """Archive a shipment."""
    shipment = database.load("shipments", shipment_id, Shipment)
    if shipment:
        shipment.is_archived = True
        database.save("shipments", shipment)
    return RedirectResponse(url="/shipments", status_code=303)


@router.post("/{shipment_id}/delete")
async def delete_shipment(shipment_id: str, _: None = Depends(verify_auth)):
    """Delete a shipment."""
    database.delete("shipments", shipment_id)
    return RedirectResponse(url="/shipments", status_code=303)
