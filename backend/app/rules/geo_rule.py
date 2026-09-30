from .base import FraudRule

# Reuse Person 4's Geo Intelligence. No Haversine / travel logic lives here.
from ..geo.detector import detect_impossible_geo


class GeoRule(FraudRule):

    RULE_NAME = "Geographical Anomaly"
    SCORE = 30

    def evaluate(self, transaction, history):

        # Delegate all distance / time / speed logic to the geo detector
        geo = detect_impossible_geo(transaction, history)

        if geo.get("triggered"):
            distance = geo.get("distance_km") or 0.0
            hours = geo.get("time_hours") or 0.0
            speed = geo.get("speed_kmh")
            max_speed = geo.get("max_speed_kmh") or 0.0

            if speed is None:
                reason = (
                    f"Impossible travel: transactions {distance:.1f} km apart "
                    f"at the same time"
                )
            else:
                reason = (
                    f"Impossible travel: {distance:.1f} km in "
                    f"{hours * 60:.1f} minutes "
                    f"(implied speed {speed:,.0f} km/h, "
                    f"max allowed {max_speed:.0f} km/h)"
                )

            return {
                "rule": self.RULE_NAME,
                "triggered": True,
                "score": self.SCORE,
                "reason": reason,
                "details": geo,  # extra explainability, ignored by RiskScorer
            }

        return {
            "rule": self.RULE_NAME,
            "triggered": False,
            "score": 0,
            "reason": geo.get("reason", "No geographical anomaly detected"),
            "details": geo,
        }