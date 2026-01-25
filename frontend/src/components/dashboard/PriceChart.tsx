import { PriceData } from "@/types/agent";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from "recharts";

interface PriceChartProps {
  priceHistory: PriceData[];
  currentPrice: number | null;
}

export function PriceChart({ priceHistory, currentPrice }: PriceChartProps) {
  if (!priceHistory || priceHistory.length < 2 || currentPrice === null) {
    return (
      <div className="rounded-2xl bg-slate-900 border border-slate-700 p-6 text-slate-500 text-center h-[250px] flex items-center justify-center">
        Collecting price data…
      </div>
    );
  }

  /* -----------------------------
     CHART DATA
  ------------------------------ */
  const chartData = priceHistory.map(p => {
    const predicted = p.predicted ?? p.price;
    const spread = Math.max(
      Math.abs((p.confidenceHigh ?? predicted) - predicted),
      predicted * 0.001 // 0.1% minimum
    );

    return {
      time: new Date(p.timestamp).toLocaleTimeString([], {
        minute: "2-digit",
        second: "2-digit"
      }),
      price: p.price,
      predicted,
      confidenceLow: predicted - spread,
      confidenceHigh: predicted + spread
    };
  });

  /* -----------------------------
     🔑 Y-AXIS: PRICE-CENTERED
  ------------------------------ */
  const RANGE_PERCENT = 0.006; // ±0.6%
  const minY = currentPrice * (1 - RANGE_PERCENT);
  const maxY = currentPrice * (1 + RANGE_PERCENT);

  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Price History & Predictions
        </h3>
      </div>

      <div className="h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>

              <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>

              <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#d946ef" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#d946ef" stopOpacity={0.05} />
              </linearGradient>
            </defs>

            <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#64748b" />

            <YAxis
              domain={[minY, maxY]}
              tickFormatter={(v) => `$${v.toFixed(2)}`}
              stroke="#64748b"
            />

            <Tooltip
              formatter={(v: number) => `$${v.toFixed(2)}`}
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #334155",
                borderRadius: 8
              }}
            />

            <ReferenceLine
              y={currentPrice}
              stroke="#22d3ee"
              strokeDasharray="4 4"
              strokeOpacity={0.6}
            />

            {/* Confidence */}
            <Area
              dataKey="confidenceHigh"
              stroke="none"
              fill="url(#confGrad)"
            />
            <Area
              dataKey="confidenceLow"
              stroke="none"
              fill="#020617"
            />

            {/* Predicted */}
            <Area
              dataKey="predicted"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="url(#predGrad)"
              strokeDasharray="5 5"
            />

            {/* Actual */}
            <Area
              dataKey="price"
              stroke="#06b6d4"
              strokeWidth={2}
              fill="url(#priceGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
