from datetime import datetime, timedelta, timezone

from .base import FraudRule


class VelocityRule(FraudRule):

    MAX_TRANSACTIONS = 5          # previous transactions allowed in the window
    WINDOW_MINUTES = 5            # size of the time window

    def _parse_time(self, value):
        """
        Convert a timestamp into a datetime object.
        Accepts a datetime or an ISO string like "2026-09-30T10:15:00".
        """
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))

        # Make timezone-aware and naive timestamps comparable
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)

        return value

    def evaluate(self, transaction, history):

        user_id = transaction["user_id"]

        # Without a timestamp we cannot check the time window
        if "timestamp" not in transaction:
            return {
                "rule": "Transaction Velocity",
                "triggered": False,
                "score": 0,
                "reason": "No timestamp available to check transaction velocity"
            }

        current_time = self._parse_time(transaction["timestamp"])
        window = timedelta(minutes=self.WINDOW_MINUTES)

        # Same user + inside the 5-minute window before this transaction
        recent_transactions = []

        for tx in history:
            if tx["user_id"] != user_id:
                continue

            if "timestamp" not in tx:
                continue

            tx_time = self._parse_time(tx["timestamp"])
            time_difference = current_time - tx_time

            if timedelta(0) <= time_difference <= window:
                recent_transactions.append(tx)

        count = len(recent_transactions)

        if count >= self.MAX_TRANSACTIONS:
            return {
                "rule": "Transaction Velocity",
                "triggered": True,
                "score": 30,
                "reason": (
                    f"{count + 1} transactions detected "
                    f"for user {user_id} within {self.WINDOW_MINUTES} minutes"
                )
            }

        return {
            "rule": "Transaction Velocity",
            "triggered": False,
            "score": 0,
            "reason": "Transaction frequency is within the normal range"
        }