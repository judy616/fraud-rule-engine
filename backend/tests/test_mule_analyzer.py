import json

from app.mule.analyzer import (
    MuleAnalyzer,
    build_transaction_graph,
    risk_level_for_score,
)


def txn(txn_id, sender, receiver, amount, timestamp):
    return {
        "transaction_id": txn_id,
        "user_id": sender,
        "receiver_id": receiver,
        "amount": amount,
        "timestamp": timestamp,
        "latitude": 13.0827,
        "longitude": 80.2707,
    }


def mule_pattern():
    """6 accounts pay U500, who forwards ~95% within minutes to 2 accounts."""
    rows = [
        txn(f"IN{i}", f"S{i}", "U500", 10000, f"2026-09-30T10:0{i}:00")
        for i in range(6)
    ]
    rows.append(txn("OUT1", "U500", "R1", 30000, "2026-09-30T10:08:00"))
    rows.append(txn("OUT2", "U500", "R2", 27000, "2026-09-30T10:09:00"))
    return rows


def test_risk_level_boundaries():
    assert risk_level_for_score(0) == "LOW"
    assert risk_level_for_score(29) == "LOW"
    assert risk_level_for_score(30) == "MEDIUM"
    assert risk_level_for_score(49) == "MEDIUM"
    assert risk_level_for_score(50) == "HIGH"
    assert risk_level_for_score(69) == "HIGH"
    assert risk_level_for_score(70) == "CRITICAL"
    assert risk_level_for_score(100) == "CRITICAL"


def test_graph_edge_aggregates_amount_and_count():
    graph = build_transaction_graph(
        [
            txn("T1", "A", "B", 100, "2026-09-30T10:00:00"),
            txn("T2", "A", "B", 200, "2026-09-30T11:00:00"),
        ]
    )
    assert graph["A"]["B"]["total_amount"] == 300
    assert graph["A"]["B"]["transaction_count"] == 2


def test_mule_like_pattern_is_critical():
    result = MuleAnalyzer().analyze_user("U500", mule_pattern())
    assert result["mule_score"] == 100
    assert result["risk_level"] == "CRITICAL"
    assert result["indicators"] == [
        "Many incoming accounts detected",
        "Rapid outgoing transfers detected",
        "High pass-through ratio detected",
        "Multiple counterparties detected",
    ]
    assert result["metrics"]["incoming_accounts"] == 6


def test_normal_user_is_low():
    rows = [
        txn("T1", "U101", "U205", 500, "2026-09-30T10:00:00"),
        txn("T2", "U101", "U205", 700, "2026-09-30T12:00:00"),
    ]
    result = MuleAnalyzer().analyze_user("U101", rows)
    assert result["mule_score"] == 0
    assert result["risk_level"] == "LOW"
    assert result["indicators"] == []


def test_slow_forwarding_has_no_rapid_indicator():
    rows = [
        txn(f"IN{i}", f"S{i}", "U500", 10000, "2026-09-27T10:00:00")
        for i in range(5)
    ]
    rows.append(txn("OUT1", "U500", "R1", 50000, "2026-09-30T10:00:00"))  # 3 days later
    result = MuleAnalyzer().analyze_user("U500", rows)
    assert "Rapid outgoing transfers detected" not in result["indicators"]
    assert "High pass-through ratio detected" in result["indicators"]


def test_malformed_data_does_not_crash():
    rows = [
        None,
        "not a dict",
        {},
        {"user_id": "A"},
        txn("T1", "A", "B", "abc", "bad-date"),   # bad amount -> skipped
        txn("T2", "A", "B", 100, "bad-date"),     # bad timestamp -> still counted
        txn("T3", "B", "B", 100, "2026-09-30T10:00:00"),  # self transfer -> skipped
    ]
    result = MuleAnalyzer().analyze_user("B", rows)
    assert result["metrics"]["incoming_accounts"] == 1
    assert result["risk_level"] == "LOW"


def test_empty_transactions():
    analyzer = MuleAnalyzer()
    assert analyzer.analyze_user("U1", [])["mule_score"] == 0
    assert analyzer.analyze_user("U1", None)["risk_level"] == "LOW"


def test_result_is_json_compatible():
    result = MuleAnalyzer().analyze_user("U500", mule_pattern())
    json.dumps(result)  # raises if anything is not JSON-compatible
    assert "not proof" in result["disclaimer"]
