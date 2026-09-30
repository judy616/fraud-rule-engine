from abc import ABC, abstractmethod


class FraudRule(ABC):

    @abstractmethod
    def evaluate(self, transaction, history):
        """
        Evaluate a transaction against this fraud rule.

        Returns:
            A dictionary containing:
            - rule
            - triggered
            - score
            - reason
        """
        pass