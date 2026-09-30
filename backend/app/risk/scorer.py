class RiskScorer:

    def calculate(self, results):

        score = sum(
            result["score"]
            for result in results
            if result["triggered"]
        )

        # Keep score between 0 and 100
        score = min(score, 100)

        if score >= 70:
            level = "CRITICAL"
        elif score >= 50:
            level = "HIGH"
        elif score >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"

        reasons = [
            result["reason"]
            for result in results
            if result["triggered"]
        ]

        triggered_rules = [
            result["rule"]
            for result in results
            if result["triggered"]
        ]

        return {
            "score": score,
            "level": level,
            "triggered_rules": triggered_rules,
            "reasons": reasons
        }