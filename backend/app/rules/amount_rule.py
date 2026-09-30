from .base import FraudRule


class AmountRule(FraudRule):

    THRESHOLD = 100000

    def evaluate(self, transaction, history):

        amount = transaction["amount"]

        if amount > self.THRESHOLD:
            return {
                "rule": "Amount Anomaly",
                "triggered": True,
                "score": 25,
                "reason": (
                    f"Transaction amount ₹{amount:,} "
                    f"exceeds threshold of ₹{self.THRESHOLD:,}"
                )
            }

        return {
            "rule": "Amount Anomaly",
            "triggered": False,
            "score": 0,
            "reason": "Transaction amount is within the configured threshold"
        }