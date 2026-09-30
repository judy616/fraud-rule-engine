import json

from app.demo_scenarios import (
    get_scenario,
    list_scenarios,
    run_scenario,
)

REQUIRED_KEYS = {
    "transaction_id", "user_id", "amount",
    "latitude", "longitude", "timestamp", "receiver_id",
}


def test_five_scenarios_exist():
    ids = [s["id"] for s in list_scenarios()]
    assert ids == [
        "normal_transaction", "high_amount", "velocity",
        "impossible_travel", "money_mule",
    ]


def test_all_transactions_use_common_format():
    for item in list_scenarios():
        scenario = get_scenario(item["id"])
        ids = [t["transaction_id"] for t in scenario["transactions"]]
        assert scenario["target_transaction_id"] in ids
        for txn in scenario["transactions"]:
            assert REQUIRED_KEYS <= set(txn)


def test_impossible_travel_scenario_triggers_geo():
    report = run_scenario("impossible_travel")
    assert report["geo_result"]["triggered"] is True
    assert report["geo_result"]["previous_transaction_id"] == "TXN3001"


def test_other_scenarios_do_not_trigger_geo():
    for scenario_id in ["normal_transaction", "high_amount", "velocity", "money_mule"]:
        assert run_scenario(scenario_id)["geo_result"]["triggered"] is False


def test_mule_scenario_is_critical():
    result = run_scenario("money_mule")["mule_result"]
    assert result["user_id"] == "U500"
    assert result["mule_score"] == 100
    assert result["risk_level"] == "CRITICAL"


def test_non_mule_scenarios_are_low():
    for scenario_id in ["normal_transaction", "high_amount", "velocity", "impossible_travel"]:
        assert run_scenario(scenario_id)["mule_result"]["risk_level"] == "LOW"


def test_unknown_scenario_returns_none():
    assert get_scenario("does_not_exist") is None
    assert run_scenario("does_not_exist") is None


def test_reports_are_json_compatible():
    for item in list_scenarios():
        json.dumps(run_scenario(item["id"]))
