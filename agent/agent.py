import random
import math

from utils.logger import AILogger
from agent.decision_policy import calculate_score
from learning.bandit import MultiArmedBandit


class DataCollectionAgent:
    def __init__(
        self,
        total_budget: float,
        epsilon: float = 0.2,
        sentiment_weight: float = 0.7,
        market_weight: float = 0.6,
    ):
        """
        Autonomous Data Collection Agent
        Rule-based + Learning + Sentiment + Market Impact aware
        """
        self.total_budget = total_budget
        self.remaining_budget = total_budget
        self.epsilon = epsilon
        self.sentiment_weight = sentiment_weight
        self.market_weight = market_weight

        self.bandit = MultiArmedBandit()
        self.logger = AILogger(name="DataCollectionAgent")
        self.total_decisions = 0

    # --------------------------------------------------
    # Evaluation
    # --------------------------------------------------
    def evaluate_source(self, source_name, state):
        freshness = state.get("freshness", 0.5)
        reliability = state.get("reliability", 0.5)
        cost = state.get("cost", 0.0)
        sentiment = state.get("sentiment", 0.5)
        market_impact = state.get("market_impact", 0.5)

        rule_score = calculate_score(
            freshness=freshness,
            reliability=reliability,
            cost=cost,
            remaining_budget=self.remaining_budget,
        )

        learned = self.bandit.get_estimated_value(source_name)
        pulls = self.bandit.get_count(source_name)

        confidence_bonus = (
            math.sqrt(math.log(self.total_decisions + 1) / (pulls + 1))
            if self.total_decisions > 0 else 0.0
        )

        final_score = (
            rule_score
            + learned
            + 0.5 * confidence_bonus
            + self.sentiment_weight * (sentiment - 0.5)
            + self.market_weight * (market_impact - 0.5)
        )

        return final_score

    # --------------------------------------------------
    # Decision Making (FAIL-SAFE)
    # --------------------------------------------------
    def select_best_source(self, environment):
        sources = environment.get_all_sources()

        if not sources:
            self.logger.log_error("No sources available")
            return None, 0.0

        self.total_decisions += 1

        # -------- Exploration --------
        if random.random() < self.epsilon:
            source = random.choice(list(sources.keys()))
            score = self.evaluate_source(source, sources[source])
            self.logger.log_decision(source, score, self.remaining_budget)
            self._decay_epsilon()
            return source, score

        # -------- Exploitation --------
        best_source = None
        best_score = float("-inf")

        for name, state in sources.items():
            score = self.evaluate_source(name, state)

            if score > best_score:
                best_score = score
                best_source = name

        # 🔥 HARD FAIL-SAFE (CRITICAL FIX)
        if best_source is None or best_score <= 0:
            fallback = max(
                sources.items(),
                key=lambda s: (
                    s[1].get("freshness", 0.5),
                    s[1].get("reliability", 0.5)
                )
            )[0]

            self.logger.logger.warning(
                f"FALLBACK | No positive scores. Using safest source: {fallback}"
            )

            return fallback, 0.01  # minimal non-zero score

        self.logger.log_decision(best_source, best_score, self.remaining_budget)
        self._decay_epsilon()
        return best_source, best_score

    # --------------------------------------------------
    # Learning
    # --------------------------------------------------
    def update_learning(self, source_name, reward):
        if source_name is None:
            return

        old = self.bandit.get_estimated_value(source_name)
        self.bandit.update(source_name, reward)
        new = self.bandit.get_estimated_value(source_name)

        self.logger.log_reward(source_name, reward)
        self.logger.log_learning(source_name, old, new)

    # --------------------------------------------------
    # Budget
    # --------------------------------------------------
    def deduct_cost(self, cost):
        old = self.remaining_budget
        self.remaining_budget = max(0.0, self.remaining_budget - cost)
        self.logger.log_budget(old, self.remaining_budget)

    # --------------------------------------------------
    # Exploration Control
    # --------------------------------------------------
    def _decay_epsilon(self):
        self.epsilon = max(0.05, self.epsilon * 0.995)
