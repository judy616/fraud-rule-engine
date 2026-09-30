from .base import FraudRule

# Reuse Person 4's Mule Intelligence. No graph logic lives here.
from ..mule.analyzer import MuleAnalyzer


class MuleRule(FraudRule):

    RULE_NAME = "Money Mule Pattern"
    SCORE = 30
    MIN_MULE_SCORE = 50   # HIGH or above triggers the rule

    def __init__(self):
        self.analyzer = MuleAnalyzer()

    def evaluate(self, transaction, history):

        # Full transaction picture = history + the current transaction
        current_id = transaction.get("transaction_id")
        all_txns = [
            tx for tx in (history or [])
            if current_id is None or tx.get("transaction_id") != current_id
        ]
        all_txns.append(transaction)

        # Check the sender, and the receiver if present, and use the riskier one
        accounts = [transaction.get("user_id"), transaction.get("receiver_id")]
        best = None
        for account in accounts:
            if account is None:
                continue
            result = self.analyzer.analyze_user(account, all_txns)
            if best is None or result["mule_score"] > best["mule_score"]:
                best = result

        if best is None:
            return {
                "rule": self.RULE_NAME,
                "triggered": False,
                "score": 0,
                "reason": "No account information available for mule analysis",
            }

        if best["mule_score"] >= self.MIN_MULE_SCORE:
            return {
                "rule": self.RULE_NAME,
                "triggered": True,
                "score": self.SCORE,
                "reason": (
                    f"Money-mule-like behaviour on account {best['user_id']}: "
                    f"mule score {best['mule_score']}/100 ({best['risk_level']}) - "
                    + "; ".join(best["indicators"])
                ),
                "details": best,
            }

        return {
            "rule": self.RULE_NAME,
            "triggered": False,
            "score": 0,
            "reason": "No money-mule-like behaviour detected",
            "details": best,
        }
