"""
Geo Intelligence: detects impossible geographical movement between transactions.

Idea: if the same user transacts in two places, we can compute the distance
between them (Haversine) and the time between them. Distance / time gives the
implied travel speed. If that speed is faster than a realistic maximum
(default: a commercial flight, ~900 km/h), the movement is flagged.

Main functions for the rest of the team:
    - detect_impossible_geo(current_txn, history)   -> check one txn vs. history
    - check_impossible_travel(txn_a, txn_b)         -> check exactly two txns
    - haversine_km(lat1, lon1, lat2, lon2)          -> raw distance helper

All results are plain JSON-compatible dictionaries.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Configuration (pass different values into the functions to override)
# ---------------------------------------------------------------------------
DEFAULT_MAX_SPEED_KMH = 900.0   # roughly a commercial flight
DEFAULT_MIN_DISTANCE_KM = 50.0  # ignore tiny moves (GPS jitter, same city)
EARTH_RADIUS_KM = 6371.0088

RULE_NAME = "IMPOSSIBLE_GEO"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _to_float(value: Any) -> float | None:
    """Convert to a finite float, or return None if impossible."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_timestamp(value: Any) -> datetime | None:
    """
    Parse an ISO-8601 string (or datetime) into a naive UTC datetime.
    Returns None for missing or malformed values instead of raising.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip())  # handles 'Z' on 3.11+
        except ValueError:
            return None
    else:
        return None

    # Normalise so aware and naive datetimes can be subtracted safely.
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _read_point(txn: Any) -> tuple[tuple[float, float, datetime] | None, str | None]:
    """
    Extract (latitude, longitude, timestamp) from a transaction dict.
    Returns (point, None) on success or (None, error_message) on failure.
    """
    if not isinstance(txn, dict):
        return None, "transaction is not a dictionary"

    lat = _to_float(txn.get("latitude"))
    lon = _to_float(txn.get("longitude"))
    if lat is None or lon is None:
        return None, "missing or invalid coordinates"
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, "coordinates out of range"

    ts = parse_timestamp(txn.get("timestamp"))
    if ts is None:
        return None, "missing or malformed timestamp"

    return (lat, lon, ts), None


def _build_result(
    triggered: bool,
    reason: str,
    distance_km: float | None = None,
    time_hours: float | None = None,
    speed_kmh: float | None = None,
    max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
    previous_transaction_id: Any = None,
    current_transaction_id: Any = None,
) -> dict[str, Any]:
    """Every result has the same keys, so callers never hit a KeyError."""
    return {
        "rule_name": RULE_NAME,
        "triggered": triggered,
        "distance_km": None if distance_km is None else round(distance_km, 2),
        "time_hours": None if time_hours is None else round(time_hours, 4),
        "speed_kmh": None if speed_kmh is None else round(speed_kmh, 2),
        "max_speed_kmh": max_speed_kmh,
        "reason": reason,
        "previous_transaction_id": previous_transaction_id,
        "current_transaction_id": current_transaction_id,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def check_impossible_travel(
    txn_a: dict[str, Any],
    txn_b: dict[str, Any],
    max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
    min_distance_km: float = DEFAULT_MIN_DISTANCE_KM,
) -> dict[str, Any]:
    """
    Compare two transactions and decide whether the movement between them
    is physically impossible. Order of arguments does not matter; the
    earlier transaction (by timestamp) is treated as 'previous'.
    """
    # Fall back to the default if someone passes a nonsense threshold.
    max_speed = _to_float(max_speed_kmh)
    if max_speed is None or max_speed <= 0:
        max_speed = DEFAULT_MAX_SPEED_KMH
    min_distance = _to_float(min_distance_km)
    if min_distance is None or min_distance < 0:
        min_distance = DEFAULT_MIN_DISTANCE_KM

    point_a, error_a = _read_point(txn_a)
    point_b, error_b = _read_point(txn_b)
    error = error_a or error_b
    if error or point_a is None or point_b is None:
        return _build_result(
            False, f"Geo check skipped: {error}", max_speed_kmh=max_speed
        )

    # Make sure 'first' is the earlier transaction.
    if point_a[2] > point_b[2]:
        txn_a, txn_b = txn_b, txn_a
        point_a, point_b = point_b, point_a

    first_id = txn_a.get("transaction_id")
    second_id = txn_b.get("transaction_id")

    distance = haversine_km(point_a[0], point_a[1], point_b[0], point_b[1])
    hours = (point_b[2] - point_a[2]).total_seconds() / 3600

    common = dict(
        distance_km=distance,
        time_hours=hours,
        max_speed_kmh=max_speed,
        previous_transaction_id=first_id,
        current_transaction_id=second_id,
    )

    # Very short distances are not meaningful (same city, GPS noise).
    if distance < min_distance:
        return _build_result(
            False, "Distance too small to be considered suspicious", **common
        )

    # Different places at the same instant: speed would be infinite.
    # We return speed_kmh=None because infinity is not JSON-compatible.
    if hours <= 0:
        return _build_result(
            True,
            "Impossible geographical movement detected: "
            "transactions at different locations at the same time",
            speed_kmh=None,
            **common,
        )

    speed = distance / hours
    if speed > max_speed:
        return _build_result(
            True,
            "Impossible geographical movement detected",
            speed_kmh=speed,
            **common,
        )

    return _build_result(
        False, "Travel speed is physically plausible", speed_kmh=speed, **common
    )


def detect_impossible_geo(
    current_txn: dict[str, Any],
    history: list[dict[str, Any]] | None,
    max_speed_kmh: float = DEFAULT_MAX_SPEED_KMH,
    min_distance_km: float = DEFAULT_MIN_DISTANCE_KM,
) -> dict[str, Any]:
    """
    Main entry point for Person 2 / Person 1.

    Compares `current_txn` with the same user's most recent earlier
    transaction that has valid coordinates and timestamp.

    `history` may contain any transactions (other users, later ones, the
    current one itself); irrelevant entries are skipped automatically.
    """
    current_point, error = _read_point(current_txn)
    if error or current_point is None:
        return _build_result(
            False, f"Geo check skipped: {error}", max_speed_kmh=max_speed_kmh
        )

    current_user = current_txn.get("user_id")
    current_id = current_txn.get("transaction_id")

    best_txn: dict[str, Any] | None = None
    best_time: datetime | None = None

    for txn in history or []:
        point, err = _read_point(txn)
        if err or point is None:
            continue  # skip malformed history entries
        if current_user is not None and txn.get("user_id") != current_user:
            continue  # only compare a user with their own history
        if current_id is not None and txn.get("transaction_id") == current_id:
            continue  # don't compare a transaction with itself
        if point[2] > current_point[2]:
            continue  # only look at earlier (or simultaneous) transactions
        if best_time is None or point[2] > best_time:
            best_txn, best_time = txn, point[2]

    if best_txn is None:
        return _build_result(
            False,
            "No previous valid transaction available for comparison",
            max_speed_kmh=max_speed_kmh,
            current_transaction_id=current_id,
        )

    return check_impossible_travel(
        best_txn, current_txn, max_speed_kmh, min_distance_km
    )