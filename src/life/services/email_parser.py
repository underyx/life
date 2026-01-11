import re
from typing import Literal

from life.models.shipment import Shipment

CarrierType = Literal["usps", "ups", "fedex", "dhl", "amazon", "other"]

# Tracking number patterns by carrier
TRACKING_PATTERNS: dict[CarrierType, list[str]] = {
    "ups": [
        r"1Z[A-Z0-9]{16}",  # Standard UPS
    ],
    "fedex": [
        r"\b\d{12}\b",  # 12-digit
        r"\b\d{15}\b",  # 15-digit
        r"\b\d{20}\b",  # 20-digit
        r"\b\d{22}\b",  # 22-digit
    ],
    "usps": [
        r"\b9[0-9]{21}\b",  # Starts with 9, 22 digits
        r"\b9[0-9]{25}\b",  # Starts with 9, 26 digits
        r"\b[A-Z]{2}\d{9}US\b",  # International format
    ],
    "amazon": [
        r"TBA\d{12,}",  # Amazon Logistics
    ],
}

# URL patterns to detect carrier from tracking URLs
URL_PATTERNS: list[tuple[CarrierType, str, str]] = [
    ("ups", r"ups\.com.*?tracknum=([A-Z0-9]+)", r"1Z[A-Z0-9]{16}"),
    ("fedex", r"fedex\.com.*?tracknumbers?=(\d+)", r"\d{12,22}"),
    ("usps", r"usps\.com.*?tLabels=([A-Z0-9]+)", r"[A-Z0-9]+"),
]


def parse_shipping_email(subject: str, body: str) -> list[Shipment]:
    """Extract shipment info from email content."""
    shipments: list[Shipment] = []
    seen_tracking: set[str] = set()

    text = f"{subject}\n{body}"

    # First, try to find tracking URLs and extract numbers
    urls = re.findall(r"https?://[^\s<>\"']+", text, re.IGNORECASE)
    for url in urls:
        for carrier, url_pattern, num_pattern in URL_PATTERNS:
            match = re.search(url_pattern, url, re.IGNORECASE)
            if match:
                tracking_num = match.group(1)
                if tracking_num not in seen_tracking:
                    seen_tracking.add(tracking_num)
                    shipments.append(
                        Shipment(
                            carrier=carrier,
                            tracking_number=tracking_num,
                            tracking_url=url,
                            source_email_subject=subject[:200],
                        )
                    )

    # Then look for standalone tracking numbers
    for carrier, patterns in TRACKING_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for tracking_num in matches:
                if tracking_num not in seen_tracking:
                    seen_tracking.add(tracking_num)
                    shipments.append(
                        Shipment(
                            carrier=carrier,
                            tracking_number=tracking_num,
                            source_email_subject=subject[:200],
                        )
                    )

    return shipments
