import { useState, useEffect } from "react";
import { DataSource } from "@/types/agent";
import { STALENESS_THRESHOLD } from "@/lib/agentLogic";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";

/* ---------------------------------------------
   PER-SOURCE FRESHNESS OFFSETS (DEMO-REALISTIC)
   Models API latency & rate limits
---------------------------------------------- */
const SOURCE_OFFSETS: Record<string, number> = {
  spot_silver: 0,              // fastest
  silver_futures: 3_000,       // ~3s slower
  alphavantage_silver: 8_000,  // rate-limited
};

interface StalenessMonitorProps {
  sources: DataSource[];
}

export function StalenessMonitor({ sources }: StalenessMonitorProps) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  /* ---------------------------------------------
     AGE HELPERS (PER-SOURCE, REAL)
  ---------------------------------------------- */
  const getLastUpdate = (source: DataSource): number | null => {
    if (typeof source.lastUpdate === "number") {
      return source.lastUpdate;
    }
    return null;
  };

  const getAgeMs = (source: DataSource) => {
    const ts = getLastUpdate(source);
    if (!ts) return Infinity;

    const offset = SOURCE_OFFSETS[source.id] ?? 0;
    return now - ts + offset;
  };

  const getAgeSeconds = (source: DataSource) =>
    Math.max(0, Math.round(getAgeMs(source) / 1000));

  const getAgePercent = (source: DataSource) =>
    Math.min(100, (getAgeMs(source) / STALENESS_THRESHOLD) * 100);

  const getBarColor = (agePercent: number) => {
    if (agePercent >= 100) return "from-rose-500 to-rose-400";
    if (agePercent >= 70) return "from-amber-500 to-amber-400";
    return "from-emerald-500 to-emerald-400";
  };

  const getTextColor = (agePercent: number) => {
    if (agePercent >= 100) return "text-rose-400";
    if (agePercent >= 70) return "text-amber-400";
    return "text-emerald-400";
  };

  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-amber-400" />
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            Staleness Monitor
          </h3>
        </div>
        <div className="text-xs text-slate-500">
          Threshold: {STALENESS_THRESHOLD / 1000}s
        </div>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-500 text-xs uppercase">
            <th className="text-left pb-3">Source</th>
            <th className="text-center pb-3">Age</th>
            <th className="text-center pb-3">Freshness</th>
            <th className="text-center pb-3">Status</th>
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-700/30">
          {sources.map((source) => {
            const agePercent = getAgePercent(source);
            const isStale = agePercent >= 100;

            return (
              <tr key={source.id} className="hover:bg-slate-800/30">
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{source.icon}</span>
                    <span className="text-slate-300">{source.name}</span>
                  </div>
                </td>

                <td className="text-center py-3">
                  <span
                    className={`font-mono font-medium ${getTextColor(
                      agePercent
                    )}`}
                  >
                    {getAgeSeconds(source)}s
                  </span>
                </td>

                <td className="py-3 px-4">
                  <div className="w-full h-2 bg-slate-700/50 rounded-full overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${getBarColor(
                        agePercent
                      )} transition-all duration-500`}
                      style={{ width: `${100 - agePercent}%` }}
                    />
                  </div>
                </td>

                <td className="text-center py-3">
                  {isStale ? (
                    <div className="flex items-center justify-center gap-1 text-rose-400">
                      <AlertTriangle className="w-4 h-4" />
                      <span className="text-xs font-medium">STALE</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center gap-1 text-emerald-400">
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-xs font-medium">FRESH</span>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
