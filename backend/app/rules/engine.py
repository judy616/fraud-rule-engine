from .base import FraudRule


class FraudEngine:

    def __init__(self, rules: list[FraudRule]):
        self.rules = rules

    def evaluate(self, transaction, history):
        results = []

        for rule in self.rules:
            result = rule.evaluate(transaction, history)
            results.append(result)

        return results