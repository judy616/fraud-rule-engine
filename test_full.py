from backend.app.rules.engine import FraudEngine
from backend.app.rules.velocity_rule import VelocityRule
from backend.app.rules.amount_rule import AmountRule
from backend.app.rules.geo_rule import GeoRule
from backend.app.rules.mule_rule import MuleRule
from backend.app.risk.scorer import RiskScorer

CHENNAI = (13.0827, 80.2707)
MUMBAI = (19.0760, 72.8777)


def tx(tid, user, amount, ts, loc=CHENNAI, receiver=None):
    t = {"transaction_id": tid, "user_id": user, "amount": amount,
         "latitude": loc[0], "longitude": loc[1], "timestamp": ts}
    if receiver:
        t["receiver_id"] = receiver
    return t


def run(title, txn, history, expect_score, expect_level):
    engine = FraudEngine([VelocityRule(), AmountRule(), GeoRule(), MuleRule()])
    risk = RiskScorer().calculate(engine.evaluate(txn, history))
    ok = risk["score"] == expect_score and risk["level"] == expect_level
    print(f"\n[{'PASS' if ok else 'FAIL'}] {title}: {risk['score']}/100 {risk['level']}"
          f" (expected {expect_score} {expect_level})")
    for r in risk["reasons"]:
        print("   -", r)


# 1. Normal
run("Normal", tx("N1", "U101", 3000, "2026-09-30T09:50:00"),
    [tx("N0", "U101", 2000, "2026-09-30T09:00:00")], 0, "LOW")

# 2. High amount only
run("High amount", tx("A1", "U102", 185000, "2026-09-30T09:50:00"),
    [tx("A0", "U102", 2000, "2026-09-30T09:00:00")], 25, "LOW")

# 3. Velocity only
vel_hist = [tx(f"V{i}", "U103", 2000, f"2026-09-30T10:0{i}:00") for i in range(1, 6)]
run("Velocity", tx("V9", "U103", 2000, "2026-09-30T10:05:00"), vel_hist, 30, "MEDIUM")

# 4. Impossible travel only
run("Impossible travel", tx("G1", "U104", 3000, "2026-09-30T10:01:00", MUMBAI),
    [tx("G0", "U104", 3000, "2026-09-30T10:00:00", CHENNAI)], 30, "MEDIUM")

# 5. Money mule only (5 senders -> U500 -> onward, fast, ~95% passed on)
senders = [tx(f"M{i}", f"S{i}", 20000, f"2026-09-30T10:0{i}:00", receiver="U500")
           for i in range(1, 6)]
run("Money mule", tx("M9", "U500", 95000, "2026-09-30T10:10:00", receiver="MULE_OUT"),
    senders, 30, "MEDIUM")

# 6. Combined: mule + high amount + impossible travel
senders2 = [tx(f"C{i}", f"S{i}", 40000, f"2026-09-30T10:0{i}:00", receiver="U500")
            for i in range(1, 6)]
prev = tx("C8", "U500", 1000, "2026-09-30T10:09:00", CHENNAI, receiver="MULE_A")
run("Combined", tx("C9", "U500", 185000, "2026-09-30T10:10:00", MUMBAI, receiver="MULE_B"),
    senders2 + [prev], 85, "CRITICAL")
