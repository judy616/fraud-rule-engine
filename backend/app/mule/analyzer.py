from __future__ import annotations

import math
from statistics import median
from typing import Any

import networkx as nx

from ..geo.detector import parse_timestamp

DEFAULT_CONFIG: dict[str, float] = {
    "incoming_low": 3,
    "incoming_full": 5,
    "counterparties_low": 4,
    "counterparties_full": 6,
    "pass_through_low": 0.7,
    "pass_through_full": 0.9,
    "hold_hours_low": 6.0,
    "hold_hours_full": 1.0,
}

WEIGHTS: dict[str, int] = {
    "incoming": 25,
    "rapid_outgoing": 25,
    "pass_through": 30,
    "counterparties": 20,
}

INDICATOR_TEXT: dict[str, str] = {
    "incoming": "Many incoming accounts detected",
    "rapid_outgoing": "Rapid outgoing transfers detected",
    "pass_through": "High pass-through ratio detected",
    "counterparties": "Multiple counterparties detected",
}

DISCLAIMER = (
    "Mule Risk Score indicates mule-like behaviour only. It is not proof "
    "that the account holder is a money mule. Human review is required."
)


def risk_level_for_score(score):
    if score >= 70:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def _clean_transactions(transactions):
    cleaned = []
    if not isinstance(transactions, (list, tuple)):
        return cleaned
    for txn in transactions:
        if not isinstance(txn, dict):
            continue
        sender = txn.get("user_id")
        receiver = txn.get("receiver_id")
        if sender is None or receiver is None:
            continue
        sender, receiver = str(sender).strip(), str(receiver).strip()
        if not sender or not receiver or sender == receiver:
            continue
        try:
            amount = float(txn.get("amount"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(amount) or amount <= 0:
            continue
        cleaned.append({
            "transaction_id": txn.get("transaction_id"),
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "timestamp": parse_timestamp(txn.get("timestamp")),
        })
    return cleaned


def _graph_from_cleaned(cleaned):
    graph = nx.DiGraph()
    for txn in cleaned:
        s, r = txn["sender"], txn["receiver"]
        if graph.has_edge(s, r):
            edge = graph[s][r]
            edge["total_amount"] += txn["amount"]
            edge["transaction_count"] += 1
            edge["transaction_ids"].append(txn["transaction_id"])
        else:
            graph.add_edge(
                s, r,
                total_amount=txn["amount"],
                transaction_count=1,
                transaction_ids=[txn["transaction_id"]],
            )
    return graph


def build_transaction_graph(transactions):
    return _graph_from_cleaned(_clean_transactions(transactions))


def _tier_points(value, low, full, weight, lower_is_better=False):
    if value is None:
        return 0.0
    if lower_is_better:
        if value <= full:
            return float(weight)
        if value <= low:
            return weight / 2
        return 0.0
    if value >= full:
        return float(weight)
    if value >= low:
        return weight / 2
    return 0.0


class MuleAnalyzer:
    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}

    def analyze_user(self, user_id: Any, transactions: Any) -> dict[str, Any]:
        user = str(user_id).strip()
        cleaned = _clean_transactions(transactions)
        graph = _graph_from_cleaned(cleaned)

        if user not in graph:
            return self._empty_result(user)

        incoming = [t for t in cleaned if t["receiver"] == user]
        outgoing = [t for t in cleaned if t["sender"] == user]

        incoming_accounts = {t["sender"] for t in incoming}
        outgoing_accounts = {t["receiver"] for t in outgoing}
        counterparties = incoming_accounts | outgoing_accounts

        total_in = sum(t["amount"] for t in incoming)
        total_out = sum(t["amount"] for t in outgoing)
        pass_through = min(total_out, total_in) / total_in if total_in > 0 else 0.0
        median_hold = self._median_holding_hours(incoming, outgoing)

        cfg = self.config
        points = {
            "incoming": _tier_points(
                len(incoming_accounts), cfg["incoming_low"], cfg["incoming_full"],
                WEIGHTS["incoming"]),
            "rapid_outgoing": _tier_points(
                median_hold, cfg["hold_hours_low"], cfg["hold_hours_full"],
                WEIGHTS["rapid_outgoing"], lower_is_better=True),
            "pass_through": _tier_points(
                pass_through, cfg["pass_through_low"], cfg["pass_through_full"],
                WEIGHTS["pass_through"]),
            "counterparties": _tier_points(
                len(counterparties), cfg["counterparties_low"],
                cfg["counterparties_full"], WEIGHTS["counterparties"]),
        }

        indicators = [INDICATOR_TEXT[k] for k in INDICATOR_TEXT if points[k] > 0]
        score = min(100, int(round(sum(points.values()))))
        level = risk_level_for_score(score)

        return {
            "user_id": user,
            "mule_score": score,
            "risk_level": level,
            "indicators": indicators,
            "summary": self._summary(level, indicators),
            "score_breakdown": {k: round(v, 1) for k, v in points.items()},
            "metrics": {
                "incoming_accounts": len(incoming_accounts),
                "outgoing_accounts": len(outgoing_accounts),
                "counterparties": len(counterparties),
                "incoming_transactions": len(incoming),
                "outgoing_transactions": len(outgoing),
                "total_incoming_amount": round(total_in, 2),
                "total_outgoing_amount": round(total_out, 2),
                "pass_through_ratio": round(pass_through, 4),
                "median_holding_hours": (
                    None if median_hold is None else round(median_hold, 4)),
            },
            "network": self._neighbourhood(graph, user),
            "disclaimer": DISCLAIMER,
        }

    @staticmethod
    def _median_holding_hours(incoming, outgoing):
        in_times = sorted(t["timestamp"] for t in incoming if t["timestamp"])
        holds = []
        for out in outgoing:
            out_time = out["timestamp"]
            if out_time is None:
                continue
            earlier = [t for t in in_times if t <= out_time]
            if earlier:
                holds.append((out_time - earlier[-1]).total_seconds() / 3600)
        return median(holds) if holds else None

    @staticmethod
    def _neighbourhood(graph, user):
        ego = nx.ego_graph(graph, user, radius=1, undirected=True)
        return {
            "nodes": sorted(ego.nodes()),
            "edges": [
                {
                    "source": s,
                    "target": r,
                    "total_amount": round(d["total_amount"], 2),
                    "transaction_count": d["transaction_count"],
                }
                for s, r, d in ego.edges(data=True)
            ],
        }

    @staticmethod
    def _summary(level, indicators):
        if not indicators:
            return "No mule-like behaviour indicators found."
        return (
            f"Mule Risk {level}: {len(indicators)} mule-like behaviour "
            "indicator(s) found in this suspicious transaction network."
        )

    @staticmethod
    def _empty_result(user):
        return {
            "user_id": user,
            "mule_score": 0,
            "risk_level": "LOW",
            "indicators": [],
            "summary": "No valid transaction activity found for this user.",
            "score_breakdown": {k: 0.0 for k in WEIGHTS},
            "metrics": {
                "incoming_accounts": 0,
                "outgoing_accounts": 0,
                "counterparties": 0,
                "incoming_transactions": 0,
                "outgoing_transactions": 0,
                "total_incoming_amount": 0.0,
                "total_outgoing_amount": 0.0,
                "pass_through_ratio": 0.0,
                "median_holding_hours": None,
            },
            "network": {"nodes": [], "edges": []},
            "disclaimer": DISCLAIMER,
        }
