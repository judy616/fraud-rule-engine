"""
Demo scenarios for SENTINEL, in the common transaction format.

Five scenarios: normal, high amount, velocity, impossible travel, money mule.
Each scenario is a plain dictionary:
    id, name, description, expected_rules, target_transaction_id, transactions

Usage (Person 2 / Person 3):
    from app.demo_scenarios import list_scenarios, get_scenario, run_scenario
    scenario = get_scenario("impossible_travel")
    report = run_scenario("money_mule")   # runs Geo + Mule modules only

Quick look from the backend folder:
    python -m app.demo_scenarios
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Any

from app.geo.detector import detect_impossible_geo
from app.mule.analyzer import MuleAnalyzer

CHENNAI = (13.0827, 80.2707)
DELHI = (28.6139, 77.2090)

BASE_TIME = datetime(2026, 9, 30, 10, 0, 0)


def _txn(
    txn_id: str,
    user_id: str,
    receiver_id: str,
    amount: float,
    minutes: int,
    place: tuple[float, float] = CHENNAI,
) -> dict[str, Any]:
    """Build one transaction in the common format. `minutes` is offset from 10:00."""
    return {
        "transaction_id": txn_id,
        "user_id": user_id,
        "amount": amount,
        "latitude": place[0],
        "longitude": place[1],
        "timestamp": (BASE_TIME + timedelta(minutes=minutes)).isoformat(),
        "receiver_id": receiver_id,
    }


def _build_scenarios() -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}

    # 1. Normal: small, regular payments from one city.
    scenarios["normal_transaction"] = {
        "id": "normal_transaction",
        "name": "Normal transaction",
        "description": "Small everyday payment from the user's usual city.",
        "expected_rules": [],
        "target_transaction_id": "TXN0003",
        "transactions": [
            _txn("TXN0001", "U100", "U200", 1200, -1440),  # yesterday
            _txn("TXN0002", "U100", "U201", 800, -240),
            _txn("TXN0003", "U100", "U200", 1500, 0),
        ],
    }

    # 2. High amount: far above the user's usual spending.
    scenarios["high_amount"] = {
        "id": "high_amount",
        "name": "High amount",
        "description": "User usually sends a few thousand, then sends 185,000.",
        "expected_rules": ["AMOUNT_ANOMALY"],
        "target_transaction_id": "TXN1001",
        "transactions": [
            _txn("TXN0901", "U101", "U205", 2500, -2880),
            _txn("TXN0902", "U101", "U205", 3200, -1440),
            _txn("TXN0903", "U101", "U206", 2800, -720),
            _txn("TXN1001", "U101", "U205", 185000, 15),
        ],
    }

    # 3. Velocity: many transactions in a few minutes.
    scenarios["velocity"] = {
        "id": "velocity",
        "name": "Velocity",
        "description": "Six transactions within five minutes.",
        "expected_rules": ["VELOCITY"],
        "target_transaction_id": "TXN2006",
        "transactions": [
            _txn(f"TXN200{i + 1}", "U102", "U210", 4000, i) for i in range(6)
        ],
    }

    # 4. Impossible travel: Chennai then Delhi 10 minutes later.
    scenarios["impossible_travel"] = {
        "id": "impossible_travel",
        "name": "Impossible travel",
        "description": "Transaction in Chennai, then Delhi only 10 minutes later.",
        "expected_rules": ["IMPOSSIBLE_GEO"],
        "target_transaction_id": "TXN3002",
        "transactions": [
            _txn("TXN3001", "U103", "U220", 5000, 0, CHENNAI),
            _txn("TXN3002", "U103", "U221", 6000, 10, DELHI),
        ],
    }

    # 5. Money mule: 6 accounts pay U500, who forwards ~95% within minutes.
    mule_txns = [
        _txn(f"TXN500{i + 1}", f"U50{i + 1}", "U500", 10000, i) for i in range(6)
    ]
    mule_txns.append(_txn("TXN5007", "U500", "U601", 30000, 8))
    mule_txns.append(_txn("TXN5008", "U500", "U602", 27000, 9))
    scenarios["money_mule"] = {
        "id": "money_mule",
        "name": "Money mule",
        "description": (
            "Six accounts send money to U500, who quickly forwards most of it "
            "to two other accounts (mule-like behaviour)."
        ),
        "expected_rules": ["MULE_RISK"],
        "target_transaction_id": "TXN5008",
        "transactions": mule_txns,
    }

    return scenarios


_SCENARIOS = _build_scenarios()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def list_scenarios() -> list[dict[str, Any]]:
    """Short summary of every scenario (no transactions), for a dropdown."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "expected_rules": list(s["expected_rules"]),
            "transaction_count": len(s["transactions"]),
        }
        for s in _SCENARIOS.values()
    ]


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    """Return a copy of one scenario, or None if the id is unknown."""
    scenario = _SCENARIOS.get(scenario_id)
    return copy.deepcopy(scenario) if scenario else None


def get_target_transaction(scenario: dict[str, Any]) -> dict[str, Any] | None:
    """The transaction the scenario is about."""
    for txn in scenario["transactions"]:
        if txn["transaction_id"] == scenario["target_transaction_id"]:
            return txn
    return None


def run_scenario(scenario_id: str) -> dict[str, Any] | None:
    """
    Run ONLY the Geo and Mule modules on a scenario.
    High amount and velocity are Person 1's rules, so they are not run here.
    """
    scenario = get_scenario(scenario_id)
    if scenario is None:
        return None

    target = get_target_transaction(scenario)
    if target is None:
        return None

    geo = detect_impossible_geo(target, scenario["transactions"])
    mule = MuleAnalyzer().analyze_user(target["user_id"], scenario["transactions"])
    return {"scenario": scenario, "geo_result": geo, "mule_result": mule}


if __name__ == "__main__":
    for item in list_scenarios():
        report = run_scenario(item["id"])
        geo, mule = report["geo_result"], report["mule_result"]
        print(
            f"{item['id']:<20} geo_triggered={str(geo['triggered']):<5} "
            f"mule_score={mule['mule_score']:>3} {mule['risk_level']}"
        )
