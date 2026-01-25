import { useEffect, useState } from "react";
import {
  DataSource,
  AgentDecision,
  AgentState,
  PriceData,
} from "@/types/agent";
import { getSilverPrediction } from "@/services/api";

/* ---------------------------------------------
   KNOWN SOURCES
---------------------------------------------- */
const KNOWN_SOURCES: DataSource[] = [
  {
    id: "spot_silver",
    name: "Spot Silver",
    icon: "🪙",
    qualityScore: 92,
    freshnessScore: 95,
    reliabilityScore: 98,
    status: "active",
    lastUpdate: Date.now(),
    callsUsed: 0,
    callsAllocated: 1000,
    priorityScore: 0,
    isSelected: false,
  },
  {
    id: "silver_futures",
    name: "Silver Futures",
    icon: "📈",
    qualityScore: 85,
    freshnessScore: 80,
    reliabilityScore: 90,
    status: "active",
    lastUpdate: Date.now(),
    callsUsed: 0,
    callsAllocated: 1000,
    priorityScore: 0,
    isSelected: false,
  },
  {
    id: "alphavantage_silver",
    name: "Alpha Vantage Silver",
    icon: "🏦",
    qualityScore: 80,
    freshnessScore: 75,
    reliabilityScore: 90,
    status: "active",
    lastUpdate: Date.now(),
    callsUsed: 0,
    callsAllocated: 1000,
    priorityScore: 0,
    isSelected: false,
  },
];

const POLL_INTERVAL =30; // seconds

export function useAutonomousAgent() {
  const [sources, setSources] = useState<DataSource[]>(KNOWN_SOURCES);
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [priceHistory, setPriceHistory] = useState<PriceData[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);

  const [agentState, setAgentState] = useState<AgentState>({
    mode: "adaptive",
    isActive: true,
    volatility: "medium",
    nextCollectionIn: POLL_INTERVAL,
    totalBudget: 1000,
    budgetUsed: 0,
    resourcesSaved: 0,
    collectionsToday: 0,
    skippedToday: 0,
  });

  /* ---------------------------------------------
     COUNTDOWN TIMER
  ---------------------------------------------- */
  useEffect(() => {
    const timer = setInterval(() => {
      setAgentState(prev => ({
        ...prev,
        nextCollectionIn: Math.max(0, prev.nextCollectionIn - 1),
      }));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  /* ---------------------------------------------
     BACKEND POLLING
  ---------------------------------------------- */
  useEffect(() => {
    const syncWithBackend = async () => {
      try {
        const data = await getSilverPrediction();

        /* RESET TIMER */
        setAgentState(prev => ({
          ...prev,
          nextCollectionIn: POLL_INTERVAL,
        }));

        /* PRICE + HISTORY */
        if (typeof data.current_price === "number") {
          setCurrentPrice(data.current_price);

          // ✅ REALISTIC CONFIDENCE BAND (CRITICAL FIX)
          const confidenceWidth =
            data.predicted_price *
            0.005 *
            (data.confidence ?? 0.5); // ±0.25–0.5%

          setPriceHistory(prev =>
            [
              ...prev,
              {
                timestamp: data.timestamp * 1000,
                price: data.current_price,
                predicted: data.predicted_price,
                confidenceLow:
                  data.predicted_price - confidenceWidth,
                confidenceHigh:
                  data.predicted_price + confidenceWidth,
              },
            ].slice(-60)
          );
        }

        /* AGENT STATE */
        setAgentState(prev => ({
          ...prev,
          volatility: data.volatility ?? prev.volatility,
          budgetUsed: prev.budgetUsed + (data.skipped ? 0 : 1),
          resourcesSaved:
            prev.resourcesSaved + (data.resources_saved ?? 0),
          collectionsToday: data.skipped
            ? prev.collectionsToday
            : prev.collectionsToday + 1,
          skippedToday: data.skipped
            ? prev.skippedToday + 1
            : prev.skippedToday,
        }));

        /* SOURCE SELECTION (ONLY ONE SELECTED) */
        setSources(prev =>
          prev.map(source => {
            const isSelected =
              source.id === data.selected_source;

            return {
              ...source,
              isSelected,
              status: isSelected
                ? data.skipped
                  ? "stale"
                  : "active"
                : "active",
              freshnessScore: isSelected
                ? Math.round((data.freshness ?? 0.9) * 100)
                : source.freshnessScore,
              priorityScore: isSelected
                ? data.decision_score
                : source.priorityScore,
              callsUsed:
                isSelected && !data.skipped
                  ? source.callsUsed + 1
                  : source.callsUsed,
              lastUpdate: isSelected
                ? Date.now()
                : source.lastUpdate,
            };
          })
        );

        /* ACTIVITY LOG */
        const decision: AgentDecision = {
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          type: data.skipped ? "skip" : "collect",
          sourceId: data.selected_source,
          sourceName: data.selected_source,
          reason: data.skipped
            ? "Skipped (freshness window)"
            : "Collected real data",
          resourcesSaved: data.resources_saved ?? 0,
        };

        setDecisions(prev => [decision, ...prev].slice(0, 50));
      } catch (err) {
        console.error("Backend sync failed:", err);
      }
    };

    syncWithBackend();
    const interval = setInterval(
      syncWithBackend,
      POLL_INTERVAL * 1000
    );

    return () => clearInterval(interval);
  }, []);

  return {
    sources,
    decisions,
    agentState,
    priceHistory,
    currentPrice,
  };
}
