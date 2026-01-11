# Life Dashboard

Personal life dashboard with shipment tracking.

## Features

- **Shipment Tracking**: Automatically extracts tracking numbers from emails via n8n webhook
- **Carrier Scraping**: Polls UPS, USPS, and FedEx for delivery status updates
- **SQLite + JSON Storage**: Schema-less storage with Pydantic validation

## Deployment

Deployed on Kubernetes at `life.ts.bence.dev` (Tailscale-only).
