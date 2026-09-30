"""Demo scenarios: each returns a transaction plus its history, ready for FraudEngine."""

CHENNAI = (13.0827, 80.2707)
MUMBAI = (19.0760, 72.8777)


def _tx(tid, user, amount, ts, loc=CHENNAI, receiver=None):
    t = {"transaction_id": tid, "user_id": user, "amount": amount,
         "latitude": loc[0], "longitude": loc[1], "timestamp": ts}
    if receiver:
        t["receiver_id"] = receiver
    return t


def normal():
    return {
        "name": "Normal",
        "description": "Small purchase, same city, no unusual pattern",
        "transaction": _tx("DEMO-N1", "U101", 3000, "2026-09-30T09:50:00"),
        "history": [_tx("DEMO-N0", "U101", 2000, "2026-09-30T09:00:00")],
    }


def high_amount():
    return {
        "name": "High Amount",
        "description": "Single transfer of Rs 1,85,000",
        "transaction": _tx("DEMO-A1", "U102", 185000, "2026-09-30T09:50:00"),
        "history": [_tx("DEMO-A0", "U102", 2000, "2026-09-30T09:00:00")],
    }


def impossible_travel():
    return {
        "name": "Impossible Travel",
        "description": "Chennai then Mumbai one minute later",
        "transaction": _tx("DEMO-G1", "U104", 3000, "2026-09-30T10:01:00", MUMBAI),
        "history": [_tx("DEMO-G0", "U104", 3000, "2026-09-30T10:00:00", CHENNAI)],
    }


def money_mule():
    senders = [_tx(f"DEMO-M{i}", f"S{i}", 20000, f"2026-09-30T10:0{i}:00", receiver="U500")
               for i in range(1, 6)]
    return {
        "name": "Money Mule",
        "description": "5 accounts pay U500, who forwards ~95% within minutes",
        "transaction": _tx("DEMO-M9", "U500", 95000, "2026-09-30T10:10:00", receiver="MULE_OUT"),
        "history": senders,
    }


def combined():
    senders = [_tx(f"DEMO-C{i}", f"S{i}", 40000, f"2026-09-30T10:0{i}:00", receiver="U500")
               for i in range(1, 6)]
    prev = _tx("DEMO-C8", "U500", 1000, "2026-09-30T10:09:00", CHENNAI, receiver="MULE_A")
    return {
        "name": "Combined (CRITICAL)",
        "description": "Mule pattern + high amount + impossible travel",
        "transaction": _tx("DEMO-C9", "U500", 185000, "2026-09-30T10:10:00", MUMBAI, receiver="MULE_B"),
        "history": senders + [prev],
    }


ALL_SCENARIOS = [normal, high_amount, impossible_travel, money_mule, combined]
