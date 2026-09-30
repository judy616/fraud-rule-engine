from app.geo.detector import (
    check_impossible_travel,
    detect_impossible_geo,
    haversine_km,
)

CHENNAI = (13.0827, 80.2707)
DELHI = (28.6139, 77.2090)
BENGALURU = (12.9716, 77.5946)


def make_txn(txn_id, user, place, timestamp):
    return {
        "transaction_id": txn_id,
        "user_id": user,
        "amount": 1000,
        "latitude": place[0],
        "longitude": place[1],
        "timestamp": timestamp,
        "receiver_id": "U205",
    }


def test_haversine_chennai_to_delhi():
    distance = haversine_km(*CHENNAI, *DELHI)
    assert 1700 < distance < 1800


def test_impossible_travel_chennai_to_delhi_in_10_minutes():
    a = make_txn("T1", "U101", CHENNAI, "2026-09-30T10:00:00")
    b = make_txn("T2", "U101", DELHI, "2026-09-30T10:10:00")
    result = check_impossible_travel(a, b)
    assert result["triggered"] is True
    assert result["speed_kmh"] > 5000
    assert result["reason"] == "Impossible geographical movement detected"


def test_plausible_travel_is_not_triggered():
    a = make_txn("T1", "U101", CHENNAI, "2026-09-30T06:00:00")
    b = make_txn("T2", "U101", BENGALURU, "2026-09-30T12:00:00")
    result = check_impossible_travel(a, b)
    assert result["triggered"] is False


def test_custom_speed_threshold():
    a = make_txn("T1", "U101", CHENNAI, "2026-09-30T10:00:00")
    b = make_txn("T2", "U101", BENGALURU, "2026-09-30T11:00:00")  # ~290 km/h
    assert check_impossible_travel(a, b)["triggered"] is False
    assert check_impossible_travel(a, b, max_speed_kmh=200)["triggered"] is True


def test_malformed_timestamp_does_not_crash():
    a = make_txn("T1", "U101", CHENNAI, "not-a-date")
    b = make_txn("T2", "U101", DELHI, "2026-09-30T10:10:00")
    result = check_impossible_travel(a, b)
    assert result["triggered"] is False
    assert "skipped" in result["reason"]


def test_missing_coordinates_does_not_crash():
    a = {"transaction_id": "T1", "user_id": "U101", "timestamp": "2026-09-30T10:00:00"}
    b = make_txn("T2", "U101", DELHI, "2026-09-30T10:10:00")
    result = check_impossible_travel(a, b)
    assert result["triggered"] is False


def test_same_time_different_places_is_triggered():
    a = make_txn("T1", "U101", CHENNAI, "2026-09-30T10:00:00")
    b = make_txn("T2", "U101", DELHI, "2026-09-30T10:00:00")
    result = check_impossible_travel(a, b)
    assert result["triggered"] is True
    assert result["speed_kmh"] is None


def test_detect_uses_latest_previous_txn_of_same_user():
    history = [
        make_txn("T1", "U101", BENGALURU, "2026-09-30T06:00:00"),  # older
        make_txn("T2", "U101", CHENNAI, "2026-09-30T10:05:00"),    # latest, same user
        make_txn("T9", "U999", DELHI, "2026-09-30T10:10:00"),      # other user
    ]
    current = make_txn("T3", "U101", DELHI, "2026-09-30T10:15:00")
    result = detect_impossible_geo(current, history)
    assert result["triggered"] is True
    assert result["previous_transaction_id"] == "T2"
    assert result["current_transaction_id"] == "T3"


def test_detect_with_no_history():
    current = make_txn("T3", "U101", DELHI, "2026-09-30T10:15:00")
    assert detect_impossible_geo(current, [])["triggered"] is False
    assert detect_impossible_geo(current, None)["triggered"] is False
