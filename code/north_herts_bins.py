from datetime import datetime
import logging
import re
from typing import List, Tuple, Optional, Dict, Any
from os import getenv

import requests

logger = logging.getLogger()

# Cloud9 Technologies API (backs the North Herts council mobile app)
API_URL = "https://apps.cloud9technologies.com/northherts/citizenmobile/mobileapi"
HEADERS = {
    "Authorization": "Basic Y2xvdWQ5OmlkQmNWNGJvcjU=",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "x-api-version": "2",
}
REQUEST_TIMEOUT = 30

POSTCODE_RE = re.compile(r"([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})", re.IGNORECASE)


def _normalise_postcode(postcode: str) -> str:
    match = POSTCODE_RE.search(postcode)
    if not match:
        return postcode.strip().upper()
    return f"{match.group(1).upper()} {match.group(2).upper()}"


def _select_address(addresses: list, house_number: Optional[str]) -> dict:
    if not addresses:
        raise ValueError("No addresses returned by the API for this postcode.")

    if not house_number:
        logger.warning("HOUSE_NUMBER not set, using first address result.")
        return addresses[0]

    number = house_number.strip().lower()
    for addr in addresses:
        # Check common address fields for the house number
        for field in ("buildingNumber", "propertyNumber", "buildingName",
                      "fullAddress", "singleLineAddress", "addressLine1"):
            value = addr.get(field)
            if value and re.search(rf"\b{re.escape(number)}\b", str(value).lower()):
                return addr

    logger.warning("No exact match for house number '%s', using first result.", house_number)
    return addresses[0]


def _parse_date(value: Any) -> Optional[datetime]:
    if value is None or not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    # Strip trailing Z or timezone for naive datetime
    if candidate.endswith("Z"):
        candidate = candidate[:-1]
    try:
        dt = datetime.fromisoformat(candidate)
        return dt.replace(tzinfo=None)
    except ValueError:
        return None


def _clean_type_name(name: str) -> str:
    cleaned = name.strip()
    for suffix in ("Collection", "collection", "Bin", "bin"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned or name


def _parse_collections(payload: Dict[str, Any]) -> List[Tuple[datetime, str]]:
    # The API may nest data under different keys
    data = (
        payload.get("wasteCollectionDates")
        or payload.get("WasteCollectionDates")
        or payload
    )

    collections_section = data.get("collections") if isinstance(data, dict) else None
    items: List[Tuple[str, Dict[str, Any]]] = []

    if isinstance(collections_section, dict):
        items = list(collections_section.items())
    elif isinstance(data, dict):
        # Fallback: look for keys ending in "CollectionDetails"
        for key, value in data.items():
            if isinstance(value, dict):
                items.append((key, value))

    results: List[Tuple[datetime, str]] = []
    seen = set()

    for key, details in items:
        if not isinstance(details, dict):
            continue

        # Determine bin type
        label = (
            details.get("containerDescription")
            or details.get("containerName")
            or details.get("collectionType")
            or key
        )
        if not isinstance(label, str):
            label = str(label)
        label = _clean_type_name(label)

        # Collect all date candidates
        date_values = []
        for date_field in ("collectionDate", "nextCollectionDate"):
            if details.get(date_field):
                date_values.append(details[date_field])

        # nextCollection can be a dict with its own date fields
        next_coll = details.get("nextCollection")
        if isinstance(next_coll, dict):
            for f in ("collectionDate", "nextCollectionDate", "date"):
                if next_coll.get(f):
                    date_values.append(next_coll[f])
        elif isinstance(next_coll, str):
            date_values.append(next_coll)

        # collectionDates is sometimes a list
        for d in (details.get("collectionDates") or []):
            date_values.append(d)

        # futureCollections is a list of dicts or strings
        for entry in (details.get("futureCollections") or []):
            if isinstance(entry, dict):
                date_values.append(
                    entry.get("collectionDate")
                    or entry.get("nextCollectionDate")
                    or entry.get("date")
                )
            else:
                date_values.append(entry)

        for val in date_values:
            parsed = _parse_date(val)
            if parsed and (parsed, label) not in seen:
                seen.add((parsed, label))
                results.append((parsed, label))

    return results


def get_north_herts_bins() -> List[Tuple[datetime, str]]:
    """
    Fetches upcoming bin collections for a North Herts address using the
    Cloud9 Technologies API and returns a List of Tuples
    (collection_date, collection_description).
    """
    postcode = getenv("HOUSE_POSTCODE")
    house_number = getenv("HOUSE_NUMBER")

    if not postcode:
        raise ValueError("HOUSE_POSTCODE environment variable is not set.")

    normalised_postcode = _normalise_postcode(postcode)
    logger.info("Looking up address for postcode: %s", normalised_postcode)

    # Step 1: Look up addresses by postcode
    resp = requests.get(
        f"{API_URL}/addresses",
        headers=HEADERS,
        params={"postcode": normalised_postcode},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    addresses = resp.json().get("addresses", [])

    # Step 2: Select the correct address
    address = _select_address(addresses, house_number)
    uprn = address.get("uprn")
    if not uprn:
        raise ValueError("Selected address does not have a UPRN.")

    logger.info("Found UPRN %s for address: %s",
                uprn, address.get("fullAddress") or address.get("singleLineAddress", ""))

    # Step 3: Fetch waste collections
    resp = requests.get(
        f"{API_URL}/wastecollections/{uprn}",
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    # Step 4: Parse the response
    results = _parse_collections(resp.json())
    logger.info("Found %d bin collection entries.", len(results))

    return results


if __name__ == "__main__":
    result = get_north_herts_bins()
    for date, bin_type in result:
        print(f"{date.strftime('%Y-%m-%d')} - {bin_type}")
