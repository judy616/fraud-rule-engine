from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2


# --------------------------------------------------
# 1. BASE RULE
# --------------------------------------------------

class FraudRule:
    name = "Base Rule"

    def evaluate(self, transaction, history):
        raise NotImplementedError


# --------------------------------------------------
# 2. AMOUNT RULE
# --------------------------------------------------

class AmountRule(FraudRule):
    name = "High Amount Rule"

    def evaluate(self, transaction, history):
        amount = transaction["amount"]

        if amount >= 100000:
            return {
                "rule": self.name,
                "triggered": True,
                "score": 25,
                "reason": f"Transaction amount ₹{amount:,.0f} is unusually high."
            }

        return {
            "rule": self.name,
            "triggered": False,
            "score": 0,
            "reason": "Transaction amount is within normal range."
        }


# --------------------------------------------------
# 3. VELOCITY RULE
# --------------------------------------------------

class VelocityRule(FraudRule):
    name = "Transaction Velocity Rule"

    def evaluate(self, transaction, history):
        user_id = transaction["user_id"]
        current_time = transaction["timestamp"]

        recent_count = 0

        for old_transaction in history:
            if old_transaction["user_id"] != user_id:
                continue

            old_time = old_transaction["timestamp"]

            difference = current_time - old_time

            if timedelta(0) <= difference <= timedelta(minutes=5):
                recent_count += 1

        # +1 because we are checking the current transaction too
        total_transactions = recent_count + 1

        if total_transactions >= 5:
            return {
                "rule": self.name,
                "triggered": True,
                "score": 30,
                "reason": f"{total_transactions} transactions detected within 5 minutes."
            }

        return {
            "rule": self.name,
            "triggered": False,
            "score": 0,
            "reason": "Transaction frequency is normal."
        }


# --------------------------------------------------
# 4. GEO / IMPOSSIBLE TRAVEL RULE
# --------------------------------------------------

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates
    using the Haversine formula.
    """

    earth_radius = 6371  # km

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius * c


class GeoRule(FraudRule):
    name = "Impossible Travel Rule"

    def evaluate(self, transaction, history):

        user_id = transaction["user_id"]

        previous_transactions = [
            t for t in history
            if t["user_id"] == user_id
        ]

        if not previous_transactions:
            return {
                "rule": self.name,
                "triggered": False,
                "score": 0,
                "reason": "No previous location available."
            }

        # Get latest transaction
        previous = max(
            previous_transactions,
            key=lambda x: x["timestamp"]
        )

        distance = calculate_distance(
            previous["latitude"],
            previous["longitude"],
            transaction["latitude"],
            transaction["longitude"]
        )

        time_difference = (
            transaction["timestamp"] - previous["timestamp"]
        ).total_seconds() / 3600

        if time_difference <= 0:
            return {
                "rule": self.name,
                "triggered": False,
                "score": 0,
                "reason": "Invalid time difference."
            }

        speed = distance / time_difference

        # Example threshold:
        # 800 km/h is treated as suspicious
        if speed > 800:

            return {
                "rule": self.name,
                "triggered": True,
                "score": 30,
                "reason": (
                    f"Impossible travel detected: "
                    f"{distance:.0f} km in "
                    f"{time_difference * 60:.0f} minutes."
                )
            }

        return {
            "rule": self.name,
            "triggered": False,
            "score": 0,
            "reason": "Location movement appears normal."
        }


# --------------------------------------------------
# 5. FRAUD ENGINE
# --------------------------------------------------

class FraudEngine:

    def __init__(self):

        self.rules = [
            AmountRule(),
            VelocityRule(),
            GeoRule()
        ]

    def analyze(self, transaction, history):

        results = []
        total_score = 0

        for rule in self.rules:

            result = rule.evaluate(
                transaction,
                history
            )

            results.append(result)

            total_score += result["score"]

        # Maximum score = 85 in our current rules
        total_score = min(total_score, 100)

        if total_score >= 60:
            risk_level = "HIGH"

        elif total_score >= 30:
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"

        return {
            "risk_score": total_score,
            "risk_level": risk_level,
            "rules": results
        }