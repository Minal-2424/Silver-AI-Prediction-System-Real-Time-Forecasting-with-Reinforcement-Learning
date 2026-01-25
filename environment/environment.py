import time
from data_sources.silver_sources import get_silver_data_sources
from utils.logger import AILogger


class SilverMarketEnvironment:
    def __init__(self):
        """
        Real-time silver market environment.
        Tracks per-source freshness and fetch timing.
        """
        self.time_step = 0
        self.logger = AILogger(name="Environment")

        # source_name -> metadata
        self.sources = {}
        self.source_meta = {}

        self._refresh_sources(initial=True)

    # -------------------------------
    # Source Loading
    # -------------------------------
    def _refresh_sources(self, initial=False):
        now = time.time()
        new_sources = get_silver_data_sources()

        if not new_sources:
            self.logger.logger.warning("No live sources loaded")
            return

        for name, data in new_sources.items():
            previous = self.source_meta.get(name)

            # Detect whether source was actually refreshed
            was_updated = (
                initial
                or previous is None
                or data.get("value") != self.sources.get(name, {}).get("value")
            )

            self.sources[name] = data

            self.source_meta[name] = {
                "last_fetched": now if was_updated else previous["last_fetched"],
                "skipped": not was_updated,
                "freshness": data.get("freshness", 0.5),
                "reliability": data.get("reliability", 0.5),
            }

        self.logger.logger.info(
            f"ENV LOAD | Sources: {list(self.sources.keys())}"
        )

    # -------------------------------
    # Interface
    # -------------------------------
    def get_all_sources(self):
        """
        Merge live data + metadata (USED BY AGENT)
        """
        merged = {}

        for name, data in self.sources.items():
            meta = self.source_meta.get(name, {})
            merged[name] = {
                **data,
                **meta,
            }

        return merged

    def get_source_meta(self):
        """
        Used by backend API to expose freshness truth to frontend
        """
        return self.source_meta

    # -------------------------------
    # Dynamics
    # -------------------------------
    def step(self):
        """
        Refresh environment with live data
        """
        self.time_step += 1
        self._refresh_sources()

        self.logger.logger.info(
            f"ENV STEP | Timestep: {self.time_step}"
        )

    # -------------------------------
    # Reward Logic (SENTIMENT + MARKET AWARE)
    # -------------------------------
    def calculate_reward(self, source_name: str) -> float:
        if source_name not in self.sources:
            self.logger.logger.warning(
                f"REWARD | Unknown source requested: {source_name}"
            )
            return -1.0

        source = self.sources[source_name]
        meta = self.source_meta.get(source_name, {})

        avg_value = self._market_average_value()
        if avg_value <= 0:
            return -1.0

        freshness = meta.get("freshness", 0.5)
        reliability = meta.get("reliability", 0.5)
        cost = source.get("cost", 0.0)
        value = source.get("value", avg_value)

        sentiment = source.get("sentiment", 0.5)
        market_impact = source.get("market_impact", 0.5)

        quality = (
            freshness
            * reliability
            * (1 / (1 + abs(value - avg_value)))
        )

        sentiment_bonus = 0.2 * (sentiment - 0.5)
        market_bonus = 0.1 * market_impact

        reward = quality - cost + sentiment_bonus + market_bonus

        self.logger.logger.info(
            f"REWARD | {source_name} | "
            f"quality={quality:.3f} cost={cost:.2f} "
            f"sentiment={sentiment:.2f} market={market_impact:.2f} "
            f"reward={reward:.3f}"
        )

        return reward

    # -------------------------------
    # Helpers
    # -------------------------------
    def _market_average_value(self):
        values = [
            s.get("value")
            for s in self.sources.values()
            if isinstance(s.get("value"), (int, float))
        ]

        return sum(values) / len(values) if values else 0.0