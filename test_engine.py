from backend.app.rules.engine import FraudEngine
from backend.app.rules.velocity_rule import VelocityRule
from backend.app.rules.amount_rule import AmountRule
from backend.app.rules.geo_rule import GeoRule
from backend.app.risk.scorer import RiskScorer


def make_tx(txn_id, amount, timestamp, lat=13.0827, lon=80.2707):
    return {
        "transaction_id": txn_id,
        "user_id": "U101",
        "amount": amount,
        "latitude": lat,
        "longitude": lon,
        "timestamp": timestamp
    }


def run_scenario(title, transaction, history):
    rules = [VelocityRule(), AmountRule(), GeoRule()]
    engine = FraudEngine(rules)
    results = engine.evaluate(transaction, history)

    scorer = RiskScorer()
    risk = scorer.calculate(results)

    print(f"\n########## {title} ##########")
    print("\n========== FRAUD ENGINE RESULT ==========")

    for result in results:
        print(f"\nRule: {result['rule']}")
        print(f"Triggered: {result['triggered']}")
        print(f"Score: {result['score']}")
        print(f"Reason: {result['reason']}")

    print("\n========== FINAL RISK ==========")
    print(f"Risk Score: {risk['score']}/100")
    print(f"Risk Level: {risk['level']}")

    print("\nTriggered Rules:")
    for rule in risk["triggered_rules"]:
        print(f"- {rule}")

    print("\nReasons:")
    for reason in risk["reasons"]:
        print(f"- {reason}")


# ---------- Scenario 1: NORMAL (transactions 10 minutes apart) ----------
normal_transaction = make_tx("TXN1001", 3000, "2026-09-30T09:50:00")

normal_history = [
    make_tx("TXN0996", 2000, "2026-09-30T09:00:00"),
    make_tx("TXN0997", 3000, "2026-09-30T09:10:00"),
    make_tx("TXN0998", 2500, "2026-09-30T09:20:00"),
    make_tx("TXN0999", 4000, "2026-09-30T09:30:00"),
    make_tx("TXN1000", 3500, "2026-09-30T09:40:00"),
]

run_scenario("SCENARIO 1: NORMAL (OUTSIDE 5-MIN WINDOW)",
             normal_transaction, normal_history)


# ---------- Scenario 2: SUSPICIOUS (5 transactions within 5 minutes) ----------
suspicious_transaction = make_tx(
    "TXN2001", 185000, "2026-09-30T10:05:00",
    lat=19.0760, lon=72.8777
)

suspicious_history = [
    make_tx("TXN1996", 2000, "2026-09-30T10:01:00"),
    make_tx("TXN1997", 3000, "2026-09-30T10:02:00"),
    make_tx("TXN1998", 2500, "2026-09-30T10:03:00"),
    make_tx("TXN1999", 4000, "2026-09-30T10:03:30"),
    make_tx("TXN2000", 3500, "2026-09-30T10:04:00"),
]

run_scenario("SCENARIO 2: SUSPICIOUS (5+ IN 5 MINUTES)",
             suspicious_transaction, suspicious_history)